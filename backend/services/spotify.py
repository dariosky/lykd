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

from services.slack import slack
from utils import humanize_milliseconds
from utils.cache import disk_cache
from utils.chunks import reverse_block_chunks
from utils.logs import ratelimited_log

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
                    wait_seconds = max(0, int(retry_after))
                    ratelimited_log(60 * 60)(
                        slack.send_message, "⚠️ Rate-limited by Spotify"
                    )
                    logger.debug(
                        f"Rate-limited, retry after {humanize_milliseconds(wait_seconds * 1000)} seconds"
                    )
                    return wait_seconds
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
                    updated_tokens = await spotify.refresh_token(user=user)
                    user.tokens = {
                        **(user.tokens or {}),
                        **updated_tokens,
                    }
                    if spotify.db_session:
                        logger.debug(f"Refreshed the user {user.email} tokens")
                        spotify.db_session.add(user)
                        spotify.db_session.commit()
                    return  # token refreshed - let's retry
                elif (
                    exception.status_code == 400
                    and "Refresh token revoked" in exception.detail
                ):
                    logger.warning("User is gone, marking as inactive")
                    slack.send_message(f"🛑User is gone: {user.email}")
                    user.tokens = None
                    if spotify.db_session:
                        logger.debug(f"Refreshed the user {user.email} tokens")
                        spotify.db_session.add(user)
                        spotify.db_session.commit()
                    fut = Future(attempt_number=retry_state.attempt_number)
                    fut.set_result(None)
                    retry_state.outcome = fut  # replace the finished future
                    raise exception
            if 400 <= exception.status_code < 500 and exception.status_code != 429:
                # don't retry on 4xx errors but 429
                raise exception


