# this file manages a cache enriching tracks
from functools import partial
from typing import Sequence, Any

from expiringdict import ExpiringDict
from sqlmodel import Session, select

from models import User, Like, Play, Track, TrackArtist, Artist, Album

new_cache = partial(
    ExpiringDict,
    max_len=10_000,
    max_age_seconds=10 * 60,  # 10 minutes cache
    items={},
)


class CacheService:
    def __init__(self):
        self.track_cache = new_cache()
        self.user_cache = new_cache()
        self.likes_cache = new_cache()

    def get_users(self, user_ids, db: Session):
        missing_ids = [uid for uid in user_ids if uid not in self.user_cache]
        if missing_ids:
            missing_users = db.exec(select(User).where(User.id.in_(missing_ids))).all()
            for user in missing_users:
                self.user_cache[user.id] = {
                    "id": user.id,
                    "name": user.name,
                    "username": user.username,
                    "picture": user.picture,
                }
        return {uid: self.user_cache[uid] for uid in user_ids}

    def get_likes(self, user: User, db: Session) -> set[str]:
        if not user:
            return set()
        if user.id not in self.likes_cache:
            likes = set(
                db.exec(select(Like.track_id).where(Like.user_id == user.id)).all()
            )
            self.likes_cache[user.id] = likes
        return self.likes_cache[user.id]

    def enrich_tracks(
        self,
        items: list[Play | Like],
        date_field: str,
        user: User,
        db: Session,
    ) -> list[dict]:
        track_ids = {t.track_id for t in items}
        user_ids = [user.id] if user else []
        users_map = self.get_users(user_ids + [track.user_id for track in items], db)
        user_likes = self.get_likes(user, db)
        tracks: Sequence[Track] = db.exec(
            select(Track).where(Track.id.in_(track_ids))
        ).all()
        tracks_map: dict[str, Track] = {t.id: t for t in tracks}

        # Album info
        album_ids = {t.album_id for t in tracks if t.album_id}
        albums_map: dict[str, Album] = {
            a.id: a for a in db.exec(select(Album).where(Album.id.in_(album_ids))).all()
        }

        # Artists per track
        ta_rows = db.exec(
            select(TrackArtist).where(TrackArtist.track_id.in_(track_ids))
        ).all()
        artist_ids = list({ta.artist_id for ta in ta_rows})
        artists_map: dict[str, Artist] = {
            a.id: a
            for a in db.exec(select(Artist).where(Artist.id.in_(artist_ids))).all()
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
            u = users_map.get(p.user_id, {})
            t = tracks_map.get(p.track_id)
            album = albums_map.get(t.album_id) if (t and t.album_id) else None
            results.append(
                {
                    "user": {
                        "id": p.user_id,
                        "name": u.get("name"),
                        "username": u.get("username"),
                        "picture": u.get("picture"),
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
                    date_field: getattr(p, date_field).isoformat(),
                    "context_uri": getattr(p, "context_uri", None),
                    "liked": p.track_id in user_likes,
                }
            )
        return results


cache = CacheService()
