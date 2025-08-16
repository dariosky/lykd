"""adding last scan times

Revision ID: dc4e98e5718a
Revises: e4635b15000d
Create Date: 2025-08-16 18:26:03.189626

"""

import models
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "dc4e98e5718a"
down_revision = "e4635b15000d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "last_like_scan_full",
                models.types.UtcAwareDateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_like_scan",
                models.types.UtcAwareDateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "last_history_sync",
                models.types.UtcAwareDateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                models.types.UtcAwareDateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("last_history_sync")
        batch_op.drop_column("last_like_scan")
        batch_op.drop_column("last_like_scan_full")
