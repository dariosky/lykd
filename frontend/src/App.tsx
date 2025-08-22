import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiService, ApiStatus, queryKeys, UserResponse } from "./api";
import Homepage from "./Homepage";
import Dashboard from "./Dashboard";
import "./App.css";
import { Footer } from "./Footer.tsx";

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
    staleTime: 60 * 1000, // 60 seconds
    refetchInterval: 60 * 1000, // Refetch every 60 seconds
    retry: 2,
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

  // If user is not logged in, show Homepage (without footer here)
  if (!currentUser) {
    return <Homepage />;
  }

  // If user is logged in, show Dashboard; footer remains part of this page
  return (
    <>
      <Dashboard />

      <Footer loading={isLoading} error={error} apiStatus={apiStatus} />
    </>
  );
}

export default App;
