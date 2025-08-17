import React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import Layout from "./Layout";
import { apiService, queryKeys, SpotifyStats } from "./api";
import "./SpotifyImport.css";
import { Link } from "react-router-dom";

function SpotifyImportPage() {
  const [file, setFile] = React.useState<File | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  // Fetch stats to determine if import is temporarily blocked
  const { data: stats } = useQuery<SpotifyStats, Error>({
    queryKey: queryKeys.spotifyStats,
    queryFn: apiService.getSpotifyStats,
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000, // Refetch every minute
    retry: 1,
  });

  // Local countdown in seconds, minute precision updates
  const [waitSeconds, setWaitSeconds] = React.useState<number>(0);

  React.useEffect(() => {
    if (typeof stats?.full_history_sync_wait === "number") {
      setWaitSeconds(stats.full_history_sync_wait);
    }
  }, [stats?.full_history_sync_wait]);

  React.useEffect(() => {
    if (!waitSeconds || waitSeconds <= 0) return;
    const interval = setInterval(() => {
      setWaitSeconds((prev) => (prev > 60 ? prev - 60 : 0));
    }, 60 * 1000);
    return () => clearInterval(interval);
  }, [waitSeconds]);

  const humanizeWait = (seconds: number) => {
    const totalMinutes = Math.ceil(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (hours > 0 && minutes > 0)
      return `${hours} hour${
        hours === 1 ? "" : "s"
      } and ${minutes} minute${minutes === 1 ? "" : "s"}`;
    if (hours > 0) return `${hours} hour${hours === 1 ? "" : "s"}`;
    return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  };

  const uploadMutation = useMutation({
    mutationFn: async (f: File) => apiService.uploadExtendedHistory(f),
    onSuccess: (data) => {
      setMessage(data.message || "Upload received");
      setError(null);
    },
    onError: (e: Error) => {
      setMessage(null);
      setError(e.message || "Upload failed");
    },
  });

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    setFile(files && files[0] ? files[0] : null);
    setMessage(null);
    setError(null);
  };

  const onUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || waitSeconds > 0) return;
    uploadMutation.mutate(file);
  };

  const isBlocked = (waitSeconds ?? 0) > 0;
  const lastSyncDate = stats?.last_full_history_sync
    ? new Date(stats.last_full_history_sync)
    : null;
  const lastSyncHuman = lastSyncDate
    ? lastSyncDate.toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <Layout>
      <div className="import-page">
        <div className="import-header">
          <Link to="/settings" className="back-link">
            ← Back to Settings
          </Link>
          <h1>Import your full Spotify streaming history</h1>
        </div>

        <div className="import-content">
          <section className="import-card">
            <h2>Why this is needed</h2>
            <p>
              Probably you want to get stats about all your Spotify history -
              not only from now on.
            </p>
            <p>
              Spotify's public APIs allow apps like LYKD to fetch up to 24 hours
              of listening data from the moment you first connect your account.
              To import your complete listening history, you need to request the
              Extended streaming history directly from Spotify.
            </p>
            <p>
              Go to the Spotify privacy page and request your Extended streaming
              history. Spotify will prepare the data and send it to your email
              within a couple of days.
            </p>
            <p>
              Privacy page:{" "}
              <a
                href="https://www.spotify.com/ca-en/account/privacy/"
                target="_blank"
                rel="noreferrer"
                className="link"
              >
                https://www.spotify.com/ca-en/account/privacy/
              </a>
            </p>
            <p>
              Once you receive the email, download the ZIP file and upload it
              below to import your past listening history into LYKD.
            </p>
          </section>

          <section className="import-card">
            {lastSyncHuman && (
              <>
                <p className="subtitle">
                  You already uploaded your full history sync on {lastSyncHuman}
                  .
                </p>
                <div className="stat-grid">
                  <div className="stat-item red">
                    <div className="stat-left">
                      <span className="stat-icon" aria-hidden>
                        📅
                      </span>
                      <span className="stat-label">
                        Last full history upload
                      </span>
                    </div>
                    <div className="stat-value">{lastSyncHuman}</div>
                  </div>
                  {typeof stats?.total_plays_synced === "number" && (
                    <div className="stat-item green">
                      <div className="stat-left">
                        <span className="stat-icon" aria-hidden>
                          ▶️
                        </span>
                        <span className="stat-label">Total plays imported</span>
                      </div>
                      <div className="stat-value">
                        {stats.total_plays_synced.toLocaleString()}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
            <h2>Upload your ZIP</h2>
            {isBlocked ? (
              <p className="subtitle">
                Extended history import is temporarily unavailable. Please try
                again in {humanizeWait(waitSeconds)}.
              </p>
            ) : null}
            <form onSubmit={onUpload} className="upload-form">
              <input
                type="file"
                accept=".zip,application/zip,application/x-zip-compressed"
                onChange={onFileChange}
                disabled={isBlocked}
              />
              <button
                type="submit"
                className="upload-button"
                disabled={!file || uploadMutation.isPending || isBlocked}
              >
                {uploadMutation.isPending ? "Uploading…" : "Upload ZIP"}
              </button>
              {message && <p className="success">{message}</p>}
              {error && <p className="error">{error}</p>}
            </form>
          </section>
        </div>
      </div>
    </Layout>
  );
}

export default SpotifyImportPage;
