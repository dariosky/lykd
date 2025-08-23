import datetime

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
from services.cache import cache
from services.spotify import get_spotify_client, Spotify

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
    else:
        results = cache.enrich_tracks(items, field, current_user, session)

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


@router.get("/likes")
async def user_likes(
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
    # TODO: Fix - seeing duplicates in likes
    return get_page(
        Model=Like,
        session=session,
        current_user=current_user,
        limit=limit,
        before=before,
        include_me=include_me,
        user=user,
        q=q,
        show_ignored=show_ignored,
    )


@router.post("/like")
async def toggle_like(
    payload: dict,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    track_id = payload.get("track_id")
    liked = payload.get("liked")
    if not isinstance(track_id, str) or not isinstance(liked, bool):
        raise HTTPException(status_code=400, detail="Invalid payload")

    existing_like = session.get(Like, (current_user.id, track_id))
    now = datetime.datetime.now(datetime.timezone.utc)
    if liked:
        if not existing_like:
            session.add(Like(user_id=current_user.id, track_id=track_id, date=now))
            session.commit()
            if current_user.id in cache.likes_cache:  # manually update the cache
                cache.likes_cache[current_user.id].add(track_id)
        await spotify.set_liked_track(
            user=current_user,
            db_session=session,
            track_id=track_id,
            liked=True,
            liked_at=now,
        )
        return {"status": "ok", "liked": True}
    else:
        if existing_like:
            session.delete(existing_like)
            session.commit()
            if current_user.id in cache.likes_cache:  # manually update the cache
                cache.likes_cache[current_user.id].remove(track_id)
        await spotify.set_liked_track(
            user=current_user, db_session=session, track_id=track_id, liked=False
        )
        return {"status": "ok", "liked": False}
