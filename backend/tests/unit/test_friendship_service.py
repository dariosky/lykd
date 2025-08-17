import pytest
from sqlmodel import Session

from models.auth import User
from services.friendship import (
    request_friendship,
    accept_friendship,
)


@pytest.fixture
def users(test_session: Session):
    u1 = User(id="u1", name="Alice", email="alice@example.com", username="alice")
    u2 = User(id="u2", name="Bob", email="bob@example.com", username="bob")
    test_session.add(u1)
    test_session.add(u2)
    test_session.commit()
    return u1, u2


def test_only_recipient_can_accept(test_session: Session, users):
    u1, u2 = users
    # u1 sends a request to u2
    fr = request_friendship(test_session, requester=u1, recipient=u2)
    assert fr.status.value == "pending"
    assert fr.requested_by_id == u1.id

    # u1 cannot accept their own request
    with pytest.raises(PermissionError):
        accept_friendship(test_session, requester=u1, recipient=u2)

    # u2 (recipient) can accept
    fr2 = accept_friendship(test_session, requester=u2, recipient=u1)
    assert fr2.status.value == "accepted"
