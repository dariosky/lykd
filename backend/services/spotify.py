"""Spotify API integration"""

import datetime
import logging
import os
import secrets
from functools import partial
from typing import Any, AsyncGenerator
from urllib.parse import urlencode

import httpx
from sqlmodel import Session

import settings
from models.auth import User

from services.spotify_retry import exception_from_response, spotify_retry
from utils.cache import disk_cache
from utils.chunks import reverse_block_chunks
from fastapi import Request

logger = logging.getLogger("lykd.spotify")


class Spotify:
    """Handle Spotify OAuth flow and API calls"""

    def __init__(self, app_name: str = "lykd"):
        if app_name == "lykd":
            self.client_id = settings.SPOTIFY_CLIENT_ID
            self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        elif app_name == "spotlike":
            self.client_id = os.getenv("SPOTLIKE_CLIENT_ID")
            self.client_secret = os.getenv("SPOTLIKE_CLIENT_SECRET")
        else:
            raise Exception(f"Unknown app name: {app_name}")
        self.redirect_uri = f"{settings.API_URL}/spotify/callback"
        self.scopes = [
            "user-read-email",
            "user-read-private",  # to check if user is premium
            "user-library-read",
            "user-library-modify",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
            "user-read-recently-played",
            "user-top-read",
            # Playback control scopes
            "user-modify-playback-state",
            "user-read-playback-state",
            "user-read-currently-playing",
            "streaming",  # required for Web Playback SDK
        ]

        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify credentials not found in environment variables")

        # Initialize reusable HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            verify=settings.HTTPS_VERIFY,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        self.api_usage = 0  # track the number of API calls made

    async def close(self):
        """Explicitly close the HTTP client"""
        await self.client.aclose()

    def get_authorization_url(self) -> tuple[str, str]:
        """Generate authorization URL and state for OAuth flow"""
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

    async def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for access token"""
        token_url = "https://accounts.spotify.com/api/token"  # nosec: B105:hardcoded_password_string

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        response = await self.request("POST", url=token_url, data=data)

        return response.json()

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Spotify API"""
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self.request(
            "GET", url="https://api.spotify.com/v1/me", headers=headers
        )

        return response.json()

    async def refresh_token(self, *, user: User) -> dict[str, Any]:
        """Refresh access token using refresh token"""
        refresh_token = user.get_refresh_token()
        response = await self.request(
            "POST",
            url="https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )

        return response.json()

    @staticmethod
    def get_headers(user: User) -> dict[str, str]:
        if user:
            access_token = user.get_access_token()
            return {"Authorization": f"Bearer {access_token}"}
        else:
            return {}

    @disk_cache(
        cache_dir=f"{settings.BACKEND_DIR}/.cache/spotify",
        namespace="spotify",
        enable=settings.CACHE_ENABLED,
    )
    async def get_page(
        self,
        *,
        url: str,
        user: "User",
        db_session: Session,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get a page given an endpoint in the Spotify API"""
        response = await self.request(
            "GET",
            user=user,
            db_session=db_session,
            url=url,
            headers=self.get_headers(user),
            params=params,
        )

        return response.json()

    async def get_liked_page(
        self,
        *,
        user: "User",
        db_session: Session,
        next_page: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        url = next_page or "https://api.spotify.com/v1/me/tracks"
        logger.debug(f"Fetching liked page for {user} - {url}")
        return await self.get_page(
            url=url,
            user=user,
            db_session=db_session,
            params={"limit": limit} if not next_page else None,
        )

    async def get_recently_played_page(
        self,
        *,
        user: "User",
        db_session: Session,
        next_page: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        url = next_page or "https://api.spotify.com/v1/me/player/recently-played"
        logger.debug(f"Fetching recent page for {user} - {url}")
        return await self.get_page(
            url=url,
            user=user,
            db_session=db_session,
            params={"limit": limit} if not next_page else None,
        )

    async def get_playlists_page(
        self,
        *,
        user: "User",
        db_session: Session,
        next_page: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        url = next_page or "https://api.spotify.com/v1/me/playlists"
        logger.debug(f"Fetching user playlists for {user}: {url}")
        return await self.get_page(
            url=url,
            user=user,
            db_session=db_session,
            params={"limit": limit} if not next_page else None,
        )

    async def get_playlist_tracks(
        self,
        *,
        playlist_id,
        user: "User",
        db_session: Session,
        next_page: str | None = None,
        limit: int = 50,
    ):
        url = next_page or f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        logger.debug(f"Fetching playlists tracks for {user}: {url}")
        return await self.get_page(
            url=url,
            user=user,
            db_session=db_session,
            params={"limit": limit} if not next_page else None,
        )

    @staticmethod
    async def get_all(
        *, user: User, request, db_session: Session, limit=50
    ) -> list[dict[str, Any]]:
        """Get all liked songs for a user by iterating through all pages"""
        items = []
        next_page = None
        while True:
            response = await request(
                user=user, db_session=db_session, limit=limit, next_page=next_page
            )
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
    async def yield_from(*, user: User, db_session: Session, request, limit=50):
        """Yield results from a paginated list of requests"""
        next_page = None
        while True:
            response = await request(
                user=user, db_session=db_session, limit=limit, next_page=next_page
            )
            page = response.get("items", [])

            if not page:
                break
            for item in page:
                yield item

            # Check if there are more tracks
            next_page = response.get("next")
            if not next_page:
                break

    async def get_all_playlists(self, user: User, db_session: Session):
        return await self.get_all(
            user=user, db_session=db_session, request=self.get_playlists_page
        )

    async def playlist_create(
        self,
        *,
        user: User,
        db_session: Session,
        description: str | None,
        name: str,
        public: bool,
    ):
        logger.info(f"Creating playlist {name} for {user}")
        url = f"https://api.spotify.com/v1/users/{user.id}/playlists"
        response = await self.request(
            "POST",
            user=user,
            db_session=db_session,
            url=url,
            json={
                "name": name,
                "description": description,
                "public": public,
            },
        )
        return response.json()

    async def delete_playlist(
        self, *, user: User, db_session: Session, playlist_id: str
    ) -> None:
        logger.info(f"Deleting playlist {playlist_id} for {user}")
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/followers"
        response = await self.request(
            "DELETE",
            user=user,
            db_session=db_session,
            url=url,
        )
        return None

    async def playlist_change(
        self,
        *,
        user: User,
        db_session: Session,
        playlist_id: str,
        name: str | None = None,
        description: str | None = None,
        public: bool | None = None,
        collaborative: bool | None = None,
    ) -> None:
        """Update playlist details"""
        logger.info(f"Updating playlist {playlist_id} for {user}")
        payload: dict[str, Any] = dict(
            name=name,
            description=description,
            public=public,
            collaborative=collaborative,
        )
        payload = {k: v for k, v in payload.items() if v is not None}
        if not payload:
            logger.debug("playlist_change called with no changes; skipping request")
            return None
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
        response = await self.request(
            "PUT",
            user=user,
            db_session=db_session,
            url=url,
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        return None

    async def change_playlist(
        self,
        *,
        user: User,
        db_session: Session,
        playlist_id: str,
        tracks_to_add: list[str] | None = None,
        tracks_to_remove: set[str] | None = None,
    ):
        """Change a playlist by adding and/or removing tracks"""
        logger.info(f"Changing playlist {playlist_id} for {user}")
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        snapshot_id = None
        if tracks_to_remove:
            logger.debug(
                f"Removing {len(tracks_to_remove)} tracks from playlist {playlist_id}"
            )
            for tracks in reverse_block_chunks(tracks_to_remove, 100):
                payload = {"tracks": [{"uri": get_uri(t)} for t in tracks]}
                remove_response = await self.request(
                    "DELETE",
                    user=user,
                    db_session=db_session,
                    url=url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                snapshot_id = remove_response.json()["snapshot_id"]
        if tracks_to_add:
            logger.debug(
                f"Adding {len(tracks_to_add)} tracks to playlist {playlist_id}"
            )
            for tracks in reverse_block_chunks(tracks_to_add, 100):
                payload = {
                    "uris": [get_uri(t) for t in tracks],
                    "position": 0,
                }
                add_response = await self.request(
                    "POST",
                    user=user,
                    db_session=db_session,
                    url=url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                snapshot_id = add_response.json()["snapshot_id"]
        return snapshot_id

    async def yield_tracks(
        self, *, user: User, db_session: Session, tracks: set
    ) -> AsyncGenerator[dict]:
        """yield tracks from a set of track IDs"""
        for chunk in reverse_block_chunks(tracks, 50):
            resp = await self.get_page(
                url="https://api.spotify.com/v1/tracks",
                user=user,
                db_session=db_session,
                params={"ids": ",".join(chunk)},
            )
            tracks = resp.get("tracks", [])
            for track_data in tracks:
                # we skip all that don't have a track (i.e. shows)
                if (track := track_data.get("track", {})) and (track.get("id")):
                    yield track_data

    async def get_all_likes(
        self, *, user: User, db_session: Session
    ) -> list[dict[str, Any]]:
        return [
            like_data
            for like_data in await self.get_all(
                user=user,
                db_session=db_session,
                request=self.get_liked_page,
            )
            if (track := like_data.get("track", {})) and (track.get("id"))
        ]

    async def get_all_playlist_tracks(
        self, *, playlist_id: str, user: User, db_session: Session
    ) -> list[dict[str, Any]]:
        playlist_request = partial(self.get_playlist_tracks, playlist_id=playlist_id)
        return [
            item
            for item in await self.get_all(
                user=user,
                db_session=db_session,
                request=playlist_request,
            )
            if (track := item.get("track", {})) and (track.get("id"))
        ]

    async def play(
        self,
        *,
        user: User,
        db_session: Session,
        uris: list[str] | None = None,
        position_ms: int | None = None,
    ):
        """Start/resume playback on the user's active device.
        If uris is provided, start playing those tracks immediately.
        """
        url = "https://api.spotify.com/v1/me/player/play"
        payload: dict[str, Any] = {}
        if uris:
            payload["uris"] = [get_uri(u) if ":" not in u else u for u in uris]
        if position_ms is not None:
            payload["position_ms"] = position_ms
        response = await self.request(
            "PUT",
            user=user,
            db_session=db_session,
            url=url,
            headers={"Content-Type": "application/json"},
            json=payload or None,
        )
        return None

    async def pause(self, *, user: User, db_session: Session) -> None:
        url = "https://api.spotify.com/v1/me/player/pause"
        response = await self.request(
            "PUT",
            user=user,
            db_session=db_session,
            url=url,
        )
        return None

    async def next(self, *, user: User, db_session: Session) -> None:
        url = "https://api.spotify.com/v1/me/player/next"
        response = await self.request(
            "POST",
            user=user,
            db_session=db_session,
            url=url,
        )
        return None

    async def transfer_playback(
        self, *, user: User, db_session: Session, device_id: str, play: bool = True
    ) -> None:
        url = "https://api.spotify.com/v1/me/player"
        payload = {"device_ids": [device_id], "play": play}
        response = await self.request(
            "PUT",
            user=user,
            db_session=db_session,
            url=url,
            headers={"Content-Type": "application/json"},
            json=payload,
        )
        return None

    async def get_playback_state(
        self, *, user: User, db_session: Session
    ) -> dict | None:
        """Return playback state or None if nothing is playing/no active device."""
        url = "https://api.spotify.com/v1/me/player"
        response = await self.request(
            "GET",
            user=user,
            db_session=db_session,
            url=url,
            allowed_statuses={200, 202, 204, 404},
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code in (202, 204, 404):
            # 404 can be returned when no active device
            return None
        raise exception_from_response(response, f"GET {url} failed")

    async def get_track(
        self, *, user: User, db_session: Session, track_id: str
    ) -> dict:
        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        response = await self.request(
            "GET",
            user=user,
            db_session=db_session,
            url=url,
        )
        return response.json()

    async def set_liked_track(
        self,
        *,
        user: User,
        db_session: Session,
        track_id: str,
        liked: bool,
        liked_at: datetime.datetime | None = None,
    ) -> None:
        """Save or remove a track from the user's likes."""
        url = "https://api.spotify.com/v1/me/tracks"
        if liked:
            params: dict[str, Any] = {"ids": [track_id]}
            if liked_at:
                params["timestamped_ids"] = [
                    {
                        "id": track_id,
                        "added_at": liked_at.isoformat(),
                    }
                ]
            response = await self.request(
                "PUT",
                user=user,
                db_session=db_session,
                url=url,
                params=params,
            )
        else:
            response = await self.request(
                "DELETE",
                user=user,
                db_session=db_session,
                url=url,
                params={"ids": [track_id]},
            )
        return None

    @spotify_retry()
    async def request(
        self,
        method: str,
        *,
        user: User = None,
        db_session: Session = None,
        url: str,
        allowed_statuses: set[int] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Centralized HTTP request method for Spotify API calls with retry logic."""
        if user:
            headers = kwargs.pop("headers", {})
            headers = {**self.get_headers(user), **headers}
            kwargs["headers"] = headers
        response = await self.client.request(method, url, **kwargs)
        self.api_usage += 1
        if allowed_statuses:
            if response.status_code in allowed_statuses:
                return response
        elif not (200 <= response.status_code < 300):
            raise exception_from_response(response, f"Request to {url} failed")
        return response


def get_spotify_client(request: Request) -> Spotify:
    spotify = request.app.state.spotify
    return spotify


def get_uri(track_id: str, track_type: str = "track"):
    return "spotify:" + track_type + ":" + track_id
