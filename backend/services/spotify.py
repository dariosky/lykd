"""Spotify API integration"""

import secrets
import httpx
from typing import Dict, Any, TYPE_CHECKING
from urllib.parse import urlencode
from fastapi import HTTPException
from tenacity import retry, stop_after_attempt, retry_if_exception_type

import settings

if TYPE_CHECKING:
    from models.auth import User


class Spotify:
    """Handle Spotify OAuth flow and API calls"""

    def __init__(self):
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

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close the client"""
        await self.client.aclose()

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
            raise HTTPException(
                status_code=400,
                detail=f"Failed to exchange code for token: {response.text}",
            )

        return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Spotify API"""
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self.client.get(
            "https://api.spotify.com/v1/me", headers=headers
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=400, detail=f"Failed to get user info: {response.text}"
            )

        return response.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""

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
            raise HTTPException(
                status_code=400, detail=f"Failed to refresh token: {response.text}"
            )

        return response.json()

    async def get_liked_songs(
        self, access_token: str, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """Get user's liked songs from Spotify API"""
        headers = {"Authorization": f"Bearer {access_token}"}

        params = {
            "limit": limit,
            "offset": offset,
            "market": "from_token",  # Use user's market
        }

        response = await self.client.get(
            "https://api.spotify.com/v1/me/tracks", headers=headers, params=params
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get liked songs: {response.text}",
            )

        return response.json()

    async def get_all_liked_songs(self, access_token: str) -> list[Dict[str, Any]]:
        """Get all liked songs for a user by iterating through all pages"""
        all_tracks = []
        limit = 50  # Maximum allowed by Spotify API
        offset = 0

        while True:
            try:
                response = await self.get_liked_songs(access_token, limit, offset)
                tracks = response.get("items", [])

                if not tracks:
                    break

                all_tracks.extend(tracks)

                # Check if there are more tracks
                if len(tracks) < limit:
                    break

                offset += limit

            except HTTPException as e:
                if e.status_code == 401:
                    # Token might be expired, re-raise to handle token refresh
                    raise
                else:
                    # Log other errors but continue
                    print(f"Error fetching liked songs at offset {offset}: {e.detail}")
                    break

        return all_tracks

    async def get_all_liked_songs_for_user(self, user: "User") -> list[Dict[str, Any]]:
        """Get all liked songs for a user with automatic token refresh handling"""

        @retry(
            stop=stop_after_attempt(2),
            retry=retry_if_exception_type(HTTPException),
        )
        async def _fetch_with_retry():
            access_token = user.tokens.get("access_token")

            if not access_token:
                raise HTTPException(
                    status_code=400, detail="No access token found for user"
                )

            try:
                return await self.get_all_liked_songs(access_token)
            except HTTPException as e:
                if e.status_code == 401 or (
                    e.status_code == 400 and "Refresh token revoked" in e.detail
                ):
                    # Try to refresh the token
                    refresh_token = user.tokens.get("refresh_token")
                    if not refresh_token:
                        user.tokens.clear()
                        raise HTTPException(
                            status_code=400, detail="No refresh token available"
                        )

                    try:
                        token_data = await self.refresh_token(refresh_token)

                        # Update user tokens
                        user.tokens.update(
                            {
                                "access_token": token_data["access_token"],
                                "expires_in": token_data.get("expires_in"),
                                "refresh_token": token_data.get(
                                    "refresh_token", refresh_token
                                ),
                            }
                        )

                        # Retry with new token
                        return await self.get_all_liked_songs(
                            token_data["access_token"]
                        )

                    except HTTPException as refresh_error:
                        if (
                            refresh_error.status_code == 400
                            and "Refresh token revoked" in refresh_error.detail
                        ):
                            print(
                                f"Refresh token revoked for user {user.email}. Clearing tokens."
                            )
                            user.tokens.clear()
                        raise refresh_error
                else:
                    raise e

        try:
            return await _fetch_with_retry()
        except HTTPException:
            print(f"Failed to fetch liked songs for user {user.email}")
            return []
