from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

import settings
from models.auth import User
from models.common import get_session
from services import Spotify
from services.slack import slack
from .deps import generate_unique_username

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

        existing_user = session.get(User, user_info["id"])

        if existing_user:
            existing_user.tokens = token_data
            existing_user.name = user_info["display_name"] or user_info["id"]
            existing_user.picture = (
                user_info["images"][0]["url"] if user_info.get("images") else ""
            )
            # If username not set (legacy), assign one now
            if not existing_user.username:
                base_username = (
                    (user_info.get("display_name") or "").strip()
                    or (user_info.get("email") or "").split("@")[0]
                    or user_info["id"]
                )
                existing_user.username = generate_unique_username(
                    base_username, session
                )
            session.add(existing_user)
            user = existing_user
        else:
            base_username = (
                (user_info.get("display_name") or "").strip()
                or (user_info.get("email") or "").split("@")[0]
                or user_info["id"]
            )
            unique_username = generate_unique_username(base_username, session)
            user = User(
                id=user_info["id"],
                name=user_info["display_name"] or user_info["id"],
                email=user_info["email"],
                username=unique_username,
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
