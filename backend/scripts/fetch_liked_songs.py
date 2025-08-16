"""Script to fetch liked songs from Spotify for all users"""

import asyncio
import logging

from models.auth import User
from models.common import get_db
from services import Spotify
from services.likes import process_user
from sqlmodel import select
from utils import setup_logs, time_it

logger = logging.getLogger("lykd.fetch")


@time_it
async def fetch_likes():
    """Main function to fetch liked songs for all users"""

    # Get database session and fetch all users

    with get_db() as session:
        spotify_client = Spotify(db_session=session)
        users = session.exec(select(User)).all()

        logger.debug(f"Found {len(users)} users in the database")

        # Filter users that have Spotify tokens
        active_users = [user for user in users if user.tokens]

        if not active_users:
            logger.info("No active users found.")
            return

        logger.info(f"Processing {len(active_users)} users...")

        # Execute all user processing concurrently
        tasks = [process_user(session, user, spotify_client) for user in active_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing user {active_users[i]}: {result}")

        # Commit any token updates
        session.commit()
        await spotify_client.close()

    logger.info("Finished processing all users.")


if __name__ == "__main__":  # pragma no cover
    setup_logs()
    asyncio.run(fetch_likes())
