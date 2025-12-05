import { describe, it, expect } from 'vitest'
import { groupSourcesByType, formatSourceSummary, getSourceDisplayName } from './sources'
import { SourceNode } from '@/types/chat'

describe('sources utilities', () => {
  describe('groupSourcesByType', () => {
    it('should group sources by type correctly', () => {
      const sources: SourceNode[] = [
        { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } },
        { node_type: 'Job', node_id: 'j1', properties: { job_title: 'Engineer' } },
        { node_type: 'Skill', node_id: 's2', properties: { name: 'React' } },
        { node_type: 'Company', node_id: 'c1', properties: { company_name: 'Tech Corp' } }
      ]

      const grouped = groupSourcesByType(sources)

      expect(grouped.Skills).toHaveLength(2)
      expect(grouped.Jobs).toHaveLength(1)
      expect(grouped.Companies).toHaveLength(1)
    })

    it('should handle empty sources array', () => {
      const grouped = groupSourcesByType([])

      expect(grouped.Skills).toHaveLength(0)
      expect(grouped.Jobs).toHaveLength(0)
      expect(grouped.Companies).toHaveLength(0)
    })

    it('should handle sources with only one type', () => {
      const sources: SourceNode[] = [
        { node_type: 'Skill', node_id: 's1', properties: { name: 'Python' } },
        { node_type: 'Skill', node_id: 's2', properties: { name: 'Java' } }
      ]

      const grouped = groupSourcesByType(sources)

      expect(grouped.Skills).toHaveLength(2)
      expect(grouped.Jobs).toHaveLength(0)
      expect(grouped.Companies).toHaveLength(0)
    })
  })

  describe('formatSourceSummary', () => {
    it('should format summary with all source types', () => {
      const grouped = {
        Jobs: [{} as SourceNode, {} as SourceNode],
        Skills: [{} as SourceNode],
        Companies: [{} as SourceNode]
      }

      const summary = formatSourceSummary(grouped)
      expect(summary).toBe('Based on 2 jobs, 1 skill, and 1 company')
    })

    it('should handle singular correctly', () => {
      const grouped = {
        Jobs: [{} as SourceNode],
        Skills: [{} as SourceNode],
        Companies: [{} as SourceNode]
      }

      const summary = formatSourceSummary(grouped)
      expect(summary).toBe('Based on 1 job, 1 skill, and 1 company')
    })

    it('should handle plural correctly', () => {
      const grouped = {
        Jobs: [{} as SourceNode, {} as SourceNode],
        Skills: [{} as SourceNode, {} as SourceNode, {} as SourceNode],
        Companies: [{} as SourceNode, {} as SourceNode]
      }

      const summary = formatSourceSummary(grouped)
      expect(summary).toBe('Based on 2 jobs, 3 skills, and 2 companies')
    })

    it('should handle only jobs', () => {
      const grouped = {
        Jobs: [{} as SourceNode, {} as SourceNode],
        Skills: [],
        Companies: []
      }

      const summary = formatSourceSummary(grouped)
      expect(summary).toBe('Based on 2 jobs')
    })

    it('should handle empty sources', () => {
      const grouped = {
        Jobs: [],
        Skills: [],
        Companies: []
      }

      const summary = formatSourceSummary(grouped)
      expect(summary).toBe('No sources')
    })
  })

  describe('getSourceDisplayName', () => {
    it('should extract name from properties', () => {
      const source: SourceNode = {
        node_type: 'Skill',
        node_id: 's1',
        properties: { name: 'Python' }
      }

      expect(getSourceDisplayName(source)).toBe('Python')
    })

    it('should extract job_title from properties', () => {
      const source: SourceNode = {
        node_type: 'Job',
        node_id: 'j1',
        properties: { job_title: 'Software Engineer' }
      }

      expect(getSourceDisplayName(source)).toBe('Software Engineer')
    })

    it('should extract company_name from properties', () => {
      const source: SourceNode = {
        node_type: 'Company',
        node_id: 'c1',
        properties: { company_name: 'Tech Corp' }
      }

      expect(getSourceDisplayName(source)).toBe('Tech Corp')
    })

    it('should fallback to node_id if no name property', () => {
      const source: SourceNode = {
        node_type: 'Skill',
        node_id: 's1',
        properties: {}
      }

      expect(getSourceDisplayName(source)).toBe('s1')
    })
  })
})
