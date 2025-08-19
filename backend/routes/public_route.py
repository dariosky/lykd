from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

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
)
from models.common import get_session

router = APIRouter()


@router.get("/user/{username}/public")
async def get_public_profile(username: str, db: Session = Depends(get_session)):
    # Find user by username
    user = db.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_info = {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "picture": user.picture,
        "join_date": user.join_date.isoformat(),
    }

    # Playback Stats (robust scalar extraction)
    total_plays = db.exec(
        select(func.count())
        .select_from(Play)
        .join(Track, Track.id == Play.track_id)
        .where(
            Play.user_id == user.id,
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == user.id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == user.id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
    ).one()

    total_likes = db.exec(
        select(func.count())
        .select_from(Like)
        .join(Track, Track.id == Like.track_id)
        .where(
            Like.user_id == user.id,
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == user.id,
                    IgnoredTrack.track_id == Like.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == user.id,
                    TrackArtist.track_id == Like.track_id,
                )
            ),
        )
    ).one()

    total_listen_sec = (
        db.exec(
            select(func.coalesce(func.sum(Track.duration / 1000), 0))
            .select_from(Play)
            .join(Track, Track.id == Play.track_id)
            .where(
                Play.user_id == user.id,
                ~exists(
                    select(IgnoredTrack).where(
                        IgnoredTrack.user_id == user.id,
                        IgnoredTrack.track_id == Play.track_id,
                    )
                ),
                ~exists(
                    select(IgnoredArtist)
                    .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                    .where(
                        IgnoredArtist.user_id == user.id,
                        TrackArtist.track_id == Play.track_id,
                    )
                ),
            )
        ).one()
        or 0
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    monthly_listen_sec = (
        db.exec(
            select(func.coalesce(func.sum(Track.duration / 1000), 0))
            .select_from(Play)
            .join(Track, Track.id == Play.track_id)
            .where(
                Play.user_id == user.id,
                Play.date >= cutoff,
                ~exists(
                    select(IgnoredTrack).where(
                        IgnoredTrack.user_id == user.id,
                        IgnoredTrack.track_id == Play.track_id,
                    )
                ),
                ~exists(
                    select(IgnoredArtist)
                    .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                    .where(
                        IgnoredArtist.user_id == user.id,
                        TrackArtist.track_id == Play.track_id,
                    )
                ),
            )
        ).one()
        or 0
    )

    # Tracking since (oldest play date)
    tracking_since_dt = db.exec(
        select(func.min(Play.date)).where(Play.user_id == user.id)
    ).one()
    tracking_since = (
        tracking_since_dt.isoformat()
        if hasattr(tracking_since_dt, "isoformat")
        else None
    )

    # Highlights helpers
    def _track_artist_names(track_id: str) -> List[str]:
        artist_ids = db.exec(
            select(TrackArtist.artist_id).where(TrackArtist.track_id == track_id)
        ).all()
        return db.exec(select(Artist.name).where(Artist.id.in_(artist_ids))).all()

    def _track_album_info(track_id: str) -> Dict[str, Any] | None:
        album = db.exec(
            select(Album)
            .join(Track, Track.album_id == Album.id)
            .where(Track.id == track_id)
        ).first()
        if not album:
            return None
        return {
            "id": album.id,
            "name": album.name,
            "release_date": album.release_date.isoformat()
            if album.release_date
            else None,
        }

    # Top 5 songs last 30 days
    rows_30 = db.exec(
        select(Play.track_id, func.count().label("cnt"))
        .where(
            Play.user_id == user.id,
            Play.date >= cutoff,
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == user.id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == user.id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
        .group_by(Play.track_id)
        .order_by(func.count().desc())
        .limit(5)
    ).all()

    top_tracks_30: List[Dict[str, Any]] = []
    if rows_30:
        track_ids_30 = [tid for (tid, _) in rows_30]
        tracks_map = {
            t.id: t
            for t in db.exec(select(Track).where(Track.id.in_(track_ids_30))).all()
        }
        cnt_map = {tid: cnt for (tid, cnt) in rows_30}
        for tid in track_ids_30:
            t = tracks_map.get(tid)
            if not t:
                continue
            top_tracks_30.append(
                {
                    "track_id": t.id,
                    "title": t.title,
                    "duration": t.duration,
                    "play_count": int(cnt_map.get(t.id, 0)),
                    "artists": _track_artist_names(t.id),
                    "album": _track_album_info(t.id),
                }
            )

    # Top 5 songs all time
    rows_all = db.exec(
        select(Play.track_id, func.count().label("cnt"))
        .where(
            Play.user_id == user.id,
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == user.id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == user.id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
        .group_by(Play.track_id)
        .order_by(func.count().desc())
        .limit(5)
    ).all()

    top_tracks_all: List[Dict[str, Any]] = []
    if rows_all:
        track_ids_all = [tid for (tid, _) in rows_all]
        tracks_map = {
            t.id: t
            for t in db.exec(select(Track).where(Track.id.in_(track_ids_all))).all()
        }
        cnt_map = {tid: cnt for (tid, cnt) in rows_all}
        for tid in track_ids_all:
            t = tracks_map.get(tid)
            if not t:
                continue
            top_tracks_all.append(
                {
                    "track_id": t.id,
                    "title": t.title,
                    "duration": t.duration,
                    "play_count": int(cnt_map.get(t.id, 0)),
                    "artists": _track_artist_names(t.id),
                    "album": _track_album_info(t.id),
                }
            )

    # Top 5 artists by play count (each play credited to all artists of the track)
    rows_artists = db.exec(
        select(Artist.id, Artist.name, func.count().label("cnt"))
        .select_from(Play)
        .join(Track, Track.id == Play.track_id)
        .join(TrackArtist, TrackArtist.track_id == Track.id)
        .join(Artist, Artist.id == TrackArtist.artist_id)
        .where(
            Play.user_id == user.id,
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == user.id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist).where(
                    IgnoredArtist.user_id == user.id,
                    IgnoredArtist.artist_id == TrackArtist.artist_id,
                )
            ),
        )
        .group_by(Artist.id, Artist.name)
        .order_by(func.count().desc())
        .limit(5)
    ).all()

    top_artists = [
        {"artist_id": aid, "name": name, "play_count": int(cnt)}
        for (aid, name, cnt) in rows_artists
    ]

    # Most played decade
    rows_decade = db.exec(
        select(func.substr(Album.release_date, 1, 3).label("century"), func.count())
        .select_from(Play)
        .join(Track, Track.id == Play.track_id)
        .join(Album, Album.id == Track.album_id)
        .where(
            Play.user_id == user.id,
            Album.release_date.is_not(None),
            ~exists(
                select(IgnoredTrack).where(
                    IgnoredTrack.user_id == user.id,
                    IgnoredTrack.track_id == Play.track_id,
                )
            ),
            ~exists(
                select(IgnoredArtist)
                .join(TrackArtist, TrackArtist.artist_id == IgnoredArtist.artist_id)
                .where(
                    IgnoredArtist.user_id == user.id,
                    TrackArtist.track_id == Play.track_id,
                )
            ),
        )
        .group_by("century")
        .order_by(func.count().desc())
        .limit(1)
    ).all()

    most_played_decade = None
    if rows_decade:
        century = rows_decade[0][0]
        if century and len(century) == 3:
            most_played_decade = f"{century}0s"

    return {
        "user": user_info,
        "stats": {
            "total_plays": int(total_plays),
            "total_likes": int(total_likes),
            "total_listening_time_sec": int(total_listen_sec),
            "listening_time_last_30_days_sec": int(monthly_listen_sec),
            "tracking_since": tracking_since,
        },
        "highlights": {
            "top_songs_30_days": top_tracks_30,
            "top_songs_all_time": top_tracks_all,
            "top_artists": top_artists,
            "most_played_decade": most_played_decade,
        },
    }
