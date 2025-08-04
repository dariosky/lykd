import logging
import os
import tomllib
from pathlib import Path
from fastapi import FastAPI, Query, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from starlette.middleware.sessions import SessionMiddleware

import settings
# Import models and services
from models import User, get_session
from services import SpotifyOAuth
from settings import PROJECT_PATH

logger = logging.getLogger("lykd.main")

# Initialize Spotify OAuth
spotify_oauth = SpotifyOAuth()


def get_version() -> str:
    """Read version from pyproject.toml"""

    with open(PROJECT_PATH / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["version"]


def update_database():  # pragma: no cover
    """Init the DB or run the Alembic migrations"""
    import alembic.config

    if not Path("alembic.ini").is_file():
        os.chdir(Path(__file__).parent.parent)

    try:
        alembic.config.main(
            argv=[
                "--raiseerr",
                "upgrade",
                "head",
            ]
        )
    except Exception as e:
        logger.exception(f"Cannot run DB migrations: {e}")


def get_current_user_id(request: Request) -> str | None:
    """Get the current user ID from session"""
    return request.session.get("user_id")


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    """Get the current user from session"""
    user_id = get_current_user_id(request)
    if not user_id:
        return None
    return session.query(User).filter(User.id == user_id).first()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    update_database()
    app = FastAPI(
        title="LYKD",
        description="Your likes made social",
        version=get_version(),
    )

    # Add session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SESSION_SECRET_KEY,
    )

    @app.get("/")
    async def index():
        """Index endpoint returning version and status"""
        return {"version": get_version(), "status": "ok"}

    @app.get("/user/me")
    async def get_current_user_info(current_user: User | None = Depends(get_current_user)):
        """Get current user information"""
        if not current_user:
            return {"user": None}

        return {
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "picture": current_user.picture,
                "join_date": current_user.join_date.isoformat(),
                "is_admin": current_user.is_admin,
            }
        }

    @app.post("/logout")
    async def logout(request: Request):
        """Logout user by clearing session"""
        request.session.clear()
        return {"message": "Logged out successfully"}

    @app.get("/spotify/authorize")
    async def spotify_authorize():
        """Initiate Spotify OAuth flow"""
        auth_url, state = spotify_oauth.get_authorization_url()
        # In a real app, you might want to store the state in a session or cache
        return {"authorization_url": auth_url, "state": state}

    @app.get("/spotify/callback")
    async def spotify_callback(
        request: Request,
        code: str = Query(..., description="Authorization code from Spotify"),
        state: str = Query(..., description="State parameter for security"),
        error: str = Query(None, description="Error from Spotify OAuth"),
        session: Session = Depends(get_session),
    ):
        """Handle Spotify OAuth callback"""
        # TODO: Validate the state parameter to prevent CSRF attacks
        if error:
            return RedirectResponse(
                url=f"http://localhost:3000/error?message=Spotify authorization failed: {error}",
                status_code=302,
            )

        try:
            # Exchange code for token
            token_data = await spotify_oauth.exchange_code_for_token(code)

            # Get user information
            user_info = await spotify_oauth.get_user_info(token_data["access_token"])

            # Save or update user in database
            # Check if user already exists
            existing_user = (
                session.query(User).filter(User.email == user_info["email"]).first()
            )

            if existing_user:
                # Update existing user's tokens
                existing_user.tokens = {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "scope": token_data.get("scope"),
                }
                existing_user.name = user_info["display_name"] or user_info["id"]
                existing_user.picture = (
                    user_info["images"][0]["url"] if user_info.get("images") else ""
                )
                session.add(existing_user)
                user = existing_user
            else:
                # Create new user
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
                session.add(user)

            session.commit()
            session.refresh(user)

            # Store user ID in session
            request.session["user_id"] = user.id

            # Redirect to frontend with success
            return RedirectResponse(
                url="http://localhost:3000/?spotify=connected", status_code=302
            )

        except Exception as e:
            logger.exception(f"Error in Spotify callback: {e}")
            # Redirect to error page with error details
            error_message = (
                str(e)
                if str(e)
                else "Unknown error occurred during Spotify authorization"
            )
            return RedirectResponse(
                url=f"http://localhost:3000/error?message={error_message}",
                status_code=302,
            )

    return app
