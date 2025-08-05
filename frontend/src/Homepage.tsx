import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiService } from './api'
import './Homepage.css'

function Homepage() {
  const navigate = useNavigate()

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

  return (
    <div className="homepage">
      <header className="homepage-header">
        <img src="/lykd.svg" alt="LYKD" className="homepage-logo" />
        <p className="homepage-tagline">your likes made social</p>
      </header>

      <main className="homepage-main">
        <div className="welcome-section">
          <h1 className="welcome-title">Welcome to LYKD</h1>
          <p className="welcome-description">
            Connect your music services and discover new songs through your friends' recommendations.
            Keep liking your favorite tracks and get personalized suggestions based on what your network is listening to.
          </p>
        </div>

        <div className="connect-section">
          <h2 className="connect-title">Get Started</h2>
          <p className="connect-description">
            Connect your Spotify account to begin sharing your music taste and discovering new favorites.
          </p>

          <button
            className="spotify-connect-button"
            onClick={handleSpotifyConnect}
            disabled={spotifyAuthMutation.isPending}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.84-.179-.84-.66 0-.359.24-.66.54-.78 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.24 1.021zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
            Connect with Spotify
          </button>
        </div>

        <div className="features-section">
          <h2 className="features-title">What You Can Do</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </div>
              <h3>Share Your Favorites</h3>
              <p>Let your friends know about the songs you're loving right now</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <h3>Get Recommendations</h3>
              <p>Discover new music based on what your network is listening to</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zM4 18v-1c0-1.1.9-2 2-2s2 .9 2 2v1h2v-1c0-2.21-1.79-4-4-4s-4 1.79-4 4v1h2zm8-2c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2s-2 .9-2 2v6c0 1.1.9 2 2 2z"/>
                </svg>
              </div>
              <h3>Connect with Friends</h3>
              <p>Build a network of music lovers and share your taste</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                </svg>
              </div>
              <h3>Clean & Organize</h3>
              <p>Remove duplicates from your Spotify likes and sync your favourites to a sharable playlist</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Homepage
