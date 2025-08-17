"""friendship

Revision ID: 0c9d57cb5fbe
Revises: dc4e98e5718a
Create Date: 2025-08-17 20:27:17.211482

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel

from models import UtcAwareDateTime

# revision identifiers, used by Alembic.
revision = "0c9d57cb5fbe"
down_revision = "dc4e98e5718a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "friendships",
        sa.Column("user_low_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_high_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "accepted", "declined", "blocked", name="friendshipstatus"
            ),
            nullable=False,
        ),
        sa.Column(
            "requested_by_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("requested_at", UtcAwareDateTime(timezone=True), nullable=False),
        sa.Column("responded_at", UtcAwareDateTime(timezone=True), nullable=True),
        sa.CheckConstraint("user_low_id < user_high_id", name="ck_friend_order"),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_high_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_low_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("user_low_id", "user_high_id"),
        sa.UniqueConstraint("user_low_id", "user_high_id", name="uq_friend_pair"),
    )
    with op.batch_alter_table("friendships", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_friendships_requested_by_id"),
            ["requested_by_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_friendships_status"), ["status"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("friendships", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_friendships_status"))
        batch_op.drop_index(batch_op.f("ix_friendships_requested_by_id"))

    op.drop_table("friendships")
