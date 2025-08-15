import datetime as dt
import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from sqlmodel import Session

from models.auth import User
from models.common import get_db
from models.music import Play
from services.spotify import Spotify
from services.store import find_missing_tracks, store_track

logger = logging.getLogger("lykd.spotify_import")
PROGRESS_EVERY = 2_000


async def process_spotify_history_zip(user: User, zip_path: str) -> None:
    """Process a Spotify extended history ZIP in a background thread.

    Steps:
    - Extract to a temporary directory
    - Walk all .json files (any depth), sort by filename descending
    - For each JSON array item, create a Play record with date from ts and track_id from spotify_track_uri
    - Commit once at the end
    - Cleanup temp directory
    """
    work_dir = tempfile.mkdtemp(prefix="lykd_spotify_import_")
    extract_dir = Path(work_dir) / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Extract ZIP securely
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                # Prevent Zip Slip by ensuring paths stay within extract_dir
                target_path = extract_dir / member.filename
                target_path_parent = target_path.resolve().parent
                if (
                    extract_dir.resolve() not in target_path_parent.parents
                    and extract_dir.resolve() != target_path_parent
                ):
                    logger.warning(
                        f"Skipping potentially unsafe path in zip: {member.filename}"
                    )
                    continue
                zf.extract(member, path=extract_dir)
        logger.debug(f"Extracted ZIP for user {user} to {extract_dir}")

        # Collect JSON files and sort by filename desc
        json_files = list(extract_dir.rglob("*.json"))
        json_files.sort(key=lambda p: p.name, reverse=True)
        logger.debug(f"Found {len(json_files)} JSON files to process for user {user}")

        inserted = 0
        skipped = 0

        with get_db() as session:
            for jf in json_files:
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    logger.exception(f"Failed to read JSON {jf}: {e}")
                    continue

                if not isinstance(data, list):
                    logger.warning(f"Skipping non-list JSON: {jf}")
                    continue

                logger.debug(
                    f"Processing file {jf.name} with {len(data)} entries for user {user}"
                )

                for item in data:
                    try:
                        ts = item.get("ts")
                        uri = item.get("spotify_track_uri")
                        if not ts or not uri or not isinstance(uri, str):
                            skipped += 1
                            continue
                        if not uri.startswith("spotify:track:"):
                            skipped += 1
                            continue
                        # Parse timestamp (Z -> UTC)
                        try:
                            dt_utc = dt.datetime.fromisoformat(
                                ts.replace("Z", "+00:00")
                            )
                        except Exception:
                            skipped += 1
                            continue
                        track_id = uri.split(":")[-1]

                        # Upsert-like insert using merge to avoid PK conflicts; commit done at end
                        session.merge(
                            Play(user_id=user.id, track_id=track_id, date=dt_utc)
                        )
                        inserted += 1
                        if inserted % PROGRESS_EVERY == 0:
                            logger.debug(
                                f"Progress for user {user}: processed={inserted}(file={jf.name})"
                            )
                    except Exception as e:
                        logger.exception(f"Error processing item in {jf}: {e}")
                        skipped += 1
                        continue
            # One commit at the end per requirements
            logger.debug(
                f"Committing plays for user {user}: inserted={inserted} skipped={skipped}"
            )
            session.commit()

            logger.info(
                f"Spotify import finished for user {user}: inserted={inserted} skipped={skipped}"
            )
            await fill_missing_track(session, user)
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
        try:
            if zip_path and Path(zip_path).exists():
                Path(zip_path).unlink(missing_ok=True)
        except Exception:
            pass


async def fill_missing_track(session: Session, user: User):
    missing_tracks = find_missing_tracks(session)
    if missing_tracks:
        logger.info(f"Querying Spotify for {len(missing_tracks)} missing tracks")
        spotify = Spotify(db_session=session)
        async for track in spotify.yield_tracks(user=user, tracks=missing_tracks):
            store_track(track, session)
    session.commit()
    logger.info("Finished filling the track gaps from Spotify")
