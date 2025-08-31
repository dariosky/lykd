import { useNavigate } from "react-router-dom";
import { RecentActivityWidget } from "./RecentActivity";
import { useQuery } from "@tanstack/react-query";
import { apiService, queryKeys } from "./api";
import type { FriendsListResponse } from "./api";
import { useState } from "react";

export function RecentFriendsWidget() {
  const navigate = useNavigate();
  // Query friends list using React Query
  const { data, isLoading, error } = useQuery<FriendsListResponse, Error>({
    queryKey: ["friendsList"],
    queryFn: apiService.getFriendsList,
    staleTime: 30 * 1000,
    retry: 1,
  });
  // Query current user for username
  const { data: userData } = useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000,
    retry: 1,
  });
  const username = userData?.user?.username || userData?.user?.id || "";
  const publicUrl = `/user/${encodeURIComponent(username)}`;
  const [copied, setCopied] = useState(false);

  // Only count/display friends with status === "accepted"
  const acceptedFriends =
    data?.friends?.filter((f) => f.status === "accepted") ?? [];
  const friendsCount = acceptedFriends.length;

  const handleCopy = () => {
    navigator.clipboard
      .writeText(window.location.origin + publicUrl)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      });
  };

  return (
    <div className="dashboard-card">
      <div className="card-header">
        <h2
          className="link"
          onClick={() => navigate(`/recent?exclude_me=true`)}
        >
          Friends & Network
        </h2>
        <div
          className="friends"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            cursor: "pointer",
          }}
          onClick={() => navigate("/friends")}
        >
          <svg
            className="friends-icon"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="#1db954"
            aria-hidden="true"
          >
            <circle cx="8" cy="8" r="3"></circle>
            <circle cx="16" cy="9" r="2.5" opacity="0.85"></circle>
            <path d="M4 18c0-2.21 1.79-4 4-4s4 1.79 4 4v1H4v-1z"></path>
            <path
              d="M13 18c0-1.93 1.57-3.5 3.5-3.5S20 16.07 20 18v1h-7v-1z"
              opacity="0.85"
            ></path>
          </svg>
          <span
            style={{
              background: "#1db954",
              color: "white",
              borderRadius: "50%",
              minWidth: 20,
              height: 20,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 13,
              fontWeight: 600,
              marginLeft: 2,
              padding: "0 6px",
            }}
            aria-label="Number of friends"
          >
            {isLoading ? "..." : friendsCount}
          </span>
        </div>
      </div>
      <div className="card-content">
        {error ? (
          <div style={{ color: "red" }}>Error loading friends.</div>
        ) : friendsCount === 0 && !isLoading ? (
          <div
            style={{
              background: "#f6fff6",
              border: "1px solid #1db954",
              borderRadius: 10,
              padding: "18px 16px",
              textAlign: "center",
              color: "#222",
              margin: "12px 0",
              boxShadow: "0 2px 8px rgba(29,185,84,0.08)",
              fontSize: 16,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 18, marginBottom: 8 }}>
              No friends yet? Let's change that!
            </div>
            <div style={{ marginBottom: 8 }}>
              Share your public stats page so friends can send you a request:
            </div>
            <div
              style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
            >
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
                  <span
                    style={{ color: "#1db954", fontSize: 13, marginLeft: 4 }}
                  >
                    Copied!
                  </span>
                )}
              </button>
            </div>
          </div>
        ) : (
          <RecentActivityWidget
            includeMe={false}
            filterUser={null}
            className="compact"
          />
        )}
      </div>
    </div>
  );
}
