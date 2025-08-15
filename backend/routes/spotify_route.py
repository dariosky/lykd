from fastapi import (
    APIRouter,
    Depends,
    Query,
    Request,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
)
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select, func
import tempfile
import zipfile
from pathlib import Path
import logging
import os

import settings
from models.auth import User, populate_username
from models.common import get_session
from models.music import Like, Play
from routes.deps import get_current_user
from services import Spotify
from services.slack import slack
from services.spotify_history import process_spotify_history_zip

logger = logging.getLogger("lykd.spotify_import")

router = APIRouter()
spotify = Spotify()


@router.get("/spotify/authorize")
async def spotify_authorize():
    auth_url, state = spotify.get_authorization_url()
    return {"authorization_url": auth_url, "state": state}


@router.get("/spotify/callback")
async def spotify_callback(
    request: Request,
    code: str | None = Query(None, description="Authorization code from Spotify"),
    state: str | None = Query(..., description="State parameter for security"),
    error: str | None = Query(None, description="Error from Spotify OAuth"),
    session: Session = Depends(get_session),
):
    # TODO: Validate the state parameter to prevent CSRF attacks
    if error:
        return RedirectResponse(
            url=f"{settings.BASE_URL}/error?message=Spotify authorization failed: {error}",
            status_code=302,
        )

    try:
        token_data = await spotify.exchange_code_for_token(code)
        user_info = await spotify.get_user_info(token_data["access_token"])

        existing_user: User | None = session.get(User, user_info["id"])

        if existing_user:
            existing_user.tokens = token_data
            existing_user.name = user_info["display_name"] or user_info["id"]
            existing_user.picture = (
                user_info["images"][0]["url"] if user_info.get("images") else ""
            )
            # If username not set (legacy), assign one now
            if not existing_user.username:
                populate_username(session, existing_user)
            session.add(existing_user)
            user = existing_user
        else:
            user = User(
                id=user_info["id"],
                name=user_info["display_name"] or user_info["id"],
                email=user_info["email"],
                picture=user_info["images"][0]["url"]
                if user_info.get("images")
                else "",
                tokens={
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "scope": token_data.get("scope"),
                },
            )
            populate_username(session, user)
            session.add(user)
            slack.send_message(f"🐣New user connected to Spotify: {user.email}")

        session.commit()
        request.session["user_id"] = user.id
        return RedirectResponse(
            url=f"{settings.BASE_URL}/?spotify=connected", status_code=302
        )

    except Exception as e:  # pragma: no cover (keep consistent with app)
        # Redirect to error page with error details
        error_message = (
            str(e) if str(e) else "Unknown error occurred during Spotify authorization"
        )
        return RedirectResponse(
            url=f"{settings.BASE_URL}/error?message={error_message}",
            status_code=302,
        )


@router.get("/spotify/stats")
async def get_spotify_stats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get Spotify sync statistics for the current user"""

    total_likes = session.exec(
        select(func.count(Like.track_id)).where(Like.user_id == current_user.id)
    ).one()

    # Get the earliest like date (tracking since)
    earliest_like_date = session.exec(
        select(func.min(Play.date)).where(Play.user_id == current_user.id)
    ).one()

    tracking_since = None
    if earliest_like_date:
        tracking_since = earliest_like_date.isoformat()

    return {
        "total_likes_synced": total_likes,
        "tracking_since": tracking_since,
        "active": bool(current_user.tokens),
    }


@router.post("/spotify/import")
async def import_spotify_extended_history(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ..., description="ZIP file containing Extended streaming history"
    ),
    current_user: User = Depends(get_current_user),
):
    """Start a background job to import Extended streaming history from a ZIP.

    Returns immediately while the job runs in the background.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")
    # Persist upload to a temp file first
    fd, tmp_zip = tempfile.mkstemp(prefix="lykd_spotify_zip_", suffix=".zip")
    try:
        with os.fdopen(fd, "wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    finally:
        await file.close()

    # Validate ZIP signature before scheduling background work
    try:
        if not zipfile.is_zipfile(tmp_zip):
            try:
                Path(tmp_zip).unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(
                status_code=400, detail="Please upload a valid ZIP file"
            )
    except HTTPException:
        raise
    except Exception:
        try:
            Path(tmp_zip).unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Please upload a valid ZIP file")

    # Schedule background processing
    background_tasks.add_task(process_spotify_history_zip, current_user, tmp_zip)

    return {"message": "Import started"}
