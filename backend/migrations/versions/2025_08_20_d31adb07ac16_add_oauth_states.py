"""add oauth_states

Revision ID: d31adb07ac16
Revises: ffad0adbd29a
Create Date: 2025-08-20 23:48:18.113857

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel
import models


# revision identifiers, used by Alembic.
revision = "d31adb07ac16"
down_revision = "ffad0adbd29a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("state_hash", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("code_verifier", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "created_at", models.types.UtcAwareDateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "expires_at", models.types.UtcAwareDateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "consumed_at", models.types.UtcAwareDateTime(timezone=True), nullable=True
        ),
        sa.Column("request_ip", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "request_user_agent", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("request_referer", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("consumed_by_ip", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("redirect_uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("next_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("oauth_states", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_oauth_states_provider"), ["provider"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_oauth_states_state_hash"), ["state_hash"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_oauth_states_user_id"), ["user_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("oauth_states", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_oauth_states_user_id"))
        batch_op.drop_index(batch_op.f("ix_oauth_states_state_hash"))
        batch_op.drop_index(batch_op.f("ix_oauth_states_provider"))

    op.drop_table("oauth_states")
