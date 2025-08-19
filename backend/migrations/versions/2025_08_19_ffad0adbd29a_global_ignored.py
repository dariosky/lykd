"""global ignored

Revision ID: 5fad0adbd29a
Revises: b1a2c3d4e5f6
Create Date: 2025-08-19 23:31:34.704308

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel

import models

# revision identifiers, used by Alembic.
revision = "ffad0adbd29a"
down_revision = "b1a2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "global_ignored_artists",
        sa.Column("artist_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("approved_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("ts", models.types.UtcAwareDateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artists.id"],
        ),
        sa.PrimaryKeyConstraint("artist_id"),
    )
    with op.batch_alter_table("global_ignored_artists", schema=None) as batch_op:
        batch_op.create_index(
            "idx_global_ignored_artists_artist", ["artist_id"], unique=False
        )

    op.create_table(
        "global_ignored_tracks",
        sa.Column("track_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("approved_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("ts", models.types.UtcAwareDateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
        ),
        sa.PrimaryKeyConstraint("track_id"),
    )
    with op.batch_alter_table("global_ignored_tracks", schema=None) as batch_op:
        batch_op.create_index(
            "idx_global_ignored_tracks_track", ["track_id"], unique=False
        )

    with op.batch_alter_table("ignored_artists", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "reported",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            )
        )

    with op.batch_alter_table("ignored_tracks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "reported",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("ignored_tracks", schema=None) as batch_op:
        batch_op.drop_column("reported")

    with op.batch_alter_table("ignored_artists", schema=None) as batch_op:
        batch_op.drop_column("reported")

    with op.batch_alter_table("global_ignored_tracks", schema=None) as batch_op:
        batch_op.drop_index("idx_global_ignored_tracks_track")

    op.drop_table("global_ignored_tracks")
    with op.batch_alter_table("global_ignored_artists", schema=None) as batch_op:
        batch_op.drop_index("idx_global_ignored_artists_artist")

    op.drop_table("global_ignored_artists")
