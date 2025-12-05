/**
 * Navigation Component Tests
 *
 * Tests for navigation bar with active route highlighting and logout.
 * Story 5.5: Navigation & Layout Integration
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Navigation from './Navigation'

// Mock react-router-dom hooks
const mockNavigate = vi.fn()
const mockLocation = { pathname: '/chat' }

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
  }
})

// Helper function to render with router
const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage before each test
    localStorage.clear()
  })

  describe('Rendering', () => {
    it('should render app name', () => {
      renderWithRouter(<Navigation />)
      expect(screen.getByText('Career AI')).toBeInTheDocument()
    })

    it('should render all navigation links', () => {
      renderWithRouter(<Navigation />)

      expect(screen.getAllByText('Chat')).toHaveLength(2) // Desktop + Mobile
      expect(screen.getByText('Upload Data')).toBeInTheDocument()
      expect(screen.getByText('Upload')).toBeInTheDocument() // Mobile version
      expect(screen.getAllByText('Logout')).toHaveLength(2) // Desktop + Mobile
    })

    it('should render navigation bar with correct styling', () => {
      const { container } = renderWithRouter(<Navigation />)
      const nav = container.querySelector('nav')

      expect(nav).toHaveClass('bg-white', 'border-b', 'border-gray-200')
    })
  })

  describe('Active Route Highlighting', () => {
    it('should highlight Chat link when on /chat route', () => {
      mockLocation.pathname = '/chat'
      renderWithRouter(<Navigation />)

      const chatLinks = screen.getAllByText('Chat')
      const desktopChatLink = chatLinks.find(link =>
        link.className.includes('text-blue-600')
      )

      expect(desktopChatLink).toBeInTheDocument()
      expect(desktopChatLink).toHaveClass('text-blue-600', 'border-b-2', 'border-blue-600')
    })

    it('should highlight Upload Data link when on /upload route', () => {
      mockLocation.pathname = '/upload'
      renderWithRouter(<Navigation />)

      const uploadLink = screen.getByText('Upload Data')
      expect(uploadLink).toHaveClass('text-blue-600', 'border-b-2', 'border-blue-600')
    })

    it('should not highlight links when on different route', () => {
      mockLocation.pathname = '/other'
      renderWithRouter(<Navigation />)

      const chatLink = screen.getByText('Upload Data')
      expect(chatLink).toHaveClass('text-gray-600')
      expect(chatLink).not.toHaveClass('text-blue-600')
    })
  })

  describe('Logout Functionality', () => {
    it('should clear auth_token from localStorage on logout', () => {
      localStorage.setItem('auth_token', 'test-token')
      const { getAllByRole } = renderWithRouter(<Navigation />)

      const logoutButtons = getAllByRole('button', { name: /logout/i })
      fireEvent.click(logoutButtons[0]) // Click desktop logout button

      expect(localStorage.getItem('auth_token')).toBeFalsy()
    })

    it('should clear chat_messages from localStorage on logout', () => {
      localStorage.setItem('chat_messages', JSON.stringify([{ id: 1, content: 'test' }]))
      const { getAllByRole } = renderWithRouter(<Navigation />)

      const logoutButtons = getAllByRole('button', { name: /logout/i })
      fireEvent.click(logoutButtons[0])

      expect(localStorage.getItem('chat_messages')).toBeFalsy()
    })

    it('should navigate to /login on logout', () => {
      const { getAllByRole } = renderWithRouter(<Navigation />)

      const logoutButtons = getAllByRole('button', { name: /logout/i })
      fireEvent.click(logoutButtons[0])

      expect(mockNavigate).toHaveBeenCalledWith('/login')
      expect(mockNavigate).toHaveBeenCalledTimes(1)
    })

    it('should handle logout from mobile button', () => {
      localStorage.setItem('auth_token', 'test-token')
      const { getAllByRole } = renderWithRouter(<Navigation />)

      const logoutButtons = getAllByRole('button', { name: /logout/i })
      fireEvent.click(logoutButtons[1]) // Click mobile logout button

      expect(localStorage.getItem('auth_token')).toBeFalsy()
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })

  describe('Responsive Design', () => {
    it('should have desktop navigation hidden on mobile', () => {
      renderWithRouter(<Navigation />)

      const desktopNav = screen.getByText('Upload Data').closest('.hidden.md\\:flex')
      expect(desktopNav).toHaveClass('hidden', 'md:flex')
    })

    it('should have mobile navigation visible on small screens', () => {
      renderWithRouter(<Navigation />)

      const mobileNav = screen.getByText('Upload').closest('.md\\:hidden')
      expect(mobileNav).toHaveClass('md:hidden')
    })
  })

  describe('Accessibility', () => {
    it('should have focus styles on logout button', () => {
      renderWithRouter(<Navigation />)

      const logoutButtons = screen.getAllByText('Logout')
      const desktopLogout = logoutButtons[0]

      expect(desktopLogout).toHaveClass('focus:outline-none', 'focus:ring-2')
    })

    it('should be keyboard navigable', () => {
      renderWithRouter(<Navigation />)

      const chatLink = screen.getByText('Upload Data')
      expect(chatLink.tagName).toBe('A') // Should be a link element
    })
  })
})
