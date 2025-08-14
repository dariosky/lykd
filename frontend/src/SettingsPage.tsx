import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiService, queryKeys, UserResponse } from "./api";
import Layout from "./Layout";
import "./ServicesPage.css";

function SettingsPage() {
  const queryClient = useQueryClient();

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

  const [username, setUsername] = React.useState("");
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => {
    if (currentUser) {
      setUsername(currentUser.username ?? "");
    }
  }, [currentUser]);

  // Use saved username for link/copy so it only changes after save
  const savedUsername = currentUser?.username ?? "";

  const updateUsernameMutation = useMutation({
    mutationFn: (u: string) => apiService.updateUsername(u),
    onSuccess: () => {
      setMessage("Saved");
      setError(null);
      queryClient.invalidateQueries({ queryKey: queryKeys.currentUser });
      // Clear message after a short delay
      setTimeout(() => setMessage(null), 2000);
    },
    onError: (e: Error) => {
      setMessage(null);
      const msg = e.message.includes("409")
        ? "That username is taken."
        : e.message.includes("400")
          ? "Username cannot be empty."
          : "Couldn't save username.";
      setError(msg);
    },
  });

  const onSaveUsername = (e: React.FormEvent) => {
    e.preventDefault();
    updateUsernameMutation.mutate(username.trim());
  };

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const profilePath = savedUsername
    ? `/user/${savedUsername}`
    : "/user/yourname";
  const profileUrl = `${origin}${profilePath}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`${origin}/user/${savedUsername}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (_) {
      // ignore
    }
  };

  if (isUserLoading) {
    return (
      <Layout>
        <div className="services-page">
          <div className="services-header">
            <Link to="../" className="back-link">
              ← Back to Home
            </Link>
            <h1>Settings</h1>
          </div>
          <div className="loading">Loading...</div>
        </div>
      </Layout>
    );
  }

  if (!currentUser) {
    return (
      <Layout>
        <div className="services-page">
          <div className="services-header">
            <Link to="../" className="back-link">
              ← Back to Home
            </Link>
            <h1>Settings</h1>
          </div>
          <div className="no-user">Please log in to view your settings.</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="services-page">
        <div className="services-header">
          <Link to="../" className="back-link">
            ← Back to Home
          </Link>
          <h1>Settings</h1>
        </div>

        {/* Username section */}
        <div className="services-content">
          <div className="settings-card">
            <form onSubmit={onSaveUsername} className="settings-form">
              <div className="settings-form-row">
                <label htmlFor="username" className="settings-label">
                  Profile name
                </label>
                <div className="input-row">
                  <span className="input-prefix">@</span>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="settings-input input-with-prefix"
                    placeholder="yourname"
                    maxLength={40}
                    autoComplete="off"
                  />
                </div>
                <div className="settings-hint">
                  Your public profile link:
                  <div className="settings-url">
                    <a href={profilePath} className="link" rel="noreferrer">
                      {profileUrl}
                    </a>
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={handleCopy}
                      disabled={!savedUsername}
                      aria-label="Copy profile link"
                    >
                      {copied ? "Copied" : "Copy"}
                    </button>
                    {savedUsername && (
                      <Link to={profilePath} className="btn-secondary">
                        View public profile
                      </Link>
                    )}
                  </div>
                </div>
              </div>
              <div className="settings-actions">
                <button
                  type="submit"
                  className="settings-save"
                  disabled={updateUsernameMutation.isPending}
                >
                  {updateUsernameMutation.isPending ? "Saving…" : "Save"}
                </button>
                {message && <span className="settings-success">{message}</span>}
                {error && <span className="settings-error">{error}</span>}
              </div>
            </form>
          </div>
        </div>

        {/* Services section (existing) */}
        <div className="services-content">
          <div className="service-card">
            <div className="service-icon">
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.84-.179-.84-.66 0-.359.24-.66.54-.78 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.24 1.021zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z" />
              </svg>
            </div>
            <div className="service-info">
              <h3>Spotify</h3>
              <p className="service-status connected">Connected</p>
              <p className="service-email">{currentUser.email}</p>
            </div>
            <div className="service-actions">
              <div className="status-badge connected">
                <span className="status-dot"></span>
                Active
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default SettingsPage;
