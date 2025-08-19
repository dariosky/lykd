from datetime import datetime, timedelta, timezone
from typing import List

import pytest
from sqlalchemy import text
from sqlmodel import Session

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
from routes.public_route import (
    build_total_plays_stmt,
    build_top_tracks_all_time_stmt,
    build_total_likes_stmt,
    build_total_listen_sec_stmt,
    build_monthly_listen_sec_stmt,
    build_top_tracks_last_30_stmt,
    build_top_artists_stmt,
    build_most_played_decade_stmt,
    build_tracking_since_stmt,
)


def _compile_sql(stmt, session: Session) -> str:
    # Render SQL with literals so we can prefix EXPLAIN QUERY PLAN
    return str(stmt.compile(session.get_bind(), compile_kwargs={"literal_binds": True}))


def _explain_query_plan(stmt, session: Session) -> List[str]:
    sql = _compile_sql(stmt, session)
    rows = session.exec(text(f"EXPLAIN QUERY PLAN {sql}")).all()
    # SQLite returns tuples like (selectid, order, from, detail). Extract detail strings.
    details = []
    for row in rows:
        # row can be a tuple or Row; last element is detail
        details.append(row[-1] if isinstance(row, (tuple, list)) else row.detail)
    return details


def _assert_no_full_scan_on(table_name: str, details: List[str]):
    # Fail if EXPLAIN shows a full table scan on the given table (e.g., 'SCAN TABLE plays' or 'SCAN plays')
    lowered = [d.lower() for d in details]
    for d in lowered:
        if "scan" in d and table_name.lower() in d:
            pytest.fail(f"Query plan contains a full scan on {table_name}: {d}")


def _assert_uses_index_on(table_name: str, details: List[str]):
    # Pass if any step shows SEARCH ... USING INDEX / USING COVERING INDEX / USING PRIMARY KEY on the table
    lowered = [d.lower() for d in details]
    for d in lowered:
        if (
            table_name.lower() in d
            and "search" in d
            and (
                "using index" in d
                or "using primary key" in d
                or "using covering index" in d
            )
        ):
            return
    pytest.fail(f"Query plan does not show index usage for {table_name}: {details}")


@pytest.mark.parametrize("with_ignored", [False, True])
def test_total_plays_uses_index_on_plays(test_session: Session, with_ignored: bool):
    # Arrange minimal data
    user = User(id="u_idx", name="U", email="u@example.com", username="u_idx")
    artist = Artist(id="a1", name="A1")
    track = Track(id="t1", title="T1", duration=200000)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, track, ta])

    now = datetime.now(timezone.utc)
    for i in range(3):
        test_session.add(
            Play(user_id=user.id, track_id=track.id, date=now - timedelta(days=i))
        )
    test_session.add(Like(user_id=user.id, track_id=track.id, date=now))

    if with_ignored:
        # Optionally add ignored entries to ensure EXISTS subqueries don't force scans
        test_session.add(IgnoredTrack(user_id=user.id, track_id="nonexistent"))
        test_session.add(IgnoredArtist(user_id=user.id, artist_id="other"))

    test_session.commit()

    # Build statement using route builder
    stmt = build_total_plays_stmt(user.id)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)


def test_total_likes_uses_index_on_likes(test_session: Session):
    # Arrange minimal data
    user = User(id="u_like", name="U", email="ulike@example.com", username="u_like")
    artist = Artist(id="a_like", name="AL")
    track = Track(id="t_like", title="TL", duration=120000)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, track, ta])

    now = datetime.now(timezone.utc)
    test_session.add(Like(user_id=user.id, track_id=track.id, date=now))
    test_session.commit()

    # Statement for total likes using route builder
    stmt = build_total_likes_stmt(user.id)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on likes and no full scan on likes
    _assert_no_full_scan_on("likes", details)
    _assert_uses_index_on("likes", details)


def test_total_listen_sec_uses_index_on_plays(test_session: Session):
    # Arrange minimal data
    user = User(
        id="u_listen", name="U", email="ulisten@example.com", username="u_listen"
    )
    artist = Artist(id="a_listen", name="AL")
    album = Album(id="al_listen", name="Album L")
    track = Track(id="t_listen", title="TL", duration=180000, album_id=album.id)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, album, track, ta])

    now = datetime.now(timezone.utc)
    test_session.add(Play(user_id=user.id, track_id=track.id, date=now))
    test_session.commit()

    # Statement for total listen seconds using route builder
    stmt = build_total_listen_sec_stmt(user.id)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)


