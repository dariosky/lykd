import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import Layout from "./Layout";
import { apiService, queryKeys, IgnoredListResponse } from "./api";
import {
  UnignoreArtistButton,
  UnignoreTrackButton,
  ReportArtistButton,
  ReportTrackButton,
} from "./IgnoreButtons";
import "./IgnoredPage.css";

export default function IgnoredPage() {
  const { data, isLoading, isError, error } = useQuery<
    IgnoredListResponse,
    Error
  >({
    queryKey: queryKeys.ignored,
    queryFn: apiService.getIgnored,
    staleTime: 30_000,
    retry: 0, // surface 500s immediately
  });

  return (
    <Layout>
      <div className="ignored-page">
        <div className="ignored-page-header">
          <Link to="/" className="back-link">
            ← Back to Home
          </Link>
          <h1>Ignored Items</h1>
          <p className="ignored-description">
            Manage tracks and artists you've chosen to ignore. These items won't
            appear in your activity feeds and stats you'll see.
          </p>
          <p>
            There are tracks/artist we all aren't much interested into: once you
            ignored them for yourself you can report them for global exclusion:
            and admin will verify them and choose to accept it or not. These
            normally are white-noise playlists, and "less artistic" ones (no
            offense intended).
          </p>
        </div>

        {isLoading && (
          <div className="loading-section">
            <div className="loading-spinner"></div>
            <p>Loading ignored items...</p>
          </div>
        )}

        {isError && (
          <div className="error-section">
            <div className="error-title">Failed to load ignored items</div>
            <div className="error-message">{error?.message}</div>
          </div>
        )}

        {data && (
          <div className="ignored-content">
            {/* Ignored Artists Section */}
            <section className="ignored-section">
              <h2>🎤 Ignored Artists ({data.artists.length})</h2>
              {data.artists.length === 0 ? (
                <div className="empty-state">
                  <p>No ignored artists yet.</p>
                </div>
              ) : (
                <ul className="ignored-list">
                  {data.artists.map((artist) => (
                    <li key={artist.artist_id} className="ignored-item">
                      <div className="ignored-left">
                        <div className="ignored-avatar placeholder">🎤</div>
                      </div>
                      <div className="ignored-main">
                        <div className="ignored-title">{artist.name}</div>
                        <div className="ignored-subtitle">Artist</div>
                      </div>
                      <div className="ignored-actions">
                        {!artist.is_global && !artist.reported && (
                          <ReportArtistButton
                            artistId={artist.artist_id}
                            artistName={artist.name}
                            title="Request global ignore"
                            className="mr-2"
                          />
                        )}
                        <UnignoreArtistButton
                          artistId={artist.artist_id}
                          artistName={artist.name}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Ignored Tracks Section */}
            <section className="ignored-section">
              <h2>🎵 Ignored Tracks ({data.tracks.length})</h2>
              {data.tracks.length === 0 ? (
                <div className="empty-state">
                  <p>No ignored tracks yet.</p>
                </div>
              ) : (
                <ul className="ignored-list">
                  {data.tracks.map((track) => (
                    <li key={track.track_id} className="ignored-item">
                      <div className="ignored-left">
                        {track.album?.picture ? (
                          <img
                            className="ignored-avatar"
                            src={track.album.picture}
                            alt=""
                            title={track.album.name || ""}
                          />
                        ) : (
                          <div className="ignored-avatar placeholder">🎵</div>
                        )}
                      </div>
                      <div className="ignored-main">
                        <div className="ignored-title">{track.title}</div>
                        <div className="ignored-subtitle">
                          {track.artists.join(", ")}
                          {track.album?.name && ` • ${track.album.name}`}
                        </div>
                      </div>
                      <div className="ignored-actions">
                        {!track.is_global && !track.reported && (
                          <ReportTrackButton
                            trackId={track.track_id}
                            title="Request global ignore"
                            className="mr-2"
                          />
                        )}
                        <UnignoreTrackButton trackId={track.track_id} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </div>
    </Layout>
  );
}
