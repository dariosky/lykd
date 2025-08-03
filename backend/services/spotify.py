"""Spotify OAuth and API integration"""

import secrets
import httpx
from typing import Dict, Any
from urllib.parse import urlencode
from fastapi import HTTPException

import settings


class SpotifyOAuth:
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

        async with httpx.AsyncClient(
            verify=False
        ) as client:  # verify=False for self-signed certs, remove in production
            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to exchange code for token: {response.text}",
                )

            return response.json()

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Spotify API"""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                "https://api.spotify.com/v1/me", headers=headers
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400, detail=f"Failed to get user info: {response.text}"
                )

            return response.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        token_url = "https://accounts.spotify.com/api/token"

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=400, detail=f"Failed to refresh token: {response.text}"
                )

            return response.json()
