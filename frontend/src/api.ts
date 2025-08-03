// API service functions for TanStack Query

export interface ApiStatus {
  version: string
  status: string
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
}

// Query keys for consistent cache management
export const queryKeys = {
  backendStatus: ['backend', 'status'] as const,
  spotifyAuth: ['spotify', 'auth'] as const,
}
