"""migrate to uid likes and ignore

Revision ID: a703d0e6ec71
Revises: 4ec607b432b8
Create Date: 2025-09-04 20:12:01.478716

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel

# Use ORM to backfill
from sqlmodel import Session, select
from models.music import Like, Track, IgnoredTrack, GlobalIgnoredTrack

# revision identifiers, used by Alembic.
revision = "a703d0e6ec71"
down_revision = "4ec607b432b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("uid", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.create_index(batch_op.f("ix_tracks_uid"), ["uid"], unique=False)
        batch_op.drop_column("uri")

    with op.batch_alter_table("global_ignored_tracks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("uid", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.create_foreign_key("global_ignore_uid_fg", "tracks", ["uid"], ["uid"])

    with op.batch_alter_table("ignored_tracks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "uid", sqlmodel.sql.sqltypes.AutoString(), default=None, nullable=True
            )
        )
        batch_op.create_foreign_key("ignore_uid_fg", "tracks", ["uid"], ["uid"])

    with op.batch_alter_table("likes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("uid", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )
        batch_op.create_foreign_key("likes_uid_fg", "tracks", ["uid"], ["id"])

    with Session(op.get_bind()) as db:
        # migrate likes
        for like, track in db.exec(
            select(Like, Track).where(Like.track_id == Track.id)
        ):
            like.uid = track.uid
            db.merge(like)

        # migrate ignored tracks
        for ignored_track, track in db.exec(
            select(IgnoredTrack, Track).where(IgnoredTrack.track_id == Track.id)
        ):
            ignored_track.uid = track.uid
            db.merge(ignored_track)

        # migrate global ignored tracks
        for ignored_track, track in db.exec(
            select(GlobalIgnoredTrack, Track).where(
                GlobalIgnoredTrack.track_id == Track.id
            )
        ):
            ignored_track.uid = track.uid
            db.merge(ignored_track)
        db.commit()


def downgrade() -> None:
    with op.batch_alter_table("likes", schema=None) as batch_op:
        batch_op.drop_constraint("likes_uid_fg", type_="foreignkey")
        batch_op.drop_column("uid")

    with op.batch_alter_table("ignored_tracks", schema=None) as batch_op:
        batch_op.drop_constraint("ignore_uid_fg", type_="foreignkey")
        batch_op.drop_column("uid")

    with op.batch_alter_table("global_ignored_tracks", schema=None) as batch_op:
        batch_op.drop_constraint("global_ignore_uid_fg", type_="foreignkey")
        batch_op.drop_column("uid")

    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("uri", sa.VARCHAR(), nullable=True))
        batch_op.drop_index(batch_op.f("ix_tracks_uid"))
        batch_op.drop_column("uid")
