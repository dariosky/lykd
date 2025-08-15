import React from "react";
import { useMutation } from "@tanstack/react-query";
import Layout from "./Layout";
import { apiService } from "./api";
import "./SpotifyImport.css";

function SpotifyImportPage() {
  const [file, setFile] = React.useState<File | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

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
    if (!file) return;
    uploadMutation.mutate(file);
  };

  return (
    <Layout>
      <div className="import-page">
        <div className="import-header">
          <h1>Import your full Spotify streaming history</h1>
          <p className="subtitle">
            Fill the gaps beyond the 24-hour API window.
          </p>
        </div>

        <div className="import-content">
          <section className="import-card">
            <h2>Why this is needed</h2>
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
            <h2>Upload your ZIP</h2>
            <form onSubmit={onUpload} className="upload-form">
              <input
                type="file"
                accept=".zip,application/zip,application/x-zip-compressed"
                onChange={onFileChange}
              />
              <button
                type="submit"
                className="upload-button"
                disabled={!file || uploadMutation.isPending}
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
