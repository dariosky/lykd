"""Script to fetch liked songs from Spotify for all users"""

import asyncio
import logging

from models.auth import User
from models.common import get_session
from services import Spotify
from services.likes import process_user_likes
from sqlmodel import select
from utils import setup_logs, time_it

logger = logging.getLogger("lykd.fetch")


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

        # Execute all user processing concurrently
        tasks = [
            process_user_likes(session, user, spotify_client)
            for user in users_with_tokens
        ]
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
