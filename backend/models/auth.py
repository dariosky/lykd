"""Authentication models"""

import datetime
import re
from typing import Any

from sqlalchemy import func
from sqlmodel import SQLModel, Field, Column, JSON, Session, select
from .common import CamelModel
from .types import UtcAwareDateTime  # adjust import as needed


class User(SQLModel, CamelModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    username: str | None = Field(default=None, index=True, unique=True, nullable=True)
    picture: str | None = None
    tokens: dict[str, Any] | None = Field(default_factory=dict, sa_column=Column(JSON))
    join_date: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(UtcAwareDateTime(), nullable=False),
    )
    is_admin: bool = False

    last_like_scan_full: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UtcAwareDateTime(), nullable=True),
    )

    last_like_scan: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UtcAwareDateTime(), nullable=True),
    )

    last_history_sync: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UtcAwareDateTime(), nullable=True),
    )

    updated_at: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UtcAwareDateTime(), onupdate=func.now(), nullable=True),
    )

    def get_access_token(self) -> str:
        return self.tokens.get("access_token") if self.tokens else None

    def get_refresh_token(self) -> str:
        return self.tokens.get("refresh_token") if self.tokens else None

    def __str__(self):
        return self.email


def populate_username(db_session: Session, user: User) -> str:
    # Extract base username from name or email
    base_username = ""

    if user.name and user.name.strip():
        # Split on any punctuation or whitespace and take first part
        parts = re.split(r"[\s\W]+", user.name.strip())
        if parts and parts[0]:
            base_username = parts[0].lower()

    if not base_username and user.email:
        # Fall back to email part before @
        email_part = user.email.split("@")[0]
        # Split on punctuation/spaces and take first part
        parts = re.split(r"[\s\W]+", email_part)
        if parts and parts[0]:
            base_username = parts[0].lower()

    if not base_username:
        base_username = "user"

    # Generate unique username
    candidate = base_username
    suffix = 2

    while True:
        # Check if username already exists
        existing_user = db_session.exec(
            select(User).where(User.username == candidate)
        ).first()

        if not existing_user:
            break

        candidate = f"{base_username}#{suffix}"
        suffix += 1

    # Update the user with the new username
    user.username = candidate
    db_session.add(user)

    return candidate


class OAuthState(SQLModel, CamelModel, table=True):
    """Single-use OAuth state to prevent CSRF and enable auditing.

    We store a hash of the state (not the raw token), timing info, and
    client metadata to detect/restrict misbehaving clients.
    """

    __tablename__ = "oauth_states"

    id: int | None = Field(default=None, primary_key=True)
    provider: str = Field(default="spotify", index=True)

    # Store a hash of the state for security; keep it unique for single-use
    state_hash: str = Field(index=True, unique=True)

    # Optional PKCE code_verifier storage (if used)
    code_verifier: str | None = Field(default=None)

    # Timestamps
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(UtcAwareDateTime(), nullable=False),
    )
    expires_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=10),
        sa_column=Column(UtcAwareDateTime(), nullable=False),
    )
    consumed_at: datetime.datetime | None = Field(
        default=None,
        sa_column=Column(UtcAwareDateTime(), nullable=True),
    )

    # Client tracking to spot misbehaving clients
    request_ip: str | None = Field(default=None)
    request_user_agent: str | None = Field(default=None)
    request_referer: str | None = Field(default=None)
    consumed_by_ip: str | None = Field(default=None)

    # Optional metadata to help debugging flows
    redirect_uri: str | None = Field(default=None)
    next_url: str | None = Field(default=None)

    attempt_count: int = Field(default=0)

    # The user that completed the handshake (set on successful callback)
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
