"""Unit tests for main application endpoints."""

from unittest.mock import Mock


class TestAppEndpoints:
    """Test main application endpoints."""

    def test_index_endpoint(self, client):
        """Test the index endpoint returns version and status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["status"] == "ok"

    def test_get_current_user_info_unauthenticated(self, client):
        """Test get current user info when not authenticated."""
        response = client.get("/user/me")
        assert response.status_code == 200
        data = response.json()
        assert data["user"] is None

    def test_get_current_user_info_authenticated(self, client, test_user, test_app):
        """Test get current user info when authenticated."""
        # Mock the get_current_user dependency to return our test user
        from routes.deps import get_current_user

        test_app.dependency_overrides[get_current_user] = lambda: test_user

        response = client.get("/user/me")
        assert response.status_code == 200
        data = response.json()

        assert data["user"] is not None
        user_data = data["user"]
        assert user_data["id"] == test_user.id
        assert user_data["name"] == test_user.name
        assert user_data["email"] == test_user.email
        assert user_data["picture"] == test_user.picture
        assert "join_date" in user_data
        assert user_data["is_admin"] == test_user.is_admin

        # Clean up dependency override
        del test_app.dependency_overrides[get_current_user]

    def test_logout_endpoint(self, client):
        """Test logout endpoint clears session."""
        response = client.post("/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully"

    def test_spotify_authorize_endpoint(self, client):
        """Test Spotify authorization endpoint."""
        response = client.get("/spotify/authorize")
        assert response.status_code == 200
        data = response.json()

        assert "authorization_url" in data
        assert "state" in data
        assert "spotify.com/authorize" in data["authorization_url"]

    async def test_spotify_callback_success(self, client, test_session, httpx_mock):
        """Test successful Spotify OAuth callback."""
        # Get a valid state first
        auth_resp = client.get("/spotify/authorize")
        assert auth_resp.status_code == 200
        auth_state = auth_resp.json()["state"]

        # Mock Spotify API responses
        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json={
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_in": 3600,
                "scope": "user-read-email",
            },
            status_code=200,
        )

        httpx_mock.add_response(
            method="GET",
            url="https://api.spotify.com/v1/me",
            json={
                "id": "new_user_123",
                "display_name": "New User",
                "email": "newuser@example.com",
                "images": [{"url": "https://example.com/new_image.jpg"}],
            },
            status_code=200,
        )

        response = client.get(
            f"/spotify/callback?code=test_code&state={auth_state}",
            follow_redirects=False,
        )

        assert response.status_code == 302  # Redirect
        assert "127.0.0.1:3000" in response.headers["location"]
        assert "spotify=connected" in response.headers["location"]

    def test_spotify_callback_error(self, client):
        """Test Spotify callback with error parameter."""
        response = client.get(
            "/spotify/callback?error=access_denied&state=test_state",
            follow_redirects=False,
        )

        assert response.status_code == 302  # Redirect
        assert "127.0.0.1:3000/error" in response.headers["location"]
        assert (
            response.headers["location"]
            == "http://127.0.0.1:3000/error?message=Spotify%20authorization%20failed:%20access_denied"
        )

    async def test_spotify_callback_existing_user(
        self, client, test_user, test_session, httpx_mock
    ):
        """Test Spotify callback for existing user updates tokens."""
        # Get a valid state first
        auth_resp = client.get("/spotify/authorize")
        assert auth_resp.status_code == 200
        auth_state = auth_resp.json()["state"]

        new_token_data = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "scope": "user-read-email",
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
            json={
                "id": test_user.id,
                "display_name": "Updated Name",
                "email": test_user.email,
                "images": [{"url": "https://example.com/updated_image.jpg"}],
            },
            status_code=200,
        )

        response = client.get(
            f"/spotify/callback?code=test_code&state={auth_state}",
            follow_redirects=False,
        )

        assert response.status_code == 302

        # Verify user was updated
        updated_user = test_session.get(type(test_user), test_user.id)
        assert updated_user.tokens["access_token"] == "new_access_token"
        assert updated_user.name == "Updated Name"

    async def test_spotify_callback_exception_handling(self, client, httpx_mock):
        """Test Spotify callback handles exceptions gracefully."""
        # Get a valid state first
        auth_resp = client.get("/spotify/authorize")
        assert auth_resp.status_code == 200
        auth_state = auth_resp.json()["state"]

        # Mock failed token exchange
        httpx_mock.add_response(
            method="POST",
            url="https://accounts.spotify.com/api/token",
            json={"error": "invalid_grant"},
            status_code=400,
        )

        response = client.get(
            f"/spotify/callback?code=test_code&state={auth_state}",
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "127.0.0.1:3000/error" in response.headers["location"]


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_version(self):
        """Test get_version function reads from pyproject.toml."""
        from app import get_version

        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_current_user_id_with_session(self, client):
        """Test get_current_user_id with valid session."""
        from routes.deps import get_current_user_id

        # Create a mock request with session
        mock_request = Mock()
        mock_request.session = {"user_id": "test_user_123"}

        user_id = get_current_user_id(mock_request)
        assert user_id == "test_user_123"

    def test_get_current_user_id_without_session(self):
        """Test get_current_user_id without session."""
        from routes.deps import get_current_user_id

        mock_request = Mock()
        mock_request.session = {}

        user_id = get_current_user_id(mock_request)
        assert user_id is None

    def test_get_current_user_with_valid_user(self, test_session, test_user):
        """Test get_current_user with valid user ID."""
        from routes.deps import get_current_user

        mock_request = Mock()
        mock_request.session = {"user_id": test_user.id}

        user = get_current_user(mock_request, test_session)
        assert user is not None
        assert user.id == test_user.id

    def test_get_current_user_with_invalid_user(self, test_session):
        """Test get_current_user with invalid user ID."""
        from routes.deps import get_current_user

        mock_request = Mock()
        mock_request.session = {"user_id": "nonexistent_user"}

        user = get_current_user(mock_request, test_session)
        assert user is None
