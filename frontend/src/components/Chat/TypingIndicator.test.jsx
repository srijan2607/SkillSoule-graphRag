import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import TypingIndicator from './TypingIndicator'

describe('TypingIndicator', () => {
  it('renders without crashing', () => {
    const { container } = render(<TypingIndicator />)
    expect(container).toBeInTheDocument()
  })

  it('renders three animated dots', () => {
    const { container } = render(<TypingIndicator />)
    const dots = container.querySelectorAll('.animate-bounce')
    expect(dots).toHaveLength(3)
  })

  it('applies correct styling to match AssistantMessage', () => {
    const { container } = render(<TypingIndicator />)
    const messageContainer = container.querySelector('.bg-gray-100')
    expect(messageContainer).toBeInTheDocument()
  })

  it('has staggered animation delays', () => {
    const { container } = render(<TypingIndicator />)
    const dots = container.querySelectorAll('.animate-bounce')

    // Check that animation delays are different
    expect(dots[0]).toHaveStyle({ animationDelay: '0ms' })
    expect(dots[1]).toHaveStyle({ animationDelay: '150ms' })
    expect(dots[2]).toHaveStyle({ animationDelay: '300ms' })
  })
})
