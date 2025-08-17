"""adding indexes

Revision ID: 3fff3f6745bc
Revises: 0c9d57cb5fbe
Create Date: 2025-08-18 00:20:11.827778

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "3fff3f6745bc"
down_revision = "0c9d57cb5fbe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("artists_tracks", schema=None) as batch_op:
        batch_op.create_index("idx_artists_tracks_artist", ["artist_id"], unique=False)
        batch_op.create_index("idx_artists_tracks_track", ["track_id"], unique=False)

    with op.batch_alter_table("plays", schema=None) as batch_op:
        batch_op.create_index("idx_plays_date", ["date"], unique=False)
        batch_op.create_index("idx_plays_track", ["track_id"], unique=False)
        batch_op.create_index("idx_plays_user_date", ["user_id", "date"], unique=False)
        batch_op.create_index(
            "idx_plays_user_date_track", ["user_id", "date", "track_id"], unique=False
        )

    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.create_index("idx_tracks_album_id", ["album_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.drop_index("idx_tracks_album_id")

    with op.batch_alter_table("plays", schema=None) as batch_op:
        batch_op.drop_index("idx_plays_user_date_track")
        batch_op.drop_index("idx_plays_user_date")
        batch_op.drop_index("idx_plays_track")
        batch_op.drop_index("idx_plays_date")

    with op.batch_alter_table("artists_tracks", schema=None) as batch_op:
        batch_op.drop_index("idx_artists_tracks_track")
        batch_op.drop_index("idx_artists_tracks_artist")
