from typing import Any, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.sql import and_, exists, or_
from sqlmodel import Session, select

from models.auth import User
from models.common import get_session
from models.music import (
    Album,
    Artist,
    GlobalIgnoredArtist,
    GlobalIgnoredTrack,
    IgnoredArtist,
    IgnoredTrack,
    Play,
    Track,
    TrackArtist,
    Like,
)
from routes.deps import current_user, parse_ui_date, date_range_for_token
from routes.friendship import get_friends

router = APIRouter()


def get_page(
    Model: type[Play] | type[Like],
    session: Session,
    current_user: User | None,
    field: str = "date",
    limit: int = Query(20, ge=1, le=100),
    before: str | None = None,
    include_me: bool = True,
    user: str | None = None,  # target username
    q: str | None = None,  # free-search
    show_ignored: bool = False,
):
    sort_field = getattr(Model, field)
    query = select(Model).order_by(sort_field.desc())

    before_dt = parse_ui_date(before)
    if before and not before_dt:
        raise HTTPException(status_code=400, detail="Invalid 'before' parameter")

    # Determine allowed user ids (me + friends)
    friends = get_friends(session, current_user)
    friends_ids = {friend.id for friend in friends}
    allowed_ids = friends_ids | {current_user.id}

    # Resolve user filter
    filter_user_id: str | None = None
    if user:
        target = session.exec(select(User).where(User.username == user)).first()
        if not target:
            target = session.get(User, user)  # get by id
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        filter_user_id = target.id
        if filter_user_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="Forbidden user filter")

    if before_dt:
        query = query.where(sort_field < before_dt)

    # Restrict to allowed users
    if filter_user_id:
        query = query.where(Model.user_id == filter_user_id)
    else:
        if include_me:
            query = query.where(Model.user_id.in_(list(allowed_ids)))
        else:
            # friends only (avoid negative predicate for better index usage)
            if friends_ids:
                query = query.where(Model.user_id.in_(friends_ids))
            else:
                # No friends, force empty result fast
                query = query.where(Model.user_id == "__none__")

    # Exclude items ignored globally or by current user (by track or by any artist)
    if not show_ignored:
        ignore_global_track = exists(
            select(GlobalIgnoredTrack).where(
                GlobalIgnoredTrack.track_id == Model.track_id
            )
        )
        ignore_global_artist = exists(
            select(GlobalIgnoredArtist)
            .join(TrackArtist, TrackArtist.artist_id == GlobalIgnoredArtist.artist_id)
            .where(TrackArtist.track_id == Model.track_id)
        )
        ignore_user_track = exists(
            select(IgnoredTrack).where(
                IgnoredTrack.user_id == current_user.id,
                IgnoredTrack.track_id == Model.track_id,
            )
        )
        ignore_user_artist = exists(
            select(IgnoredArtist)
            .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
            .where(
                IgnoredArtist.user_id == current_user.id,
                TrackArtist.track_id == Model.track_id,
            )
        )
        query = query.where(
            ~ignore_global_track,
            ~ignore_global_artist,
            ~ignore_user_track,
            ~ignore_user_artist,
        )

    if q:
        # Split by whitespace, AND across terms
        tokens = [t for t in q.strip().split() if t]
        for tok in tokens:
            # For each token, match any of the allowed fields (OR)
            date_rng = date_range_for_token(tok)
            if date_rng:
                term_clause = and_(sort_field >= date_rng[0], sort_field < date_rng[1])
                query = query.where(term_clause)
            else:
                like = f"%{tok}%"
                # track title
                track_title_clause = exists(
                    select(Track.id).where(
                        Track.id == Model.track_id, Track.title.ilike(like)
                    )
                )
                # album name
                album_clause = exists(
                    select(Album.id)
                    .join(Track, Track.album_id == Album.id)
                    .where(Track.id == Model.track_id, Album.name.ilike(like))
                )
                # artist name
                artist_clause = exists(
                    select(Artist.id)
                    .join(TrackArtist, TrackArtist.artist_id == Artist.id)
                    .where(
                        TrackArtist.track_id == Model.track_id, Artist.name.ilike(like)
                    )
                )
                # user.name or username
                user_clause = exists(
                    select(User.id).where(
                        User.id == Model.user_id,
                        or_(User.name.ilike(like), User.username.ilike(like)),
                    )
                )
                query = query.where(
                    or_(track_title_clause, album_clause, artist_clause, user_clause)
                )

    query = query.limit(limit)
    items: list[Model] = session.exec(query).all()

    if not items:
        return {"items": [], "next_before": None}

    # Gather related entities in bulk
    track_ids = {p.track_id for p in items}

    users_map: dict[str, User] = {
        current_user.id: current_user,
        **{u.id: u for u in friends},
    }

    tracks: Sequence[Track] = session.exec(
        select(Track).where(Track.id.in_(track_ids))
    ).all()
    tracks_map: dict[str, Track] = {t.id: t for t in tracks}

    # Album info
    album_ids = {t.album_id for t in tracks if t.album_id}
    albums_map: dict[str, Album] = {
        a.id: a
        for a in session.exec(select(Album).where(Album.id.in_(album_ids))).all()
    }

    # Artists per track
    ta_rows = session.exec(
        select(TrackArtist).where(TrackArtist.track_id.in_(track_ids))
    ).all()
    artist_ids = list({ta.artist_id for ta in ta_rows})
    artists_map: dict[str, Artist] = {
        a.id: a
        for a in session.exec(select(Artist).where(Artist.id.in_(artist_ids))).all()
    }
    track_artists: dict[str, list[str]] = {}
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
    results: list[dict[str, Any]] = []
    for p in items:
        u = users_map.get(p.user_id)
        t = tracks_map.get(p.track_id)
        album = albums_map.get(t.album_id) if (t and t.album_id) else None
        results.append(
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
                field: getattr(p, field).isoformat(),
                "context_uri": p.context_uri,
            }
        )

    next_before = getattr(items[-1], field) if len(items) == limit else None
    return {"items": results, "next_before": next_before}


@router.get("/recent")
async def recent_activity(
    session: Session = Depends(get_session),
    current_user: User | None = Depends(current_user),
    limit: int = Query(20, ge=1, le=100),
    before: str | None = None,
    include_me: bool = True,
    user: str | None = None,  # target username
    q: str | None = None,  # free-search
    show_ignored: bool = Query(False, description="Include ignored tracks and artists"),
):
    # Base query
    return get_page(
        Model=Play,
        session=session,
        current_user=current_user,
        limit=limit,
        before=before,
        include_me=include_me,
        user=user,
        q=q,
        show_ignored=show_ignored,
    )
