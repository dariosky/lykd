import React from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiService, queryKeys, UserResponse } from "./api";
import "./Layout.css";

interface LayoutProps {
  children: React.ReactNode;
}

function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false);

  // Current user query
  const { data: userResponse, refetch: refetchUser } = useQuery<
    UserResponse,
    Error
  >({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000, // 30 seconds
    retry: 1, // Don't retry too much for user info
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
    if (currentUser?.username) {
      navigate(`/user/${currentUser.username}`);
    }
  };

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (!target.closest(".user-dropdown-container")) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  }, [isDropdownOpen]);

  // Check for success parameter on mount and refetch user
  React.useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("spotify") === "connected") {
      console.log("Spotify connected successfully!");
      // Refetch user data to get the updated information
      refetchUser();
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [refetchUser]);

  const currentUser = userResponse?.user;

  return (
    <div className="layout">
      {currentUser && (
        <div className="user-header">
          <div className="user-header-content">
            <div className="header-logo" onClick={handleHomeClick}>
              <img src="/logo_dark.svg" alt="LYKD" className="logo" />
              LYKD
            </div>
            <div className="header-actions">
              {currentUser.username && (
                <button
                  className="public-profile-button"
                  onClick={handlePublicProfileClick}
                  title="Go to the public profile"
                >
                  🌎
                </button>
              )}
              <div className="user-dropdown-container">
                <button
                  className="user-button"
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                >
                  <img
                    src={currentUser.picture}
                    alt={currentUser.name}
                    className="user-avatar-small"
                  />
                  <span className="user-name-header">{currentUser.name}</span>
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className={`dropdown-arrow ${isDropdownOpen ? "open" : ""}`}
                  >
                    <path d="M7 10l5 5 5-5z" />
                  </svg>
                </button>

                {isDropdownOpen && (
                  <div className="user-dropdown">
                    <div className="dropdown-user-info">
                      <span className="dropdown-email">
                        {currentUser.email}
                      </span>
                    </div>
                    <div className="dropdown-divider"></div>
                    <button
                      className="dropdown-item"
                      onClick={handleSettingsClick}
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.028 7.028 0 0 0-1.63-.94l-.36-2.54a.5.5 0 0 0-.5-.42h-3.84a.5.5 0 0 0-.5.42l-.36 2.54c-.58.22-1.13.52-1.63.94l-2.39-.96a.5.5 0 0 0-.6.22L2.75 8.84a.5.5 0 0 0 .12.64l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58a.5.5 0 0 0-.12.64l1.92 3.32c.14.24.43.34.68.22l2.39-.96c.5.41 1.05.72 1.63.94l.36 2.54c.06.25.27.42.5.42h3.84c.25 0 .46-.17.5-.42l.36-2.54c.58-.22 1.13-.52 1.63-.94l2.39.96c.25.12.54.02.68-.22l1.92-3.32a.5.5 0 0 0-.12-.64l-2.03-1.58zM12 15.6a3.6 3.6 0 1 1 0-7.2 3.6 3.6 0 0 1 0 7.2z" />
                      </svg>
                      Settings
                    </button>
                    <button
                      className="dropdown-item logout"
                      onClick={handleLogout}
                      disabled={logoutMutation.isPending}
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.59L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" />
                      </svg>
                      {logoutMutation.isPending ? "Logging out..." : "Logout"}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {children}
    </div>
  );
}

export default Layout;
