import React from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { apiService, queryKeys, RecentItem } from "./api";
import "./Recent.css";

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

export function RecentPlayItem({ item }: { item: RecentItem }) {
  const playedAt = new Date(item.played_at);
  const time = isNaN(playedAt.getTime())
    ? ""
    : playedAt.toLocaleString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        month: "short",
        day: "2-digit",
      });
  const albumPic = item.track.album?.picture ?? null;
  return (
    <li className="recent-item" data-testid="recent-item">
      <div className="recent-left">
        {albumPic ? (
          <img
            className="recent-avatar"
            src={albumPic}
            alt={item.track.album?.name ?? ""}
          />
        ) : (
          <div className="recent-avatar placeholder">🎵</div>
        )}
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
          <span className="recent-user">{item.user.name ?? "Unknown"}</span>
          <span className="recent-dot">•</span>
          <span className="recent-time">{time}</span>
        </div>
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
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, status } =
    useInfiniteQuery({
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
        {items.map((it) => (
          <RecentPlayItem
            key={`${it.user.id}-${it.track.id}-${it.played_at}`}
            item={it}
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
