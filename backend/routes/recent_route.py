from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from models.auth import User
from models.common import get_session
from models.friendship import Friendship, FriendshipStatus
from models.music import Play, Track, TrackArtist, Artist, Album
from routes.deps import get_current_user

router = APIRouter()


def _parse_before(before: Optional[str]) -> Optional[datetime]:
    if not before:
        return None
    try:
        # Expect ISO 8601 string
        return datetime.fromisoformat(before.replace("Z", "+00:00"))
    except Exception:
        return None


def _friends_ids(session: Session, me_id: str) -> List[str]:
    rows = session.exec(
        select(Friendship).where(Friendship.status == FriendshipStatus.accepted)
    ).all()
    out: List[str] = []
    for fr in rows:
        if me_id == fr.user_low_id:
            out.append(fr.user_high_id)
        elif me_id == fr.user_high_id:
            out.append(fr.user_low_id)
    return out


@router.get("/recent")
async def recent_activity(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    before: Optional[str] = None,
    include_me: bool = True,
    user: Optional[str] = None,  # username or id to filter to a specific user
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    before_dt = _parse_before(before)
    if before and not before_dt:
        raise HTTPException(status_code=400, detail="Invalid 'before' parameter")

    # Determine allowed user ids (me + friends)
    friends = _friends_ids(session, current_user.id)
    allowed_ids = set(friends + [current_user.id])

    # If a user filter is provided, resolve it and restrict to just that user
    filter_user_id: Optional[str] = None
    if user:
        # try username first, else treat as id
        target = session.exec(select(User).where(User.username == user)).first()
        if not target:
            target = session.get(User, user)
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        filter_user_id = target.id
        if filter_user_id not in allowed_ids:
            # You can only filter to yourself or a friend
            raise HTTPException(status_code=403, detail="Forbidden user filter")

    q = select(Play).order_by(Play.date.desc())
    if before_dt:
        q = q.where(Play.date < before_dt)

    # Restrict to allowed users
    if filter_user_id:
        q = q.where(Play.user_id == filter_user_id)
    else:
        q = q.where(Play.user_id.in_(list(allowed_ids)))
        if not include_me:
            q = q.where(Play.user_id != current_user.id)

    q = q.limit(limit)
    plays: List[Play] = session.exec(q).all()

    if not plays:
        return {"items": [], "next_before": None}

    # Gather related entities in bulk
    user_ids = list({p.user_id for p in plays})
    track_ids = list({p.track_id for p in plays})

    users_map: Dict[str, User] = {
        u.id: u for u in session.exec(select(User).where(User.id.in_(user_ids))).all()
    }

    tracks: List[Track] = session.exec(
        select(Track).where(Track.id.in_(track_ids))
    ).all()
    tracks_map: Dict[str, Track] = {t.id: t for t in tracks}

    # Album info
    album_ids = [t.album_id for t in tracks if t.album_id]
    albums_map: Dict[str, Album] = {
        a.id: a
        for a in session.exec(select(Album).where(Album.id.in_(album_ids))).all()
    }

    # Artists per track
    ta_rows = session.exec(
        select(TrackArtist).where(TrackArtist.track_id.in_(track_ids))
    ).all()
    artist_ids = list({ta.artist_id for ta in ta_rows})
    artists_map: Dict[str, Artist] = {
        a.id: a
        for a in session.exec(select(Artist).where(Artist.id.in_(artist_ids))).all()
    }
    track_artists: Dict[str, List[str]] = {}
    for ta in ta_rows:
        track_artists.setdefault(ta.track_id, []).append(
            artists_map.get(ta.artist_id).name
            if artists_map.get(ta.artist_id)
            else None
        )
    # Clean None
    for k, v in list(track_artists.items()):
        track_artists[k] = [x for x in v if x]

    # Build items
    items: List[Dict[str, Any]] = []
    for p in plays:
        u = users_map.get(p.user_id)
        t = tracks_map.get(p.track_id)
        album = albums_map.get(t.album_id) if (t and t.album_id) else None
        items.append(
            {
                "user": {
                    "id": u.id if u else p.user_id,
                    "name": u.name if u else None,
                    "username": u.username if u else None,
                    "picture": u.picture if u else None,
                },
                "track": {
                    "id": t.id if t else p.track_id,
                    "title": t.title if t else None,
                    "duration": t.duration if t else None,
                    "album": (
                        {
                            "id": album.id,
                            "name": album.name,
                            "picture": album.picture,
                            "release_date": album.release_date.isoformat()
                            if album and album.release_date
                            else None,
                        }
                        if album
                        else None
                    ),
                    "artists": track_artists.get(p.track_id, []),
                },
                "played_at": p.date.isoformat(),
                "context_uri": p.context_uri,
            }
        )

    next_before = items[-1]["played_at"] if len(items) == limit else None
    return {"items": items, "next_before": next_before}
