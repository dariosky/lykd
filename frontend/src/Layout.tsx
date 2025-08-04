import React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiService, queryKeys, UserResponse } from './api'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

function Layout({ children }: LayoutProps) {
  const navigate = useNavigate()
  const [isDropdownOpen, setIsDropdownOpen] = React.useState(false)

  // Current user query
  const {
    data: userResponse,
    refetch: refetchUser
  } = useQuery<UserResponse, Error>({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000, // 30 seconds
    retry: 1, // Don't retry too much for user info
  })

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: apiService.logout,
    onSuccess: () => {
      // Reload the page to reset all state
      window.location.href = "/"
    },
    onError: (error: Error) => {
      console.error('Error logging out:', error)
      // Still reload the page even if logout fails
      window.location.reload()
    },
  })

  const handleLogout = () => {
    setIsDropdownOpen(false)
    logoutMutation.mutate()
  }

  const handleServicesClick = () => {
    setIsDropdownOpen(false)
    navigate('/services')
  }

  const handleHomeClick = () => {
    setIsDropdownOpen(false)
    navigate('/')
  }

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (!target.closest('.user-dropdown-container')) {
        setIsDropdownOpen(false)
      }
    }

    if (isDropdownOpen) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [isDropdownOpen])

  // Check for success parameter on mount and refetch user
  React.useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.get('spotify') === 'connected') {
      console.log('Spotify connected successfully!')
      // Refetch user data to get the updated information
      refetchUser()
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [refetchUser])

  const currentUser = userResponse?.user

  return (
    <div className="layout">
      {currentUser && (
        <div className="user-header">
          <div className="user-header-content">
            <div className="user-dropdown-container">
              <button
                className="user-button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              >
                <img
                  src={currentUser.picture}
                  alt={currentUser.name}
                  className="user-avatar-small"
                />
                <span className="user-name-header">{currentUser.name}</span>
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className={`dropdown-arrow ${isDropdownOpen ? 'open' : ''}`}
                >
                  <path d="M7 10l5 5 5-5z"/>
                </svg>
              </button>

              {isDropdownOpen && (
                <div className="user-dropdown">
                  <div className="dropdown-user-info">
                    <span className="dropdown-email">{currentUser.email}</span>
                  </div>
                  <div className="dropdown-divider"></div>
                  <button
                    className="dropdown-item"
                    onClick={handleHomeClick}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                    </svg>
                    Home
                  </button>
                  <button
                    className="dropdown-item"
                    onClick={handleServicesClick}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                    </svg>
                    Services
                  </button>
                  <button
                    className="dropdown-item logout"
                    onClick={handleLogout}
                    disabled={logoutMutation.isPending}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.59L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
                    </svg>
                    {logoutMutation.isPending ? 'Logging out...' : 'Logout'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {children}
    </div>
  )
}

export default Layout
