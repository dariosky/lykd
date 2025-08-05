import { useQuery } from "@tanstack/react-query";
import { apiService, queryKeys, UserResponse } from "./api";
import "./Dashboard.css";

function Dashboard() {
  // Current user query
  const { data: userResponse, isLoading: isUserLoading } = useQuery<
    UserResponse,
    Error
  >({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000, // 30 seconds
    retry: 1,
  });

  const currentUser = userResponse?.user;

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

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="welcome-message">
          <h1>Welcome back, {currentUser?.name}!</h1>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="dashboard-grid">
          <div className="dashboard-card">
            <div className="card-header">
              <h2>Recent Activity</h2>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" />
              </svg>
            </div>
            <div className="card-content">
              <div className="activity-placeholder">
                <p>
                  Your music activity will appear here once you start using the
                  app.
                </p>
              </div>
            </div>
          </div>

          <div className="dashboard-card">
            <div className="card-header">
              <h2>Friends & Network</h2>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zM4 18v-1c0-1.1.9-2 2-2s2 .9 2 2v1h2v-1c0-2.21-1.79-4-4-4s-4 1.79-4 4v1h2zm8-2c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2s-2 .9-2 2v6c0 1.1.9 2 2 2z" />
              </svg>
            </div>
            <div className="card-content">
              <div className="friends-placeholder">
                <p>
                  Connect with friends to start sharing music recommendations.
                </p>
              </div>
            </div>
          </div>

          <div className="dashboard-card">
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
