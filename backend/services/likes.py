# Create async tasks for all users
import datetime
from functools import partial

from models.auth import User
from models.music import Like, PlaylistTrack, Play, Playlist
from services import Spotify
from services.store import (
    store_track,
    store_playlist,
    update_likes_db,
    update_playlist_db,
)
from sqlmodel import select, Session

import logging

from utils.dates import parse_date

logger = logging.getLogger("lykd.likes")


async def process_likes(
    db: Session, spotify: Spotify, user: User, playlist_name: str = "Lykd Songs"
) -> None:
    # here I want to get the songs to add and remove - we have the fast or the slow way
    now = datetime.datetime.now(datetime.timezone.utc)
    full_scan = (
        user.last_like_scan_full is None
        or user.last_like_scan_full <= now - datetime.timedelta(hours=12)
    )

    all_db_like_ids = {
        like.track_id
        for like in db.exec(
            select(Like).where(
                Like.user_id == user.id,
            )
        )
    }

    if full_scan:
        logger.info(f"Full scan for {user.email} likes")
        # Fetch all liked songs from Spotify
        all_spotify_likes = await spotify.get_all(
            user=user,
            request=spotify.get_liked_page,
        )
        logger.info(f"Processing {len(all_spotify_likes)} liked songs for user {user}:")

        all_spotify_likes_ids = {
            spotify_like.get("track", {}).get("id")
            for spotify_like in all_spotify_likes
        }
        new_spotify_likes = [
            spotify_like
            for spotify_like in all_spotify_likes
            if spotify_like.get("track", {}).get("id") not in all_db_like_ids
        ]

        tracks_to_remove = all_db_like_ids - all_spotify_likes_ids
    else:
        if user.last_like_scan and user.last_like_scan > now - datetime.timedelta(
            minutes=15
        ):
            return
        logger.info(f"Quick scan for {user} likes")
        new_spotify_likes = []
        async for spotify_like in spotify.yield_from(
            user=user,
            request=spotify.get_liked_page,
        ):
            track_id = spotify_like.get("track", {}).get("id")
            existing_like = db.get(Like, (user.id, track_id))
            if existing_like:
                break

            new_spotify_likes.append(spotify_like)

        all_spotify_likes = new_spotify_likes
        tracks_to_remove = set()

    if new_spotify_likes or tracks_to_remove or full_scan:
        spotify_playlist = await spotify.get_or_create_playlist(
            user=user, playlist_name=playlist_name
        )
        playlist = store_playlist(spotify_playlist, db_session=db)

    if full_scan:
        playlist: Playlist
        # DONE: the Spotify playlist has different likes than the DB
        # in the full_scan we should retrieve also the whole playlist to decide what
        logger.debug(f"Full scan to sync playlist {playlist_name}")
        playlist_request = partial(spotify.get_playlist_tracks, playlist_id=playlist.id)
        existing_spotify_tracks = await spotify.get_all(
            user=user, request=playlist_request
        )
        existing_tracks_ids = {
            item.get("track", {}).get("id") for item in existing_spotify_tracks
        }
    else:
        # we assume that the playlist contains what we knew from the DB
        existing_tracks_ids = all_db_like_ids

    if new_spotify_likes or tracks_to_remove or existing_tracks_ids != all_db_like_ids:
        tracks_to_add = {
            spotify_like.get("track", {}).get("id")
            for spotify_like in new_spotify_likes
        }
        logger.debug(
            f"Likes for {user}: {len(tracks_to_add)} to add, {len(tracks_to_remove)} to remove"
        )

        for like in new_spotify_likes:
            track_data = like.get("track", {})
            try:
                store_track(track_data, db)
            except Exception as e:
                logger.error(
                    f" Error processing track {track_data.get('name', 'Unknown')}: {e}"
                )

        await spotify.change_playlist(
            user=user,
            playlist_id=playlist.id,
            tracks_to_add=[  # we need the order of the tracks to be preserved
                track_id
                for spotify_like in all_spotify_likes
                if (track_id := spotify_like.get("track", {}).get("id"))
                not in existing_tracks_ids
            ],
            tracks_to_remove=tracks_to_remove,
        )
        new_likes = [
            Like(
                user_id=user.id,
                track_id=like.get("track", {}).get("id"),
                date=parse_date(like["added_at"]),
            )
            for like in new_spotify_likes
        ]
        update_likes_db(
            user,
            likes_to_add=new_likes,
            tracks_to_remove=tracks_to_remove,
            db=db,
        )
        update_playlist_db(
            playlist.id,
            tracks_to_add=[
                PlaylistTrack(
                    playlist_id=playlist.id,
                    track_id=like.track_id,
                    date=like.date,
                )
                for like in new_likes
            ],
            tracks_to_remove=tracks_to_remove,
            db=db,
        )
        db.commit()
        logger.info(
            f"{user} likes:"
            f" {len(tracks_to_add)} added, {len(tracks_to_remove)} deleted "
        )
    # update the user with the new last scan time
    now = datetime.datetime.now(datetime.timezone.utc)
    if full_scan:
        user.last_like_scan_full = now
    else:
        user.last_like_scan = now
    db.add(user)
    db.commit()


async def process_user(db: Session, user: User, spotify: Spotify):
    # Create a Spotify playlist

    # store the liked songs - create likes and sync with the playlist
    await process_likes(db, spotify, user)
    await process_plays(db, spotify, user)


async def process_plays(db, spotify: Spotify, user):
    # this works a bit differently than likes
    # we yield and stop as soon as we find a play that has been already written
    added = 0
    async for play in spotify.yield_from(
        user=user,
        request=spotify.get_recently_played_page,
    ):
        track_data = play.get("track", {})
        track_id = track_data.get("id")
        played_at = parse_date(play.get("played_at"))
        existing_play = db.get(Play, (user.id, track_id, played_at))
        if existing_play:
            # play already exists, stop processing
            break
        context = play.get("context") or {}
        context_uri = context.get("uri")
        track = store_track(track_data, db)
        db.merge(
            Play(
                user_id=user.id,
                track_id=track.id,
                date=played_at,
                context_uri=context_uri,
            )
        )
        added += 1
    if added > 0:
        logger.info(f"Added {added} new plays from {user}")
        db.commit()
