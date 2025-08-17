import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from models.auth import User


@pytest.fixture
def two_users(test_session: Session):
    a = User(id="u1", name="Alice", email="alice@example.com", username="alice")
    b = User(id="u2", name="Bob", email="bob@example.com", username="bob")
    test_session.add(a)
    test_session.add(b)
    test_session.commit()
    return a, b


def test_request_status_and_accept_flow(
    client: TestClient, test_app, test_session: Session, two_users
):
    a, b = two_users

    # As Alice (viewer)
    from routes.deps import get_current_user

    test_app.dependency_overrides[get_current_user] = lambda: a

    # Initially no relation
    r = client.get(f"/friendship/status/{b.username}")
    assert r.status_code == 200
    assert r.json()["status"] == "none"

    # Send request
    r = client.post(f"/friendship/request/{b.username}")
    assert r.status_code == 200
    assert r.json()["friendship"]["status"] == "pending"

    # Outgoing pending for Alice
    r = client.get(f"/friendship/status/{b.username}")
    assert r.status_code == 200
    assert r.json()["status"] == "pending_outgoing"

    # Switch to Bob
    test_app.dependency_overrides[get_current_user] = lambda: b

    # Incoming pending for Bob
    r = client.get(f"/friendship/status/{a.username}")
    assert r.status_code == 200
    assert r.json()["status"] == "pending_incoming"

    # Pending list shows Alice
    r = client.get("/friendship/pending")
    assert r.status_code == 200
    pending = r.json()["pending"]
    assert len(pending) == 1
    assert pending[0]["user"]["id"] == a.id

    # Alice cannot accept (403) — switch to Alice and try accept
    test_app.dependency_overrides[get_current_user] = lambda: a
    r = client.post(f"/friendship/accept/{b.username}")
    assert r.status_code == 403

    # Bob can accept
    test_app.dependency_overrides[get_current_user] = lambda: b
    r = client.post(f"/friendship/accept/{a.username}")
    assert r.status_code == 200
    assert r.json()["friendship"]["status"] == "accepted"

    # Now friends from both perspectives
    test_app.dependency_overrides[get_current_user] = lambda: a
    r = client.get(f"/friendship/status/{b.username}")
    assert r.json()["status"] == "friends"

    test_app.dependency_overrides[get_current_user] = lambda: b
    r = client.get(f"/friendship/status/{a.username}")
    assert r.json()["status"] == "friends"

    # Pending list empty now
    r = client.get("/friendship/pending")
    assert r.json()["pending"] == []

    # Cleanup override
    del test_app.dependency_overrides[get_current_user]


def test_identifier_by_id_works(client: TestClient, test_app, two_users):
    a, b = two_users
    from routes.deps import get_current_user

    # As Alice send request using Bob's id
    test_app.dependency_overrides[get_current_user] = lambda: a
    r = client.post(f"/friendship/request/{b.id}")
    assert r.status_code == 200

    # As Bob accept using Alice's id
    test_app.dependency_overrides[get_current_user] = lambda: b
    r = client.post(f"/friendship/accept/{a.id}")
    assert r.status_code == 200

    del test_app.dependency_overrides[get_current_user]
