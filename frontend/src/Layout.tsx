import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useLocation } from "react-router-dom";
import {
  apiService,
  queryKeys,
  PendingRequestsResponse,
  ReportsResponse,
} from "./api";
import { useAuth } from "./AuthContext";
import "./Layout.css";
import MiniPlayer from "./MiniPlayer";
import UserDropdown from "./UserDropdown";
import ErrorBoundary from "./ErrorBoundary";

interface LayoutProps {
  children: React.ReactNode;
}

function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState(window.innerWidth <= 600);
  React.useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 600);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);
  return isMobile;
}

function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);
  const [isNotifOpen, setIsNotifOpen] = React.useState(false);
  const [isAdminOpen, setIsAdminOpen] = React.useState(false);

  const { user: currentUser, isLoggedIn } = useAuth();
  const isMobile = useIsMobile();

  // Helper to ensure getPendingRequests only runs if logged in (using AuthContext)
  const getPendingRequestsIfLoggedIn = React.useCallback(async () => {
    if (isLoggedIn) {
      return await apiService.getPendingRequests();
    } else {
      return { pending: [] };
    }
  }, [isLoggedIn]);

  // Pending friendship requests (fetch once user query has resolved)
  const { data: pendingResp, refetch: refetchPending } = useQuery<
    PendingRequestsResponse,
    Error
  >({
    queryKey: queryKeys.pendingRequests,
    queryFn: getPendingRequestsIfLoggedIn,
    enabled: isLoggedIn, // run after user query resolves
    staleTime: 2 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
  const pending = pendingResp?.pending ?? [];

  // Admin reports
  const { data: reports } = useQuery<ReportsResponse, Error>({
    queryKey: queryKeys.reports,
    queryFn: apiService.getReports,
    enabled: !!currentUser?.is_admin,
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  });
  const totalReports =
    (reports?.tracks.length ?? 0) + (reports?.artists.length ?? 0);

  // Accept / Decline mutations
  const acceptMutation = useMutation({
    mutationFn: (username: string) => apiService.acceptFriendRequest(username),
    onSuccess: (_data, username) => {
      // refresh lists and status for that user
      refetchPending();
      queryClient.invalidateQueries({
        queryKey: queryKeys.friendshipStatus(username),
      });
    },
  });
  const declineMutation = useMutation({
    mutationFn: (username: string) => apiService.declineFriendRequest(username),
    onSuccess: (_data, username) => {
      refetchPending();
      queryClient.invalidateQueries({
        queryKey: queryKeys.friendshipStatus(username),
      });
    },
  });

  // Admin approve/reject mutations
  const approveTrack = useMutation({
    mutationFn: (trackId: string) => apiService.approveTrackReport(trackId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.reports }),
  });
  const rejectTrack = useMutation({
    mutationFn: (trackId: string) => apiService.rejectTrackReport(trackId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.reports }),
  });
  const approveArtist = useMutation({
    mutationFn: (artistId: string) => apiService.approveArtistReport(artistId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.reports }),
  });
  const rejectArtist = useMutation({
    mutationFn: (artistId: string) => apiService.rejectArtistReport(artistId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.reports }),
  });

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: apiService.logout,
    onSuccess: () => {
      // Reload the page to reset all state
      window.location.href = "/";
    },
    onError: (error: Error) => {
      console.error("Error logging out:", error);
      // Still reload the page even if logout fails
      window.location.reload();
    },
  });

  const handleLogout = () => {
    setIsDropdownOpen(false);
    logoutMutation.mutate();
  };

  const handleSettingsClick = () => {
    setIsDropdownOpen(false);
    navigate("/settings");
  };

  const handleHomeClick = () => {
    setIsDropdownOpen(false);
    navigate("/");
  };

  const handlePublicProfileClick = () => {
    setIsDropdownOpen(false);
    if (currentUser?.username) {
      navigate(`/user/${currentUser.username}`);
    }
  };

  const handleIgnoredClick = () => {
    setIsDropdownOpen(false);
    navigate("/ignored");
  };

  // Close dropdowns when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest(".user-dropdown-container")) {
        setIsDropdownOpen(false);
      }
      if (!target.closest(".notif-dropdown-container")) {
        setIsNotifOpen(false);
      }
      if (!target.closest(".admin-dropdown-container")) {
        setIsAdminOpen(false);
      }
    };

    if (isDropdownOpen || isNotifOpen || isAdminOpen) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [isDropdownOpen, isNotifOpen, isAdminOpen]);

  // Check for success parameter on mount and refetch user
  React.useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("spotify") === "connected") {
      // console.log("Spotify connected successfully!");
      // Refetch user data to get the updated information
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  return (
    <div className="layout">
      <div className="user-header">
        <div className="user-header-content">
          <div className="header-logo" onClick={handleHomeClick}>
            <img src="/logo_dark.svg" alt="LYKD" className="logo" />
            LYKD
          </div>

          {/* Center tabs (only meaningful when logged in) */}
          <div className="header-center">
            {currentUser ? (
              <nav className="main-tabs" aria-label="Primary">
                {(() => {
                  const isLikes = location.pathname.startsWith("/likes");
                  const isRecent =
                    location.pathname === "/" ||
                    location.pathname.startsWith("/recent");
                  return (
                    <>
                      <button
                        className={`main-tab recent ${isRecent ? "active" : ""}`}
                        onClick={() => navigate("/")}
                      >
                        Recent
                      </button>
                      <button
                        className={`main-tab likes ${isLikes ? "active" : ""}`}
                        onClick={() => navigate("/likes")}
                      >
                        Likes
                      </button>
                    </>
                  );
                })()}
              </nav>
            ) : null}
          </div>

          <div className="header-actions">
            {/* Notifications bell */}
            <div className="notif-dropdown-container">
              {pending.length > 0 && (
                <button
                  className="notif-button"
                  onClick={() => setIsNotifOpen(!isNotifOpen)}
                  aria-label="Friend requests"
                >
                  🔔
                  <span
                    className="notif-badge"
                    aria-label={`${pending.length} pending`}
                  >
                    {pending.length}
                  </span>
                </button>
              )}
              {isNotifOpen && pending.length > 0 && (
                <div className="notif-dropdown">
                  <div className="notif-title">Friend requests</div>
                  <ul className="notif-list">
                    {pending.map((p) => (
                      <li key={p.user.id} className="notif-item">
                        <div className="notif-user">
                          {p.user.picture ? (
                            <img
                              className="notif-avatar"
                              src={p.user.picture}
                              alt={p.user.name}
                            />
                          ) : (
                            <div className="notif-avatar placeholder">👤</div>
                          )}
                          <div className="notif-user-meta">
                            <div className="notif-name">{p.user.name}</div>
                            {p.user.username && (
                              <div className="notif-username">
                                @{p.user.username}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="notif-actions">
                          <button
                            className="btn-accept"
                            onClick={() =>
                              acceptMutation.mutate(
                                p.user.username ?? p.user.id,
                              )
                            }
                            disabled={acceptMutation.isPending}
                          >
                            Accept
                          </button>
                          <button
                            className="btn-decline"
                            onClick={() =>
                              declineMutation.mutate(
                                p.user.username ?? p.user.id,
                              )
                            }
                            disabled={declineMutation.isPending}
                          >
                            Decline
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Admin reports */}
            {currentUser?.is_admin && totalReports > 0 && (
              <div className="admin-dropdown-container">
                <button
                  className="notif-button"
                  onClick={() => setIsAdminOpen(!isAdminOpen)}
                  aria-label="Pending reports"
                  title="Pending global ignore reports"
                >
                  🛡️
                  {totalReports > 0 && (
                    <span
                      className="notif-badge"
                      aria-label={`${totalReports} pending`}
                    >
                      {totalReports}
                    </span>
                  )}
                </button>
                {isAdminOpen && (
                  <div className="notif-dropdown">
                    <div className="notif-title">Pending reports</div>
                    <div className="notif-subtitle">Artists</div>
                    {reports?.artists.length ? (
                      <ul className="notif-list">
                        {reports.artists.map((a) => (
                          <li key={a.artist_id} className="notif-item">
                            <div className="notif-user-meta">
                              <div className="notif-name">{a.name}</div>
                              <div className="notif-username">
                                {a.report_count} reports
                              </div>
                            </div>
                            <div className="notif-actions">
                              <button
                                className="btn-accept"
                                onClick={() =>
                                  approveArtist.mutate(a.artist_id)
                                }
                                disabled={approveArtist.isPending}
                              >
                                Approve
                              </button>
                              <button
                                className="btn-decline"
                                onClick={() => rejectArtist.mutate(a.artist_id)}
                                disabled={rejectArtist.isPending}
                              >
                                Reject
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="empty-state small">No artist reports</div>
                    )}

                    <div className="notif-subtitle mt-2">Tracks</div>
                    {reports?.tracks.length ? (
                      <ul className="notif-list">
                        {reports.tracks.map((t) => (
                          <li key={t.track_id} className="notif-item">
                            <div className="notif-user">
                              {t.album?.picture ? (
                                <img
                                  className="notif-avatar"
                                  src={t.album.picture}
                                  alt={t.album?.name ?? "Album"}
                                />
                              ) : (
                                <div className="notif-avatar placeholder">
                                  🎵
                                </div>
                              )}
                              <div className="notif-user-meta">
                                <div className="notif-name">{t.title}</div>
                                <div className="notif-username">
                                  {t.artists.join(", ")}
                                  {t.album?.name ? ` • ${t.album.name}` : ""}
                                </div>
                                <div className="notif-username">
                                  {t.report_count} reports
                                </div>
                              </div>
                            </div>
                            <div className="notif-actions">
                              <button
                                className="btn-accept"
                                onClick={() => approveTrack.mutate(t.track_id)}
                                disabled={approveTrack.isPending}
                              >
                                Approve
                              </button>
                              <button
                                className="btn-decline"
                                onClick={() => rejectTrack.mutate(t.track_id)}
                                disabled={rejectTrack.isPending}
                              >
                                Reject
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="empty-state small">No track reports</div>
                    )}
                  </div>
                )}
              </div>
            )}

            <UserDropdown
              currentUser={currentUser}
              isDropdownOpen={isDropdownOpen}
              setIsDropdownOpen={setIsDropdownOpen}
              isMobile={isMobile}
              handlePublicProfileClick={handlePublicProfileClick}
              handleSettingsClick={handleSettingsClick}
              handleIgnoredClick={handleIgnoredClick}
              handleLogout={handleLogout}
              logoutMutation={logoutMutation}
            />
          </div>
        </div>
      </div>

      <ErrorBoundary resetKeys={[location.key]}>{children}</ErrorBoundary>

      {/* Mini player fixed in bottom-right */}
      <MiniPlayer />
    </div>
  );
}

export default Layout;
