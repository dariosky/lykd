"""Test configuration and fixtures for LYKD backend tests."""

import asyncio
import os
import sys
import pathlib
import pytest
import tempfile
from unittest.mock import patch


from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set test environment before importing backend modules
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LYKD_CLIENT_ID"] = "test_client_id"
os.environ["LYKD_CLIENT_SECRET"] = "test_client_secret"
os.environ["SESSION_SECRET_KEY"] = "test_secret_key"
os.environ["TESTING_MODE"] = "True"
os.environ["CACHE_ENABLED"] = "False"
os.environ["SLACK_TOKEN"] = ""


@pytest.fixture(autouse=True, scope="session")
def anyio_backend():  # pragma: no cover
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Ensure models are imported so tables are registered in SQLModel.metadata
    import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def override_get_session(test_session):
    """Override the get_session dependency for testing."""

    def _override_get_session():
        yield test_session

    return _override_get_session


@pytest.fixture
def test_app(override_get_session):
    """Create a test FastAPI application."""
    # Patch update_database to skip migrations in tests
    with patch("app.update_database"):
        from app import create_app

        app = create_app()
    from models.common import get_session

    app.dependency_overrides[get_session] = override_get_session
    yield app
    del app.dependency_overrides[get_session]


@pytest.fixture
def client(test_app):
    """Create a test client."""
    with TestClient(test_app) as client:
        yield client


@pytest.fixture
def test_user_data():
    """Test user data for Spotify responses."""
    return {
        "id": "test_user_123",
        "display_name": "Test User",
        "email": "test@example.com",
        "images": [{"url": "https://example.com/image.jpg"}],
    }


@pytest.fixture
def test_token_data():
    """Test token data for Spotify OAuth responses."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
        "scope": "user-read-email user-library-read",
    }


@pytest.fixture
def test_user(test_session, test_user_data, test_token_data):
    """Create a test user in the database."""
    from models.auth import User

    user = User(
        id=test_user_data["id"],
        name=test_user_data["display_name"],
        email=test_user_data["email"],
        picture=test_user_data["images"][0]["url"],
        tokens=test_token_data,
    )
    test_session.add(user)
    test_session.commit()
    return user


@pytest.fixture
def authenticated_client(client, test_user):
    """Create an authenticated test client."""
    # For FastAPI TestClient, we need to manually set cookies or use a different approach
    # We'll modify the app's session dependency for testing
    return client


@pytest.fixture
def mock_spotify_responses(test_user_data, test_token_data):
    """Mock Spotify API responses."""
    return {
        "token_exchange": test_token_data,
        "user_info": test_user_data,
        "liked_songs": {
            "items": [
                {
                    "track": {
                        "id": "track_123",
                        "name": "Test Song",
                        "artists": [{"id": "artist_123", "name": "Test Artist"}],
                        "album": {
                            "id": "album_123",
                            "name": "Test Album",
                            "images": [{"url": "https://example.com/album.jpg"}],
                        },
                    }
                }
            ],
            "next": None,
            "total": 1,
        },
        "recently_played": {
            "items": [
                {
                    "track": {
                        "id": "track_456",
                        "name": "Recent Song",
                        "artists": [{"id": "artist_456", "name": "Recent Artist"}],
                        "album": {
                            "id": "album_456",
                            "name": "Recent Album",
                        },
                    },
                    "played_at": "2023-08-07T12:00:00Z",
                }
            ],
            "next": None,
        },
        "top_tracks": {
            "items": [
                {
                    "id": "track_789",
                    "name": "Top Song",
                    "artists": [{"id": "artist_789", "name": "Top Artist"}],
                    "album": {"id": "album_789", "name": "Top Album"},
                }
            ],
            "next": None,
            "total": 1,
        },
    }


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture(autouse=True)
def reset_database_state(test_session):
    """Reset database state after each test."""
    yield
    # Handle any pending rollbacks first
    try:
        if test_session.in_transaction():
            test_session.rollback()

        # Clean up all tables after each test using proper SQLAlchemy text() function
        from sqlalchemy import text

        for table in reversed(SQLModel.metadata.sorted_tables):
            try:
                test_session.execute(text(f"DELETE FROM {table.name}"))
                test_session.commit()
            except Exception:
                test_session.rollback()
    except Exception:
        # If session is in bad state, just pass
        pass
