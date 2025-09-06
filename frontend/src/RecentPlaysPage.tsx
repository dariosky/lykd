import React from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { apiService, queryKeys, RecentItem } from "./api";
import { RecentPlayItem } from "./RecentActivity";
import { useSearchParams } from "react-router-dom";
import "./Recent.css";

export default function RecentPlaysPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const userParam = searchParams.get("user");
  const excludeParam = searchParams.get("exclude_me") === "true";
  const qParam = searchParams.get("q") ?? "";

  // Local debounced search text state
  const [searchText, setSearchText] = React.useState(qParam);
  React.useEffect(() => {
    // Keep local state in sync if URL changes externally
    if (qParam !== searchText) setSearchText(qParam);
  }, [qParam, searchText]);

  const filterUser = userParam;
  const excludeMe = filterUser ? false : excludeParam;
  const includeMe = !excludeMe;

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, status } =
    useInfiniteQuery({
      queryKey: queryKeys.recent(includeMe, filterUser, qParam || null),
      queryFn: ({ pageParam }) =>
        apiService.getRecent({
          limit: 30,
          before: pageParam ?? null,
          include_me: includeMe,
          user: filterUser,
          q: qParam || null,
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
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting && hasNextPage && !isFetchingNextPage)
            fetchNextPage();
        });
      },
      { rootMargin: "300px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage, data]);

  const items = data?.pages.flatMap((p) => p.items) ?? [];

  // Debounced URL update for search
  React.useEffect(() => {
    const handle = window.setTimeout(() => {
      if (searchText !== qParam) {
        const next = new URLSearchParams(searchParams);
        if (searchText) next.set("q", searchText);
        else next.delete("q");
        setSearchParams(next, { replace: true });
      }
    }, 500);
    return () => window.clearTimeout(handle);
  }, [searchText, qParam, searchParams, setSearchParams]);

  const onItemUserClick = (it: RecentItem) => {
    const ident = it.user.username || it.user.id;
    const next = new URLSearchParams(searchParams);
    next.set("user", ident);
    // With a user filter applied, exclude_me is irrelevant: drop it
    next.delete("exclude_me");
    setSearchParams(next, { replace: true });
  };

  const clearFilter = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("user");
    setSearchParams(next, { replace: true });
  };

  const toggleExclude = (checked: boolean) => {
    const next = new URLSearchParams(searchParams);
    if (checked) next.set("exclude_me", "true");
    else next.delete("exclude_me");
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="recent-page">
      <div className="page-header">
        <div className="title-row">
          <h1 className="page-title">Recent Activity</h1>
          <div className="actions">
            <label className="recent-menu-item">
              <input
                type="checkbox"
                checked={excludeMe}
                onChange={(e) => toggleExclude(e.target.checked)}
                disabled={!!filterUser}
              />
              <span>Exclude my activity</span>
            </label>
          </div>
        </div>
        <div className="filters">
          {filterUser ? (
            <div className="filter-chip">
              Filtering by: {filterUser}
              <button className="chip-clear" onClick={clearFilter}>
                Clear
              </button>
            </div>
          ) : (
            <div className="filter-chip muted">All users</div>
          )}
        </div>
        <div className="search">
          <input
            className="search-input"
            type="search"
            placeholder="Search title, album, artist, user or date"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
        </div>
      </div>

      <div className="page-content">
        <ul className="recent-list large">
          {status === "pending" && (
            <div className="recent-loading">Loading…</div>
          )}
          {status === "error" && (
            <div className="recent-error">Failed to load recent activity.</div>
          )}
          {status === "success" &&
            items.map((it) => {
              const pillName = it.user.name ?? it.user.username ?? "Unknown";
              const avatar = it.user.picture ? (
                <img
                  className="pill-avatar"
                  src={it.user.picture}
                  alt={pillName}
                />
              ) : (
                <div className="initials-avatar" aria-hidden>
                  {(it.user.username || it.user.name || "?")
                    ?.slice(0, 1)
                    .toUpperCase()}
                </div>
              );
              return (
                <div
                  key={`${it.user.id}-${it.track.id}-${it.date}`}
                  className="recent-row"
                >
                  <button
                    className="user-pill"
                    onClick={() => onItemUserClick(it)}
                    data-name={pillName}
                  >
                    {avatar}
                    <span>{pillName}</span>
                  </button>
                  <RecentPlayItem item={it} userLinkBase="/recent" />
                </div>
              );
            })}
        </ul>
        {hasNextPage && (
          <div ref={loadMoreRef} className="recent-load-more" aria-hidden>
            {isFetchingNextPage ? "Loading more…" : ""}
          </div>
        )}
        {items.length === 0 && status === "success" && (
          <div className="recent-empty large">No recent activity.</div>
        )}
      </div>
    </div>
  );
}
