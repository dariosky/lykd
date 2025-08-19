"""add idx_plays_user_track

Revision ID: b1a2c3d4e5f6
Revises: ad2786ea98a0
Create Date: 2025-08-19 18:45:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1a2c3d4e5f6"
down_revision = "ad2786ea98a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plays", schema=None) as batch_op:
        batch_op.create_index(
            "idx_plays_user_track", ["user_id", "track_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("plays", schema=None) as batch_op:
        batch_op.drop_index("idx_plays_user_track")
