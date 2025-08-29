import React from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { apiService, queryKeys, RecentItem, PlayResponse } from "./api";
import "./Recent.css";
import { formatLocalDateTime } from "./date";
import { Link } from "react-router-dom";
import { ensureWebPlaybackDevice } from "./spotifyWeb";
import { emit } from "./playbackBus";

export function RecentPlayItem({
  item,
  userLinkBase = "/recent",
  source = "recent",
}: {
  item: RecentItem;
  userLinkBase?: string;
  source?: "recent" | "likes" | "profile";
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

  const [liked, setLiked] = React.useState<boolean>(Boolean(item.liked));
  React.useEffect(() => {
    setLiked(Boolean(item.liked));
  }, [item.liked, item.track.id]);

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
      if (!noDevice) {
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

  const onLikeClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const prev = liked;
    const next = !prev;
    setLiked(next);
    try {
      await apiService.setLike(item.track.id, next);
    } catch (err) {
      setLiked(prev);
      const msg = (err as Error)?.message || "Failed to update like";
      // Keep it minimal to avoid noisy alerts
      console.error(msg);
    }
  };

  const Container: React.ElementType = source === "profile" ? "div" : "li";

  return (
    <Container className="recent-item" data-testid="recent-item">
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
          {isPremium && (
            <button
              className="play-overlay"
              aria-label="Play"
              onClick={onPlayClick}
            >
              ▶
            </button>
          )}
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
      <button
        className={`recent-like-btn${liked ? " liked" : ""}`}
        aria-label={liked ? "Unlike" : "Like"}
        title={liked ? "Unlike" : "Like"}
        aria-pressed={liked}
        onClick={onLikeClick}
      >
        <svg
          width="28"
          height="28"
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
    </Container>
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
