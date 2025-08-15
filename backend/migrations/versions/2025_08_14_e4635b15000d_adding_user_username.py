"""adding user.username

Revision ID: e4635b15000d
Revises: 78caabe80357
Create Date: 2025-08-14 22:45:55.181705

"""

import logging

from alembic import op
import sqlalchemy as sa

# Use ORM to backfill
from sqlmodel import Session, select
from models.auth import User, populate_username

# revision identifiers, used by Alembic.
revision = "e4635b15000d"
down_revision = "78caabe80357"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    try:
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.add_column(sa.Column("username", sa.String(), nullable=True))
            batch_op.create_index(
                batch_op.f("ix_users_username"), ["username"], unique=True
            )
    except Exception as e:
        logger.error(e)

    # Backfill usernames using ORM
    with Session(op.get_bind()) as session:
        users = session.exec(
            select(User).where((User.username.is_(None)) | (User.username == ""))
        ).all()
        for user in users:
            populate_username(session, user)

        session.commit()


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_username"))
        batch_op.drop_column("username")
