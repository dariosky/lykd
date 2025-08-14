import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BrowserRouter,
  Routes,
  Route,
  useNavigate,
  Navigate,
} from "react-router-dom";
import App from "./App";
import ErrorPage from "./ErrorPage";
import SettingsPage from "./SettingsPage";
import PublicProfilePage from "./PublicProfilePage";
import "./index.css";

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

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_relativeSplatPath: true,
          v7_startTransition: true,
        }}
      >
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route
            path="/services"
            element={<Navigate to="/settings" replace />}
          />
          <Route path="/user/:username" element={<PublicProfilePage />} />
          <Route path="/error" element={<ErrorPageWrapper />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
