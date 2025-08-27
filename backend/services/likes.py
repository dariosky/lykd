# Create async tasks for all users
import datetime

from models.auth import User
from models.music import Like, PlaylistTrack, Play, Playlist
from services import Spotify
from services.store import (
    store_track,
    store_playlist,
    update_likes_db,
    update_playlist_db,
)
from sqlmodel import select, Session

import logging

from utils.dates import parse_date

logger = logging.getLogger("lykd.likes")


async def get_one_liked_playlist(
    user: User, db_session: Session, spotify: Spotify
) -> dict:
    """This ensure that we are using ONE playlist for likes per user

    the target name depends on the user.app_name - but it will make sure to get
    just one playlist (the oldest) between all the ones named after Lykd or Spotlike
    """
    playlists = await spotify.get_all_playlists(user=user, db_session=db_session)
    playlist_name_candidates = {"Liked playlist", "Lykd Songs", "Lykd playlist"}
    same_name_playlists = [
        p
        for p in playlists
        if p["name"] in playlist_name_candidates and p["owner"]["id"] == user.id
    ]
    target_name = "Liked playlist" if user.app_name == "spotlike" else "Lykd playlist"
    target_description = (
        f"All the songs you like - synced by {user.app_name.value.capitalize()}"
    )
    target_public = False  # the synced playlist is always private
    assert target_name in playlist_name_candidates  # nosec B101

    if not same_name_playlists:
        spotify_playlist = await spotify.playlist_create(
            user,
            description=target_description,
            name=target_name,
            public=target_public,
        )
    else:
        spotify_playlist = same_name_playlists[-1]  # getting the oldest
        if len(same_name_playlists) > 1:  # removing the others
            for duplicated_playlist in same_name_playlists[:-1]:
                playlist_id = duplicated_playlist["id"]
                logger.debug(
                    f"Removing duplicated playlist {playlist_id} - {user} - {duplicated_playlist['name']}"
                )
                await spotify.delete_playlist(
                    user=user, db_session=db_session, playlist_id=playlist_id
                )
        changes = {}
        if spotify_playlist["name"] != target_name:
            changes["name"] = target_name
        if spotify_playlist["description"] != target_description:
            changes["description"] = target_description
        if spotify_playlist["public"] != target_public:
            spotify_playlist["public"] = target_public

        if changes:
            await spotify.playlist_change(
                user=user,
                db_session=db_session,
                playlist_id=spotify_playlist["id"],
                **changes,
            )

    return spotify_playlist


