import pytest
from sqlmodel import Session

from models.music import Artist, Album, Track, TrackArtist, IgnoredTrack, IgnoredArtist
from routes.deps import current_user


@pytest.fixture
def auth_override(test_app, test_user):
    # Override current_user dependency to simulate authenticated user
    test_app.dependency_overrides[current_user] = lambda: test_user
    try:
        yield
    finally:
        test_app.dependency_overrides.pop(current_user, None)


def create_track_with_artists(
    session: Session,
    *,
    track_id: str,
    title: str,
    album_id: str | None,
    artists: list[tuple[str, str]],
):
    if album_id:
        album = Album(
            id=album_id,
            name=f"Album {album_id}",
            picture=None,
            release_date=None,
            release_date_precision=None,
        )
        session.add(album)
    track = Track(id=track_id, title=title, duration=123, album_id=album_id)
    session.add(track)
    for aid, aname in artists:
        a = session.get(Artist, aid) or Artist(
            id=aid, name=aname, picture=None, uri=None
        )
        session.add(a)
        # avoid duplicate PK insertions for the same track/artist pair
        if not session.get(TrackArtist, (track_id, aid)):
            session.add(TrackArtist(track_id=track_id, artist_id=aid))
    session.commit()
    return track


def test_ignore_get_unauthorized(client):
    resp = client.get("/ignore")
    assert resp.status_code == 401


def test_ignore_get_with_aggregation(client, test_session, test_user, auth_override):
    # t1: two artists, with album (duplicate pair skipped by helper)
    create_track_with_artists(
        test_session,
        track_id="t1",
        title="Song 1",
        album_id="alb1",
        artists=[("a1", "Artist A"), ("a2", "Artist B"), ("a2", "Artist B")],
    )
    # t2: single artist, no album
    create_track_with_artists(
        test_session,
        track_id="t2",
        title="Song 2",
        album_id=None,
        artists=[("a3", "Solo Artist")],
    )

    # Mark ignored
    test_session.add(IgnoredTrack(user_id=test_user.id, track_id="t1"))
    test_session.add(IgnoredTrack(user_id=test_user.id, track_id="t2"))
    # Also ignore an artist
    test_session.add(IgnoredArtist(user_id=test_user.id, artist_id="a2"))
    test_session.commit()

    resp = client.get("/ignore")
    assert resp.status_code == 200
    data = resp.json()

    tracks = {t["track_id"]: t for t in data["tracks"]}
    assert set(tracks.keys()) == {"t1", "t2"}

    t1 = tracks["t1"]
    assert t1["title"] == "Song 1"
    assert t1["album"] == {"id": "alb1", "name": "Album alb1", "picture": None}
    # aggregation order may vary; compare as sets
    assert set(t1["artists"]) == {"Artist A", "Artist B"}

    t2 = tracks["t2"]
    assert t2["title"] == "Song 2"
    assert t2["album"] is None
    assert t2["artists"] == ["Solo Artist"]

    # Ignored artists list
    artists = {a["artist_id"]: a for a in data["artists"]}
    assert artists == {"a2": {"artist_id": "a2", "name": "Artist B"}}


def test_ignore_track_crud(client, test_session, test_user, auth_override):
    # Seed a track and its album/artist
    create_track_with_artists(
        test_session,
        track_id="t3",
        title="Song 3",
        album_id="alb3",
        artists=[("a9", "Other Artist")],
    )

    # POST ignore track (idempotent)
    r1 = client.post("/ignore/track/t3")
    assert r1.status_code == 200
    assert r1.json()["message"] == "ignored"
    # repeat
    r1b = client.post("/ignore/track/t3")
    assert r1b.status_code == 200

    # GET should include t3
    g = client.get("/ignore")
    assert g.status_code == 200
    tids = {t["track_id"] for t in g.json()["tracks"]}
    assert "t3" in tids

    # DELETE unignore
    d = client.delete("/ignore/track/t3")
    assert d.status_code == 200
    assert d.json()["message"] == "unignored"

    # GET should not include t3
    g2 = client.get("/ignore")
    assert g2.status_code == 200
    tids2 = {t["track_id"] for t in g2.json()["tracks"]}
    assert "t3" not in tids2

    # POST non-existent track -> 404
    r404 = client.post("/ignore/track/nope")
    assert r404.status_code == 404


def test_ignore_artist_crud(client, test_session, test_user, auth_override):
    # Seed artist
    a = Artist(id="ax", name="Artist X", picture=None, uri=None)
    test_session.add(a)
    test_session.commit()

    # POST ignore artist (idempotent)
    r1 = client.post("/ignore/artist/ax")
    assert r1.status_code == 200
    assert r1.json()["message"] == "ignored"
    r1b = client.post("/ignore/artist/ax")
    assert r1b.status_code == 200

    # GET should include ax
    g = client.get("/ignore")
    assert g.status_code == 200
    aids = {a["artist_id"] for a in g.json()["artists"]}
    assert "ax" in aids

    # DELETE unignore
    d = client.delete("/ignore/artist/ax")
    assert d.status_code == 200
    assert d.json()["message"] == "unignored"

    # GET should not include ax
    g2 = client.get("/ignore")
    assert g2.status_code == 200
    aids2 = {a["artist_id"] for a in g2.json()["artists"]}
    assert "ax" not in aids2

    # POST non-existent artist -> 404
    r404 = client.post("/ignore/artist/zzz")
    assert r404.status_code == 404
