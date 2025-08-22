"""adding playlist snapshot

Revision ID: bae845b7158a
Revises: 58bec5fc7a82
Create Date: 2025-08-22 15:18:57.430839

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "bae845b7158a"
down_revision = "58bec5fc7a82"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("playlists", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("snapshot_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_collaborative",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("playlists", schema=None) as batch_op:
        batch_op.drop_column("is_collaborative")
        batch_op.drop_column("snapshot_id")
