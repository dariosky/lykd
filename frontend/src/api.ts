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
};

// Query keys for consistent cache management
export const queryKeys = {
  backendStatus: ["backend", "status"] as const,
  currentUser: ["user", "me"] as const,
  spotifyAuth: ["spotify", "auth"] as const,
};
