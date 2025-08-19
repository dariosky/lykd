import datetime
from datetime import timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.auth import User
from models.friendship import Friendship, FriendshipStatus
from models.music import Play, Track, Artist, Album, TrackArtist


@pytest.fixture
def setup_users_and_friends(test_session: Session):
    me = User(id="me", name="Me", email="me@example.com", username="meu")
    f1 = User(id="f1", name="Friend1", email="f1@example.com", username="f1u")
    nf = User(id="nf", name="NotFriend", email="nf@example.com", username="nfu")
    test_session.add_all([me, f1, nf])

    # Friends: me <-> f1 accepted
    low, high = ("f1", "me") if "f1" < "me" else ("me", "f1")
    fr = Friendship(
        user_low_id=low,
        user_high_id=high,
        status=FriendshipStatus.accepted,
        requested_by_id=low,
    )
    test_session.add(fr)

    # Tracks and artists/albums
    t1 = Track(id="t1", title="Nevermind", duration=200000)
    t2 = Track(id="t2", title="Song2", duration=180000)
    a1 = Artist(id="a1", name="Nirvana", picture=None)
    alb = Album(
        id="alb1",
        name="Album1",
        picture=None,
        release_date=None,
        release_date_precision=None,
    )
    t1.album_id = alb.id
    test_session.add_all([t1, t2, a1, alb])
    test_session.add_all([TrackArtist(track_id="t1", artist_id="a1")])

    # Plays spanning dates
    now = datetime.datetime(2013, 8, 15, tzinfo=timezone.utc)
    plays = [
        Play(user_id="me", track_id="t1", date=now),  # 2013-08-15 me Nirvana/Nevermind
        Play(
            user_id="f1", track_id="t2", date=now - datetime.timedelta(days=2)
        ),  # 2013-08-13 friend Song2
        Play(
            user_id="me", track_id="t2", date=now.replace(year=2012)
        ),  # 2012-08-15 me Song2
    ]
    test_session.add_all(plays)
    test_session.commit()
    return me, f1, nf, now


def test_recent_basic_and_include_me(
    client: TestClient, test_app, setup_users_and_friends
):
    me, f1, nf, now = setup_users_and_friends
    from routes.deps import get_current_user

    test_app.dependency_overrides[get_current_user] = lambda: me

    # Default includes me
    r = client.get("/recent?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 3
    assert data["items"][0]["user"]["id"] == "me"

    # Exclude me
    r = client.get("/recent?limit=10&include_me=false")
    assert r.status_code == 200
    data = r.json()
    assert all(item["user"]["id"] != "me" for item in data["items"])  # only friends

    del test_app.dependency_overrides[get_current_user]


def test_recent_pagination_and_before(
    client: TestClient, test_app, setup_users_and_friends
):
    me, *_ = setup_users_and_friends
    from routes.deps import get_current_user

    test_app.dependency_overrides[get_current_user] = lambda: me

    r1 = client.get("/recent?limit=2")
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["items"]) == 2
    assert d1["next_before"] is not None

    # Fetch next page using next_before
    r2 = client.get(f"/recent?limit=2&before={d1['next_before']}")
    assert r2.status_code == 200
    d2 = r2.json()
    # Remaining 1 item, no next_before
    assert len(d2["items"]) == 1
    assert d2["next_before"] is None

    del test_app.dependency_overrides[get_current_user]


def test_recent_user_filter_and_auth(
    client: TestClient, test_app, setup_users_and_friends
):
    me, f1, nf, _ = setup_users_and_friends
    from routes.deps import get_current_user

    # Unauthenticated -> 401
    r = client.get("/recent")
    assert r.status_code == 401

    # As me - filter to friend OK
    test_app.dependency_overrides[get_current_user] = lambda: me
    r = client.get(f"/recent?user={f1.username}")
    assert r.status_code == 200
    data = r.json()
    assert all(item["user"]["id"] == f1.id for item in data["items"])  # only friend

    # Filter to non-friend -> 403
    r = client.get(f"/recent?user={nf.username}")
    assert r.status_code == 403

    del test_app.dependency_overrides[get_current_user]


def test_recent_search_by_title(client: TestClient, test_app, setup_users_and_friends):
    me, *_ = setup_users_and_friends
    from routes.deps import get_current_user

    test_app.dependency_overrides[get_current_user] = lambda: me

    # Search by token matching track title (Nevermind)
    r = client.get("/recent?limit=10&q=never")
    assert r.status_code == 200
    items = r.json()["items"]
    assert any("Nevermind" == it["track"]["title"] for it in items)

    # Search by artist
    r = client.get("/recent?limit=10&q=nirvana")
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(it["track"]["title"] == "Nevermind" for it in items)

    del test_app.dependency_overrides[get_current_user]


def test_recent_search_by_date_tokens(
    client: TestClient, test_app, setup_users_and_friends
):
    me, *_ = setup_users_and_friends
    from routes.deps import get_current_user

    test_app.dependency_overrides[get_current_user] = lambda: me

    # Year-only should include 2013 items only
    r = client.get("/recent?limit=10&q=2013")
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(it["played_at"].startswith("2013-") for it in items)

    # Year-month should include only 2013-08
    r = client.get("/recent?limit=10&q=2013-08")
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(it["played_at"].startswith("2013-08") for it in items)

    del test_app.dependency_overrides[get_current_user]