async def process_likes(db: Session, spotify: Spotify, user: User) -> None:
    # here I want to get the songs to add and remove - we have the fast or the slow way
    now = datetime.datetime.now(datetime.timezone.utc)
    full_scan = (
        user.last_like_scan_full is None
        or user.last_like_scan_full <= now - datetime.timedelta(hours=12)
    )

    all_db_like_ids = {
        like.track_id
        for like in db.exec(
            select(Like).where(
                Like.user_id == user.id,
            )
        )
    }

    if full_scan:
        logger.info(f"Full scan for {user} likes")
        # Fetch all liked songs from Spotify
        # TODO: Deduplicate likes before full-sync here
        all_spotify_likes = await spotify.get_all_likes(
            user=user,
            db_session=db,
        )
        logger.info(f"Processing {len(all_spotify_likes)} liked songs for user {user}:")

        all_spotify_likes_ids = {
            spotify_like["track"]["id"] for spotify_like in all_spotify_likes
        }
        new_spotify_likes = [
            spotify_like
            for spotify_like in all_spotify_likes
            if spotify_like["track"]["id"] not in all_db_like_ids
        ]

        tracks_to_remove = all_db_like_ids - all_spotify_likes_ids
    else:
        if user.last_like_scan and user.last_like_scan > now - datetime.timedelta(
            minutes=15
        ):
            return
        logger.info(f"Quick scan for {user} likes")
        new_spotify_likes = []
        async for spotify_like in spotify.yield_from(
            user=user,
            db_session=db,
            request=spotify.get_liked_page,
        ):
            track_id = spotify_like.get("track", {}).get("id")
            existing_like = db.get(Like, (user.id, track_id))
            if existing_like:
                break

            new_spotify_likes.append(spotify_like)
        # TODO: Deduplicate likes before quick-sync here
        tracks_to_remove = set()

    if new_spotify_likes or tracks_to_remove or full_scan:
        spotify_playlist = await get_one_liked_playlist(
            user=user, db_session=db, spotify=spotify
        )
        playlist = store_playlist(spotify_playlist, db_session=db)

    if full_scan:
        playlist: Playlist
        # DONE: the Spotify playlist has different likes than the DB
        # in the full_scan we should retrieve also the whole playlist to decide what
        # DONE: Don't do a full-scan if the snapshot is unchanged
        # TODO: Harden the sync and write tests
        if playlist.snapshot_id != spotify_playlist.get("snapshot_id"):
            logger.debug(f"Full scan to sync playlist {playlist.name}")

            logger.debug("Refreshing existing playlist tracks from Spotify")
            existing_spotify_tracks = await spotify.get_all_playlist_tracks(
                playlist_id=playlist.id, user=user, db_session=db
            )
            existing_tracks_ids = {
                item.get("track", {}).get("id") for item in existing_spotify_tracks
            }
            if (playlist_len := len(existing_spotify_tracks)) != (
                playlist_unique := len(existing_tracks_ids)
            ):
                logger.warning(
                    "Duplicates found:"
                    f" we have {playlist_len} vs {playlist_unique} unique."
                    " Recreating the playlist."
                )
                tracks_to_remove = existing_tracks_ids  # remove all

                new_spotify_likes = []  # get all the likes again - avoiding duplicates from the oldest
                distinct_tracks = set()
                for spot_like in existing_spotify_tracks[::-1]:
                    track_id = spot_like["track"]["id"]
                    if track_id not in distinct_tracks:
                        distinct_tracks.add(track_id)
                        new_spotify_likes.append(spot_like)
                new_spotify_likes = new_spotify_likes[::-1]
                existing_tracks_ids = set()  # we are going to delete them all

        else:
            existing_tracks_ids = {
                pt.track_id
                for pt in db.exec(
                    select(PlaylistTrack).where(
                        PlaylistTrack.playlist_id == playlist.id,
                    )
                )
            }
    else:
        # we assume that the playlist contains what we knew from the DB
        existing_tracks_ids = all_db_like_ids

    # here I should have:
    # - new_spotify_likes: the list of likes to add in order
    # - tracks_to_remove: the set of track IDs to remove
    # - existing_tracks_ids: the set of track in the Spotify playlist
    # - all_db_like_ids: the set of tracks in the DB

    if new_spotify_likes or tracks_to_remove or existing_tracks_ids != all_db_like_ids:
        tracks_to_add = {
            spotify_like.get("track", {}).get("id")
            for spotify_like in new_spotify_likes
        }
        logger.debug(
            f"Likes for {user}: {len(tracks_to_add)} to add, {len(tracks_to_remove)} to remove"
        )

        for spot_like in new_spotify_likes:
            track_data = spot_like.get("track", {})
            try:
                store_track(track_data, db)
            except Exception as e:
                logger.error(
                    f" Error processing track {track_data.get('name', 'Unknown')}: {e}"
                )

        new_change_snapshot = await spotify.change_playlist(
            user=user,
            db_session=db,
            playlist_id=playlist.id,
            tracks_to_add=[  # we need the order of the tracks to be preserved
                track_id
                for spotify_like in new_spotify_likes
                if (track_id := spotify_like.get("track", {}).get("id"))
                not in existing_tracks_ids
            ],
            tracks_to_remove=tracks_to_remove,
        )
        new_likes = [
            Like(
                user_id=user.id,
                track_id=like.get("track", {}).get("id"),
                date=parse_date(like["added_at"]),
            )
            for like in new_spotify_likes
        ]
        update_likes_db(
            user,
            likes_to_add=new_likes,
            tracks_to_remove=tracks_to_remove,
            db=db,
        )
        update_playlist_db(
            playlist.id,
            tracks_to_add=[
                PlaylistTrack(
                    playlist_id=playlist.id,
                    track_id=like.track_id,
                    date=like.date,
                )
                for like in new_likes
            ],
            tracks_to_remove=tracks_to_remove,
            snapshot_id=new_change_snapshot if full_scan else None,
            db=db,
        )
        db.commit()
        logger.info(
            f"{user} likes:"
            f" {len(tracks_to_add)} added, {len(tracks_to_remove)} deleted "
        )
    # update the user with the new last scan time
    now = datetime.datetime.now(datetime.timezone.utc)
    if full_scan:
        user.last_like_scan_full = now
    else:
        user.last_like_scan = now
    db.add(user)
    db.commit()


async def process_user(db: Session, user: User, spotify: Spotify):
    # Create a Spotify playlist

    # store the liked songs - create likes and sync with the playlist
    await process_likes(db, spotify, user)
    await process_plays(db, spotify, user)


async def process_plays(db: Session, spotify: Spotify, user):
    # this works a bit differently than likes
    # we yield and stop as soon as we find a play that has been already written
    added = 0
    async for play in spotify.yield_from(
        user=user,
        db_session=db,
        request=spotify.get_recently_played_page,
    ):
        track_data = play.get("track", {})
        track_id = track_data.get("id")
        played_at = parse_date(play.get("played_at"))
        existing_play = db.get(Play, (user.id, track_id, played_at))
        if existing_play:
            # play already exists, stop processing
            break
        context = play.get("context") or {}
        context_uri = context.get("uri")
        track = store_track(track_data, db)
        db.merge(
            Play(
                user_id=user.id,
                track_id=track.id,
                date=played_at,
                context_uri=context_uri,
            )
        )
        added += 1
    if added > 0:
        logger.info(f"Added {added} new plays from {user}")
        db.commit()
