from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from models.auth import User
from models.common import get_session
from models.friendship import Friendship, FriendshipStatus
from routes.deps import get_current_user
from services.friendship import (
    request_friendship as svc_request_friendship,
    accept_friendship as svc_accept_friendship,
    decline_friendship as svc_decline_friendship,
    unfriend as svc_unfriend,
)

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
    current_user: User | None = Depends(get_current_user),
):
    """Return the relationship status between the current user and the target user.
    Possible statuses: none, self, friends, pending_outgoing, pending_incoming
    """
    target = _get_user_by_identifier(session, identifier)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if not current_user:
        return {"status": "none"}

    if current_user.id == target.id:
        return {"status": "self"}

    low, high = Friendship.canonical_pair(current_user.id, target.id)
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
        if friendship.requested_by_id == current_user.id:
            return {"status": "pending_outgoing"}
        else:
            return {"status": "pending_incoming"}

    # declined/blocked treated as none for now
    return {"status": "none"}


@router.get("/pending")
async def pending_requests(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Incoming requests to current_user
    rows: List[Friendship] = session.exec(
        select(Friendship).where(Friendship.status == FriendshipStatus.pending)
    ).all()

    pending_list = []
    for fr in rows:
        if current_user.id not in (fr.user_low_id, fr.user_high_id):
            continue
        if fr.requested_by_id == current_user.id:
            # Outgoing, skip for this endpoint
            continue
        other_id = (
            fr.user_high_id if current_user.id == fr.user_low_id else fr.user_low_id
        )
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
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    recipient = _get_user_by_identifier(session, identifier)
    if not recipient:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        fr = svc_request_friendship(
            session, requester=current_user, recipient=recipient
        )
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
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    other = _get_user_by_identifier(session, identifier)
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        fr = svc_accept_friendship(session, requester=current_user, recipient=other)
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
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    other = _get_user_by_identifier(session, identifier)
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        fr = svc_decline_friendship(session, requester=current_user, recipient=other)
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
    current_user: User | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    other = _get_user_by_identifier(session, identifier)
    if not other:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        svc_unfriend(session, user_id=current_user.id, other_id=other.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Unfriended"}
