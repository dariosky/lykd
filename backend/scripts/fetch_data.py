"""Script to fetch liked songs from Spotify for all users"""

import argparse
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
async def fetch_all(max_concurrency: int = 3):
    """Main function to fetch liked songs for all users

    Args:
        max_concurrency: Maximum number of users to process concurrently.
    """

    # Normalize concurrency
    if max_concurrency is None or max_concurrency < 1:
        logger.warning(
            "max_concurrency must be >= 1; defaulting to 1 (was %s)", max_concurrency
        )
        max_concurrency = 1

    # Get database session and fetch all users

    with get_db() as session:
        spotify_lykd = Spotify(app_name="lykd")
        spotify_spotlike = Spotify(app_name="spotlike")
        users = session.exec(select(User)).all()

        logger.debug(f"Found {len(users)} users in the database")

        # Filter users that have Spotify tokens
        active_users = [user for user in users if user.tokens]

        if not active_users:
            logger.info("No active users found.")
            return

        logger.info(f"Processing {len(active_users)} users...")

        # Bounded concurrency semaphore
        sem = asyncio.Semaphore(max_concurrency)

        async def _process_user_bounded(user: User):
            async with sem:
                spotify_client = (
                    spotify_lykd if user.app_name == "lykd" else spotify_spotlike
                )
                return await process_user(session, user, spotify_client)

        # Execute user processing with bounded concurrency
        tasks = [_process_user_bounded(user) for user in active_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing user {active_users[i]}: {result}")

        # Commit any token updates
        session.commit()
        await spotify_lykd.close()
        await spotify_spotlike.close()

    logger.info("Finished processing all users.")


if __name__ == "__main__":  # pragma no cover
    setup_logs()

    parser = argparse.ArgumentParser(
        description="Fetch data from Spotify for all users"
    )
    parser.add_argument(
        "-c",
        "--max-concurrency",
        type=int,
        default=3,
        help="Maximum number of users to process concurrently (default: 3)",
    )
    args = parser.parse_args()

    asyncio.run(fetch_all(args.max_concurrency))
