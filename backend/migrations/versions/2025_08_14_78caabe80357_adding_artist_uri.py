"""adding artist.uri

Revision ID: 78caabe80357
Revises: b852c4338504
Create Date: 2025-08-14 00:52:06.212336

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = "78caabe80357"
down_revision = "b852c4338504"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("artists", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("artists", schema=None) as batch_op:
        batch_op.drop_column("uri")
