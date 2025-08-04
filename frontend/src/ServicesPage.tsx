import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { apiService, queryKeys, UserResponse } from './api'
import Layout from './Layout'
import './ServicesPage.css'

function ServicesPage() {
  // Current user query
  const {
    data: userResponse,
    isLoading: isUserLoading,
  } = useQuery<UserResponse, Error>({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000, // 30 seconds
    retry: 1,
  })

  const currentUser = userResponse?.user

  if (isUserLoading) {
    return (
      <Layout>
        <div className="services-page">
          <div className="services-header">
            <Link to="../" className="back-link">← Back to Home</Link>
            <h1>Your Services</h1>
          </div>
          <div className="loading">Loading...</div>
        </div>
      </Layout>
    )
  }

  if (!currentUser) {
    return (
      <Layout>
        <div className="services-page">
          <div className="services-header">
            <Link to="../" className="back-link">← Back to Home</Link>
            <h1>Your Services</h1>
          </div>
          <div className="no-user">Please log in to view your services.</div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="services-page">
        <div className="services-header">
          <Link to="../" className="back-link">← Back to Home</Link>
          <h1>Your Services</h1>
        </div>

        <div className="services-content">
          <div className="service-card">
            <div className="service-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.84-.179-.84-.66 0-.359.24-.66.54-.78 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.24 1.021zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
            </div>
            <div className="service-info">
              <h3>Spotify</h3>
              <p className="service-status connected">Connected</p>
              <p className="service-email">{currentUser.email}</p>
            </div>
            <div className="service-actions">
              <div className="status-badge connected">
                <span className="status-dot"></span>
                Active
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export default ServicesPage
