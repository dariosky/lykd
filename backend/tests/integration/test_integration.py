"""Integration tests for complete application flows."""

import pytest
from unittest.mock import patch


class TestSpotifyOAuthIntegration:
    """Test complete Spotify OAuth integration flow."""

    @pytest.mark.asyncio
    async def test_complete_oauth_flow_new_user(self, client, test_session, httpx_mock):
        """Test complete OAuth flow for a new user."""
        # Step 1: Get authorization URL
        auth_response = client.get("/spotify/authorize")
        assert auth_response.status_code == 200
        auth_data = auth_response.json()
        assert "authorization_url" in auth_data
        assert "state" in auth_data

        # Step 2: Mock Spotify API calls for callback
        mock_token_data = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "scope": "user-read-email user-library-read",
        }

        mock_user_data = {
            "id": "integration_user_123",
            "display_name": "Integration Test User",
            "email": "integration@example.com",
            "images": [{"url": "https://example.com/integration.jpg"}],
        }

        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json=mock_token_data,
            status_code=200,
        )

        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            json=mock_user_data,
            status_code=200,
        )

        # Step 3: Handle callback
        callback_response = client.get(
            f"/spotify/callback?code=test_code&state={auth_data['state']}",
            follow_redirects=False,
        )

        assert callback_response.status_code == 302
        assert "127.0.0.1:3000" in callback_response.headers["location"]
        assert "spotify=connected" in callback_response.headers["location"]

        # Step 4: Verify user was created in database
        from models.auth import User

        user = (
            test_session.query(User)
            .filter(User.email == mock_user_data["email"])
            .first()
        )
        assert user is not None
        assert user.id == mock_user_data["id"]
        assert user.name == mock_user_data["display_name"]
        assert user.tokens["access_token"] == mock_token_data["access_token"]

    @pytest.mark.asyncio
    async def test_oauth_flow_existing_user_token_update(
        self, client, test_user, test_session, httpx_mock
    ):
        """Test OAuth flow updates tokens for existing user."""
        original_token = test_user.tokens.get("access_token")

        # Get a valid state first
        auth_response = client.get("/spotify/authorize")
        assert auth_response.status_code == 200
        state = auth_response.json()["state"]

        new_token_data = {
            "access_token": "updated_access_token",
            "refresh_token": "updated_refresh_token",
            "expires_in": 3600,
            "scope": "user-read-email user-library-read",
        }

        updated_user_data = {
            "id": test_user.id,
            "display_name": "Updated Name",
            "email": test_user.email,
            "images": [{"url": "https://example.com/updated.jpg"}],
        }

        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json=new_token_data,
            status_code=200,
        )

        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            json=updated_user_data,
            status_code=200,
        )

        callback_response = client.get(
            f"/spotify/callback?code=test_code&state={state}", follow_redirects=False
        )
        assert callback_response.status_code == 302

        # Verify user tokens were updated
        assert test_user.tokens["access_token"] == "updated_access_token"
        assert test_user.tokens["access_token"] != original_token
        assert test_user.name == "Updated Name"

    def test_protected_endpoints_without_auth(self, client):
        """Test that protected endpoints work properly without authentication."""
        # /user/me should return null user when not authenticated
        response = client.get("/user/me")
        assert response.status_code == 200
        assert response.json()["user"] is None

    def test_session_management_flow(self, client, test_user, test_app):
        """Test complete session management flow."""
        # Start without authentication
        response = client.get("/user/me")
        assert response.json()["user"] is None

        # Mock the get_current_user dependency to return our test user
        from routes.deps import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: test_user

        # Now should be authenticated
        response = client.get("/user/me")
        assert response.json()["user"]["id"] == test_user.id

        # Test logout
        logout_response = client.post("/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["message"] == "Logged out successfully"

        # Clean up dependency override
        del test_app.dependency_overrides[get_current_user]


class TestDatabaseIntegration:
    """Test database integration with the application."""

    def test_user_persistence_across_requests(self, client, test_user, test_app):
        """Test that user data persists correctly across requests."""
        from routes.deps import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: test_user

        # Make multiple requests and verify data consistency
        for _ in range(3):
            response = client.get("/user/me")
            assert response.status_code == 200
            user_data = response.json()["user"]
            assert user_data["id"] == test_user.id
            assert user_data["email"] == test_user.email
            assert user_data["name"] == test_user.name

        # Clean up dependency override
        del test_app.dependency_overrides[get_current_user]

    def test_database_transaction_handling(self, client, test_session, httpx_mock):
        """Test that database transactions are handled correctly."""
        from models.auth import User

        # Count users before
        initial_count = test_session.query(User).count()

        # Get a valid state first
        auth_response = client.get("/spotify/authorize")
        assert auth_response.status_code == 200
        state = auth_response.json()["state"]

        # Mock failed token exchange
        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json={"error": "invalid_grant"},
            status_code=400,
        )

        response = client.get(
            f"/spotify/callback?code=test_code&state={state}", follow_redirects=False
        )
        assert response.status_code == 302
        assert "error" in response.headers["location"]

        # Verify no new users were created due to the error
        final_count = test_session.query(User).count()
        assert final_count == initial_count


class TestErrorHandling:
    """Test error handling across the application."""

    def test_spotify_api_error_handling(self, client, httpx_mock):
        """Test handling of Spotify API errors."""
        # Get a valid state first
        auth_response = client.get("/spotify/authorize")
        assert auth_response.status_code == 200
        state = auth_response.json()["state"]

        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json={"error": "invalid_grant"},
            status_code=400,
        )

        response = client.get(
            f"/spotify/callback?code=invalid_code&state={state}",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "error" in response.headers["location"]

    def test_database_connection_error_handling(self, client):
        """Test handling of database connection errors."""
        with patch("models.common.get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            # This should handle the database error gracefully
            client.get("/user/me")
            # The exact response depends on your error handling implementation
            # but it should not crash the application


class TestApplicationConfiguration:
    """Test application configuration and initialization."""

    def test_app_creation_with_middleware(self, test_app):
        """Test that the FastAPI app is created with proper middleware."""
        # Check that middleware is configured
        middleware_classes = [middleware.cls for middleware in test_app.user_middleware]

        # Should have SessionMiddleware and BrotliMiddleware
        assert len(middleware_classes) >= 2

    def test_app_metadata(self, test_app):
        """Test application metadata configuration."""
        assert test_app.title == "LYKD"
        assert test_app.description == "Your likes made social"
        assert "version" in test_app.openapi()["info"]

    def test_environment_variable_handling(self):
        """Test that environment variables are properly handled."""
        import os

        # These should be set by our test configuration
        assert os.getenv("TESTING") == "true"
        assert os.getenv("SPOTIFY_CLIENT_ID") == "test_client_id"
        assert os.getenv("DATABASE_URL") == "sqlite:///:memory:"
