from fastapi import APIRouter, Depends, HTTPException
from models.auth import User
from models.common import get_session
from models.friendship import Friendship, FriendshipStatus
from models.music import Like, Play
from routes.deps import current_user
from services.cache import cache
from services.friendship import (
    accept_friendship as svc_accept_friendship,
)
from services.friendship import (
    decline_friendship as svc_decline_friendship,
)
from services.friendship import (
    request_friendship as svc_request_friendship,
)
from services.friendship import (
    unfriend as svc_unfriend,
)
from sqlalchemy import or_
from sqlmodel import Session, select

router = APIRouter(prefix="/friendship")


def _get_user_by_identifier(session: Session, ident: str) -> User | None:
    # Try by username first (non-null only), then by id
    user = session.exec(select(User).where(User.username == ident)).first()
    if user:
        return user
    return session.get(User, ident)


@router.get("/status/{identifier}")
async def friendship_status(
    identifier: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    """Return the relationship status between the current user and the target user.
    Possible statuses: none, self, friends, pending_outgoing, pending_incoming
    """
    target = _get_user_by_identifier(session, identifier)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == target.id:
        return {"status": "self"}

    low, high = Friendship.canonical_pair(user.id, target.id)
    friendship = session.exec(
        select(Friendship).where(
            Friendship.user_low_id == low, Friendship.user_high_id == high
        )
    ).first()

    if not friendship:
        return {"status": "none"}

    if friendship.status == FriendshipStatus.accepted:
        return {"status": "friends"}

    if friendship.status == FriendshipStatus.pending:
        if friendship.requested_by_id == user.id:
            return {"status": "pending_outgoing"}
        else:
            return {"status": "pending_incoming"}

    # declined/blocked treated as none for now
    return {"status": "none"}


@router.get("/pending")
async def pending_requests(
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    # Incoming requests to current_user
    rows: list[Friendship] = session.exec(
        select(Friendship).where(Friendship.status == FriendshipStatus.pending)
    ).all()

    pending_list = []
    for fr in rows:
        if user.id not in (fr.user_low_id, fr.user_high_id):
            continue
        if fr.requested_by_id == user.id:
            # Outgoing, skip for this endpoint
            continue
        other_id = fr.user_high_id if user.id == fr.user_low_id else fr.user_low_id
        other = session.get(User, other_id)
        if not other:
            continue
        pending_list.append(
            {
                "user": {
                    "id": other.id,
                    "name": other.name,
                    "username": other.username,
                    "picture": other.picture,
                },
                "requested_at": fr.requested_at.isoformat(),
            }
        )

    # Sort newest first
    pending_list.sort(key=lambda x: x["requested_at"], reverse=True)

    return {"pending": pending_list}


@router.post("/request/{identifier}")
async def send_friend_request(
    identifier: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    recipient = _get_user_by_identifier(session, identifier)
    if not recipient:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        fr = svc_request_friendship(session, requester=user, recipient=recipient)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "friendship": {
            "status": fr.status,
            "requested_by_id": fr.requested_by_id,
            "requested_at": fr.requested_at.isoformat(),
        }
    }


@router.post("/accept/{identifier}")
async def accept_request(
    identifier: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    other = _get_user_by_identifier(session, identifier)
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        fr = svc_accept_friendship(session, requester=user, recipient=other)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "friendship": {
            "status": fr.status,
            "responded_at": fr.responded_at.isoformat() if fr.responded_at else None,
        }
    }


@router.post("/decline/{identifier}")
async def decline_request(
    identifier: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    other = _get_user_by_identifier(session, identifier)
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        fr = svc_decline_friendship(session, requester=user, recipient=other)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "friendship": {
            "status": fr.status,
            "responded_at": fr.responded_at.isoformat() if fr.responded_at else None,
        }
    }


@router.delete("/{identifier}")
async def unfriend(
    identifier: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    other = _get_user_by_identifier(session, identifier)
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        svc_unfriend(session, user_id=user.id, other_id=other.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Unfriended"}


def get_friends(session: Session, user: User) -> list[User]:
    friendships = session.exec(
        select(Friendship).where(
            Friendship.status == FriendshipStatus.accepted,
            or_(Friendship.user_low_id == user.id, Friendship.user_high_id == user.id),
        )
    ).all()
    friends_ids = [
        fr.user_high_id if user.id == fr.user_low_id else fr.user_low_id
        for fr in friendships
    ]
    return list(session.exec(select(User).where(User.id.in_(friends_ids))).all())


@router.get("/list")
async def list_friends_and_pending(
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    from sqlalchemy import func, or_ as sa_or, and_ as sa_and
    from models.auth import User
    from models.friendship import Friendship, FriendshipStatus

    # Subquery for last_play
    subquery_last_play = (
        select(func.max(Play.date))
        .where(Play.user_id == User.id, Friendship.status == "accepted")
        .scalar_subquery()
    )
    subquery_last_play_track_id = (
        select(Play.track_id)
        .where(Play.user_id == User.id, Friendship.status == "accepted")
        .order_by(Play.date.desc())
        .limit(1)
        .scalar_subquery()
    )

    query = (
        select(
            User.id,
            User.username,
            User.picture,
            Friendship.status,
            Friendship.requested_by_id,
            func.count(Like.track_id).label("likes"),
            subquery_last_play.label("last_play"),
            subquery_last_play_track_id.label("last_play_track_id"),
        )
        .join(
            Friendship,
            sa_or(
                Friendship.user_low_id == User.id,
                Friendship.user_high_id == User.id,
            ),
        )
        .outerjoin(
            Like,
            sa_and(
                Like.user_id == User.id,
                Friendship.status == FriendshipStatus.accepted,
            ),
        )
        .where(
            sa_and(
                sa_or(
                    Friendship.user_low_id == user.id,
                    Friendship.user_high_id == user.id,
                ),
                Friendship.status.in_(
                    [
                        FriendshipStatus.accepted,
                        FriendshipStatus.pending,
                    ]
                ),
                User.id != user.id,
            ),
        )
        .group_by(
            User.id,
            User.username,
            User.picture,
            Friendship.status,
            Friendship.requested_by_id,
        )
    )

    friends = []
    for row in session.exec(query):
        friendship = {
            "id": row.id,
            "username": row.username,
            "picture": row.picture,
        }
        if row.status == FriendshipStatus.pending:
            friendship["status"] = (
                "requested" if row.requested_by_id == user.id else "pending"
            )
        elif row.status == FriendshipStatus.accepted and row.last_play:
            last_play = Play(user_id=row.id, track_id=row.last_play_track_id)
            enriched_tracks = cache.enrich_tracks(
                [last_play], "date", User(id=row.id), session
            )

            friendship.update(
                {
                    "likes": row.likes,
                    "last_play": enriched_tracks[0],
                    "status": row.status,
                }
            )
        friends.append(friendship)

    return {"friends": friends}
