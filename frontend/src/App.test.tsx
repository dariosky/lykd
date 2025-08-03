import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from './App'

// Mock fetch
const mockFetch = vi.fn()
;(globalThis as any).fetch = mockFetch

describe('App', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  it('renders LYKD title', () => {
    mockFetch.mockResolvedValueOnce({
      json: async () => ({ version: '0.1.0', status: 'ok' })
    })

    render(<App />)
    expect(screen.getByText('LYKD')).toBeInTheDocument()
    expect(screen.getByText('Your likes made social')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    mockFetch.mockImplementationOnce(() => new Promise(() => {})) // Never resolves

    render(<App />)
    expect(screen.getByText('Connecting to backend...')).toBeInTheDocument()
  })

  it('displays API status when backend responds', async () => {
    mockFetch.mockResolvedValueOnce({
      json: async () => ({ version: '0.1.0', status: 'ok' })
    })

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('✅ Backend connected')).toBeInTheDocument()
      expect(screen.getByText('Version: 0.1.0')).toBeInTheDocument()
      expect(screen.getByText('Status: ok')).toBeInTheDocument()
    })
  })

  it('displays error message when backend fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Failed to connect to backend')).toBeInTheDocument()
    })
  })
})
