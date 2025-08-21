"""storing user.subscribed

Revision ID: 58bec5fc7a82
Revises: d31adb07ac16
Create Date: 2025-08-21 23:44:00.107563

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "58bec5fc7a82"
down_revision = "d31adb07ac16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "subscribed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("subscribed")
