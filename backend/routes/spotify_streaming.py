from fastapi import Depends, HTTPException, APIRouter
from pydantic import BaseModel
from sqlmodel import Session

from models import User
from models.common import get_session
from routes.deps import current_user
from services import Spotify
from services.spotify import get_spotify_client

router = APIRouter()


class PlayRequest(BaseModel):
    track_id: str
    context: dict | None = None


class TransferRequest(BaseModel):
    device_id: str
    play: bool | None = True


@router.post("/spotify/play")
async def spotify_play(
    body: PlayRequest,
    user: User = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
    db: Session = Depends(get_session),
):
    # Start playback; if it succeeds, also return track details for immediate UI update
    try:
        await spotify.play(user=user, db_session=db, uris=[body.track_id])
    except HTTPException as e:
        if e.status_code == 404 and "No active device" in (e.detail or ""):
            raise HTTPException(
                status_code=404,
                detail="No active device - open Spotify on one of your devices",
            )
        raise

    # Fetch track details for immediate display
    try:
        t = await spotify.get_track(user=user, db_session=db, track_id=body.track_id)
        artists = [
            a.get("name") for a in (t.get("artists") or []) if a and a.get("name")
        ]
        images = (t.get("album") or {}).get("images") or []
        album_image = images[0]["url"] if images else None
        track_payload = {
            "id": t.get("id"),
            "name": t.get("name"),
            "artists": artists,
            "album_image": album_image,
            "duration_ms": t.get("duration_ms") or 0,
        }
    except Exception:
        track_payload = None

    return {"status": "ok", "track": track_payload}


@router.post("/spotify/resume")
async def spotify_resume(
    user: User = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
    db: Session = Depends(get_session),
):
    try:
        await spotify.play(user=user, db_session=db, uris=None)
    except HTTPException as e:
        if e.status_code == 404 and "No active device" in (e.detail or ""):
            raise HTTPException(
                status_code=404,
                detail="No active device - open Spotify on one of your devices",
            )
        raise
    return {"status": "ok"}


@router.post("/spotify/pause")
async def spotify_pause(
    user: User = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
    db: Session = Depends(get_session),
):
    try:
        await spotify.pause(user=user, db_session=db)
    except HTTPException as e:
        raise e
    return {"status": "ok"}


@router.post("/spotify/next")
async def spotify_next(
    user: User = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
    db: Session = Depends(get_session),
):
    try:
        await spotify.next(user=user, db_session=db)
    except HTTPException as e:
        raise e
    return {"status": "ok"}


@router.get("/spotify/playback")
async def spotify_playback(
    user: User = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
    db: Session = Depends(get_session),
):
    state = await spotify.get_playback_state(user=user, db_session=db)
    # Return minimal info (pass-through for now)
    return {"state": state}


@router.get("/spotify/token")
async def spotify_token(
    user: User = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
    db: Session = Depends(get_session),
):
    # Try to always return a valid token; refresh when possible
    try:
        access_token = user.get_access_token()
        if not access_token:
            updated = await spotify.refresh_token(user=user)
            user.tokens = {**(user.tokens or {}), **updated}
            db.add(user)
            db.commit()
            access_token = user.get_access_token()
        if not access_token:
            raise HTTPException(status_code=401, detail="Missing access token")
        return {"access_token": access_token}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spotify/transfer")
async def spotify_transfer(
    body: TransferRequest,
    user: User = Depends(current_user),
    spotify: Spotify = Depends(get_spotify_client),
    db: Session = Depends(get_session),
):
    try:
        await spotify.transfer_playback(
            user=user, db_session=db, device_id=body.device_id, play=bool(body.play)
        )
        return {"status": "ok"}
    except HTTPException as e:
        raise e
