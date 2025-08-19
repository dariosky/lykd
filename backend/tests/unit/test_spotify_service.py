"""Unit tests for Spotify service with mocked API calls using pytest-httpx."""

import pytest
from unittest.mock import patch
from fastapi import HTTPException

import settings
from models.auth import User
from services.spotify import Spotify


def get_test_user(
    access_token: str = "access token", refresh_token: str = "refresh token"
) -> User:
    return User(
        id="test",
        name="Test User",
        email="f@t",
        tokens={"refresh_token": refresh_token, "access_token": access_token},
    )


class TestSpotifyService:
    """Test Spotify service with mocked API calls."""

    @pytest.fixture
    def spotify_service(self):
        """Create a Spotify service instance for testing."""
        return Spotify()

    def test_spotify_initialization(self):
        """Test Spotify service initialization."""
        spotify = Spotify()
        assert spotify.client_id == "test_client_id"
        assert spotify.client_secret == "test_client_secret"
        assert "127.0.0.1:3000/api/spotify/callback" in spotify.redirect_uri
        assert len(spotify.scopes) > 0
        assert "user-read-email" in spotify.scopes

    def test_spotify_initialization_missing_credentials(self):
        """Test Spotify initialization fails with missing credentials."""
        with patch.object(settings, "SPOTIFY_CLIENT_ID", ""):
            with pytest.raises(ValueError, match="Spotify credentials not found"):
                Spotify()

    def test_get_authorization_url(self, spotify_service):
        """Test get_authorization_url generates proper URL and state."""
        auth_url, state = spotify_service.get_authorization_url()

        assert "spotify.com/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "response_type=code" in auth_url
        assert "redirect_uri=" in auth_url
        assert "scope=" in auth_url
        assert f"state={state}" in auth_url
        assert len(state) >= 32  # Check state is sufficiently random

    async def test_exchange_code_for_token_success(
        self, spotify_service, httpx_mock, test_token_data
    ):
        """Test successful token exchange using pytest-httpx."""
        # Mock the Spotify token endpoint
        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json=test_token_data,
            status_code=200,
        )

        result = await spotify_service.exchange_code_for_token("test_code")

        assert result == test_token_data

    async def test_exchange_code_for_token_failure(self, spotify_service, httpx_mock):
        """Test token exchange failure handling."""
        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json={"error": "invalid_grant"},
            status_code=400,
            is_reusable=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await spotify_service.exchange_code_for_token("invalid code")

        assert exc_info.value.status_code == 400
        assert "Failed to exchange code for token" in str(exc_info.value.detail)

    async def test_get_user_info_success(
        self, spotify_service, httpx_mock, test_user_data
    ):
        """Test successful user info retrieval."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            json=test_user_data,
            status_code=200,
        )

        result = await spotify_service.get_user_info("test_access_token")

        assert result == test_user_data

    async def test_get_user_info_failure(self, spotify_service, httpx_mock):
        """Test user info retrieval failure."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            json={"error": {"status": 400, "message": "access token expired"}},
            status_code=400,
        )

        with pytest.raises(HTTPException) as exc_info:
            await spotify_service.get_user_info("invalid_token")

        assert exc_info.value.status_code == 400

    async def test_get_liked_songs_success(
        self, spotify_service, httpx_mock, mock_spotify_responses
    ):
        """Test successful liked songs retrieval."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me/tracks?limit=50",
            json=mock_spotify_responses["liked_songs"],
            status_code=200,
        )

        result = await spotify_service.get_liked_page(user=get_test_user())

        assert result == mock_spotify_responses["liked_songs"]

    async def test_get_liked_songs_with_pagination(self, spotify_service, httpx_mock):
        """Test liked songs retrieval with pagination."""
        # First page
        second_page_url = "https://api.spotify.com/v1/me/tracks?offset=1&limit=1"
        first_page = {
            "items": [{"track": {"id": "track1", "name": "Song 1"}}],
            "next": second_page_url,
            "total": 100,
        }

        # Second page
        second_page = {
            "items": [{"track": {"id": "track2", "name": "Song 2"}}],
            "next": None,
            "total": 100,
        }

        # Mock both requests
        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me/tracks?limit=1",
            json=first_page,
            status_code=200,
        )

        httpx_mock.add_response(
            method="GET",
            url=second_page_url,
            json=second_page,
            status_code=200,
        )

        result = await spotify_service.get_all(
            user=get_test_user(), request=spotify_service.get_liked_page, limit=1
        )

        assert len(result) == 2
        assert result[0]["track"]["id"] == "track1"
        assert result[1]["track"]["id"] == "track2"

    async def test_refresh_token_success(self, spotify_service, httpx_mock):
        """Test successful token refresh."""
        new_token_data = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "scope": "user-read-email",
        }

        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json=new_token_data,
            status_code=200,
        )

        result = await spotify_service.refresh_token(user=get_test_user())

        assert result == new_token_data

    async def test_refresh_token_failure(self, spotify_service, httpx_mock):
        """Test token refresh failure."""
        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json={"error": "invalid_grant"},
            status_code=400,
        )

        with pytest.raises(HTTPException) as exc_info:
            await spotify_service.refresh_token(
                user=get_test_user(
                    access_token="invalid_token", refresh_token="invalid_token"
                )
            )

        assert exc_info.value.status_code == 400
        assert (
            str(exc_info.value.detail)
            == 'Failed to exchange code for token: {"error":"invalid_grant"}'
        )

    async def test_rate_limit_handling(self, spotify_service, httpx_mock):
        """Test rate limit handling with retry logic."""
        # First call returns 429 (rate limited)
        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            status_code=429,
            headers={"Retry-After": "1"},
        )

        # Second call succeeds
        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            json={"id": "user123"},
            status_code=200,
        )

        # This should retry and succeed
        with patch("asyncio.sleep") as mock_sleep:
            result = await spotify_service.get_user_info("test_token")
            assert result == {"id": "user123"}
            mock_sleep.assert_called_once_with(1)

    @pytest.mark.parametrize(
        "status_code,error_data",
        [
            (400, {"error": "invalid_request", "error_description": "Invalid request"}),
            (401, {"error": "invalid_token", "error_description": "Token expired"}),
            (403, {"error": "forbidden", "error_description": "Insufficient scope"}),
            (429, {"error": "rate_limited", "error_description": "Too many requests"}),
            (
                500,
                {"error": "server_error", "error_description": "Internal server error"},
            ),
        ],
    )
    async def test_api_error_handling(
        self, spotify_service, httpx_mock, status_code, error_data
    ):
        """Test handling of various API error responses."""
        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            json=error_data,
            status_code=status_code,
            is_reusable=status_code in (429, 500),
        )

        with pytest.raises(HTTPException) as exc_info:
            await spotify_service.get_user_info("test_token")

        assert exc_info.value.status_code == status_code