spotify_retry = partial(
    retry,
    before_sleep=before_sleep_log(logger, logging.WARNING),
    wait=wait_retry_after_or_default(
        default_wait=wait_random(0, 0 if settings.TESTING_MODE else 0.5)
    ),
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
        self.redirect_uri = f"{settings.API_URL}/spotify/callback"
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
            verify=not settings.DEBUG_MODE,
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
        token_url = "https://accounts.spotify.com/api/token"  # nosec: B105:hardcoded_password_string

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

    def get_headers(self, user: User):
        access_token = user.get_access_token()
        return {"Authorization": f"Bearer {access_token}"}

    @disk_cache(
        cache_dir=f"{settings.BACKEND_DIR}/.cache/spotify",
        namespace="spotify",
        enable=settings.DEBUG_MODE,
    )
    @spotify_retry()
    async def get_page(
        self, *, url: str, user: "User", params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Get a page given an endpoint in the Spotify API"""
        response = await self.client.get(
            url, headers=self.get_headers(user), params=params
        )

        if response.status_code != 200:
            raise exception_from_response(response, f"GET {url} failed")

        return response.json()

    async def get_liked_page(
        self, *, user: "User", next_page: str | None = None, limit: int = 50
    ) -> Dict[str, Any]:
        url = next_page or "https://api.spotify.com/v1/me/tracks"
        logger.debug(f"Fetching liked page for {user} - {url}...")
        return await self.get_page(
            url=url,
            user=user,
            params={"limit": limit} if not next_page else None,
        )

    async def get_recently_played_page(
        self, *, user: "User", next_page: str | None = None, limit: int = 50
    ) -> Dict[str, Any]:
        url = next_page or "https://api.spotify.com/v1/me/player/recently-played"
        logger.debug(f"Fetching recent page for {user} - {url}...")
        return await self.get_page(
            url=url, user=user, params={"limit": limit} if not next_page else None
        )

    async def get_playlists_page(
        self, *, user: "User", next_page: str | None = None, limit: int = 50
    ) -> Dict[str, Any]:
        url = next_page or "https://api.spotify.com/v1/me/playlists"
        logger.debug(f"Fetching playlists page for {user}: {url}")
        return await self.get_page(
            url=url,
            user=user,
            params={"limit": limit} if not next_page else None,
        )

    @staticmethod
    async def get_all(*, user: User, request, limit=50) -> list[Dict[str, Any]]:
        """Get all liked songs for a user by iterating through all pages"""
        items = []
        next_page = None
        while True:
            response = await request(user=user, limit=limit, next_page=next_page)
            page = response.get("items", [])

            if not page:
                break

            items.extend(page)

            # Check if there are more tracks
            next_page = response.get("next")
            if not next_page:
                break

        return items

    @staticmethod
    async def yield_from(*, user: User, request, limit=50):
        """Yield results from a paginated list of requests"""
        next_page = None
        while True:
            response = await request(user=user, limit=limit, next_page=next_page)
            page = response.get("items", [])

            if not page:
                break
            for item in page:
                yield item

            # Check if there are more tracks
            next_page = response.get("next")
            if not next_page:
                break

    @spotify_retry()
    async def get_or_create_playlist(self, user: User, playlist_name: str):
        playlists = await self.get_all_playlists(user)
        same_name_playlists = [
            p
            for p in playlists
            if p["name"] == playlist_name and p["owner"]["id"] == user.id
        ]

        if not same_name_playlists:
            playlist = await self.playlist_create(
                user,
                description="All the songs you like - synced by Lykd",
                name=playlist_name,
                public=False,
            )
        else:
            playlist = same_name_playlists[-1]  # getting the last
            if len(same_name_playlists) > 1:
                for duplicated_playlist in same_name_playlists[:-1]:
                    playlist_id = duplicated_playlist["id"]
                    logger.debug(f"Removing duplicated {playlist_id}")
                    await self.delete_playlist(user, playlist_id)

        return playlist

    async def get_all_playlists(self, user: User):
        return await self.get_all(user=user, request=self.get_playlists_page)

    @spotify_retry()
    async def playlist_create(
        self, user: User, description: str | None, name: str, public: bool
    ):
        logger.info(f"Creating playlist {name} for {user}")
        params = {"name": name, "description": description, public: public}
        url = f"https://api.spotify.com/v1/users/{user.id}/playlists"
        response = await self.client.post(
            url,
            headers=self.get_headers(user),
            json=params,
        )

        if response.status_code != 201:
            raise exception_from_response(response, f"Request to {url} failed")

        return response.json()

    async def delete_playlist(self, user, playlist_id: str) -> None:
        logger.info(f"Deleting playlist {playlist_id} for {user}")
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/followers"
        response = await self.client.delete(
            url,
            headers=self.get_headers(user),
        )

        if response.status_code != 200:
            raise exception_from_response(response, f"Delete {url} failed")

        return None

    @spotify_retry()
    async def change_playlist(
        self,
        user: User,
        playlist_id: str,
        tracks_to_add: list[str] | None = None,
        tracks_to_remove: set[str] | None = None,
    ):
        """Change a playlist by adding and/or removing tracks"""
        logger.info(f"Changing playlist {playlist_id} for {user}")

        # Remove tracks first if specified
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        if tracks_to_remove:
            logger.debug(
                f"Removing {len(tracks_to_remove)} tracks from playlist {playlist_id}"
            )
            for tracks in reverse_block_chunks(tracks_to_remove, 100):
                payload = {"tracks": [{"uri": get_uri(t)} for t in tracks]}

                remove_response = await self.client.delete(
                    url,
                    headers={
                        **self.get_headers(user),
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if remove_response.status_code != 200:
                    raise exception_from_response(
                        remove_response, f"Remove tracks from {url} failed"
                    )

        # Add tracks if specified
        if tracks_to_add:
            logger.debug(
                f"Adding {len(tracks_to_add)} tracks to playlist {playlist_id}"
            )
            for tracks in reverse_block_chunks(tracks_to_add, 100):
                payload = {
                    "uris": [get_uri(t) for t in tracks],
                    "position": 0,
                }
                add_response = await self.client.post(
                    url,
                    headers={
                        **self.get_headers(user),
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if add_response.status_code != 201:
                    raise exception_from_response(
                        add_response, f"Add tracks to {url} failed"
                    )


def get_uri(track_id: str, track_type: str = "track"):
    return "spotify:" + track_type + ":" + track_id
