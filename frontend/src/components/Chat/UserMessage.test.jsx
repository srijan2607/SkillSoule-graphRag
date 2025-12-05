import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UserMessage from './UserMessage'

describe('UserMessage', () => {
  it('renders message content', () => {
    render(<UserMessage content="Hello, world!" />)
    expect(screen.getByText('Hello, world!')).toBeInTheDocument()
  })

  it('renders timestamp when provided', () => {
    const timestamp = new Date('2025-01-15T10:30:00')
    render(<UserMessage content="Test message" timestamp={timestamp} />)
    expect(screen.getByText('10:30 AM')).toBeInTheDocument()
  })

  it('does not render timestamp when not provided', () => {
    render(<UserMessage content="Test message" />)
    const timestampElement = screen.queryByText(/\d{1,2}:\d{2}/)
    expect(timestampElement).not.toBeInTheDocument()
  })

  it('applies correct styling classes', () => {
    const { container } = render(<UserMessage content="Test" />)
    const messageDiv = container.querySelector('.bg-blue-500')
    expect(messageDiv).toBeInTheDocument()
    expect(messageDiv?.classList.contains('text-white')).toBe(true)
  })

  it('handles multiline content', () => {
    const multilineContent = 'Line 1\nLine 2\nLine 3'
    const { container } = render(<UserMessage content={multilineContent} />)
    const messageElement = container.querySelector('.whitespace-pre-wrap')
    expect(messageElement?.textContent).toBe(multilineContent)
  })
})
