"""Unit tests for public route endpoints."""

from datetime import datetime, timezone, timedelta
from models.auth import User
from models.music import Play, Like, Track, TrackArtist, Artist, Album


class TestPublicRouteEndpoints:
    """Test public route endpoints."""

    def test_get_public_profile_unauthenticated_access(self, client, test_session):
        """Test that non-authenticated users can access public profiles."""
        # Create a test user
        user = User(
            id="test_public_user",
            name="Public Test User",
            username="testuser123",
            email="test@example.com",
            picture="https://example.com/pic.jpg",
        )
        test_session.add(user)
        test_session.commit()

        # Test access without authentication
        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        assert "user" in data
        assert "stats" in data
        assert "highlights" in data

    def test_get_public_profile_user_not_found(self, client):
        """Test 404 when user doesn't exist."""
        response = client.get("/user/nonexistentuser/public")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_get_public_profile_basic_user_info(self, client, test_session):
        """Test that basic user info is returned correctly."""
        user = User(
            id="test_user_info",
            name="Test User Info",
            username="infouser",
            email="info@example.com",
            picture="https://example.com/info.jpg",
            join_date=datetime(2023, 1, 15, tzinfo=timezone.utc),
        )
        test_session.add(user)
        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        user_info = data["user"]

        assert user_info["id"] == user.id
        assert user_info["name"] == user.name
        assert user_info["username"] == user.username
        assert user_info["picture"] == user.picture
        assert user_info["join_date"] == "2023-01-15T00:00:00+00:00"

    def test_get_public_profile_empty_stats(self, client, test_session):
        """Test that empty stats are handled correctly."""
        user = User(
            id="test_empty_stats",
            name="Empty Stats User",
            username="emptyuser",
            email="empty@example.com",
        )
        test_session.add(user)
        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        assert stats["total_plays"] == 0
        assert stats["total_likes"] == 0
        assert stats["total_listening_time_sec"] == 0
        assert stats["listening_time_last_30_days_sec"] == 0
        assert stats["tracking_since"] is None

        highlights = data["highlights"]
        assert highlights["top_songs_30_days"] == []
        assert highlights["top_songs_all_time"] == []
        assert highlights["top_artists"] == []
        assert highlights["most_played_decade"] is None

    def test_get_public_profile_with_play_data(self, client, test_session):
        """Test profile with actual play data."""
        # Create test user
        user = User(
            id="test_play_data",
            name="Play Data User",
            username="playuser",
            email="play@example.com",
        )
        test_session.add(user)

        # Create test artist
        artist = Artist(id="artist_1", name="Test Artist")
        test_session.add(artist)

        # Create test album
        album = Album(
            id="album_1", name="Test Album", release_date=datetime(2020, 1, 1)
        )
        test_session.add(album)

        # Create test track
        track = Track(
            id="track_1",
            title="Test Song",
            duration=240000,  # 4 minutes in milliseconds
            album_id=album.id,
        )
        test_session.add(track)

        # Create track-artist relationship
        track_artist = TrackArtist(track_id=track.id, artist_id=artist.id)
        test_session.add(track_artist)

        # Create plays
        now = datetime.now(timezone.utc)
        old_play = Play(
            user_id=user.id,
            track_id=track.id,
            date=now - timedelta(days=60),  # Older than 30 days
        )
        recent_play = Play(
            user_id=user.id,
            track_id=track.id,
            date=now - timedelta(days=10),  # Within 30 days
        )
        test_session.add_all([old_play, recent_play])

        # Create a like
        like = Like(user_id=user.id, track_id=track.id, date=now - timedelta(days=5))
        test_session.add(like)

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        assert stats["total_plays"] == 2
        assert stats["total_likes"] == 1
        assert stats["total_listening_time_sec"] == 480  # 2 plays * 4 minutes
        assert stats["listening_time_last_30_days_sec"] == 240  # 1 play * 4 minutes
        assert stats["tracking_since"] is not None

    def test_get_public_profile_top_tracks_30_days(self, client, test_session):
        """Test top tracks for last 30 days."""
        # Create test user
        user = User(
            id="test_top_tracks_30",
            name="Top Tracks 30 User",
            username="topuser30",
            email="top30@example.com",
        )
        test_session.add(user)

        # Create test data
        artist = Artist(id="artist_top", name="Top Artist")
        album = Album(
            id="album_top", name="Top Album", release_date=datetime(2021, 1, 1)
        )
        track = Track(
            id="track_top",
            title="Top Song",
            duration=180000,  # 3 minutes
            album_id=album.id,
        )
        track_artist = TrackArtist(track_id=track.id, artist_id=artist.id)

        test_session.add_all([artist, album, track, track_artist])

        # Create multiple recent plays
        now = datetime.now(timezone.utc)
        for i in range(3):
            play = Play(
                user_id=user.id, track_id=track.id, date=now - timedelta(days=i + 1)
            )
            test_session.add(play)

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        top_tracks_30 = data["highlights"]["top_songs_30_days"]

        assert len(top_tracks_30) == 1
        track_data = top_tracks_30[0]["track"]
        assert track_data["id"] == track.id
        assert track_data["title"] == track.title
        assert track_data["duration"] == track.duration
        assert track_data["artists"] == [artist.name]
        assert track_data["album"]["id"] == album.id
        assert track_data["album"]["name"] == album.name
        assert top_tracks_30[0]["play_count"] == 3

    def test_get_public_profile_top_artists(self, client, test_session):
        """Test top artists functionality."""
        # Create test user
        user = User(
            id="test_top_artists",
            name="Top Artists User",
            username="artistuser",
            email="artist@example.com",
        )
        test_session.add(user)

        # Create test artists
        artist1 = Artist(id="artist_1", name="Popular Artist")
        artist2 = Artist(id="artist_2", name="Less Popular Artist")
        test_session.add_all([artist1, artist2])

        # Create tracks and plays
        album = Album(id="album_test", name="Test Album")
        track1 = Track(id="track_1", title="Song 1", duration=200000, album_id=album.id)
        track2 = Track(id="track_2", title="Song 2", duration=200000, album_id=album.id)

        test_session.add_all([album, track1, track2])

        # Artist relationships
        ta1 = TrackArtist(track_id=track1.id, artist_id=artist1.id)
        ta2 = TrackArtist(track_id=track2.id, artist_id=artist2.id)
        test_session.add_all([ta1, ta2])

        # Create more plays for artist1
        now = datetime.now(timezone.utc)
        for i in range(5):
            play = Play(
                user_id=user.id, track_id=track1.id, date=now - timedelta(days=i)
            )
            test_session.add(play)

        # Create fewer plays for artist2
        for i in range(2):
            play = Play(
                user_id=user.id, track_id=track2.id, date=now - timedelta(days=i)
            )
            test_session.add(play)

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        top_artists = data["highlights"]["top_artists"]

        assert len(top_artists) == 2
        assert top_artists[0]["artist_id"] == artist1.id
        assert top_artists[0]["name"] == artist1.name
        assert top_artists[0]["play_count"] == 5
        assert top_artists[1]["artist_id"] == artist2.id
        assert top_artists[1]["name"] == artist2.name
        assert top_artists[1]["play_count"] == 2

    def test_get_public_profile_most_played_decade(self, client, test_session):
        """Test most played decade calculation."""
        # Create test user
        user = User(
            id="test_decade",
            name="Decade User",
            username="decadeuser",
            email="decade@example.com",
        )
        test_session.add(user)

        # Create test data with 1990s album
        artist = Artist(id="decade_artist", name="90s Artist")
        album_90s = Album(
            id="album_90s", name="90s Album", release_date=datetime(1995, 6, 15)
        )
        track_90s = Track(
            id="track_90s", title="90s Song", duration=200000, album_id=album_90s.id
        )
        track_artist = TrackArtist(track_id=track_90s.id, artist_id=artist.id)

        test_session.add_all([artist, album_90s, track_90s, track_artist])

        # Create plays
        now = datetime.now(timezone.utc)
        for i in range(3):
            play = Play(
                user_id=user.id, track_id=track_90s.id, date=now - timedelta(days=i)
            )
            test_session.add(play)

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        most_played_decade = data["highlights"]["most_played_decade"]

        assert most_played_decade == "1990s"

    def test_get_public_profile_case_sensitive_username(self, client, test_session):
        """Test that username lookup is case sensitive."""
        user = User(
            id="test_case",
            name="Case Test User",
            username="CaseUser",
            email="case@example.com",
        )
        test_session.add(user)
        test_session.commit()

        # Test exact case works
        response = client.get("/user/CaseUser/public")
        assert response.status_code == 200

        # Test different case fails
        response = client.get("/user/caseuser/public")
        assert response.status_code == 404

    def test_get_public_profile_no_auth_required(self, client, test_session):
        """Test that no authentication headers are required."""
        user = User(
            id="test_no_auth",
            name="No Auth User",
            username="noauthuser",
            email="noauth@example.com",
        )
        test_session.add(user)
        test_session.commit()

        # Make request without any auth headers
        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        # Make request with invalid auth headers (should still work)
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get(f"/user/{user.username}/public", headers=headers)
        assert response.status_code == 200
