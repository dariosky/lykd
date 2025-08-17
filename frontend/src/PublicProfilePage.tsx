import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "./Layout";
import {
  apiService,
  PublicProfileResponse,
  NotFoundError,
  FriendshipStatusResponse,
  queryKeys,
  UserResponse,
} from "./api";
import "./PublicProfile.css";

function formatDurationDHMS(totalSec: number): string {
  const days = Math.floor(totalSec / 86400);
  const hours = Math.floor((totalSec % 86400) / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const parts: string[] = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0 || days > 0) parts.push(`${hours}h`);
  parts.push(`${minutes}m`);
  return parts.join(" ");
}

function formatDate(iso?: string | null): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

// Add a simple number formatter for thousand separators
const nf = new Intl.NumberFormat(undefined);
function formatNumber(n: number): string {
  return nf.format(n);
}

export default function PublicProfilePage() {
  const { username = "" } = useParams();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery<
    PublicProfileResponse,
    Error
  >({
    queryKey: ["publicProfile", username],
    queryFn: () => apiService.getPublicProfile(username),
    enabled: !!username,
    staleTime: 30_000,
    // Do not retry if it's a 404 (NotFoundError)
    retry: (_failureCount, err) => !(err instanceof NotFoundError),
  });

  // Current viewer from query (shared with Layout, deduped)
  const { data: viewerResp } = useQuery<UserResponse, Error>({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30_000,
    retry: 1,
  });
  const viewer = viewerResp?.user ?? null;

  // Friendship status query
  const {
    data: frStatus,
    refetch: refetchFrStatus,
    isFetching: loadingStatus,
  } = useQuery<FriendshipStatusResponse, Error>({
    queryKey: queryKeys.friendshipStatus(username),
    queryFn: () => apiService.getFriendshipStatus(username),
    enabled: !!username && !!viewer, // only when logged in
    staleTime: 10_000,
  });

  // Send request mutation
  const sendRequestMutation = useMutation({
    mutationFn: () => apiService.sendFriendRequest(username),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.friendshipStatus(username),
      });
      refetchFrStatus();
      // Also refresh pending list for the other screen if needed
      queryClient.invalidateQueries({ queryKey: queryKeys.pendingRequests });
    },
  });

  const isNotFound = isError && error instanceof NotFoundError;

  // Decide button label/state
  const status = frStatus?.status;
  const showFriendAction =
    !!viewer && data && viewer.username !== data.user.username;
  const friendBtn = (() => {
    if (!showFriendAction) return null;
    if (loadingStatus) {
      return (
        <button className="btn-primary" disabled>
          Checking…
        </button>
      );
    }
    switch (status) {
      case "friends":
        return (
          <button className="btn-primary" disabled>
            ✓ Friends
          </button>
        );
      case "pending_outgoing":
        return (
          <button className="btn-primary" disabled>
            Request sent
          </button>
        );
      case "pending_incoming":
        return (
          <button
            className="btn-primary"
            disabled
            title="Respond from notifications"
          >
            Respond pending
          </button>
        );
      case "self":
        return null;
      default:
        return (
          <button
            className="btn-primary"
            onClick={() => sendRequestMutation.mutate()}
            disabled={sendRequestMutation.isPending}
          >
            {sendRequestMutation.isPending ? "Sending…" : "Add friend"}
          </button>
        );
    }
  })();

  return (
    <Layout>
      <div className="public-profile-page">
        <div className="public-profile-header">
          <Link to="/" className="back-link">
            ← Back to Home
          </Link>
          {isLoading && <div className="loading-small">Loading profile…</div>}
        </div>

        {isNotFound && (
          <div className="public-profile-content">
            <div className="card empty-state">
              <div className="empty-icon" aria-hidden>
                🕵️‍♂️
              </div>
              <div className="empty-title">Profile not found</div>
            </div>
          </div>
        )}

        {isError && !isNotFound && (
          <div className="public-profile-content">
            <div className="card error-box">
              <div className="error-title">Failed to load profile</div>
              <div className="error-message">{error?.message}</div>
              <div className="error-actions">
                <button
                  className="btn-primary"
                  onClick={() => refetch()}
                  disabled={isFetching}
                >
                  {isFetching ? "Retrying…" : "Retry"}
                </button>
              </div>
            </div>
          </div>
        )}

        {data && (
          <div className="public-profile-content">
            <div
              className="profile-hero"
              style={{
                justifyContent: "space-between",
                gap: "1rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                }}
              >
                {data.user.picture && (
                  <img
                    src={data.user.picture}
                    alt={data.user.name}
                    className="profile-avatar"
                  />
                )}
                <div className="profile-meta">
                  <h1>{data.user.name}</h1>
                  <div className="username">@{data.user.username}</div>
                </div>
              </div>
              {friendBtn}
            </div>

            <section className="card">
              <h2>🎧 Playback Stats</h2>
              <div className="stat-row">
                <div className="stat-item red">
                  <div className="stat-left">
                    <span className="stat-icon" aria-hidden>
                      ❤️
                    </span>
                    <span className="stat-label">Liked songs</span>
                  </div>
                  <div className="stat-value">
                    {formatNumber(data.stats.total_likes)}
                  </div>
                </div>

                <div className="stat-item green">
                  <div className="stat-left">
                    <span className="stat-icon" aria-hidden>
                      ▶️
                    </span>
                    <span className="stat-label">Total plays</span>
                  </div>
                  <div className="stat-value">
                    {formatNumber(data.stats.total_plays)}
                  </div>
                </div>
              </div>

              <div className="stat-row">
                <div className="stat-item">
                  <div className="stat-left">
                    <span className="stat-icon" aria-hidden>
                      🕒
                    </span>
                    <span className="stat-label">
                      Listening time (all time)
                    </span>
                  </div>
                  <div className="stat-value">
                    {formatDurationDHMS(data.stats.total_listening_time_sec)}
                  </div>
                </div>
                <div className="stat-item">
                  <div className="stat-left">
                    <span className="stat-icon" aria-hidden>
                      ⏳
                    </span>
                    <span className="stat-label">Listening time (30 days)</span>
                  </div>
                  <div className="stat-value">
                    {formatDurationDHMS(
                      data.stats.listening_time_last_30_days_sec,
                    )}
                  </div>
                </div>
              </div>

              <div className="stat-row">
                <div className="stat-item">
                  <div className="stat-left">
                    <span className="stat-icon" aria-hidden>
                      📅
                    </span>
                    <span className="stat-label">Tracking since</span>
                  </div>
                  <div className="stat-value">
                    {formatDate(data.stats.tracking_since)}
                  </div>
                </div>
              </div>
            </section>

            <section className="card">
              <h2>🔥 Top Highlights</h2>
              <div className="highlights-grid">
                <div className="highlight">
                  <div className="highlight-title">📆 Top songs (30 days)</div>
                  <ul className="list">
                    {data.highlights.top_songs_30_days.map((t) => (
                      <li key={`30-${t.track_id}`} className="list-item">
                        <div className="list-main">
                          <div className="list-title">🎵 {t.title}</div>
                          <div className="list-sub">
                            {t.artists.join(", ")}
                            {t.album?.name ? ` • ${t.album.name}` : ""}
                          </div>
                        </div>
                        <div className="list-meta">
                          ▶️ {formatNumber(t.play_count)} plays
                        </div>
                      </li>
                    ))}
                    {data.highlights.top_songs_30_days.length === 0 && (
                      <li className="list-empty">No data</li>
                    )}
                  </ul>
                </div>
                <div className="highlight">
                  <div className="highlight-title">🏆 Top songs (all time)</div>
                  <ul className="list">
                    {data.highlights.top_songs_all_time.map((t) => (
                      <li key={`all-${t.track_id}`} className="list-item">
                        <div className="list-main">
                          <div className="list-title">🎵 {t.title}</div>
                          <div className="list-sub">
                            {t.artists.join(", ")}
                            {t.album?.name ? ` • ${t.album.name}` : ""}
                          </div>
                        </div>
                        <div className="list-meta">
                          ▶️ {formatNumber(t.play_count)} plays
                        </div>
                      </li>
                    ))}
                    {data.highlights.top_songs_all_time.length === 0 && (
                      <li className="list-empty">No data</li>
                    )}
                  </ul>
                </div>
                <div className="highlight">
                  <div className="highlight-title">🌟 Top artists</div>
                  <ul className="list">
                    {data.highlights.top_artists.map((a) => (
                      <li key={a.artist_id} className="list-item">
                        <div className="list-main">
                          <div className="list-title">🎤 {a.name}</div>
                        </div>
                        <div className="list-meta">
                          ▶️ {formatNumber(a.play_count)} plays
                        </div>
                      </li>
                    ))}
                    {data.highlights.top_artists.length === 0 && (
                      <li className="list-empty">No data</li>
                    )}
                  </ul>
                </div>
                <div className="highlight">
                  <div className="highlight-title">🕰️ Most played decade</div>
                  <div className="decade">
                    {data.highlights.most_played_decade || "No data"}
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </Layout>
  );
}
