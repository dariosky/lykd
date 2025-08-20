import datetime
import os
import hashlib

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

import settings
from models.auth import User, populate_username, OAuthState
from models.common import get_session
from models.music import Like, Play
from routes.deps import current_user
from services import Spotify
from services.slack import slack
from services.spotify_history import process_spotify_history_zip

logger = logging.getLogger("lykd.spotify_import")

router = APIRouter()
spotify = Spotify()


@router.get("/spotify/authorize")
async def spotify_authorize(
    request: Request,
    next: str | None = Query(None, description="Optional next URL after login"),
    session: Session = Depends(get_session),
):
    auth_url, state = spotify.get_authorization_url()

    # Persist single-use state with client metadata for validation/auditing
    state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    client_ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    referer = request.headers.get("referer")

    oauth_state = OAuthState(
        provider="spotify",
        state_hash=state_hash,
        request_ip=client_ip,
        request_user_agent=ua,
        request_referer=referer,
        redirect_uri=spotify.redirect_uri,
        next_url=next,
    )
    session.add(oauth_state)
    session.commit()

    return {"authorization_url": auth_url, "state": state}


@router.get("/spotify/callback")
async def spotify_callback(
    request: Request,
    code: str | None = Query(None, description="Authorization code from Spotify"),
    state: str | None = Query(..., description="State parameter for security"),
    error: str | None = Query(None, description="Error from Spotify OAuth"),
    session: Session = Depends(get_session),
):
    if error:
        return RedirectResponse(
            url=f"{settings.BASE_URL}/error?message=Spotify authorization failed: {error}",
            status_code=302,
        )

    try:
        # Validate and atomically consume the state to prevent CSRF/replay
        if not state:
            return RedirectResponse(
                url=f"{settings.BASE_URL}/error?message=Missing state",
                status_code=302,
            )

        state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
        now = datetime.datetime.now(datetime.timezone.utc)
        client_ip = request.client.host if request.client else None

        # Look up the state using SQLModel and consume it
        oauth_state = session.exec(
            select(OAuthState).where(
                OAuthState.provider == "spotify",
                OAuthState.state_hash == state_hash,
                OAuthState.consumed_at.is_(None),
                OAuthState.expires_at > now,
            )
        ).one_or_none()

        if not oauth_state:
            return RedirectResponse(
                url=f"{settings.BASE_URL}/error?message=Invalid or expired state",
                status_code=302,
            )

        oauth_state.consumed_at = now
        oauth_state.consumed_by_ip = client_ip
        oauth_state.attempt_count = (oauth_state.attempt_count or 0) + 1
        session.add(oauth_state)
        session.commit()

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

        # Link the oauth_state to the user who completed the handshake
        oauth_state.user_id = user.id
        session.add(oauth_state)

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
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Get Spotify sync statistics for the current user"""

    total_likes = session.exec(
        select(func.count(Like.track_id)).where(Like.user_id == user.id)
    ).one()
    total_plays = session.exec(
        select(func.count(Play.track_id)).where(Play.user_id == user.id)
    ).one()

    # Get the earliest like date (tracking since)
    earliest_like_date = session.exec(
        select(func.min(Play.date)).where(Play.user_id == user.id)
    ).one()

    tracking_since = None
    if earliest_like_date:
        tracking_since = earliest_like_date.isoformat()

    return {
        "total_likes_synced": total_likes,
        "total_plays_synced": total_plays,
        "tracking_since": tracking_since,
        "active": bool(user.tokens),
        "full_history_sync_wait": get_history_sync_seconds_wait(user),
        "last_full_history_sync": user.last_history_sync,
    }


def get_history_sync_seconds_wait(current_user: User) -> int:
    """How long the user should wait before syncing history again."""
    if not current_user.last_history_sync:
        return 0
    # Default to 30 days ago if no sync has been done yet
    cutoff = current_user.last_history_sync + datetime.timedelta(days=1)
    now = datetime.datetime.now(datetime.timezone.utc)
    if now > cutoff:
        return 0
    return int((cutoff - now).total_seconds())


@router.post("/spotify/import")
async def import_spotify_extended_history(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(
        ..., description="ZIP file containing Extended streaming history"
    ),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    """Start a background job to import Extended streaming history from a ZIP.

    Returns immediately while the job runs in the background.
    """
    if get_history_sync_seconds_wait(user) > 0:
        raise HTTPException(
            status_code=429, detail="You need to wait before syncing again"
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")
    # Persist upload to a temp file first
    fd, tmp_zip = tempfile.mkstemp(prefix="lykd_spotify_zip_", suffix=".zip")
    with os.fdopen(fd, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
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

    # mark the user as having started a history sync
    user.last_history_sync = datetime.datetime.now(datetime.timezone.utc)
    session.add(user)
    session.commit()

    # Schedule background processing
    background_tasks.add_task(process_spotify_history_zip, user, tmp_zip)

    return {"message": "Import started"}
