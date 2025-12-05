import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import SourceGroup from './SourceGroup'

describe('SourceGroup', () => {
  it('should render group title and sources', () => {
    const sources = [
      { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } },
      { node_type: 'Skill', node_id: 's2', properties: { name: 'React' } }
    ]

    render(<SourceGroup title="Skills" sources={sources} />)

    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText(/Python/)).toBeInTheDocument()
    expect(screen.getByText(/React/)).toBeInTheDocument()
  })

  it('should not render when sources array is empty', () => {
    const { container } = render(<SourceGroup title="Skills" sources={[]} />)

    expect(container.firstChild).toBeNull()
  })

  it('should display source with job_title property', () => {
    const sources = [
      { 
        node_type: 'Job', 
        node_id: 'j1', 
        properties: { job_title: 'Software Engineer' } 
      }
    ]

    render(<SourceGroup title="Jobs" sources={sources} />)

    expect(screen.getByText(/Software Engineer/)).toBeInTheDocument()
  })

  it('should display source with company_name property', () => {
    const sources = [
      { 
        node_type: 'Company', 
        node_id: 'c1', 
        properties: { company_name: 'Tech Corp' } 
      }
    ]

    render(<SourceGroup title="Companies" sources={sources} />)

    expect(screen.getByText(/Tech Corp/)).toBeInTheDocument()
  })

  it('should fallback to node_id if no name property', () => {
    const sources = [
      { node_type: 'Skill', node_id: 'unknown-skill', properties: {} }
    ]

    render(<SourceGroup title="Skills" sources={sources} />)

    expect(screen.getByText(/unknown-skill/)).toBeInTheDocument()
  })

  it('should render multiple sources with bullet points', () => {
    const sources = [
      { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } },
      { node_type: 'Skill', node_id: 's2', properties: { name: 'Java' } },
      { node_type: 'Skill', node_id: 's3', properties: { name: 'React' } }
    ]

    render(<SourceGroup title="Skills" sources={sources} />)

    const items = screen.getAllByText(/•/)
    expect(items).toHaveLength(3)
  })
})
