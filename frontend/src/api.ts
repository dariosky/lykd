// API service functions for TanStack Query

export interface ApiStatus {
  version: string;
  status: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  username?: string | null;
  picture: string;
  join_date: string;
  is_admin: boolean;
}

export interface UserResponse {
  user: User | null;
}

export interface PublicTrackItem {
  track_id: string;
  title: string;
  duration: number;
  play_count: number;
  artists: string[];
  album?: { id: string; name: string; release_date: string | null } | null;
}

export interface PublicArtistItem {
  artist_id: string;
  name: string;
  play_count: number;
}

export interface PublicProfileResponse {
  user: {
    id: string;
    name: string;
    username: string;
    picture: string | null;
    join_date: string;
  };
  stats: {
    total_plays: number;
    total_likes: number;
    total_listening_time_sec: number;
    listening_time_last_30_days_sec: number;
    tracking_since?: string | null;
  };
  highlights: {
    top_songs_30_days: PublicTrackItem[];
    top_songs_all_time: PublicTrackItem[];
    top_artists: PublicArtistItem[];
    most_played_decade: string | null;
  };
}

export interface SpotifyStats {
  total_likes_synced: number;
  total_plays_synced: number;
  tracking_since: string | null;
  active: boolean;
  full_history_sync_wait: number; // seconds to wait before extended import is available
  last_full_history_sync: string | null; // ISO string when user last ran full history import
}

// Friendship
export type FriendshipStatus =
  | "none"
  | "self"
  | "friends"
  | "pending_outgoing"
  | "pending_incoming";

export interface FriendshipStatusResponse {
  status: FriendshipStatus;
}

export interface PendingRequestItem {
  user: {
    id: string;
    name: string;
    username: string | null;
    picture: string | null;
  };
  requested_at: string;
}

export interface PendingRequestsResponse {
  pending: PendingRequestItem[];
}

// Ignored items
export interface IgnoredTrackItem {
  track_id: string;
  title: string;
  album?: { id: string; name: string; picture: string | null } | null;
  artists: string[];
  is_global: boolean;
  reported: boolean;
}
export interface IgnoredArtistItem {
  artist_id: string;
  name: string;
  is_global: boolean;
  reported: boolean;
}
export interface IgnoredListResponse {
  tracks: IgnoredTrackItem[];
  artists: IgnoredArtistItem[];
}

// Admin reports
export interface ReportTrackItem {
  track_id: string;
  title: string;
  album?: { id: string; name: string; picture: string | null } | null;
  artists: string[];
  report_count: number;
}
export interface ReportArtistItem {
  artist_id: string;
  name: string;
  report_count: number;
}
export interface ReportsResponse {
  tracks: ReportTrackItem[];
  artists: ReportArtistItem[];
}

// Recent activity
export interface RecentTrack {
  id: string;
  title: string | null;
  duration: number | null;
  album?: {
    id: string;
    name: string;
    picture: string | null;
    release_date: string | null;
  } | null;
  artists: string[];
}

export interface RecentUserRef {
  id: string;
  name: string | null;
  username: string | null;
  picture: string | null;
}

export interface RecentItem {
  user: RecentUserRef;
  track: RecentTrack;
  played_at: string;
  context_uri?: string | null;
}

export interface RecentResponse {
  items: RecentItem[];
  next_before: string | null;
}

// A specific error to represent 404 Not Found responses
export class NotFoundError extends Error {
  status: number;
  constructor(message = "Profile not found") {
    super(message);
    this.name = "NotFoundError";
    this.status = 404;
  }
}

