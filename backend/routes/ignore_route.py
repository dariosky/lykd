from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy import func

from models.auth import User
from models.common import get_session
from models.music import (
    IgnoredTrack,
    IgnoredArtist,
    Track,
    Artist,
    TrackArtist,
    Album,
    GlobalIgnoredTrack,
    GlobalIgnoredArtist,
)
from routes.deps import current_user

router = APIRouter()


@router.get("/ignore")
async def list_ignored(
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    artist_agg = func.string_agg(Artist.name, ",").label("artist_names")

    # Fetch ignored tracks with aggregated artist names and global+reported flags
    stmt_tracks = (
        select(
            Track.id,  # track_id
            Track.title,  # title
            Album.id,  # album_id
            Album.name,  # album_name
            Album.picture,  # album_picture
            func.max(GlobalIgnoredTrack.track_id).label("global_track_id"),
            func.max(IgnoredTrack.reported).label("reported_flag"),
            artist_agg,
        )
        .select_from(IgnoredTrack)
        .join(Track, Track.id == IgnoredTrack.track_id)
        .join(Album, Album.id == Track.album_id, isouter=True)
        .join(TrackArtist, TrackArtist.track_id == Track.id, isouter=True)
        .join(Artist, Artist.id == TrackArtist.artist_id, isouter=True)
        .outerjoin(
            GlobalIgnoredTrack, GlobalIgnoredTrack.track_id == IgnoredTrack.track_id
        )
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
        global_track_id,
        reported_flag,
        artist_names,
    ) in track_rows:
        artists_list = []
        if artist_names:
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
                "is_global": global_track_id is not None,
                "reported": bool(reported_flag),
            }
        )

    # Efficiently fetch ignored artists with id, name and global+reported flags
    stmt_artists = (
        select(
            Artist.id,
            Artist.name,
            func.max(GlobalIgnoredArtist.artist_id).label("global_artist_id"),
            func.max(IgnoredArtist.reported).label("reported_flag"),
        )
        .select_from(IgnoredArtist)
        .join(Artist, Artist.id == IgnoredArtist.artist_id)
        .outerjoin(
            GlobalIgnoredArtist,
            GlobalIgnoredArtist.artist_id == IgnoredArtist.artist_id,
        )
        .where(IgnoredArtist.user_id == user.id)
        .group_by(Artist.id, Artist.name)
        .order_by(IgnoredArtist.ts.desc())
    )
    artist_rows = session.exec(stmt_artists).all()
    artists_payload = [
        {
            "artist_id": ar_id,
            "name": name,
            "is_global": global_id is not None,
            "reported": bool(reported_flag),
        }
        for (ar_id, name, global_id, reported_flag) in artist_rows
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


@router.post("/ignore/track/{track_id}/report")
async def report_ignored_track(
    track_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    if not session.get(Track, track_id):
        raise HTTPException(status_code=404, detail="Track not found")

    obj = session.get(IgnoredTrack, (user.id, track_id))
    if not obj:
        obj = IgnoredTrack(user_id=user.id, track_id=track_id, reported=True)
        session.add(obj)
    else:
        obj.reported = True
        session.add(obj)
    session.commit()
    return {"message": "reported"}


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


@router.post("/ignore/artist/{artist_id}/report")
async def report_ignored_artist(
    artist_id: str,
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    if not session.get(Artist, artist_id):
        raise HTTPException(status_code=404, detail="Artist not found")

    obj = session.get(IgnoredArtist, (user.id, artist_id))
    if not obj:
        obj = IgnoredArtist(user_id=user.id, artist_id=artist_id, reported=True)
        session.add(obj)
    else:
        obj.reported = True
        session.add(obj)
    session.commit()
    return {"message": "reported"}


# Admin endpoints to approve/reject and list reports
@router.get("/reports")
async def list_reports(
    session: Session = Depends(get_session),
    admin: User | None = Depends(current_user),
):
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")

    # Tracks that have been reported but not yet globally approved
    artist_agg = func.string_agg(Artist.name, ",").label("artist_names")
    stmt_track_reports = (
        select(
            Track.id,
            Track.title,
            Album.id,
            Album.name,
            Album.picture,
            func.count(IgnoredTrack.user_id).label("report_count"),
            artist_agg,
        )
        .select_from(IgnoredTrack)
        .join(Track, Track.id == IgnoredTrack.track_id)
        .join(Album, Album.id == Track.album_id, isouter=True)
        .join(TrackArtist, TrackArtist.track_id == Track.id, isouter=True)
        .join(Artist, Artist.id == TrackArtist.artist_id, isouter=True)
        .outerjoin(
            GlobalIgnoredTrack, GlobalIgnoredTrack.track_id == IgnoredTrack.track_id
        )
        .where(IgnoredTrack.reported.is_(True))
        .where(GlobalIgnoredTrack.track_id.is_(None))
        .group_by(Track.id, Track.title, Album.id, Album.name, Album.picture)
        .order_by(func.max(IgnoredTrack.ts).desc())
    )
    track_rows = session.exec(stmt_track_reports).all()
    track_reports = []
    for (
        track_id,
        title,
        album_id,
        album_name,
        album_picture,
        report_count,
        artist_names,
    ) in track_rows:
        artists_list = []
        if artist_names:
            artists_list = [s.strip() for s in str(artist_names).split(",") if s]
        track_reports.append(
            {
                "track_id": track_id,
                "title": title,
                "album": (
                    {"id": album_id, "name": album_name, "picture": album_picture}
                    if album_id is not None
                    else None
                ),
                "artists": artists_list,
                "report_count": int(report_count or 0),
            }
        )

    # Artists that have been reported but not yet globally approved
    stmt_artist_reports = (
        select(
            Artist.id,
            Artist.name,
            func.count(IgnoredArtist.user_id).label("report_count"),
        )
        .select_from(IgnoredArtist)
        .join(Artist, Artist.id == IgnoredArtist.artist_id)
        .outerjoin(
            GlobalIgnoredArtist,
            GlobalIgnoredArtist.artist_id == IgnoredArtist.artist_id,
        )
        .where(IgnoredArtist.reported.is_(True))
        .where(GlobalIgnoredArtist.artist_id.is_(None))
        .group_by(Artist.id, Artist.name)
        .order_by(func.max(IgnoredArtist.ts).desc())
    )
    artist_rows = session.exec(stmt_artist_reports).all()
    artist_reports = [
        {
            "artist_id": artist_id,
            "name": name,
            "report_count": int(report_count or 0),
        }
        for (artist_id, name, report_count) in artist_rows
    ]

    return {"tracks": track_reports, "artists": artist_reports}


@router.post("/admin/ignore/track/{track_id}/approve")
async def admin_approve_track(
    track_id: str,
    session: Session = Depends(get_session),
    admin: User | None = Depends(current_user),
):
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    if not session.get(Track, track_id):
        raise HTTPException(status_code=404, detail="Track not found")

    existing = session.get(GlobalIgnoredTrack, track_id)
    if not existing:
        session.add(GlobalIgnoredTrack(track_id=track_id, approved_by=admin.id))
    # Clear reported flags for this track across all users
    for it in session.exec(
        select(IgnoredTrack).where(
            IgnoredTrack.track_id == track_id, IgnoredTrack.reported.is_(True)
        )
    ):
        it.reported = False
        session.add(it)
    session.commit()
    return {"message": "approved"}


@router.post("/admin/ignore/artist/{artist_id}/approve")
async def admin_approve_artist(
    artist_id: str,
    session: Session = Depends(get_session),
    admin: User | None = Depends(current_user),
):
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    if not session.get(Artist, artist_id):
        raise HTTPException(status_code=404, detail="Artist not found")

    existing = session.get(GlobalIgnoredArtist, artist_id)
    if not existing:
        session.add(GlobalIgnoredArtist(artist_id=artist_id, approved_by=admin.id))
    # Clear reported flags for this artist across all users
    for ia in session.exec(
        select(IgnoredArtist).where(
            IgnoredArtist.artist_id == artist_id, IgnoredArtist.reported.is_(True)
        )
    ):
        ia.reported = False
        session.add(ia)
    session.commit()
    return {"message": "approved"}


@router.post("/admin/ignore/track/{track_id}/reject")
async def admin_reject_track(
    track_id: str,
    session: Session = Depends(get_session),
    admin: User | None = Depends(current_user),
):
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    if not session.get(Track, track_id):
        raise HTTPException(status_code=404, detail="Track not found")

    # Clear reported flags for this track across all users (do not add to global ignores)
    for it in session.exec(
        select(IgnoredTrack).where(
            IgnoredTrack.track_id == track_id, IgnoredTrack.reported.is_(True)
        )
    ):
        it.reported = False
        session.add(it)
    session.commit()
    return {"message": "rejected"}


@router.post("/admin/ignore/artist/{artist_id}/reject")
async def admin_reject_artist(
    artist_id: str,
    session: Session = Depends(get_session),
    admin: User | None = Depends(current_user),
):
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    if not session.get(Artist, artist_id):
        raise HTTPException(status_code=404, detail="Artist not found")

    # Clear reported flags for this artist across all users (do not add to global ignores)
    for ia in session.exec(
        select(IgnoredArtist).where(
            IgnoredArtist.artist_id == artist_id, IgnoredArtist.reported.is_(True)
        )
    ):
        ia.reported = False
        session.add(ia)
    session.commit()
    return {"message": "rejected"}
