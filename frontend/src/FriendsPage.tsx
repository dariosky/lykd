import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiService } from "./api";
import { formatLocalDateTime } from "./date";
import { Link } from "react-router-dom";
import "./Recent.css";
import { useState } from "react";

export default function FriendsPage() {
  const queryClient = useQueryClient();
  const { data, status } = useQuery({
    queryKey: ["friendsList"],
    queryFn: apiService.getFriendsList,
    staleTime: 30 * 1000,
    retry: 1,
  });

  // Mutations for actions
  const unfriendMutation = useMutation({
    mutationFn: (id: string) => apiService.unfriend(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["friendsList"] }),
  });
  const declineMutation = useMutation({
    mutationFn: (username: string) => apiService.declineFriendRequest(username),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["friendsList"] }),
  });
  const acceptMutation = useMutation({
    mutationFn: (username: string) => apiService.acceptFriendRequest(username),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["friendsList"] }),
  });

  const { data: userData } = useQuery({
    queryKey: ["currentUser"],
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000,
    retry: 1,
  });
  const username = userData?.user?.username || userData?.user?.id || "";
  const publicUrl = `/user/${encodeURIComponent(username)}`;
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard
      .writeText(window.location.origin + publicUrl)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      });
  };

  const friends = data?.friends ?? [];

  return (
    <div className="likes-page">
      <div className="page-header">
        <div className="title-row">
          <h1 className="page-title">Friends</h1>
        </div>
      </div>
      <div className="page-content">
        <ul className="recent-list large">
          <li className="friend-header-row">
            <span className="friend-header friend-header-avatar">Picture</span>
            <span className="friend-header friend-header-username">
              Username
            </span>
            <span className="friend-header friend-header-link">Stats</span>
            <span className="friend-header friend-header-likes">Likes</span>
            <span className="friend-header friend-header-lastplay">
              Last Play
            </span>
            <span className="friend-header friend-header-actions">Actions</span>
          </li>
          {status === "pending" && (
            <div className="recent-loading">Loading…</div>
          )}
          {status === "error" && (
            <div className="recent-error">Failed to load friends.</div>
          )}
          {status === "success" &&
            friends.map((f) => {
              const pillName = f.username ?? "Unknown";
              const avatar = f.picture ? (
                <img
                  className="pill-avatar friend-avatar"
                  src={f.picture}
                  alt={pillName}
                />
              ) : (
                <div className="initials-avatar friend-avatar" aria-hidden>
                  {(f.username || "?")?.slice(0, 1).toUpperCase()}
                </div>
              );
              return (
                <li key={f.id} className="friend-row">
                  <div className="friend-cell friend-avatar-cell">{avatar}</div>
                  <div className="friend-cell friend-username-cell">
                    <Link
                      className="recent-user link friend-username"
                      to={`/user/${encodeURIComponent(f.username)}`}
                      data-name={pillName}
                    >
                      {pillName}
                    </Link>
                  </div>
                  <div className="friend-cell friend-link-cell">
                    <Link
                      className="friend-stats-link"
                      to={`/user/${encodeURIComponent(f.username)}`}
                      style={{
                        color: "#fff",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.3em",
                        fontWeight: 500,
                      }}
                    >
                      <span
                        role="img"
                        aria-label="Dashboard"
                        style={{ fontSize: "1.1em" }}
                      >
                        🌐
                      </span>
                      View Stats
                    </Link>
                  </div>
                  <div className="friend-cell friend-likes-cell">
                    {f.status === "accepted" && (
                      <span
                        className="friend-likes"
                        style={{ color: "#e74c3c", fontWeight: 500 }}
                      >
                        ❤️ {f.likes}
                      </span>
                    )}
                  </div>
                  <div className="friend-cell friend-lastplay-cell">
                    {f.status === "accepted" ? (
                      <span
                        className="friend-date"
                        style={{ color: "#27ae60", fontWeight: 500 }}
                      >
                        {f.last_play
                          ? formatLocalDateTime(f.last_play)
                          : "Never"}
                      </span>
                    ) : (
                      <span className="friend-date muted">—</span>
                    )}
                  </div>
                  <div className="friend-cell friend-actions-cell">
                    {f.status === "accepted" && (
                      <button
                        onClick={() => unfriendMutation.mutate(f.id)}
                        disabled={unfriendMutation.isPending}
                        className="friend-action-btn underline-btn no-bg"
                        style={{
                          background: "none",
                          boxShadow: "none",
                          border: "none",
                          color: "#bbb",
                          fontWeight: 500,
                        }}
                      >
                        <span
                          role="img"
                          aria-label="Unfriend"
                          style={{ marginRight: 4 }}
                        >
                          ❌
                        </span>
                        <span className="underline">Unfriend</span>
                      </button>
                    )}
                    {f.status === "requested" && (
                      <button
                        onClick={() => declineMutation.mutate(f.username)}
                        disabled={declineMutation.isPending}
                        className="friend-action-btn underline-btn no-bg"
                        style={{
                          background: "none",
                          boxShadow: "none",
                          border: "none",
                          color: "#bbb",
                          fontWeight: 500,
                        }}
                      >
                        <span
                          role="img"
                          aria-label="Cancel"
                          style={{ marginRight: 4 }}
                        >
                          🚫
                        </span>
                        <span className="underline">Cancel request</span>
                      </button>
                    )}
                    {f.status === "pending" && (
                      <>
                        <button
                          onClick={() => acceptMutation.mutate(f.username)}
                          disabled={acceptMutation.isPending}
                          className="friend-action-btn underline-btn no-bg"
                          style={{
                            background: "none",
                            boxShadow: "none",
                            border: "none",
                            color: "#bbb",
                            fontWeight: 500,
                          }}
                        >
                          <span
                            role="img"
                            aria-label="Accept"
                            style={{ marginRight: 4 }}
                          >
                            ✅
                          </span>
                          <span className="underline">Accept</span>
                        </button>
                        <button
                          onClick={() => declineMutation.mutate(f.username)}
                          disabled={declineMutation.isPending}
                          className="friend-action-btn underline-btn no-bg"
                          style={{
                            background: "none",
                            boxShadow: "none",
                            border: "none",
                            color: "#bbb",
                            fontWeight: 500,
                          }}
                        >
                          <span
                            role="img"
                            aria-label="Decline"
                            style={{ marginRight: 4 }}
                          >
                            🚫
                          </span>
                          <span className="underline">Decline</span>
                        </button>
                      </>
                    )}
                  </div>
                </li>
              );
            })}
        </ul>
        {friends.length === 0 && status === "success" && (
          <div className="recent-empty large">No friends yet.</div>
        )}
      </div>
      {/* Share public stats panel */}
      <div
        style={{
          background: "#f6fff6",
          border: "1px solid #1db954",
          borderRadius: 10,
          padding: "18px 16px",
          textAlign: "center",
          color: "#222",
          margin: "24px 0 0 0",
          boxShadow: "0 2px 8px rgba(29,185,84,0.08)",
          fontSize: 16,
        }}
      >
        <div style={{ marginBottom: 8 }}>
          Share your public stats page so friends can send you a request:
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          <a
            href={publicUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: "#1db954",
              fontWeight: 600,
              textDecoration: "underline",
              fontSize: 16,
            }}
          >
            Your Public stats page
          </a>
          <button
            onClick={handleCopy}
            style={{
              color: "#1db954",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 0,
              marginLeft: 2,
              display: "flex",
              alignItems: "center",
            }}
            aria-label="Copy public stats link"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill={copied ? "#1db954" : "#888"}
              style={{ transition: "fill 0.2s" }}
            >
              <rect
                x="9"
                y="9"
                width="10"
                height="10"
                rx="2"
                fill="currentColor"
              />
              <rect
                x="5"
                y="5"
                width="10"
                height="10"
                rx="2"
                fill="currentColor"
                opacity="0.5"
              />
            </svg>
            {copied && (
              <span style={{ color: "#1db954", fontSize: 13, marginLeft: 4 }}>
                Copied!
              </span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
