# Create async tasks for all users
from typing import Any

from models import User, Like, Playlist
from services import Spotify
from services.store import store_track
from sqlmodel import select, Session
import datetime
from datetime import timezone


async def process_user_likes(
    db: Session, user: User, spotify: Spotify, playlist_name: str = "Lyked Songs"
):
    """
    For a user
    1. Create a Spotify playlist named "Liked Songs"
    2. Fetch all liked songs from Spotify - create tracks and likes in the db and in the playlist
    3. Delete all the unliked songs
    """
    playlist = await spotify.get_or_create_playlist(
        user=user, playlist_name=playlist_name
    )
    print(f"Processing user likes: {user.email}")
    liked_songs = await spotify.get_all(
        user=user,
        request=spotify.get_liked_page,
    )

    process_liked_songs(db, user, liked_songs, playlist)
    return user.email, len(liked_songs)


def process_liked_songs(
    db: Session, user: User, liked_songs: list[dict[str, Any]], playlist: Playlist
) -> None:
    """Process and store all liked songs data"""
    print(f"\nProcessing {len(liked_songs)} liked songs for user {user.email}:")

    for i, item in enumerate(liked_songs):
        track_data = item.get("track", {})
        if not track_data:
            continue

        try:
            # Store the track and its related data
            stored_track = store_track(track_data, db)

            # Create or update the like relationship
            statement = select(Like).where(
                Like.user_id == user.id,
                Like.track_id == stored_track.id,
            )
            existing_like = db.exec(statement).first()

            if not existing_like:
                # Create new like
                like = Like(
                    user_id=user.id,
                    track_id=stored_track.id,
                    date=datetime.datetime.now(timezone.utc),
                )
                db.add(like)
                db.commit()

            # Progress feedback
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(liked_songs)} tracks...")

        except Exception as e:
            print(f"  Error processing track {track_data.get('name', 'Unknown')}: {e}")
            # Rollback the transaction for this track and continue
            db.rollback()
            continue

    print(
        f"Successfully processed all {len(liked_songs)} liked songs for user {user.email}"
    )

    # TODO: Here you can add code to store the songs in your database
    # For example, create Track, Artist, Album records and user_liked_songs associations
