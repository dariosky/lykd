// API service functions for TanStack Query

export interface ApiStatus {
  version: string
  status: string
}

export interface User {
  id: string
  name: string
  email: string
  picture: string
  join_date: string
  is_admin: boolean
}

export interface UserResponse {
  user: User | null
}

export const apiService = {
  // Fetch backend status with 5-second stale time
  getBackendStatus: async (): Promise<ApiStatus> => {
    const response = await fetch('/api/')
    if (!response.ok) {
      throw new Error(`API returned ${response.status}: ${response.statusText}`)
    }
    return response.json()
  },

  // Get current user information
  getCurrentUser: async (): Promise<UserResponse> => {
    const response = await fetch('/api/user/me', {
      credentials: 'include', // Include cookies for session
    })
    if (!response.ok) {
      throw new Error(`Failed to get user info: ${response.status}`)
    }
    return response.json()
  },

  // Get Spotify authorization URL
  getSpotifyAuthUrl: async (): Promise<{ authorization_url: string; state: string }> => {
    const response = await fetch('/api/spotify/authorize')
    if (!response.ok) {
      throw new Error(`Failed to get authorization URL: ${response.status}`)
    }
    const data = await response.json()
    if (!data.authorization_url) {
      throw new Error('No authorization URL received from server')
    }
    return data
  },

  // Logout user
  logout: async (): Promise<{ message: string }> => {
    const response = await fetch('/api/logout', {
      method: 'POST',
      credentials: 'include', // Include cookies for session
    })
    if (!response.ok) {
      throw new Error(`Failed to logout: ${response.status}`)
    }
    return response.json()
  },
}

// Query keys for consistent cache management
export const queryKeys = {
  backendStatus: ['backend', 'status'] as const,
  currentUser: ['user', 'me'] as const,
  spotifyAuth: ['spotify', 'auth'] as const,
}
