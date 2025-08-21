import { useQuery } from "@tanstack/react-query";
import { apiService, queryKeys, UserResponse } from "./api";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";
import { RecentActivityWidget } from "./RecentActivity";

function Dashboard() {
  const { data: userResponse, isLoading: isUserLoading } = useQuery<
    UserResponse,
    Error
  >({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000,
    retry: 1,
  });

  const currentUser = userResponse?.user;
  const navigate = useNavigate();

  if (isUserLoading) {
    return (
      <div className="dashboard">
        <div className="dashboard-loading">
          <div className="loading-spinner"></div>
          <p>Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  const myIdent = currentUser?.username || currentUser?.id || "";

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        {/* ...existing header code... */}
      </header>

      <main className="dashboard-main">
        <div className="dashboard-grid">
          {/* My Activity widget */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2
                className="link"
                onClick={() =>
                  navigate(`/recent?user=${encodeURIComponent(myIdent)}`)
                }
              >
                Your Recent Activity
              </h2>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="#1db954">
                <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" />
              </svg>
            </div>
            <div className="card-content">
              <RecentActivityWidget
                includeMe={true}
                filterUser={myIdent}
                className="compact"
              />
            </div>
          </div>

          {/* Friends & Network widget */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2
                className="link"
                onClick={() => navigate(`/recent?exclude_me=true`)}
              >
                Friends & Network
              </h2>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="#1db954"
                aria-hidden="true"
              >
                <circle cx="8" cy="8" r="3"></circle>
                <circle cx="16" cy="9" r="2.5" opacity="0.85"></circle>
                <path d="M4 18c0-2.21 1.79-4 4-4s4 1.79 4 4v1H4v-1z"></path>
                <path
                  d="M13 18c0-1.93 1.57-3.5 3.5-3.5S20 16.07 20 18v1h-7v-1z"
                  opacity="0.85"
                ></path>
              </svg>
            </div>
            <div className="card-content">
              <RecentActivityWidget
                includeMe={false}
                filterUser={null}
                className="compact"
              />
            </div>
          </div>

          {/* Recommendations card unchanged */}
          <div className="dashboard-card" style={{ display: "none" }}>
            <div className="card-header">
              <h2>Recommendations</h2>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
            </div>
            <div className="card-content">
              <div className="recommendations-placeholder">
                <p>
                  Personalized music recommendations will appear here based on
                  your network's activity.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