def test_monthly_listen_sec_uses_index_on_plays(test_session: Session):
    # Arrange minimal data
    user = User(id="u_month", name="U", email="umonth@example.com", username="u_month")
    artist = Artist(id="a_month", name="AM")
    album = Album(id="al_month", name="Album M")
    track = Track(id="t_month", title="TM", duration=200000, album_id=album.id)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, album, track, ta])

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    test_session.add(
        Play(user_id=user.id, track_id=track.id, date=now - timedelta(days=5))
    )
    test_session.commit()

    # Statement for monthly listen seconds using route builder
    stmt = build_monthly_listen_sec_stmt(user.id, cutoff)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)


def test_top_tracks_last_30_uses_index_on_plays(test_session: Session):
    # Arrange minimal data
    user = User(
        id="u_last30", name="U", email="ulast30@example.com", username="u_last30"
    )
    artist = Artist(id="a_last30", name="AL30")
    album = Album(id="al_last30", name="Album 30")
    track = Track(id="t_last30", title="TL30", duration=220000, album_id=album.id)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, album, track, ta])

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    for i in range(3):
        test_session.add(
            Play(user_id=user.id, track_id=track.id, date=now - timedelta(days=i))
        )
    test_session.commit()

    # Statement for top tracks last 30 days using route builder
    stmt = build_top_tracks_last_30_stmt(user.id, cutoff)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)


def test_top_tracks_all_time_uses_index_on_plays(test_session: Session):
    # Arrange minimal data
    user = User(id="u_idx2", name="U2", email="u2@example.com", username="u_idx2")
    artist = Artist(id="a2", name="A2")
    album = Album(id="al2", name="AL2")
    track = Track(id="t2", title="T2", duration=180000, album_id=album.id)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, album, track, ta])

    now = datetime.now(timezone.utc)
    for i in range(5):
        test_session.add(
            Play(user_id=user.id, track_id=track.id, date=now - timedelta(days=i))
        )
    test_session.commit()

    # Statement for top songs all-time using route builder
    stmt = build_top_tracks_all_time_stmt(user.id)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)


def test_top_artists_uses_index_on_plays(test_session: Session):
    # Arrange minimal data
    user = User(id="u_art", name="U", email="uart@example.com", username="u_art")
    artist = Artist(id="a_art", name="AA")
    album = Album(id="al_art", name="AL A")
    track = Track(id="t_art", title="TA", duration=200000, album_id=album.id)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, album, track, ta])

    now = datetime.now(timezone.utc)
    for i in range(4):
        test_session.add(
            Play(user_id=user.id, track_id=track.id, date=now - timedelta(days=i))
        )
    test_session.commit()

    # Statement for top artists using route builder
    stmt = build_top_artists_stmt(user.id)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)


def test_most_played_decade_uses_index_on_plays(test_session: Session):
    # Arrange minimal data
    user = User(id="u_dec", name="U", email="udec@example.com", username="u_dec")
    artist = Artist(id="a_dec", name="AD")
    album = Album(id="al_dec", name="ALD", release_date=datetime(1995, 1, 1))
    track = Track(id="t_dec", title="TD", duration=210000, album_id=album.id)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, album, track, ta])

    now = datetime.now(timezone.utc)
    test_session.add(Play(user_id=user.id, track_id=track.id, date=now))
    test_session.commit()

    # Statement for most played decade using route builder
    stmt = build_most_played_decade_stmt(user.id)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)


def test_tracking_since_uses_index_on_plays(test_session: Session):
    # Arrange minimal data
    user = User(id="u_since", name="U", email="usince@example.com", username="u_since")
    artist = Artist(id="a_since", name="AS")
    album = Album(id="al_since", name="ALS")
    track = Track(id="t_since", title="TS", duration=190000, album_id=album.id)
    ta = TrackArtist(track_id=track.id, artist_id=artist.id)
    test_session.add_all([user, artist, album, track, ta])

    now = datetime.now(timezone.utc)
    for days_ago in [40, 20, 1]:
        test_session.add(
            Play(
                user_id=user.id, track_id=track.id, date=now - timedelta(days=days_ago)
            )
        )
    test_session.commit()

    # Statement for tracking since using route builder
    stmt = build_tracking_since_stmt(user.id)

    details = _explain_query_plan(stmt, test_session)

    # Assert: planner uses an index on plays and no full scan on plays
    _assert_no_full_scan_on("plays", details)
    _assert_uses_index_on("plays", details)
