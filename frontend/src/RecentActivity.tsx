import React from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { apiService, queryKeys, RecentItem, PlayResponse } from "./api";
import { IgnoreTrackButton } from "./IgnoreButtons";
import "./Recent.css";
import { formatLocalDateTime } from "./date";
import { Link } from "react-router-dom";
import { ensureWebPlaybackDevice } from "./spotifyWeb";
import { emit } from "./playbackBus";

export function useLocalStorageBoolean(key: string, initial: boolean) {
  const [value, setValue] = React.useState<boolean>(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return initial;
      return raw === "true";
    } catch {
      return initial;
    }
  });
  React.useEffect(() => {
    try {
      localStorage.setItem(key, value ? "true" : "false");
    } catch {}
  }, [key, value]);
  return [value, setValue] as const;
}

export function RecentPlayItem({
  item,
  showIgnore = true,
  userLinkBase = "/recent",
  source = "recent",
}: {
  item: RecentItem;
  showIgnore?: boolean;
  userLinkBase?: string;
  source?: "recent" | "likes";
}) {
  const time = formatLocalDateTime(item.date);
  const albumPic = item.track.album?.picture ?? null;
  const userIdent = item.user.username || item.user.id;
  const userDisplay = item.user.name ?? item.user.username ?? "Unknown";

  const { data: me } = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30_000,
  });
  const isPremium = Boolean(me?.user?.subscribed);

  const publishPlayed = (resp: PlayResponse) => {
    const t = resp.track;
    if (!t) return;
    emit("played", {
      id: t.id,
      name: t.name,
      artists: t.artists,
      albumImage: t.album_image,
      durationMs: t.duration_ms,
    });
  };

  const onPlayClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const doPlay = async () =>
      apiService.playTrack({
        trackId: item.track.id,
        context: {
          source,
          user: { id: item.user.id, username: item.user.username },
          context_uri: item.context_uri ?? null,
        },
      });

    try {
      const resp = await doPlay();
      publishPlayed(resp);
    } catch (err) {
      const msg = (err as Error)?.message || "Failed to start playback";
      const noDevice = /no active device/i.test(msg);
      if (!noDevice || !isPremium) {
        alert(msg);
        return;
      }
      try {
        // Create browser device and transfer playback
        const deviceId = await ensureWebPlaybackDevice();
        await apiService.transferPlayback(deviceId, true);
        // Wait briefly to ensure device is ready
        await new Promise((resolve) => setTimeout(resolve, 500));
        const resp = await doPlay();
        publishPlayed(resp);
        // No error alert shown if retry succeeds
      } catch (e2) {
        alert((e2 as Error)?.message || "Cannot start web playback");
      }
    }
  };

  return (
    <li className="recent-item" data-testid="recent-item">
      <div className="recent-left">
        <div className="recent-avatar-wrap">
          {albumPic ? (
            <img
              className="recent-avatar"
              src={albumPic}
              alt={""}
              title={item.track.album?.name ?? ""}
            />
          ) : (
            <div className="recent-avatar placeholder">🎵</div>
          )}
          <button
            className="play-overlay"
            aria-label="Play"
            onClick={onPlayClick}
          >
            ▶
          </button>
        </div>
      </div>
      <div className="recent-main">
        <div className="recent-track">
          <span className="recent-title">
            {item.track.title ?? "Unknown track"}
          </span>
          {item.track.artists.length > 0 && (
            <span className="recent-artists">
              {" "}
              • {item.track.artists.join(", ")}
            </span>
          )}
        </div>
        <div className="recent-meta">
          <Link
            to={`${userLinkBase}?user=${encodeURIComponent(userIdent)}`}
            className="recent-user link"
          >
            {userDisplay}
          </Link>
          <span className="recent-dot">•</span>
          <span className="recent-time">{time}</span>
        </div>
      </div>
      <div className="recent-actions">
        {showIgnore && (
          <IgnoreTrackButton
            trackId={item.track.id}
            className="recent-ignore-btn"
          />
        )}
      </div>
    </li>
  );
}

export function RecentActivityWidget({
  includeMe,
  filterUser,
  className,
}: {
  includeMe: boolean;
  filterUser?: string | null;
  className?: string;
}) {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    status,
    error,
  } = useInfiniteQuery({
    queryKey: [...queryKeys.recent(includeMe, filterUser ?? null)],
    queryFn: ({ pageParam }) =>
      apiService.getRecent({
        limit: 20,
        before: pageParam ?? null,
        include_me: includeMe,
        user: filterUser ?? null,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_before,
    retry: 0, // show errors immediately
  });

  const loadMoreRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    if (!hasNextPage) return;
    const el = loadMoreRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting && hasNextPage && !isFetchingNextPage) {
            fetchNextPage();
          }
        });
      },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage, data]);

  const items = data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <div className={`recent-widget ${className ?? ""}`}>
      <ul className="recent-list">
        {status === "pending" && <div className="recent-loading">Loading…</div>}
        {status === "error" && (
          <div className="recent-error">
            Failed to load recent activity:{" "}
            {String((error as Error)?.message || "Server error")}
          </div>
        )}
        {status === "success" &&
          items.map((it) => (
            <RecentPlayItem
              key={`${it.user.id}-${it.track.id}-${it.date}`}
              item={it}
              showIgnore={false}
              userLinkBase="/recent"
              source="recent"
            />
          ))}
      </ul>
      {hasNextPage && (
        <div ref={loadMoreRef} className="recent-load-more" aria-hidden>
          {isFetchingNextPage ? "Loading more…" : ""}
        </div>
      )}
      {items.length === 0 && status === "success" && (
        <div className="recent-empty">No recent activity yet.</div>
      )}
    </div>
  );
}

export function SettingsDropdown({
  includeMe,
  setIncludeMe,
}: {
  includeMe: boolean;
  setIncludeMe: (v: boolean) => void;
}) {
  const [open, setOpen] = React.useState(false);
  React.useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Element;
      if (!t.closest(".recent-settings")) setOpen(false);
    };
    if (open) {
      document.addEventListener("click", onDoc);
      return () => document.removeEventListener("click", onDoc);
    }
  }, [open]);

  return (
    <div className="recent-settings">
      <button
        className="recent-gear"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Recent settings"
      >
        ⚙️
      </button>
      {open && (
        <div className="recent-menu" role="menu">
          <label className="recent-menu-item">
            <input
              type="checkbox"
              checked={includeMe}
              onChange={(e) => setIncludeMe(e.target.checked)}
            />
            <span>Show my activity</span>
          </label>
        </div>
      )}
    </div>
  );
}
