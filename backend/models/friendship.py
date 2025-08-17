import datetime
from enum import Enum

from sqlalchemy import UniqueConstraint, CheckConstraint, Column
from sqlmodel import SQLModel, Field

from models.types import UtcAwareDateTime


class FriendshipStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    blocked = "blocked"


class Friendship(SQLModel, table=True):
    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("user_low_id", "user_high_id", name="uq_friend_pair"),
        CheckConstraint("user_low_id < user_high_id", name="ck_friend_order"),
    )

    # Canonical pair (always low < high)
    user_low_id: str = Field(foreign_key="users.id", primary_key=True)
    user_high_id: str = Field(foreign_key="users.id", primary_key=True)

    # Request flow
    status: FriendshipStatus = Field(default=FriendshipStatus.pending, index=True)
    requested_by_id: str = Field(foreign_key="users.id", index=True)

    requested_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(UtcAwareDateTime(), nullable=False),
    )
    responded_at: datetime.datetime | None = Field(
        sa_column=Column(UtcAwareDateTime(), nullable=True),
    )

    # Helpers
    @staticmethod
    def canonical_pair(a: str, b: str) -> tuple[str, str]:
        return (a, b) if a < b else (b, a)
