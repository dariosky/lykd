"""Add music tables

Revision ID: 319b86f813a9
Revises: 71e6c5debeb0
Create Date: 2025-08-05 17:58:24.085212

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = "319b86f813a9"
down_revision = "71e6c5debeb0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "album",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("picture", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column(
            "release_date_precision",
            sa.Enum("day", "month", "year", name="dateprecision"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "artist",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("picture", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "album_artist",
        sa.Column("album_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("artist_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["album_id"],
            ["album.id"],
        ),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artist.id"],
        ),
        sa.PrimaryKeyConstraint("album_id", "artist_id"),
    )
    op.create_table(
        "track",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("album_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["album_id"],
            ["album.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "liked",
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("track_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["track.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "track_id", "date"),
    )
    op.create_table(
        "play",
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("track_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["track.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "track_id", "date"),
    )
    op.create_table(
        "track_artist",
        sa.Column("track_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("artist_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artist.id"],
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["track.id"],
        ),
        sa.PrimaryKeyConstraint("track_id", "artist_id"),
    )


def downgrade() -> None:
    op.drop_table("track_artist")
    op.drop_table("play")
    op.drop_table("liked")
    op.drop_table("track")
    op.drop_table("album_artist")
    op.drop_table("artist")
    op.drop_table("album")
