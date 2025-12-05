import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChatInput from './ChatInput'

describe('ChatInput', () => {
  it('renders input field and send button', () => {
    const mockOnSend = vi.fn()
    render(<ChatInput onSend={mockOnSend} />)

    expect(screen.getByPlaceholderText(/ask me anything/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Send message')).toBeInTheDocument()
  })

  it('calls onSend when form is submitted with valid text', async () => {
    const mockOnSend = vi.fn()
    const user = userEvent.setup()

    render(<ChatInput onSend={mockOnSend} />)

    const input = screen.getByPlaceholderText(/ask me anything/i)
    await user.type(input, 'Hello')
    await user.click(screen.getByLabelText('Send message'))

    expect(mockOnSend).toHaveBeenCalledWith('Hello')
  })

  it('clears input after sending message', async () => {
    const mockOnSend = vi.fn()
    const user = userEvent.setup()

    render(<ChatInput onSend={mockOnSend} />)

    const input = screen.getByPlaceholderText(/ask me anything/i)
    await user.type(input, 'Hello')
    await user.click(screen.getByLabelText('Send message'))

    expect(input.value).toBe('')
  })

  it('does not call onSend with empty or whitespace-only text', async () => {
    const mockOnSend = vi.fn()
    const user = userEvent.setup()

    render(<ChatInput onSend={mockOnSend} />)

    const sendButton = screen.getByLabelText('Send message')
    await user.click(sendButton)

    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('trims whitespace from message', async () => {
    const mockOnSend = vi.fn()
    const user = userEvent.setup()

    render(<ChatInput onSend={mockOnSend} />)

    const input = screen.getByPlaceholderText(/ask me anything/i)
    await user.type(input, '  Hello  ')
    await user.click(screen.getByLabelText('Send message'))

    expect(mockOnSend).toHaveBeenCalledWith('Hello')
  })

  it('sends message on Enter key', async () => {
    const mockOnSend = vi.fn()
    const user = userEvent.setup()

    render(<ChatInput onSend={mockOnSend} />)

    const input = screen.getByPlaceholderText(/ask me anything/i)
    await user.type(input, 'Hello{Enter}')

    expect(mockOnSend).toHaveBeenCalledWith('Hello')
  })

  it('does not send message on Shift+Enter', async () => {
    const mockOnSend = vi.fn()
    const user = userEvent.setup()

    render(<ChatInput onSend={mockOnSend} />)

    const input = screen.getByPlaceholderText(/ask me anything/i)
    await user.type(input, 'Line 1{Shift>}{Enter}{/Shift}Line 2')

    expect(mockOnSend).not.toHaveBeenCalled()
    expect(input.value).toContain('Line 1')
    expect(input.value).toContain('Line 2')
  })

  it('disables input and button when disabled prop is true', () => {
    const mockOnSend = vi.fn()
    render(<ChatInput onSend={mockOnSend} disabled={true} />)

    const input = screen.getByPlaceholderText(/ask me anything/i)
    const button = screen.getByLabelText('Send message')

    expect(input).toBeDisabled()
    expect(button).toBeDisabled()
  })

  it('disables send button when input is empty', () => {
    const mockOnSend = vi.fn()
    render(<ChatInput onSend={mockOnSend} />)

    const button = screen.getByLabelText('Send message')
    expect(button).toBeDisabled()
  })
})
