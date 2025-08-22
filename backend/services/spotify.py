"""Spotify API integration"""

import logging
import secrets
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

    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
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

    async def close(self):
        """Explicitly close the HTTP client"""
        await self.client.aclose()

    @spotify_retry()
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

    @spotify_retry()
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

        response = await self.client.post(token_url, data=data)

        if response.status_code != 200:
            raise exception_from_response(response, "Failed to exchange code for token")

        return response.json()

    @spotify_retry()
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Spotify API"""
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self.client.get(
            "https://api.spotify.com/v1/me", headers=headers
        )

        if response.status_code != 200:
            raise exception_from_response(response, "Failed to get user info")

        return response.json()

    @spotify_retry()
    async def refresh_token(self, *, user: User) -> dict[str, Any]:
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
        enable=settings.CACHE_ENABLED,
    )
    @spotify_retry()
    async def get_page(
        self,
        *,
        url: str,
        user: "User",
        db_session: Session,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get a page given an endpoint in the Spotify API"""
        response = await self.client.get(
            url, headers=self.get_headers(user), params=params
        )

        if response.status_code != 200:
            raise exception_from_response(response, f"GET {url} failed")

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

    @spotify_retry()
    async def get_or_create_playlist(
        self, user: User, db_session: Session, playlist_name: str
    ):
        playlists = await self.get_all_playlists(user=user, db_session=db_session)
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
                    logger.debug(f"Removing duplicated playlist {playlist_id}")
                    await self.delete_playlist(user, playlist_id)

        return playlist

    async def get_all_playlists(self, user: User, db_session: Session):
        return await self.get_all(
            user=user, db_session=db_session, request=self.get_playlists_page
        )

    @spotify_retry()
    async def playlist_create(
        self,
        user: User,
        db_session: Session,
        description: str | None,
        name: str,
        public: bool,
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

    @spotify_retry()
    async def delete_playlist(
        self, user: User, db_session: Session, playlist_id: str
    ) -> None:
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
        db_session: Session,
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

                remove_response = await self.client.request(
                    method="DELETE",
                    url=url,
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

    async def yield_tracks(
        self, user: User, db_session: Session, tracks: set
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
                yield track_data

    @spotify_retry()
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
        headers = {**self.get_headers(user), "Content-Type": "application/json"}
        response = await self.client.put(url, headers=headers, json=payload or None)
        if response.status_code not in (200, 202, 204):
            raise exception_from_response(response, f"PUT {url} failed")
        return None

    @spotify_retry()
    async def pause(self, *, user: User, db_session: Session) -> None:
        url = "https://api.spotify.com/v1/me/player/pause"
        response = await self.client.put(url, headers=self.get_headers(user))
        if response.status_code not in (200, 202, 204):
            raise exception_from_response(response, f"PUT {url} failed")
        return None

    @spotify_retry()
    async def next(self, *, user: User, db_session: Session) -> None:
        url = "https://api.spotify.com/v1/me/player/next"
        response = await self.client.post(url, headers=self.get_headers(user))
        if response.status_code not in (200, 202, 204):
            raise exception_from_response(response, f"POST {url} failed")
        return None

    @spotify_retry()
    async def transfer_playback(
        self, *, user: User, db_session: Session, device_id: str, play: bool = True
    ) -> None:
        url = "https://api.spotify.com/v1/me/player"
        payload = {"device_ids": [device_id], "play": play}
        response = await self.client.put(
            url,
            headers={**self.get_headers(user), "Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code not in (200, 202, 204):
            raise exception_from_response(response, f"PUT {url} failed")
        return None

    @spotify_retry()
    async def get_playback_state(
        self, *, user: User, db_session: Session
    ) -> dict | None:
        """Return playback state or None if nothing is playing/no active device."""
        url = "https://api.spotify.com/v1/me/player"
        response = await self.client.get(url, headers=self.get_headers(user))
        if response.status_code == 200:
            return response.json()
        if response.status_code in (202, 204, 404):
            # 404 can be returned when no active device
            return None
        raise exception_from_response(response, f"GET {url} failed")

    @spotify_retry()
    async def get_track(
        self, *, user: User, db_session: Session, track_id: str
    ) -> dict:
        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        response = await self.client.get(url, headers=self.get_headers(user))
        if response.status_code != 200:
            raise exception_from_response(response, f"GET {url} failed")
        return response.json()


def get_spotify_client(request: Request) -> Spotify:
    spotify = request.app.state.spotify
    return spotify


def get_uri(track_id: str, track_type: str = "track"):
    return "spotify:" + track_type + ":" + track_id
