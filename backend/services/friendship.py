import datetime
import logging

from sqlmodel import Session, select

from models.auth import User
from models.friendship import Friendship, FriendshipStatus

logger = logging.getLogger("lykd.friendship")


def request_friendship(
    session: Session, *, requester: User, recipient: User
) -> Friendship:
    if requester == recipient:
        raise ValueError("Cannot friend yourself.")

    low, high = Friendship.canonical_pair(requester.id, recipient.id)
    existing = session.exec(
        select(Friendship).where(
            Friendship.user_low_id == low,
            Friendship.user_high_id == high,
        )
    ).first()

    now = datetime.datetime.now(datetime.timezone.utc)
    if existing:
        match existing.status:
            case FriendshipStatus.accepted:
                raise ValueError("Users are already friends.")
            case FriendshipStatus.pending:
                # Optional: if the opposite user sends another request, you could auto-accept here.
                raise ValueError("A request is already pending.")
            case _:
                # Re-open the flow
                logger.debug("Refreshing the friendship request.")
                existing.status = FriendshipStatus.pending
                existing.requested_by_id = requester.id
                existing.requested_at = now
                existing.responded_at = None
                session.add(existing)
                session.commit()
                return existing

    friendship = Friendship(
        user_low_id=low,
        user_high_id=high,
        status=FriendshipStatus.pending,
        requested_by_id=requester.id,
        requested_at=now,
    )
    session.add(friendship)
    session.commit()
    return friendship


def accept_friendship(
    session: Session, *, requester: User, recipient: User
) -> Friendship:
    low, high = Friendship.canonical_pair(requester.id, recipient.id)
    friendship = session.exec(
        select(Friendship).where(
            Friendship.user_low_id == low,
            Friendship.user_high_id == high,
        )
    ).first()
    if not friendship or friendship.status != FriendshipStatus.pending:
        raise ValueError("No pending request to accept.")

    if friendship.requested_by_id == recipient.id:
        raise PermissionError("Requester cannot accept their own request.")

    friendship.status = FriendshipStatus.accepted
    friendship.responded_at = datetime.datetime.now(datetime.timezone.utc)
    session.add(friendship)
    session.commit()
    return friendship


def decline_friendship(
    session: Session, *, requester: User, recipient: User
) -> Friendship:
    low, high = Friendship.canonical_pair(requester.id, recipient.id)
    friendship = session.exec(
        select(Friendship).where(
            Friendship.user_low_id == low,
            Friendship.user_high_id == high,
        )
    ).first()
    if not friendship or friendship.status != FriendshipStatus.pending:
        raise ValueError("No pending request to decline.")
    friendship.status = FriendshipStatus.declined
    friendship.responded_at = datetime.datetime.now(datetime.timezone.utc)
    session.add(friendship)
    session.commit()
    return friendship


def unfriend(session: Session, *, user_id: str, other_id: str) -> None:
    low, high = Friendship.canonical_pair(user_id, other_id)
    friendship = session.exec(
        select(Friendship).where(
            Friendship.user_low_id == low,
            Friendship.user_high_id == high,
            Friendship.status == FriendshipStatus.accepted,
        )
    ).first()
    if not friendship:
        raise ValueError("No existing friendship to decline.")
    session.delete(friendship)
    session.commit()
