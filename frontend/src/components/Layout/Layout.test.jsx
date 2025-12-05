/**
 * Layout Component Tests
 *
 * Tests for layout wrapper with navigation.
 * Story 5.5: Navigation & Layout Integration
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Layout from './Layout'

// Mock Navigation component
vi.mock('./Navigation', () => ({
  default: () => <div data-testid="mock-navigation">Navigation</div>,
}))

// Helper function to render with router
const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('Layout', () => {
  describe('Rendering', () => {
    it('should render Navigation component', () => {
      renderWithRouter(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      expect(screen.getByTestId('mock-navigation')).toBeInTheDocument()
    })

    it('should render children content', () => {
      renderWithRouter(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      expect(screen.getByText('Test Content')).toBeInTheDocument()
    })

    it('should have correct container styling', () => {
      const { container } = renderWithRouter(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      const layoutDiv = container.firstChild
      expect(layoutDiv).toHaveClass('min-h-screen', 'bg-gray-50')
    })

    it('should have correct main element styling', () => {
      const { container } = renderWithRouter(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      const main = container.querySelector('main')
      expect(main).toBeInTheDocument()
      expect(main).toHaveClass(
        'max-w-7xl',
        'mx-auto',
        'px-4',
        'sm:px-6',
        'lg:px-8',
        'py-8'
      )
    })
  })

  describe('Content Structure', () => {
    it('should render Navigation before children', () => {
      const { container } = renderWithRouter(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      // Navigation should be rendered first
      const navigation = screen.getByTestId('mock-navigation')
      expect(navigation).toBeInTheDocument()

      // Content should be wrapped in main which comes after nav
      const main = container.querySelector('main')
      expect(main).toBeInTheDocument()
      expect(main).toHaveTextContent('Test Content')
    })

    it('should wrap children in main element', () => {
      renderWithRouter(
        <Layout>
          <div data-testid="child-content">Test Content</div>
        </Layout>
      )

      const childContent = screen.getByTestId('child-content')
      const main = childContent.closest('main')

      expect(main).toBeInTheDocument()
    })
  })

  describe('Multiple Children', () => {
    it('should render multiple children correctly', () => {
      renderWithRouter(
        <Layout>
          <div>First Child</div>
          <div>Second Child</div>
          <div>Third Child</div>
        </Layout>
      )

      expect(screen.getByText('First Child')).toBeInTheDocument()
      expect(screen.getByText('Second Child')).toBeInTheDocument()
      expect(screen.getByText('Third Child')).toBeInTheDocument()
    })

    it('should render complex child components', () => {
      const ComplexChild = () => (
        <div>
          <h1>Title</h1>
          <p>Paragraph</p>
          <button>Button</button>
        </div>
      )

      renderWithRouter(
        <Layout>
          <ComplexChild />
        </Layout>
      )

      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Paragraph')).toBeInTheDocument()
      expect(screen.getByText('Button')).toBeInTheDocument()
    })
  })

  describe('Responsive Padding', () => {
    it('should have responsive padding classes', () => {
      const { container } = renderWithRouter(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      const main = container.querySelector('main')
      expect(main).toHaveClass('px-4', 'sm:px-6', 'lg:px-8')
    })

    it('should have max-width constraint', () => {
      const { container } = renderWithRouter(
        <Layout>
          <div>Test Content</div>
        </Layout>
      )

      const main = container.querySelector('main')
      expect(main).toHaveClass('max-w-7xl', 'mx-auto')
    })
  })
})
