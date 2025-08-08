"""Script to fetch liked songs from Spotify for all users"""

import asyncio
import logging
from typing import Any, Dict, List

from models.auth import User
from models.common import get_session
from services import Spotify
from sqlmodel import select

from utils import time_it, setup_logs

logger = logging.getLogger("lykd.fetch")


def process_liked_songs(user: User, liked_songs: List[Dict[str, Any]]) -> None:
    """Process and optionally store the liked songs data"""
    print(f"\nProcessing {len(liked_songs)} liked songs for user {user.email}:")

    for i, item in enumerate(liked_songs[:5]):  # Show first 5 as example
        track = item.get("track", {})
        artists = ", ".join([artist["name"] for artist in track.get("artists", [])])
        print(f"  {i + 1}. {track.get('name', 'Unknown')} by {artists}")

    if len(liked_songs) > 5:
        print(f"  ... and {len(liked_songs) - 5} more songs")

    # TODO: Here you can add code to store the songs in your database
    # For example, create Track, Artist, Album records and user_liked_songs associations


@time_it
async def fetch_likes():
    """Main function to fetch liked songs for all users"""
    print("Starting to fetch liked songs for all users...")

    # Get database session and fetch all users
    session = next(get_session())
    spotify_client = None

    try:
        spotify_client = Spotify(db_session=session)
        users = session.exec(select(User)).all()

        print(f"Found {len(users)} users in the database")

        if not users:
            print(
                "No users found. Make sure users have been created and have Spotify tokens."
            )
            return

        # Filter users that have Spotify tokens
        users_with_tokens = [user for user in users if user.tokens]

        if not users_with_tokens:
            print("No users with Spotify tokens found.")
            return

        print(
            f"Processing {len(users_with_tokens)} users with Spotify tokens concurrently..."
        )

        # Create async tasks for all users
        async def process_user(user: User):
            """Process a single user and return results"""
            print(f"Processing user: {user.email}")
            liked_songs = await spotify_client.get_all(
                user=user,
                request=spotify_client.get_liked_page,
            )

            if liked_songs:
                process_liked_songs(user, liked_songs)
                return user.email, len(liked_songs)
            else:
                print(f"No liked songs retrieved for user {user.email}")
                return user.email, 0

        # Execute all user processing concurrently
        tasks = [process_user(user) for user in users_with_tokens]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle any exceptions
        total_songs = 0
        successful_users = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Error processing user {users_with_tokens[i].email}: {result}"
                )
            else:
                user_email, song_count = result
                total_songs += song_count
                if song_count > 0:
                    successful_users += 1

        print("\n=== Summary ===")
        print(f"Total users processed: {len(users_with_tokens)}")
        print(f"Users with liked songs: {successful_users}")
        print(f"Total liked songs fetched: {total_songs}")

        # Commit any token updates
        session.commit()

    except Exception as e:
        print(f"Error during execution: {e}")
        if session:
            session.rollback()
        raise
    finally:
        # Close the Spotify client to free HTTP connections
        if spotify_client:
            await spotify_client.close()
        # Properly close the database session
        if session:
            session.close()

    print("\nFinished processing all users.")


if __name__ == "__main__":
    setup_logs()
    asyncio.run(fetch_likes())
