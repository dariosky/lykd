from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, exists
from sqlmodel import Session, select

from models.auth import User
from models.music import (
    Play,
    Like,
    Track,
    TrackArtist,
    Artist,
    Album,
    IgnoredTrack,
    IgnoredArtist,
    GlobalIgnoredTrack,
    GlobalIgnoredArtist,
)
from models.common import get_session
from routes.deps import get_current_user
from routes.friendship_route import get_friends
from services.cache import cache

router = APIRouter()


# Query builders (reusable in tests)
def build_total_stmt(
    Model: type[Play | Like], user_id: str, viewer_id: str | None = None
):
    if viewer_id is None:
        viewer_id = user_id
    return (
        select(func.count())
        .select_from(Model)
        .where(
            Model.user_id == user_id,
            ~exists(
                select(GlobalIgnoredTrack).where(
                    GlobalIgnoredTrack.track_id == Model.track_id
                )
            ),
            ~exists(
                select(GlobalIgnoredArtist)
                .join(
                    TrackArtist, TrackArtist.artist_id == GlobalIgnoredArtist.artist_id
                )
                .where(TrackArtist.track_id == Model.track_id)
            ),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == viewer_id,
                    IgnoredTrack.track_id == Model.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == viewer_id,
                    TrackArtist.track_id == Model.track_id,
                )
            ),
        )
    )


