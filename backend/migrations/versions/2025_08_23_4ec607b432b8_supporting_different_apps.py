"""supporting different apps

Revision ID: 4ec607b432b8
Revises: bae845b7158a
Create Date: 2025-08-23 17:45:06.384059

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4ec607b432b8"
down_revision = "bae845b7158a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "app_name",
                sa.Enum("spotlike", "lykd", name="apps"),
                server_default=sa.text("'spotlike'"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("app_name")
