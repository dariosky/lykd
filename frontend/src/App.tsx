import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiService, queryKeys, ApiStatus, UserResponse } from "./api";
import Layout from "./Layout";
import Homepage from "./Homepage";
import Dashboard from "./Dashboard";
import "./App.css";

function App() {
  const navigate = useNavigate();

  // Backend status query with 5-second stale time
  const {
    data: apiStatus,
    isLoading,
    error,
  } = useQuery<ApiStatus, Error>({
    queryKey: queryKeys.backendStatus,
    queryFn: apiService.getBackendStatus,
    staleTime: 5 * 1000, // 5 seconds
    refetchInterval: 5 * 1000, // Refetch every 5 seconds
    retry: 3,
  });

  // Current user query
  const { data: userResponse, isLoading: isUserLoading } = useQuery<
    UserResponse,
    Error
  >({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000, // 30 seconds
    retry: 1, // Don't retry too much for user info
  });

  // Show error page for API failures
  React.useEffect(() => {
    if (error) {
      navigate(`/error?type=api&message=${encodeURIComponent(error.message)}`);
    }
  }, [error, navigate]);

  const currentUser = userResponse?.user;

  // Show loading state while checking authentication
  if (isUserLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // If user is not logged in, show Homepage without Layout
  if (!currentUser) {
    return <Homepage />;
  }

  // If user is logged in, show Dashboard with Layout
  return (
    <Layout>
      <Dashboard />

      <footer className="footer">
        <div className="footer-content">
          {isLoading && (
            <div className="status-indicator loading">
              <span>Connecting to backend...</span>
            </div>
          )}
          {error && (
            <div className="status-indicator error">
              <span>Backend connection failed</span>
            </div>
          )}
          {apiStatus && (
            <>
              <div className="status-indicator">
                <div className="status-dot"></div>
                <span>Backend: {apiStatus.status}</span>
              </div>
              <span>•</span>
              <span>Version: {apiStatus.version}</span>
            </>
          )}
        </div>
      </footer>
    </Layout>
  );
}

export default App;
