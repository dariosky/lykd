import { useQuery } from "@tanstack/react-query";
import { apiService, ApiStatus, queryKeys } from "./api";
import Homepage from "./Homepage";
import Dashboard from "./Dashboard";
import "./App.css";
import { Footer } from "./Footer.tsx";
import { useAuth } from "./AuthContext";

function App() {
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

  const { isLoggedIn, loading: isUserLoading } = useAuth();

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
  if (!isLoggedIn) {
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
