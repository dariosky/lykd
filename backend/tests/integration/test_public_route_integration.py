"""Integration tests for public route endpoints."""

from datetime import datetime, timezone, timedelta

from models import Friendship, FriendshipStatus
from models.auth import User
from models.music import (
    Play,
    Like,
    Track,
    TrackArtist,
    Artist,
    Album,
    IgnoredTrack,
    IgnoredArtist,
)


class TestPublicRouteIntegration:
    """Integration tests for public route with ignored tracks/artists."""

    def test_public_profile_with_ignored_tracks(self, client, test_session):
        """Test that ignored tracks are properly excluded from stats and highlights."""
        # Create test user
        user = User(
            id="test_ignored_tracks",
            name="Ignored Tracks User",
            username="ignoreduser",
            email="ignored@example.com",
        )
        test_session.add(user)

        # Create test data
        artist = Artist(id="ignored_artist", name="Test Artist")
        album = Album(
            id="ignored_album", name="Test Album", release_date=datetime(2020, 1, 1)
        )

        # Create two tracks
        track1 = Track(
            id="track_1",
            title="Normal Song",
            duration=200000,
            album_id=album.id,
            uid="uid_1",
        )
        track2 = Track(
            id="track_2",
            title="Ignored Song",
            duration=200000,
            album_id=album.id,
            uid="uid_2",
        )

        track_artist1 = TrackArtist(track_id=track1.id, artist_id=artist.id)
        track_artist2 = TrackArtist(track_id=track2.id, artist_id=artist.id)

        test_session.add_all(
            [artist, album, track1, track2, track_artist1, track_artist2]
        )

        # Create plays for both tracks
        now = datetime.now(timezone.utc)
        for i in range(3):
            play1 = Play(
                user_id=user.id, track_id=track1.id, date=now - timedelta(days=i)
            )
            play2 = Play(
                user_id=user.id, track_id=track2.id, date=now - timedelta(days=i)
            )
            test_session.add_all([play1, play2])

        # Create likes for both tracks
        like1 = Like(user_id=user.id, track_id=track1.id, date=now)
        like2 = Like(user_id=user.id, track_id=track2.id, date=now)
        test_session.add_all([like1, like2])

        # Ignore track2
        ignored_track = IgnoredTrack(user_id=user.id, track_id=track2.id)
        test_session.add(ignored_track)

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        # Should only count non-ignored track
        assert stats["total_plays"] == 3  # Only track1 plays
        assert stats["total_likes"] == 1  # Only track1 like
        assert stats["total_listening_time_sec"] == 600  # Only track1 duration * 3

        # Unauthenticated users should not see  highlights
        assert "top_songs_30_days" not in data["highlights"]
        assert "top_songs_all_time" not in data["highlights"]

    def test_public_profile_with_ignored_artists(self, client, test_session):
        """Test that tracks by ignored artists are excluded."""
        # Create test user
        user = User(
            id="test_ignored_artists",
            name="Ignored Artists User",
            username="ignoredartistuser",
            email="ignoredartist@example.com",
        )
        test_session.add(user)

        # Create test data
        artist1 = Artist(id="normal_artist", name="Normal Artist")
        artist2 = Artist(id="ignored_artist", name="Ignored Artist")
        album = Album(
            id="test_album", name="Test Album", release_date=datetime(2020, 1, 1)
        )

        track1 = Track(
            id="track_1", title="Normal Song", duration=200000, album_id=album.id
        )
        track2 = Track(
            id="track_2",
            title="Song by Ignored Artist",
            duration=200000,
            album_id=album.id,
        )

        track_artist1 = TrackArtist(track_id=track1.id, artist_id=artist1.id)
        track_artist2 = TrackArtist(track_id=track2.id, artist_id=artist2.id)

        test_session.add_all(
            [artist1, artist2, album, track1, track2, track_artist1, track_artist2]
        )

        # Create plays for both tracks
        now = datetime.now(timezone.utc)
        for i in range(2):
            play1 = Play(
                user_id=user.id, track_id=track1.id, date=now - timedelta(days=i)
            )
            play2 = Play(
                user_id=user.id, track_id=track2.id, date=now - timedelta(days=i)
            )
            test_session.add_all([play1, play2])

        # Ignore artist2
        ignored_artist = IgnoredArtist(user_id=user.id, artist_id=artist2.id)
        test_session.add(ignored_artist)

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()

        # Should only count plays from non-ignored artist
        assert data["stats"]["total_plays"] == 2

        # Top artists should not be visible for non-friends
        assert "top_artists" not in data["highlights"]

    def test_public_profile_with_multiple_artists_per_track(
        self, client, test_session, test_user, auth_override
    ):
        """Test tracks with multiple artists are handled correctly."""
        # Create test user
        user = User(
            id="test_multi_artists",
            name="Multi Artists User",
            username="multiartistuser",
            email="multiartist@example.com",
        )
        test_session.add(user)
        test_session.add(
            Friendship(
                user_low_id=user.id,
                user_high_id=test_user.id,
                status=FriendshipStatus.accepted,
                requested_by_id=user.id,
            )
        )  # Make them friends

        # Create multiple artists
        artist1 = Artist(id="artist_1", name="Artist One")
        artist2 = Artist(id="artist_2", name="Artist Two")
        artist3 = Artist(id="artist_3", name="Artist Three")

        album = Album(
            id="multi_album",
            name="Collaboration Album",
            release_date=datetime(2021, 1, 1),
        )

        # Create track with multiple artists
        track = Track(
            id="collab_track",
            title="Collaboration Song",
            duration=240000,
            album_id=album.id,
        )

        # Link track to all artists
        track_artist1 = TrackArtist(track_id=track.id, artist_id=artist1.id)
        track_artist2 = TrackArtist(track_id=track.id, artist_id=artist2.id)
        track_artist3 = TrackArtist(track_id=track.id, artist_id=artist3.id)

        test_session.add_all(
            [
                artist1,
                artist2,
                artist3,
                album,
                track,
                track_artist1,
                track_artist2,
                track_artist3,
            ]
        )

        # Create plays
        now = datetime.now(timezone.utc)
        for i in range(3):
            play = Play(
                user_id=user.id, track_id=track.id, date=now - timedelta(days=i)
            )
            test_session.add(play)

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        assert data["user"]["is_friend"] is True

        # Check that all artists are credited for the plays
        top_artists = data["highlights"]["top_artists"]
        assert len(top_artists) == 3

        # All artists should have same play count since it's the same track
        for artist_data in top_artists:
            assert artist_data["play_count"] == 3

        # Check that track includes all artist names
        top_tracks = data["highlights"]["top_songs_all_time"]
        assert len(top_tracks) == 1
        track_data = top_tracks[0]
        assert len(track_data["track"]["artists"]) == 3
        artist_names = set(track_data["track"]["artists"])
        assert artist_names == {"Artist One", "Artist Two", "Artist Three"}

    def test_public_profile_comprehensive_stats(
        self, client, test_session, test_user, auth_override
    ):
        """Test comprehensive statistics with mixed old and recent data."""
        # Create test user
        user = User(
            id="test_comprehensive",
            name="Comprehensive User",
            username="compuser",
            email="comp@example.com",
        )
        test_session.add(user)
        test_session.add(  # Make them friends
            Friendship(
                user_low_id=user.id,
                user_high_id=test_user.id,
                status=FriendshipStatus.accepted,
                requested_by_id=user.id,
            )
        )

        # Create test data
        artist = Artist(id="comp_artist", name="Comprehensive Artist")
        album_old = Album(
            id="album_old", name="Old Album", release_date=datetime(1985, 6, 1)
        )
        album_new = Album(
            id="album_new", name="New Album", release_date=datetime(2023, 6, 1)
        )

        track_old = Track(
            id="track_old", title="Old Song", duration=300000, album_id=album_old.id
        )
        track_new = Track(
            id="track_new", title="New Song", duration=180000, album_id=album_new.id
        )

        track_artist_old = TrackArtist(track_id=track_old.id, artist_id=artist.id)
        track_artist_new = TrackArtist(track_id=track_new.id, artist_id=artist.id)

        test_session.add_all(
            [
                artist,
                album_old,
                album_new,
                track_old,
                track_new,
                track_artist_old,
                track_artist_new,
            ]
        )

        # Create plays with different time periods
        now = datetime.now(timezone.utc)

        # Old plays (outside 30-day window)
        for i in range(5):
            play = Play(
                user_id=user.id,
                track_id=track_old.id,
                date=now - timedelta(days=50 + i),
            )
            test_session.add(play)

        # Recent plays (within 30-day window)
        for i in range(3):
            play = Play(
                user_id=user.id,
                track_id=track_new.id,
                date=now - timedelta(days=10 + i),
            )
            test_session.add(play)

        # Some likes
        like1 = Like(
            user_id=user.id, track_id=track_old.id, date=now - timedelta(days=40)
        )
        like2 = Like(
            user_id=user.id, track_id=track_new.id, date=now - timedelta(days=5)
        )
        test_session.add_all([like1, like2])

        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        # Verify total stats
        assert stats["total_plays"] == 8  # 5 old + 3 new
        assert stats["total_likes"] == 2
        assert stats["total_listening_time_sec"] == 2040  # 5*300 + 3*180 seconds
        assert stats["listening_time_last_30_days_sec"] == 540  # 3*180 seconds
        assert stats["tracking_since"] is not None

        # Verify highlights
        highlights = data["highlights"]

        # 30-day top tracks should only show recent track
        assert len(highlights["top_songs_30_days"]) == 1
        assert highlights["top_songs_30_days"][0]["track"]["id"] == track_new.id
        assert highlights["top_songs_30_days"][0]["play_count"] == 3

        # All-time top tracks should show old track first (more plays)
        assert len(highlights["top_songs_all_time"]) == 2
        assert highlights["top_songs_all_time"][0]["track"]["id"] == track_old.id
        assert highlights["top_songs_all_time"][0]["play_count"] == 5
        assert highlights["top_songs_all_time"][1]["track"]["id"] == track_new.id
        assert highlights["top_songs_all_time"][1]["play_count"] == 3

        # Most played decade should be 1980s
        assert highlights["most_played_decade"] == "1980s"

    def test_public_profile_response_structure(
        self, client, test_session, test_user, auth_override
    ):
        """Test that the response has the correct structure and data types."""
        user = User(
            id="test_structure",
            name="Structure User",
            username="structureuser",
            email="structure@example.com",
            join_date=datetime(2023, 5, 1, tzinfo=timezone.utc),
        )
        test_session.add(user)
        test_session.add(  # Make them friends
            Friendship(
                user_low_id=user.id,
                user_high_id=test_user.id,
                status=FriendshipStatus.accepted,
                requested_by_id=user.id,
            )
        )
        test_session.commit()

        response = client.get(f"/user/{user.username}/public")
        assert response.status_code == 200

        data = response.json()

        # Verify top-level structure
        assert set(data.keys()) == {"user", "stats", "highlights"}

        # Verify user structure
        user_data = data["user"]
        assert set(user_data.keys()) == {
            "id",
            "name",
            "username",
            "picture",
            "join_date",
            "is_friend",
        }
        assert isinstance(user_data["id"], str)
        assert isinstance(user_data["name"], str)
        assert isinstance(user_data["username"], str)
        assert user_data["picture"] is None or isinstance(user_data["picture"], str)
        assert isinstance(user_data["join_date"], str)

        # Verify stats structure
        stats = data["stats"]
        expected_stats_keys = {
            "total_plays",
            "total_likes",
            "total_listening_time_sec",
            "listening_time_last_30_days_sec",
            "tracking_since",
        }
        assert set(stats.keys()) == expected_stats_keys
        assert isinstance(stats["total_plays"], int)
        assert isinstance(stats["total_likes"], int)
        assert isinstance(stats["total_listening_time_sec"], int)
        assert isinstance(stats["listening_time_last_30_days_sec"], int)
        assert stats["tracking_since"] is None or isinstance(
            stats["tracking_since"], str
        )

        # Verify highlights structure
        highlights = data["highlights"]
        expected_highlights_keys = {
            "top_songs_30_days",
            "top_songs_all_time",
            "top_artists",
            "most_played_decade",
        }
        assert set(highlights.keys()) == expected_highlights_keys
        assert isinstance(highlights["top_songs_30_days"], list)
        assert isinstance(highlights["top_songs_all_time"], list)
        assert isinstance(highlights["top_artists"], list)
        assert highlights["most_played_decade"] is None or isinstance(
            highlights["most_played_decade"], str
        )
