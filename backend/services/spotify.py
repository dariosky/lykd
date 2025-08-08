"""Spotify API integration"""

import logging
import secrets
from functools import partial
from typing import Any, Dict
from urllib.parse import urlencode

import httpx
from tenacity.wait import wait_base

import settings
from fastapi import HTTPException
from models.auth import User
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_random,
    Future,
)

logger = logging.getLogger("lykd.spotify")


def exception_from_response(response: httpx.Response, prefix=None) -> HTTPException:
    """Create an HTTPException from a httpx response"""
    return HTTPException(
        status_code=response.status_code,
        detail=f"{prefix}: {response.text}" if prefix else response.text,
        headers=response.headers,
    )


class wait_retry_after_or_default(wait_base):
    def __init__(self, default_wait):
        self.default_wait = default_wait

    def __call__(self, retry_state):
        ex = retry_state.outcome.exception()
        if isinstance(ex, HTTPException):
            retry_after = getattr(ex, "headers", {}).get("Retry-After")
            if retry_after is not None:
                try:
                    return max(0, int(retry_after))
                except ValueError:
                    pass
        return self.default_wait(retry_state)


async def renew_token_if_expired(retry_state):
    """Renew token if the retry is due to an expired token"""
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        if isinstance(exception, HTTPException):
            if "user" in retry_state.kwargs:
                user: User = retry_state.kwargs[
                    "user"
                ]  # we need a user to renew the token
                spotify: Spotify = retry_state.args[0]
                if (
                    exception.status_code == 401
                    and "access token expired" in exception.detail
                ):
                    user.tokens.update(await spotify.refresh_token(user=user))
                    if spotify.db_session:
                        logger.debug(f"Refreshed the user {user.email} tokens")
                        spotify.db_session.add(user)
                        spotify.db_session.commit()
                elif (
                    exception.status_code == 400
                    and "Refresh token revoked" in exception.detail
                ):
                    logger.warning("User is gone, marking as inactive")
                    user.tokens = None
                    if spotify.db_session:
                        logger.debug(f"Refreshed the user {user.email} tokens")
                        spotify.db_session.add(user)
                        spotify.db_session.commit()
                    fut = Future(attempt_number=retry_state.attempt_number)
                    fut.set_result(None)
                    retry_state.outcome = fut  # replace the finished future
                    raise exception
            if (
                exception.status_code >= 400
                and exception.status_code < 500
                and exception.status_code != 429
            ):
                # don't retry on 4xx errors but 429
                raise exception


spotify_retry = partial(
    retry,
    before_sleep=before_sleep_log(logger, logging.WARNING),
    wait=wait_retry_after_or_default(default_wait=wait_random(0, 0.5)),
    stop=stop_after_attempt(2),
    reraise=True,
    after=renew_token_if_expired,
)


class Spotify:
    """Handle Spotify OAuth flow and API calls"""

    def __init__(self, db_session=None):
        self.db_session = db_session
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = f"{settings.SELF_URL}/spotify/callback"
        self.scopes = [
            "user-read-email",
            "user-library-read",
            "user-library-modify",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
            "user-read-recently-played",
            "user-top-read",
        ]

        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify credentials not found in environment variables")

        # Initialize reusable HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            verify=False,  # Remove in production
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def close(self):
        """Explicitly close the HTTP client"""
        await self.client.aclose()

    @spotify_retry()
    def get_authorization_url(self) -> tuple[str, str]:
        """Generate authorization URL and state for OAuth flow"""
        # TODO: save the state in memory?
        state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state,
            "show_dialog": "true",
        }

        auth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
        return auth_url, state

    @spotify_retry()
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        token_url = "https://accounts.spotify.com/api/token"

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = await self.client.post(token_url, data=data)

        if response.status_code != 200:
            raise exception_from_response(response, "Failed to exchange code for token")

        return response.json()

    @spotify_retry()
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Spotify API"""
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self.client.get(
            "https://api.spotify.com/v1/me", headers=headers
        )

        if response.status_code != 200:
            raise exception_from_response(response, "Failed to get user info")

        return response.json()

    @spotify_retry()
    async def refresh_token(self, *, user: User) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        refresh_token = user.get_refresh_token()
        response = await self.client.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )

        if response.status_code != 200:
            raise exception_from_response(response, "Failed to exchange code for token")

        return response.json()

    @spotify_retry()
    async def get_liked_page(
        self, *, user: "User", limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's liked songs from Spotify API"""
        access_token = user.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        params = {
            "offset": offset,
            "limit": limit,
        }
        logger.debug(f"Fetching liked page for {user.email} - {offset}...")

        response = await self.client.get(
            "https://api.spotify.com/v1/me/tracks", headers=headers, params=params
        )

        if response.status_code != 200:
            raise exception_from_response(response, "Failed to get liked songs")

        return response.json()

    async def get_all(self, *, user: User, request, limit=50) -> list[Dict[str, Any]]:
        """Get all liked songs for a user by iterating through all pages"""
        items = []
        offset = 0

        while True:
            response = await request(user=user, limit=limit, offset=offset)
            page = response.get("items", [])

            if not page:
                break

            items.extend(page)

            # Check if there are more tracks
            next_url = response.get("next")
            if len(page) < limit or not next_url:
                break

            offset += limit

        return items
