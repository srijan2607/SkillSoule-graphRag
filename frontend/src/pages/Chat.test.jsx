import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import Chat from './Chat'

// Mock the AuthContext
const mockLogout = vi.fn()
const mockNavigate = vi.fn()

// Mock the useChat hook
const mockSendMessage = vi.fn()
const mockClearMessages = vi.fn()
let mockMessages = []
let mockIsLoading = false

vi.mock('../hooks/useChat', () => ({
  useChat: () => ({
    messages: mockMessages,
    isLoading: mockIsLoading,
    error: null,
    sendMessage: mockSendMessage,
    clearMessages: mockClearMessages
  })
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { email: 'test@example.com' },
    logout: mockLogout
  })
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

describe('Chat Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock state
    mockMessages = []
    mockIsLoading = false
    // Mock scrollIntoView for all tests
    Element.prototype.scrollIntoView = vi.fn()
  })

  const renderChat = () => {
    return render(
      <BrowserRouter>
        <Chat />
      </BrowserRouter>
    )
  }

  it('renders chat page with header', () => {
    renderChat()
    expect(screen.getByText('Graph RAG Chat')).toBeInTheDocument()
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
  })

  it('shows empty state when no messages', () => {
    renderChat()
    expect(screen.getByText(/ask me anything about careers/i)).toBeInTheDocument()
  })

  it('renders navigation component', () => {
    renderChat()
    // Navigation component should be present (tested separately in Navigation.test.jsx)
    expect(screen.getByText('Career AI')).toBeInTheDocument()
  })

  it('adds user message when sending', async () => {
    const user = userEvent.setup()

    // Update mock to include message after send
    mockSendMessage.mockImplementation((content) => {
      mockMessages = [{
        id: '1',
        role: 'user',
        content,
        timestamp: new Date()
      }]
    })

    renderChat()

    const input = screen.getByPlaceholderText(/ask me anything/i)
    await user.type(input, 'Hello assistant')
    await user.click(screen.getByLabelText('Send message'))

    expect(mockSendMessage).toHaveBeenCalledWith('Hello assistant')
  })

  it('calls sendMessage when form is submitted', async () => {
    const user = userEvent.setup()
    renderChat()

    const input = screen.getByPlaceholderText(/ask me anything/i)
    await user.type(input, 'Test query')
    await user.click(screen.getByLabelText('Send message'))

    // Verify sendMessage was called with correct argument
    expect(mockSendMessage).toHaveBeenCalledWith('Test query')
  })

  it('shows assistant response after delay', async () => {
    // Set up messages with assistant response
    mockMessages = [
      {
        id: '1',
        role: 'user',
        content: 'Test message',
        timestamp: new Date()
      },
      {
        id: '2',
        role: 'assistant',
        content: 'This is the assistant response',
        timestamp: new Date()
      }
    ]

    renderChat()

    // Assistant response should be visible
    expect(screen.getByText('This is the assistant response')).toBeInTheDocument()
  })

  it('disables input while loading', async () => {
    // Set loading state
    mockIsLoading = true

    renderChat()

    const input = screen.getByPlaceholderText(/ask me anything/i)

    // Input should be disabled when loading
    expect(input).toBeDisabled()
  })

  it('hides empty state after first message', async () => {
    const { rerender } = render(
      <BrowserRouter>
        <Chat />
      </BrowserRouter>
    )

    expect(screen.getByText(/ask me anything about careers/i)).toBeInTheDocument()

    // Simulate sending message by updating mock state
    mockMessages = [{
      id: '1',
      role: 'user',
      content: 'First message',
      timestamp: new Date()
    }]

    // Re-render to reflect new state
    rerender(
      <BrowserRouter>
        <Chat />
      </BrowserRouter>
    )

    expect(screen.queryByText(/ask me anything about careers/i)).not.toBeInTheDocument()
  })

  it('maintains message history', async () => {
    // Set up message history
    mockMessages = [
      {
        id: '1',
        role: 'user',
        content: 'First message',
        timestamp: new Date()
      },
      {
        id: '2',
        role: 'assistant',
        content: 'First response',
        timestamp: new Date()
      },
      {
        id: '3',
        role: 'user',
        content: 'Second message',
        timestamp: new Date()
      }
    ]

    renderChat()

    // Both messages should be visible
    expect(screen.getByText('First message')).toBeInTheDocument()
    expect(screen.getByText('Second message')).toBeInTheDocument()
  })
})
