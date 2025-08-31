import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BrowserRouter,
  Routes,
  Route,
  useNavigate,
  Navigate,
  Outlet,
} from "react-router-dom";
import App from "./App";
import ErrorPage from "./ErrorPage";
import SettingsPage from "./SettingsPage";
import PublicProfilePage from "./PublicProfilePage";
import SpotifyImportPage from "./SpotifyImportPage";
import RecentPlaysPage from "./RecentPlaysPage";
import IgnoredPage from "./IgnoredPage";
import LikesPage from "./LikesPage";
import Layout from "./Layout";
import { AuthProvider } from "./AuthContext";
import "./index.css";
import "./common.css";
import NotFoundPage from "./NotFoundPage";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function ErrorPageWrapper() {
  const navigate = useNavigate();
  return <ErrorPage onGoHome={() => navigate("/")} />;
}

function LayoutRoute() {
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}
// Add demo mode class to body if VITE_DEMO=1
if (import.meta.env.VITE_DEMO === "1") {
  document.body.classList.add("demo");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter
          future={{
            v7_relativeSplatPath: true,
            v7_startTransition: true,
          }}
        >
          <Routes>
            {/* All primary routes are nested under Layout to persist MiniPlayer */}
            <Route element={<LayoutRoute />}>
              <Route path="/" element={<App />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/spotify/import" element={<SpotifyImportPage />} />
              <Route path="/recent" element={<RecentPlaysPage />} />
              <Route path="/likes" element={<LikesPage />} />
              <Route path="/ignored" element={<IgnoredPage />} />
              <Route
                path="/services"
                element={<Navigate to="/settings" replace />}
              />
              <Route path="/user/:username" element={<PublicProfilePage />} />
              <Route path="*" element={<NotFoundPage />} />
              <Route path="/error" element={<ErrorPageWrapper />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
