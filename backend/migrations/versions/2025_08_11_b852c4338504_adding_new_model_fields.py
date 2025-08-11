"""adding new model fields

Revision ID: b852c4338504
Revises: 27810886f3cc
Create Date: 2025-08-11 16:06:53.539521

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "b852c4338504"
down_revision = "27810886f3cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("albums", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    with op.batch_alter_table("playlists", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
    with op.batch_alter_table("plays", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("context_uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("plays", schema=None) as batch_op:
        batch_op.drop_column("context_uri")
    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.drop_column("uri")

    with op.batch_alter_table("playlists", schema=None) as batch_op:
        batch_op.drop_column("uri")

    with op.batch_alter_table("albums", schema=None) as batch_op:
        batch_op.drop_column("uri")
