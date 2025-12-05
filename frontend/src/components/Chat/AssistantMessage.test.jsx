import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AssistantMessage from './AssistantMessage'

describe('AssistantMessage', () => {
  it('renders message content', () => {
    render(<AssistantMessage content="Hello from assistant!" />)
    expect(screen.getByText('Hello from assistant!')).toBeInTheDocument()
  })

  it('renders timestamp when provided', () => {
    const timestamp = new Date('2025-01-15T14:45:00')
    render(<AssistantMessage content="Test message" timestamp={timestamp} />)
    expect(screen.getByText('2:45 PM')).toBeInTheDocument()
  })

  it('does not render timestamp when not provided', () => {
    render(<AssistantMessage content="Test message" />)
    const timestampElement = screen.queryByText(/\d{1,2}:\d{2}/)
    expect(timestampElement).not.toBeInTheDocument()
  })

  it('renders SourceCitations when sources provided', () => {
    const sources = [
      { node_type: 'Skill', node_id: 'skill-001', properties: { name: 'Python' } },
      { node_type: 'Job', node_id: 'job-001', properties: { job_title: 'Engineer' } }
    ]
    render(<AssistantMessage content="Test" sources={sources} />)
    
    // Should show source summary (collapsed by default)
    expect(screen.getByText('Based on 1 job and 1 skill')).toBeInTheDocument()
  })

  it('does not render SourceCitations when sources array is empty', () => {
    render(<AssistantMessage content="Test" sources={[]} />)
    expect(screen.queryByText(/Based on/)).not.toBeInTheDocument()
  })

  it('does not render SourceCitations when sources is null', () => {
    render(<AssistantMessage content="Test" sources={null} />)
    expect(screen.queryByText(/Based on/)).not.toBeInTheDocument()
  })

  it('expands sources when clicked', () => {
    const sources = [
      { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } },
      { node_type: 'Job', node_id: 'j1', properties: { job_title: 'Software Engineer' } }
    ]
    render(<AssistantMessage content="Test" sources={sources} />)
    
    // Initially collapsed
    expect(screen.queryByText('Skills')).not.toBeInTheDocument()
    
    // Click to expand
    const button = screen.getByRole('button', { name: /expand sources/i })
    fireEvent.click(button)
    
    // Now expanded
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('Jobs')).toBeInTheDocument()
    expect(screen.getByText(/Python/)).toBeInTheDocument()
    expect(screen.getByText(/Software Engineer/)).toBeInTheDocument()
  })

  it('applies correct styling classes', () => {
    const { container } = render(<AssistantMessage content="Test" />)
    const messageDiv = container.querySelector('.bg-gray-100')
    expect(messageDiv).toBeInTheDocument()
    expect(messageDiv?.classList.contains('text-gray-900')).toBe(true)
  })

  it('integrates SourceCitations below message content', () => {
    const sources = [
      { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } }
    ]
    const { container } = render(
      <AssistantMessage content="Test message" sources={sources} />
    )
    
    const messageContainer = container.querySelector('.bg-gray-100')
    expect(messageContainer).toBeInTheDocument()
    
    // SourceCitations should be within the message container
    const sourceCitations = messageContainer?.querySelector('.source-citations')
    expect(sourceCitations).toBeInTheDocument()
  })
})