def build_total_listen_sec_stmt(user_id: str, viewer_id: str | None = None):
    if viewer_id is None:
        viewer_id = user_id
    return (
        select(func.coalesce(func.sum(Track.duration / 1000), 0))
        .select_from(Play)
        .join(Track, Track.id == Play.track_id)
        .where(
            Play.user_id == user_id,
            ~exists(
                select(GlobalIgnoredTrack).where(
                    GlobalIgnoredTrack.track_id == Play.track_id
                )
            ),
            ~exists(
                select(GlobalIgnoredArtist)
                .join(
                    TrackArtist, TrackArtist.artist_id == GlobalIgnoredArtist.artist_id
                )
                .where(TrackArtist.track_id == Play.track_id)
            ),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == viewer_id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == viewer_id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
    )


def build_monthly_listen_sec_stmt(
    user_id: str, cutoff: datetime, viewer_id: str | None = None
):
    if viewer_id is None:
        viewer_id = user_id
    return (
        select(func.coalesce(func.sum(Track.duration / 1000), 0))
        .select_from(Play)
        .join(Track, Track.id == Play.track_id)
        .where(
            Play.user_id == user_id,
            Play.date >= cutoff,
            ~exists(
                select(GlobalIgnoredTrack).where(
                    GlobalIgnoredTrack.track_id == Play.track_id
                )
            ),
            ~exists(
                select(GlobalIgnoredArtist)
                .join(
                    TrackArtist, TrackArtist.artist_id == GlobalIgnoredArtist.artist_id
                )
                .where(TrackArtist.track_id == Play.track_id)
            ),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == viewer_id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == viewer_id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
    )


def build_top_tracks_last_30_stmt(
    user_id: str, cutoff: datetime, viewer_id: str | None = None
):
    if viewer_id is None:
        viewer_id = user_id
    return (
        select(Play.track_id, func.count().label("cnt"))
        .where(
            Play.user_id == user_id,
            Play.date >= cutoff,
            ~exists(
                select(GlobalIgnoredTrack).where(
                    GlobalIgnoredTrack.track_id == Play.track_id
                )
            ),
            ~exists(
                select(GlobalIgnoredArtist)
                .join(
                    TrackArtist, TrackArtist.artist_id == GlobalIgnoredArtist.artist_id
                )
                .where(TrackArtist.track_id == Play.track_id)
            ),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == viewer_id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == viewer_id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
        .group_by(Play.track_id)
        .order_by(func.count().desc())
        .limit(5)
    )


def build_top_tracks_all_time_stmt(user_id: str, viewer_id: str | None = None):
    if viewer_id is None:
        viewer_id = user_id
    return (
        select(Play.track_id, func.count().label("cnt"))
        .where(
            Play.user_id == user_id,
            ~exists(
                select(GlobalIgnoredTrack).where(
                    GlobalIgnoredTrack.track_id == Play.track_id
                )
            ),
            ~exists(
                select(GlobalIgnoredArtist)
                .join(
                    TrackArtist, TrackArtist.artist_id == GlobalIgnoredArtist.artist_id
                )
                .where(TrackArtist.track_id == Play.track_id)
            ),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == viewer_id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == viewer_id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
        .group_by(Play.track_id)
        .order_by(func.count().desc())
        .limit(5)
    )


def build_top_artists_stmt(user_id: str, viewer_id: str | None = None):
    if viewer_id is None:
        viewer_id = user_id
    return (
        select(Artist.id, Artist.name, func.count().label("cnt"))
        .select_from(Play)
        .join(Track, Track.id == Play.track_id)
        .join(TrackArtist, TrackArtist.track_id == Track.id)
        .join(Artist, Artist.id == TrackArtist.artist_id)
        .where(
            Play.user_id == user_id,
            ~exists(
                select(GlobalIgnoredTrack).where(
                    GlobalIgnoredTrack.track_id == Play.track_id
                )
            ),
            ~exists(
                select(GlobalIgnoredArtist).where(
                    GlobalIgnoredArtist.artist_id == TrackArtist.artist_id
                )
            ),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == viewer_id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist).where(
                    IgnoredArtist.user_id == viewer_id,
                    IgnoredArtist.artist_id == TrackArtist.artist_id,
                )
            ),
        )
        .group_by(Artist.id, Artist.name)
        .order_by(func.count().desc())
        .limit(5)
    )


def build_most_played_decade_stmt(user_id: str, viewer_id: str | None = None):
    if viewer_id is None:
        viewer_id = user_id
    return (
        select(func.substr(Album.release_date, 1, 3).label("century"), func.count())
        .select_from(Play)
        .join(Track, Track.id == Play.track_id)
        .join(Album, Album.id == Track.album_id)
        .where(
            Play.user_id == user_id,
            Album.release_date.is_not(None),
            ~exists(
                select(GlobalIgnoredTrack).where(
                    GlobalIgnoredTrack.track_id == Play.track_id
                )
            ),
            ~exists(
                select(GlobalIgnoredArtist)
                .join(
                    TrackArtist, TrackArtist.artist_id == GlobalIgnoredArtist.artist_id
                )
                .where(TrackArtist.track_id == Play.track_id)
            ),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == viewer_id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == viewer_id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
        .group_by("century")
        .order_by(func.count().desc())
        .limit(1)
    )


def build_tracking_since_stmt(user_id: str):
    return select(func.min(Play.date)).where(Play.user_id == user_id)


@router.get("/user/{username}/public")
async def get_public_profile(
    username: str,
    db: Session = Depends(get_session),
    viewer: User | None = Depends(get_current_user),
):
    # Find user by username
    user = db.exec(select(User).where(User.username == username)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if viewer is None:
        viewer_id = user.id
    else:
        viewer_id = viewer.id
    if viewer is None:
        is_friend = False
    else:
        current_friends = get_friends(db, viewer)
        is_friend = user in current_friends or user == viewer

    user_info = {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "picture": user.picture,
        "join_date": user.join_date.isoformat(),
        "is_friend": is_friend,
    }

    # Playback Stats (use query builders)
    total_likes = db.exec(build_total_stmt(Like, user.id, viewer_id)).one() or 0
    total_plays = db.exec(build_total_stmt(Play, user.id, viewer_id)).one() or 0

    total_listen_sec = (
        db.exec(build_total_listen_sec_stmt(user.id, viewer_id)).one() or 0
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    monthly_listen_sec = (
        db.exec(build_monthly_listen_sec_stmt(user.id, cutoff, viewer_id)).one() or 0
    )

    # Tracking since (oldest play date)
    tracking_since_dt = db.exec(build_tracking_since_stmt(user.id)).one()
    tracking_since = (
        tracking_since_dt.isoformat()
        if hasattr(tracking_since_dt, "isoformat")
        else None
    )

    # Most played decade
    rows_decade = db.exec(build_most_played_decade_stmt(user.id, viewer_id)).all()
    most_played_decade = None
    if rows_decade:
        century = rows_decade[0][0]
        if century and len(century) == 3:
            most_played_decade = f"{century}0s"
    stats = {
        "user": user_info,
        "stats": {
            "total_plays": int(total_plays),
            "total_likes": int(total_likes),
            "total_listening_time_sec": int(total_listen_sec),
            "listening_time_last_30_days_sec": int(monthly_listen_sec),
            "tracking_since": tracking_since,
        },
        "highlights": {
            "most_played_decade": most_played_decade,
        },
    }
    if is_friend:
        # Top 5 songs last 30 days
        rows_30 = db.exec(
            build_top_tracks_last_30_stmt(user.id, cutoff, viewer_id)
        ).all()

        top_tracks_30: list[dict[str, Any]] = []
        if rows_30:
            track_ids_30 = [tid for (tid, _) in rows_30]
            cnt_map_30 = {tid: int(cnt) for (tid, cnt) in rows_30}
            hydrated_30 = cache.enrich_tracks(
                [Like(track_id=track_id, user_id=user.id) for track_id in track_ids_30],
                "date",
                viewer,
                db,
            )
            # enrich with play_count, preserving order
            for item in hydrated_30:
                item["play_count"] = cnt_map_30.get(item["track"]["id"], 0)
            top_tracks_30 = hydrated_30

        # Top 5 songs all time (use query builder)
        rows_all = db.exec(build_top_tracks_all_time_stmt(user.id, viewer_id)).all()

        top_tracks_all: list[dict[str, Any]] = []
        if rows_all:
            track_ids_all = [tid for (tid, _) in rows_all]
            cnt_map_all = {tid: int(cnt) for (tid, cnt) in rows_all}
            hydrated_all = cache.enrich_tracks(
                [
                    Like(track_id=track_id, user_id=user.id)
                    for track_id in track_ids_all
                ],
                "date",
                viewer,
                db,
            )
            for item in hydrated_all:
                item["play_count"] = cnt_map_all.get(item["track"]["id"], 0)
            top_tracks_all = hydrated_all

        # Top 5 artists by play count
        rows_artists = db.exec(build_top_artists_stmt(user.id, viewer_id)).all()
        top_artists = [
            {"artist_id": aid, "name": name, "play_count": int(cnt)}
            for (aid, name, cnt) in rows_artists
        ]
        stats["highlights"].update(
            {
                "top_songs_30_days": top_tracks_30,
                "top_songs_all_time": top_tracks_all,
                "top_artists": top_artists,
            }
        )

    return stats


@router.get("/get/next")
async def get_next_stub():
    return {"next": None}
