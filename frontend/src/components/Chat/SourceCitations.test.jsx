import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SourceCitations from './SourceCitations'

describe('SourceCitations', () => {
  const mockSources = [
    { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } },
    { node_type: 'Skill', node_id: 's2', properties: { name: 'React' } },
    { node_type: 'Job', node_id: 'j1', properties: { job_title: 'Software Engineer' } },
    { node_type: 'Company', node_id: 'c1', properties: { company_name: 'Tech Corp' } }
  ]

  it('should not render when sources is null', () => {
    const { container } = render(<SourceCitations sources={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('should not render when sources is empty array', () => {
    const { container } = render(<SourceCitations sources={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('should render summary with correct counts', () => {
    render(<SourceCitations sources={mockSources} />)
    
    expect(screen.getByText('Based on 1 job, 2 skills, and 1 company')).toBeInTheDocument()
  })

  it('should start collapsed by default', () => {
    render(<SourceCitations sources={mockSources} />)
    
    // Summary should be visible
    expect(screen.getByText('Based on 1 job, 2 skills, and 1 company')).toBeInTheDocument()
    
    // Details should not be visible
    expect(screen.queryByText('Skills')).not.toBeInTheDocument()
    expect(screen.queryByText('Jobs')).not.toBeInTheDocument()
  })

  it('should expand when clicked', () => {
    render(<SourceCitations sources={mockSources} />)
    
    const button = screen.getByRole('button', { name: /expand sources/i })
    fireEvent.click(button)
    
    // Details should now be visible
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('Jobs')).toBeInTheDocument()
    expect(screen.getByText('Companies')).toBeInTheDocument()
  })

  it('should collapse when clicked again', () => {
    render(<SourceCitations sources={mockSources} />)
    
    const button = screen.getByRole('button')
    
    // Expand
    fireEvent.click(button)
    expect(screen.getByText('Skills')).toBeInTheDocument()
    
    // Collapse
    fireEvent.click(button)
    expect(screen.queryByText('Skills')).not.toBeInTheDocument()
  })

  it('should toggle with keyboard (Enter key)', () => {
    render(<SourceCitations sources={mockSources} />)
    
    const button = screen.getByRole('button')
    
    fireEvent.keyDown(button, { key: 'Enter' })
    expect(screen.getByText('Skills')).toBeInTheDocument()
    
    fireEvent.keyDown(button, { key: 'Enter' })
    expect(screen.queryByText('Skills')).not.toBeInTheDocument()
  })

  it('should toggle with keyboard (Space key)', () => {
    render(<SourceCitations sources={mockSources} />)
    
    const button = screen.getByRole('button')
    
    fireEvent.keyDown(button, { key: ' ' })
    expect(screen.getByText('Skills')).toBeInTheDocument()
  })

  it('should update aria-expanded attribute', () => {
    render(<SourceCitations sources={mockSources} />)
    
    const button = screen.getByRole('button')
    
    expect(button).toHaveAttribute('aria-expanded', 'false')
    
    fireEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
  })

  it('should only show groups with sources', () => {
    const sourcesOnlySkills = [
      { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } }
    ]
    
    render(<SourceCitations sources={sourcesOnlySkills} />)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.queryByText('Jobs')).not.toBeInTheDocument()
    expect(screen.queryByText('Companies')).not.toBeInTheDocument()
  })

  it('should display source details when expanded', () => {
    render(<SourceCitations sources={mockSources} />)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    expect(screen.getByText(/Python/)).toBeInTheDocument()
    expect(screen.getByText(/React/)).toBeInTheDocument()
    expect(screen.getByText(/Software Engineer/)).toBeInTheDocument()
    expect(screen.getByText(/Tech Corp/)).toBeInTheDocument()
  })

  it('should handle singular/plural correctly', () => {
    const singleSources = [
      { node_type: 'Job', node_id: 'j1', properties: { job_title: 'Engineer' } }
    ]
    
    render(<SourceCitations sources={singleSources} />)
    expect(screen.getByText('Based on 1 job')).toBeInTheDocument()
    
    const pluralSources = [
      { node_type: 'Job', node_id: 'j1', properties: { job_title: 'Engineer' } },
      { node_type: 'Job', node_id: 'j2', properties: { job_title: 'Designer' } }
    ]
    
    const { rerender } = render(<SourceCitations sources={pluralSources} />)
    rerender(<SourceCitations sources={pluralSources} />)
    expect(screen.getByText('Based on 2 jobs')).toBeInTheDocument()
  })
})
