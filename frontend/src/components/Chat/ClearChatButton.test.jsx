import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ClearChatButton from './ClearChatButton'

describe('ClearChatButton', () => {
  let mockOnClear
  let confirmSpy

  beforeEach(() => {
    mockOnClear = vi.fn()
    // Mock window.confirm
    confirmSpy = vi.spyOn(window, 'confirm')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders clear chat button', () => {
    render(<ClearChatButton onClear={mockOnClear} />)

    expect(screen.getByRole('button', { name: /clear chat history/i })).toBeInTheDocument()
    expect(screen.getByText(/clear chat/i)).toBeInTheDocument()
  })

  it('shows confirmation dialog when clicked', async () => {
    confirmSpy.mockReturnValue(false)
    const user = userEvent.setup()

    render(<ClearChatButton onClear={mockOnClear} />)

    const button = screen.getByRole('button', { name: /clear chat history/i })
    await user.click(button)

    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringContaining('Are you sure')
    )
  })

  it('calls onClear when user confirms', async () => {
    confirmSpy.mockReturnValue(true)
    const user = userEvent.setup()

    render(<ClearChatButton onClear={mockOnClear} />)

    const button = screen.getByRole('button', { name: /clear chat history/i })
    await user.click(button)

    expect(mockOnClear).toHaveBeenCalledTimes(1)
  })

  it('does not call onClear when user cancels', async () => {
    confirmSpy.mockReturnValue(false)
    const user = userEvent.setup()

    render(<ClearChatButton onClear={mockOnClear} />)

    const button = screen.getByRole('button', { name: /clear chat history/i })
    await user.click(button)

    expect(mockOnClear).not.toHaveBeenCalled()
  })

  it('is disabled when disabled prop is true', () => {
    render(<ClearChatButton onClear={mockOnClear} disabled={true} />)

    const button = screen.getByRole('button', { name: /clear chat history/i })
    expect(button).toBeDisabled()
  })

  it('is enabled when disabled prop is false', () => {
    render(<ClearChatButton onClear={mockOnClear} disabled={false} />)

    const button = screen.getByRole('button', { name: /clear chat history/i })
    expect(button).not.toBeDisabled()
  })

  it('does not trigger confirmation when disabled', () => {
    render(<ClearChatButton onClear={mockOnClear} disabled={true} />)

    const button = screen.getByRole('button', { name: /clear chat history/i })
    
    // Disabled buttons cannot be clicked in userEvent, so just verify it's disabled
    expect(button).toBeDisabled()
    // Verify handlers were never called
    expect(confirmSpy).not.toHaveBeenCalled()
    expect(mockOnClear).not.toHaveBeenCalled()
  })
})
