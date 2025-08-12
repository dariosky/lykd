# Create async tasks for all users
from typing import Any


from models.auth import User
from models.music import Playlist, Like, PlaylistTrack
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


async def process_user(
    db: Session, user: User, spotify: Spotify, playlist_name: str = "Lykd Songs"
):
    # Create a Spotify playlist
    spotify_playlist = await spotify.get_or_create_playlist(
        user=user, playlist_name=playlist_name
    )
    playlist = store_playlist(spotify_playlist, db_session=db)
    logger.debug(f"Processing user likes: {user.email}")
    # Fetch all liked songs from Spotify
    liked_songs = await spotify.get_all(
        user=user,
        request=spotify.get_liked_page,
    )
    # store the liked songs - create likes and sync with the playlist
    await process_liked_songs(db, spotify, user, liked_songs, playlist)
    await process_plays(db, spotify, user)
    return user.email, len(liked_songs)


async def process_liked_songs(
    db: Session,
    spotify: Spotify,
    user: User,
    liked_songs: list[dict[str, Any]],
    playlist: Playlist,
) -> None:
    """Process and store all liked songs data"""
    logging.info(f"\nProcessing {len(liked_songs)} liked songs for user {user.email}:")
    all_db_like_ids = {
        like.track_id
        for like in db.exec(
            select(Like).where(
                Like.user_id == user.id,
            )
        )
    }
    all_spotify_likes_ids = {
        spotify_like.get("track", {}).get("id") for spotify_like in liked_songs
    }

    new_spotify_likes = [
        spotify_like
        for spotify_like in liked_songs
        if spotify_like.get("track", {}).get("id") not in all_db_like_ids
    ]
    tracks_to_add = {
        spotify_like.get("track", {}).get("id") for spotify_like in new_spotify_likes
    }
    tracks_to_remove = all_db_like_ids - all_spotify_likes_ids

    for like in new_spotify_likes:
        track_data = like.get("track", {})
        try:
            store_track(track_data, db)
        except Exception as e:
            logger.error(
                f"  Error processing track {track_data.get('name', 'Unknown')}: {e}"
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

    if tracks_to_add or tracks_to_remove:
        # TODO: can be that the Spotify playlist has different likes than the DB
        await spotify.change_playlist(
            user=user,
            playlist_id=playlist.id,
            tracks_to_add=[
                track_id
                for spotify_like in new_spotify_likes
                if (track_id := spotify_like.get("track", {}).get("id"))
                not in all_db_like_ids
            ],
            tracks_to_remove=tracks_to_remove,
        )
        db.commit()
        logger.info(
            f"{user.email} likes:"
            f" {len(tracks_to_add)} added, {len(tracks_to_remove)} deleted "
        )


async def process_plays(db, spotify: Spotify, user):
    # this works a bit differently than likes
    # we yield and stop as soon as we find a play that has been already written
    async for play in spotify.yield_from(
        user=user,
        request=spotify.get_recently_played_page,
    ):
        track_data = play.get("track", {})
        print(track_data)
        break  # TODO: this will stop processing the following data
