import React from "react";
import { apiService } from "./api";
import "./MiniPlayer.css";
import { on } from "./playbackBus";
import { ensureWebPlaybackDevice } from "./spotifyWeb";
import { useAuth } from "./AuthContext";

interface PlaybackItem {
  id: string;
  name: string;
  artists: string[];
  albumImage: string | null;
  durationMs: number;
}

const FETCH_STATE_EVERY_MS = 10000;

export function MiniPlayer() {
  const [state, setState] = React.useState<{
    isPlaying: boolean;
    progressMs: number;
    deviceName?: string | null;
    item: PlaybackItem | null;
  }>({ isPlaying: false, progressMs: 0, deviceName: null, item: null });

  const [lastEndedTrackId, setLastEndedTrackId] = React.useState<string | null>(
    null,
  );
  const [error, setError] = React.useState<string | null>(null);
  const [flash, setFlash] = React.useState<null | "play" | "pause" | "next">(
    null,
  );
  const [liked, setLiked] = React.useState<boolean>(false);
  const flashOnce = (kind: "play" | "pause" | "next") => {
    setFlash(kind);
    window.setTimeout(() => setFlash(null), 200);
  };

  const fetchState = React.useCallback(async () => {
    try {
      const resp = await apiService.getPlayback();
      const s = resp.state as any | null;
      if (!s) {
        setState((prev) => ({
          ...prev,
          item: null,
          isPlaying: false,
          progressMs: 0,
          deviceName: null,
        }));
        return;
      }
      const item = s.item;
      const artists: string[] = Array.isArray(item?.artists)
        ? item.artists.map((a: any) => a.name)
        : [];
      const albumImage = item?.album?.images?.[0]?.url ?? null;
      const durationMs = item?.duration_ms ?? 0;
      const playbackItem: PlaybackItem | null = item
        ? {
            id: item.id,
            name: item.name,
            artists,
            albumImage,
            durationMs,
          }
        : null;
      setState({
        isPlaying: Boolean(s.is_playing),
        progressMs: s.progress_ms ?? 0,
        deviceName: s.device?.name ?? null,
        item: playbackItem,
      });

      // Auto-advance via backend when track ends (stubbed now)
      if (
        playbackItem &&
        !s.is_playing &&
        typeof s.progress_ms === "number" &&
        durationMs > 0 &&
        s.progress_ms >= durationMs - 1000 &&
        lastEndedTrackId !== playbackItem.id
      ) {
        setLastEndedTrackId(playbackItem.id);
        try {
          const next = await apiService.getNext();
          if (next?.next?.track_id) {
            await apiService.playTrack({ trackId: next.next.track_id });
            // refresh quickly after starting next
            setTimeout(fetchState, 1000);
          }
        } catch (e) {
          // ignore errors for now
        }
      }
    } catch (e: any) {
      setError(e?.message || "Playback error");
    }
  }, [lastEndedTrackId]);

  const { isLoggedIn } = useAuth();

  // Helper to ensure fetchState only runs if logged in (using AuthContext)
  const fetchStateIfLoggedIn = React.useCallback(async () => {
    if (isLoggedIn) {
      await fetchState();
    } else {
      setState((prev) => ({
        ...prev,
        item: null,
        isPlaying: false,
        progressMs: 0,
        deviceName: null,
      }));
    }
  }, [fetchState, isLoggedIn]);

  // Subscribe to immediate play events to update UI without waiting for polling
  React.useEffect(() => {
    const off = on("played", (p) => {
      setState((prev) => ({
        ...prev,
        isPlaying: true,
        progressMs: 0,
        item: {
          id: p.id,
          name: p.name,
          artists: p.artists,
          albumImage: p.albumImage,
          durationMs: p.durationMs,
        },
      }));
      flashOnce("play");
    });
    return () => off();
  }, []);

  React.useEffect(() => {
    let intervalId: number | undefined;
    let cancelled = false;
    (async () => {
      await fetchStateIfLoggedIn();
      if (!cancelled) {
        intervalId = window.setInterval(
          fetchStateIfLoggedIn,
          FETCH_STATE_EVERY_MS,
        );
      }
    })();
    return () => {
      cancelled = true;
      if (intervalId) window.clearInterval(intervalId);
    };
  }, [fetchStateIfLoggedIn]);

  // Fetch like status for current track
  React.useEffect(() => {
    const fetchLike = async () => {
      if (state.item?.id) {
        try {
          const resp = await apiService.getTrackLike(state.item.id);
          setLiked(Boolean(resp?.liked));
        } catch {
          setLiked(false);
        }
      }
    };
    fetchLike();
  }, [state.item?.id]);

  const onTogglePlay = async () => {
    try {
      if (state.isPlaying) {
        await apiService.pausePlayback();
        flashOnce("pause");
      } else {
        try {
          await apiService.resumePlayback();
        } catch (e: any) {
          const msg = e?.message || "";
          if (/no active device/i.test(msg)) {
            try {
              const deviceId = await ensureWebPlaybackDevice();
              await apiService.transferPlayback(deviceId, true);
              await apiService.resumePlayback();
            } catch (ie) {
              throw ie;
            }
          } else {
            throw e;
          }
        }
        flashOnce("play");
      }
      setTimeout(fetchStateIfLoggedIn, 400);
    } catch (e: any) {
      setError(e?.message || "Failed to toggle");
    }
  };

  const onNext = async () => {
    try {
      try {
        await apiService.nextPlayback();
      } catch (e: any) {
        const msg = e?.message || "";
        if (/no active device/i.test(msg)) {
          const deviceId = await ensureWebPlaybackDevice();
          await apiService.transferPlayback(deviceId, true);
          await apiService.nextPlayback();
        } else {
          throw e;
        }
      }
      flashOnce("next");
      setTimeout(fetchStateIfLoggedIn, 800);
    } catch (e: any) {
      setError(e?.message || "Failed to skip");
    }
  };

  const onLikeClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!state.item?.id) return;
    const prev = liked;
    const next = !prev;
    setLiked(next);
    try {
      await apiService.setLike(state.item.id, next);
    } catch {
      setLiked(prev);
    }
  };

  const item = state.item;
  if (!item) return null; // hide player when no active playback

  return (
    <div
      className={`mini-player ${flash ? `mp-flash mp-${flash}` : ""}`}
      role="region"
      aria-label="Mini player"
      data-flash={flash || undefined}
    >
      <>
        <div className="mp-left">
          {item.albumImage ? (
            <img src={item.albumImage} alt="Album" className="mp-cover" />
          ) : (
            <div className="mp-cover placeholder">🎵</div>
          )}
        </div>
        <div className="mp-main">
          <div className="mp-title" title={item.name}>
            {item.name}
          </div>
          <div className="mp-sub">
            <span className="mp-artists">{item.artists.join(", ")}</span>
            {state.deviceName ? <span className="mp-dot">•</span> : null}
            {state.deviceName ? (
              <span className="mp-device" title="Active device">
                {state.deviceName}
              </span>
            ) : null}
          </div>
          <div className="mp-progress">
            <div
              className="mp-bar"
              style={{
                width:
                  item.durationMs > 0
                    ? `${Math.min(
                        100,
                        Math.round((state.progressMs / item.durationMs) * 100),
                      )}%`
                    : "0%",
              }}
            />
          </div>
        </div>
        <div className="mp-actions">
          <button
            className={`mp-btn ${flash === "play" || flash === "pause" ? "mp-btn-flash" : ""}`}
            onClick={onTogglePlay}
            aria-label={state.isPlaying ? "Pause" : "Play"}
            title={state.isPlaying ? "Pause" : "Play"}
          >
            {state.isPlaying ? "❚❚" : "▶"}
          </button>
          <button
            className={`mp-btn ${flash === "next" ? "mp-btn-flash" : ""}`}
            onClick={onNext}
            aria-label="Next"
            title="Next"
          >
            »
          </button>
          <button
            className={`mp-btn mp-like-btn${liked ? " liked" : ""}`}
            aria-label={liked ? "Unlike" : "Like"}
            title={liked ? "Unlike" : "Like"}
            aria-pressed={liked}
            onClick={onLikeClick}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              role="img"
              aria-hidden="true"
            >
              <path
                d="M12 21s-6.716-4.364-9.293-8.05C.813 10.27 1.135 7.3 3.05 5.636 4.964 3.97 7.77 4.22 9.5 6c.56.57 1.03 1.23 1.5 1.94.47-.71.94-1.37 1.5-1.94 1.73-1.78 4.536-2.03 6.45-.364 1.915 1.664 2.237 4.634.343 7.314C18.716 16.636 12 21 12 21z"
                fill={liked ? "#ff4d6d" : "transparent"}
                stroke="#ff4d6d"
                strokeWidth="2"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </>
      {error && (
        <div className="mp-error" title={error} aria-live="polite">
          !
        </div>
      )}
    </div>
  );
}

export default MiniPlayer;
