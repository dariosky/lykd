import { useQuery } from "@tanstack/react-query";
import { apiService, queryKeys, UserResponse } from "./api";
import "./Dashboard.css";
import { RecentMyWidget } from "./RecentMyWidget";
import { RecentFriendsWidget } from "./RecentFriendsWidget";

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
      <main className="dashboard-main">
        <div className="dashboard-grid">
          {/* My Activity widget */}
          <RecentMyWidget myIdent={myIdent} />

          {/* Friends & Network widget */}
          <RecentFriendsWidget />

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