export const apiService = {
  // Fetch backend status with 5-second stale time
  getBackendStatus: async (): Promise<ApiStatus> => {
    const response = await fetch("/api/");
    if (!response.ok) {
      throw new Error(
        `API returned ${response.status}: ${response.statusText}`,
      );
    }
    return response.json();
  },

  // Get current user information
  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await fetch("/api/user/me", {
      credentials: "include", // Include cookies for session
    });
    if (!response.ok) {
      throw new Error(`Failed to get user info: ${response.status}`);
    }
    return response.json();
  },

  // Update username
  updateUsername: async (username: string): Promise<UserResponse> => {
    const response = await fetch("/api/user/username", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username }),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Failed to update username: ${response.status} ${errorText}`,
      );
    }
    return response.json();
  },

  // Get Spotify authorization URL
  getSpotifyAuthUrl: async (): Promise<{
    authorization_url: string;
    state: string;
  }> => {
    const response = await fetch("/api/spotify/authorize");
    if (!response.ok) {
      throw new Error(`Failed to get authorization URL: ${response.status}`);
    }
    const data = await response.json();
    if (!data.authorization_url) {
      throw new Error("No authorization URL received from server");
    }
    return data;
  },

  // Logout user
  logout: async (): Promise<{ message: string }> => {
    const response = await fetch("/api/logout", {
      method: "POST",
      credentials: "include", // Include cookies for session
    });
    if (!response.ok) {
      throw new Error(`Failed to logout: ${response.status}`);
    }
    return response.json();
  },

  // Fetch a public user profile by username
  getPublicProfile: async (
    username: string,
  ): Promise<PublicProfileResponse> => {
    const response = await fetch(
      `/api/user/${encodeURIComponent(username)}/public`,
    );
    if (response.status === 404) {
      // Throw a specific error that the UI can detect and avoid retrying
      throw new NotFoundError();
    }
    if (!response.ok) {
      throw new Error(`Error code: ${response.status}`);
    }
    return response.json();
  },

  // Friendship APIs
  getFriendshipStatus: async (
    username: string,
  ): Promise<FriendshipStatusResponse> => {
    const response = await fetch(
      `/api/friendship/status/${encodeURIComponent(username)}`,
      { credentials: "include" },
    );
    if (!response.ok) {
      throw new Error(`Failed to get friendship status: ${response.status}`);
    }
    return response.json();
  },

  sendFriendRequest: async (
    username: string,
  ): Promise<{ friendship: { status: string; requested_at: string } }> => {
    const response = await fetch(
      `/api/friendship/request/${encodeURIComponent(username)}`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok) {
      const text = await response.text();
      throw new Error(
        `Failed to send friend request: ${response.status} ${text}`,
      );
    }
    return response.json();
  },

  acceptFriendRequest: async (
    username: string,
  ): Promise<{
    friendship: { status: string; responded_at: string | null };
  }> => {
    const response = await fetch(
      `/api/friendship/accept/${encodeURIComponent(username)}`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Failed to accept: ${response.status} ${text}`);
    }
    return response.json();
  },

  declineFriendRequest: async (
    username: string,
  ): Promise<{
    friendship: { status: string; responded_at: string | null };
  }> => {
    const response = await fetch(
      `/api/friendship/decline/${encodeURIComponent(username)}`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Failed to decline: ${response.status} ${text}`);
    }
    return response.json();
  },

  getPendingRequests: async (): Promise<PendingRequestsResponse> => {
    const response = await fetch(`/api/friendship/pending`, {
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Failed to get pending requests: ${response.status}`);
    }
    return response.json();
  },

  // Ignore APIs
  getIgnored: async (): Promise<IgnoredListResponse> => {
    const response = await fetch(`/api/ignore`, { credentials: "include" });
    if (!response.ok)
      throw new Error(`Failed to get ignored: ${response.status}`);
    return response.json();
  },
  ignoreTrack: async (trackId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/ignore/track/${encodeURIComponent(trackId)}`,
      {
        method: "POST",
        credentials: "include",
      },
    );
    if (!response.ok)
      throw new Error(`Failed to ignore track: ${response.status}`);
    return response.json();
  },
  unignoreTrack: async (trackId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/ignore/track/${encodeURIComponent(trackId)}`,
      {
        method: "DELETE",
        credentials: "include",
      },
    );
    if (!response.ok)
      throw new Error(`Failed to unignore track: ${response.status}`);
    return response.json();
  },
  reportTrack: async (trackId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/ignore/track/${encodeURIComponent(trackId)}/report`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok)
      throw new Error(`Failed to report track: ${response.status}`);
    return response.json();
  },
  ignoreArtist: async (artistId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/ignore/artist/${encodeURIComponent(artistId)}`,
      {
        method: "POST",
        credentials: "include",
      },
    );
    if (!response.ok)
      throw new Error(`Failed to ignore artist: ${response.status}`);
    return response.json();
  },
  unignoreArtist: async (artistId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/ignore/artist/${encodeURIComponent(artistId)}`,
      {
        method: "DELETE",
        credentials: "include",
      },
    );
    if (!response.ok)
      throw new Error(`Failed to unignore artist: ${response.status}`);
    return response.json();
  },
  reportArtist: async (artistId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/ignore/artist/${encodeURIComponent(artistId)}/report`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok)
      throw new Error(`Failed to report artist: ${response.status}`);
    return response.json();
  },

  // Admin report review
  getReports: async (): Promise<ReportsResponse> => {
    const response = await fetch(`/api/reports`, { credentials: "include" });
    if (!response.ok)
      throw new Error(`Failed to get reports: ${response.status}`);
    return response.json();
  },
  approveTrackReport: async (trackId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/admin/ignore/track/${encodeURIComponent(trackId)}/approve`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok)
      throw new Error(`Failed to approve track: ${response.status}`);
    return response.json();
  },
  rejectTrackReport: async (trackId: string): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/admin/ignore/track/${encodeURIComponent(trackId)}/reject`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok)
      throw new Error(`Failed to reject track: ${response.status}`);
    return response.json();
  },
  approveArtistReport: async (
    artistId: string,
  ): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/admin/ignore/artist/${encodeURIComponent(artistId)}/approve`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok)
      throw new Error(`Failed to approve artist: ${response.status}`);
    return response.json();
  },
  rejectArtistReport: async (
    artistId: string,
  ): Promise<{ message: string }> => {
    const response = await fetch(
      `/api/admin/ignore/artist/${encodeURIComponent(artistId)}/reject`,
      { method: "POST", credentials: "include" },
    );
    if (!response.ok)
      throw new Error(`Failed to reject artist: ${response.status}`);
    return response.json();
  },

  // Recent activity
  getRecent: async (params: {
    limit?: number;
    before?: string | null;
    include_me?: boolean;
    user?: string | null;
    q?: string | null;
  }): Promise<RecentResponse> => {
    const qs = new URLSearchParams();
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.before) qs.set("before", params.before);
    if (params.include_me === false) qs.set("include_me", "false");
    if (params.user) qs.set("user", params.user);
    if (params.q) qs.set("q", params.q);
    const response = await fetch(`/api/recent?${qs.toString()}`, {
      credentials: "include",
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Failed to get recent: ${response.status} ${text}`);
    }
    return response.json();
  },

  // Get Spotify stats for current user
  getSpotifyStats: async (): Promise<SpotifyStats> => {
    const response = await fetch("/api/spotify/stats", {
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`Failed to get Spotify stats: ${response.status}`);
    }
    return response.json();
  },

  // Upload extended streaming history ZIP
  uploadExtendedHistory: async (file: File): Promise<{ message: string }> => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/spotify/import", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Upload failed: ${response.status} ${text}`);
    }
    return response.json();
  },
};

// Query keys for consistent cache management
export const queryKeys = {
  backendStatus: ["backend", "status"] as const,
  currentUser: ["user", "me"] as const,
  spotifyAuth: ["spotify", "auth"] as const,
  spotifyStats: ["spotify", "stats"] as const,
  friendshipStatus: (username: string) =>
    ["friendship", "status", username] as const,
  pendingRequests: ["friendship", "pending"] as const,
  recent: (includeMe: boolean, user?: string | null, q?: string | null) =>
    [
      "recent",
      includeMe ? "me+friends" : "friends",
      user ?? null,
      q ?? null,
    ] as const,
  ignored: ["ignore", "list"] as const,
  reports: ["admin", "reports"] as const,
};
