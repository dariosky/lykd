"""Unit tests for database models."""

import pytest
import datetime
from models.auth import User
from models.music import Artist, Track, Album, Play, Like


class TestUserModel:
    """Test User model functionality."""

    def test_user_creation(self, test_session):
        """Test creating a new user."""
        user_data = {
            "id": "test_user_123",
            "name": "Test User",
            "email": "test@example.com",
            "picture": "https://example.com/picture.jpg",
            "tokens": {"access_token": "token123", "refresh_token": "refresh123"},
        }

        user = User(**user_data)
        test_session.add(user)
        test_session.commit()

        assert user.id == "test_user_123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.picture == "https://example.com/picture.jpg"
        assert user.tokens["access_token"] == "token123"
        assert isinstance(user.join_date, datetime.datetime)
        assert user.is_admin is False

    def test_user_unique_email_constraint(self, test_session):
        """Test that user email must be unique."""
        user1 = User(id="user1", name="User One", email="duplicate@example.com")
        user2 = User(id="user2", name="User Two", email="duplicate@example.com")

        test_session.add(user1)
        test_session.commit()

        test_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_session.commit()

    def test_user_default_values(self, test_session):
        """Test user model default values."""
        user = User(id="test_user", name="Test User", email="test@example.com")
        test_session.add(user)
        test_session.commit()

        assert user.picture is None
        assert user.tokens == {}
        assert isinstance(user.join_date, datetime.datetime)
        assert user.is_admin is False

    def test_user_admin_flag(self, test_session):
        """Test setting user as admin."""
        user = User(
            id="admin_user", name="Admin User", email="admin@example.com", is_admin=True
        )
        test_session.add(user)
        test_session.commit()

        assert user.is_admin is True


class TestMusicModels:
    """Test music-related models."""

    def test_artist_creation(self, test_session):
        """Test creating an artist."""
        artist = Artist(
            id="artist123", name="Test Artist", picture="https://example.com/artist.jpg"
        )
        test_session.add(artist)
        test_session.commit()

        assert artist.id == "artist123"
        assert artist.name == "Test Artist"
        assert artist.picture == "https://example.com/artist.jpg"

    def test_album_creation(self, test_session):
        """Test creating an album."""
        album = Album(
            id="album123",
            name="Test Album",
            picture="https://example.com/album.jpg",
            release_date=datetime.date(2025, 8, 8),
        )
        test_session.add(album)
        test_session.commit()

        assert album.id == "album123"
        assert album.name == "Test Album"
        assert album.picture == "https://example.com/album.jpg"
        assert album.release_date == datetime.date(2025, 8, 8)

    def test_track_creation(self, test_session):
        """Test creating a track."""
        track = Track(
            id="track123",
            title="Test Track",
            duration=180000,
        )
        test_session.add(track)
        test_session.commit()

        assert track.id == "track123"
        assert track.title == "Test Track"
        assert track.duration == 180000

    def test_liked_track_relationship(self, test_session, test_user):
        """Test liked track relationship."""
        track = Track(id="liked_track", title="Liked Song", duration=60)
        test_session.merge(track)
        test_session.commit()

        liked = Like(user_id=test_user.id, track_id=track.id)
        test_session.add(liked)
        test_session.commit()

        assert liked.user_id == test_user.id
        assert liked.track_id == track.id
        assert isinstance(liked.date, datetime.datetime)

    def test_play_relationship(self, test_session, test_user):
        """Test play track relationship."""
        track = Track(id="played_track", title="Played Song", duration=18000)
        test_session.add(track)
        test_session.commit()

        play = Play(
            user_id=test_user.id,
            track_id=track.id,
            date=datetime.datetime.now(datetime.UTC),
        )
        test_session.add(play)
        test_session.commit()

        assert play.user_id == test_user.id
        assert play.track_id == track.id
        assert isinstance(play.date, datetime.datetime)

    def test_track_artist_many_to_many(self, test_session):
        """Test track-artist many-to-many relationship."""
        from models.music import TrackArtist

        artist = Artist(id="artist1", name="Artist 1")
        track = Track(id="track1", title="Track 1", duration=30)

        test_session.add(artist)
        test_session.add(track)
        test_session.commit()

        track_artist = TrackArtist(track_id=track.id, artist_id=artist.id)
        test_session.add(track_artist)
        test_session.commit()

        assert track_artist.track_id == track.id
        assert track_artist.artist_id == artist.id

    def test_album_artist_many_to_many(self, test_session):
        """Test album-artist many-to-many relationship."""
        from models.music import AlbumArtist

        artist = Artist(id="artist2", name="Artist 2")
        album = Album(id="album2", name="Album 2")

        test_session.add(artist)
        test_session.add(album)
        test_session.commit()

        album_artist = AlbumArtist(album_id=album.id, artist_id=artist.id)
        test_session.add(album_artist)
        test_session.commit()

        assert album_artist.album_id == album.id
        assert album_artist.artist_id == artist.id


class TestDatabaseSession:
    """Test database session functionality."""

    def test_get_session_dependency(self):
        """Test the get_session dependency function."""
        from models.common import get_session

        # This should return a generator
        session_gen = get_session()
        assert hasattr(session_gen, "__next__")

    def test_session_isolation(self, test_session):
        """Test that test sessions are properly isolated."""
        # Create a user in this test
        user = User(
            id="isolation_test", name="Isolation Test", email="isolation@test.com"
        )
        test_session.add(user)
        test_session.commit()

        # Verify user exists
        found_user = test_session.get(User, "isolation_test")
        assert found_user is not None
        assert found_user.name == "Isolation Test"
