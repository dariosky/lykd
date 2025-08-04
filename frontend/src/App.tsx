import React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiService, queryKeys, ApiStatus, UserResponse } from './api'
import Layout from './Layout'
import './App.css'

function App() {
  const navigate = useNavigate()

  // Backend status query with 5-second stale time
  const {
    data: apiStatus,
    isLoading,
    error
  } = useQuery<ApiStatus, Error>({
    queryKey: queryKeys.backendStatus,
    queryFn: apiService.getBackendStatus,
    staleTime: 5 * 1000, // 5 seconds
    refetchInterval: 5 * 1000, // Refetch every 5 seconds
    retry: 3,
  })

  // Current user query
  const {
    data: userResponse,
    isLoading: isUserLoading,
  } = useQuery<UserResponse, Error>({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000, // 30 seconds
    retry: 1, // Don't retry too much for user info
  })

  // Spotify authorization mutation
  const spotifyAuthMutation = useMutation({
    mutationFn: apiService.getSpotifyAuthUrl,
    onSuccess: (data) => {
      // Redirect to Spotify authorization page
      window.location.href = data.authorization_url
    },
    onError: (error: Error) => {
      console.error('Error initiating Spotify connection:', error)
      // Navigate to error page with URL params
      navigate(`/error?type=api&message=${encodeURIComponent(error.message)}`)
    },
  })

  const handleSpotifyConnect = () => {
    spotifyAuthMutation.mutate()
  }

  // Show error page for API failures
  React.useEffect(() => {
    if (error) {
      navigate(`/error?type=api&message=${encodeURIComponent(error.message)}`)
    }
  }, [error, navigate])

  const currentUser = userResponse?.user

  return (
    <Layout>
      <header className="header">
        <img src="/lykd.svg" alt="LYKD" className="logo" />
        <p className="tagline">your likes made social</p>
      </header>

      <main className="main-content">
        <div className="services-section">
          <h2 className="services-title">Your Services</h2>
          {currentUser ? (
            <div className="spotify-connected">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.84-.179-.84-.66 0-.359.24-.66.54-.78 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.24 1.021zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
              <span>Spotify connected to {currentUser.email}</span>
            </div>
          ) : (
            <button
              className="spotify-button"
              onClick={handleSpotifyConnect}
              disabled={spotifyAuthMutation.isPending || isUserLoading}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.84-.179-.84-.66 0-.359.24-.66.54-.78 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.24 1.021zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
              {spotifyAuthMutation.isPending ? 'Connecting...' : 'Connect to Spotify'}
            </button>
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="footer-content">
          {isLoading && (
            <div className="status-indicator loading">
              <span>Connecting to backend...</span>
            </div>
          )}
          {error && (
            <div className="status-indicator error">
              <span>Backend connection failed</span>
            </div>
          )}
          {apiStatus && (
            <>
              <div className="status-indicator">
                <div className="status-dot"></div>
                <span>Backend: {apiStatus.status}</span>
              </div>
              <span>•</span>
              <span>Version: {apiStatus.version}</span>
            </>
          )}
        </div>
      </footer>
    </Layout>
  )
}

export default App
