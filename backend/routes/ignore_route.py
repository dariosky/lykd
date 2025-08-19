from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy import func

from models.auth import User
from models.common import get_session
from models.music import IgnoredTrack, IgnoredArtist, Track, Artist, TrackArtist, Album
from routes.deps import current_user

router = APIRouter()


@router.get("/ignore")
async def list_ignored(
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    artist_agg = func.string_agg(Artist.name, ",").label("artist_names")

    # Fetch ignored tracks with aggregated artist names, ordered by timestamp desc
    stmt_tracks = (
        select(
            Track.id,  # track_id
            Track.title,  # title
            Album.id,  # album_id
            Album.name,  # album_name
            Album.picture,  # album_picture
            artist_agg,
        )
        .select_from(IgnoredTrack)
        .join(Track, Track.id == IgnoredTrack.track_id)
        .join(Album, Album.id == Track.album_id, isouter=True)
        .join(TrackArtist, TrackArtist.track_id == Track.id, isouter=True)
        .join(Artist, Artist.id == TrackArtist.artist_id, isouter=True)
        .where(IgnoredTrack.user_id == user.id)
        .group_by(Track.id, Track.title, Album.id, Album.name, Album.picture)
        .order_by(IgnoredTrack.ts.desc())
    )
    track_rows = session.exec(stmt_tracks).all()

    tracks_payload = []
    for (
        track_id,
        title,
        album_id,
        album_name,
        album_picture,
        artist_names,
    ) in track_rows:
        artists_list = []
        if artist_names:
            # Split on comma and strip whitespace for both SQLite and Postgres
            artists_list = [s.strip() for s in str(artist_names).split(",") if s]
        tracks_payload.append(
            {
                "track_id": track_id,
                "title": title,
                "album": (
                    {"id": album_id, "name": album_name, "picture": album_picture}
                    if album_id is not None
                    else None
                ),
                "artists": artists_list,
            }
        )

    # Efficiently fetch ignored artists with id and name only, ordered by timestamp desc
    stmt_artists = (
        select(Artist.id, Artist.name)
        .select_from(IgnoredArtist)
        .join(Artist, Artist.id == IgnoredArtist.artist_id)
        .where(IgnoredArtist.user_id == user.id)
        .order_by(IgnoredArtist.ts.desc())
    )
    artist_rows = session.exec(stmt_artists).all()
    artists_payload = [
        {"artist_id": ar_id, "name": name} for (ar_id, name) in artist_rows
    ]

    return {"tracks": tracks_payload, "artists": artists_payload}


@router.post("/ignore/track/{track_id}")
async def ignore_track(
    track_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    # Ensure track exists
    if not session.get(Track, track_id):
        raise HTTPException(status_code=404, detail="Track not found")

    existing = session.get(IgnoredTrack, (user.id, track_id))
    if not existing:
        session.add(IgnoredTrack(user_id=user.id, track_id=track_id))
        session.commit()
    return {"message": "ignored"}


@router.delete("/ignore/track/{track_id}")
async def unignore_track(
    track_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    obj = session.get(IgnoredTrack, (user.id, track_id))
    if obj:
        session.delete(obj)
        session.commit()
    return {"message": "unignored"}


@router.post("/ignore/artist/{artist_id}")
async def ignore_artist(
    artist_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    if not session.get(Artist, artist_id):
        raise HTTPException(status_code=404, detail="Artist not found")

    existing = session.get(IgnoredArtist, (user.id, artist_id))
    if not existing:
        session.add(IgnoredArtist(user_id=user.id, artist_id=artist_id))
        session.commit()
    return {"message": "ignored"}


@router.delete("/ignore/artist/{artist_id}")
async def unignore_artist(
    artist_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    obj = session.get(IgnoredArtist, (user.id, artist_id))
    if obj:
        session.delete(obj)
        session.commit()
    return {"message": "unignored"}
