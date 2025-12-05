import { SourceNode } from '@/types/chat'

/**
 * Grouped sources by node type
 */
export interface GroupedSources {
  Skills: SourceNode[]
  Jobs: SourceNode[]
  Companies: SourceNode[]
}

/**
 * Group source nodes by their type
 * @param sources - Array of source nodes from query response
 * @returns Sources grouped by type (Skills, Jobs, Companies)
 */
export function groupSourcesByType(sources: SourceNode[]): GroupedSources {
  return sources.reduce(
    (acc, source) => {
      const type = source.node_type
      if (type === 'Skill') acc.Skills.push(source)
      else if (type === 'Job') acc.Jobs.push(source)
      else if (type === 'Company') acc.Companies.push(source)
      return acc
    },
    { Skills: [], Jobs: [], Companies: [] } as GroupedSources
  )
}

/**
 * Format source summary for display
 * Example: "Based on 5 jobs, 3 skills, and 2 companies"
 * @param grouped - Grouped sources by type
 * @returns Formatted summary string
 */
export function formatSourceSummary(grouped: GroupedSources): string {
  const parts: string[] = []
  
  if (grouped.Jobs.length > 0) {
    parts.push(`${grouped.Jobs.length} job${grouped.Jobs.length > 1 ? 's' : ''}`)
  }
  if (grouped.Skills.length > 0) {
    parts.push(`${grouped.Skills.length} skill${grouped.Skills.length > 1 ? 's' : ''}`)
  }
  if (grouped.Companies.length > 0) {
    parts.push(
      `${grouped.Companies.length} ${grouped.Companies.length > 1 ? 'companies' : 'company'}`
    )
  }

  if (parts.length === 0) return 'No sources'
  if (parts.length === 1) return `Based on ${parts[0]}`
  if (parts.length === 2) return `Based on ${parts[0]} and ${parts[1]}`
  
  // Oxford comma for 3+ items
  const lastPart = parts.pop()
  return `Based on ${parts.join(', ')}, and ${lastPart}`
}

/**
 * Extract display name from source node properties
 * @param source - Source node
 * @returns Display name for the source
 */
export function getSourceDisplayName(source: SourceNode): string {
  return (
    source.properties.name ||
    source.properties.job_title ||
    source.properties.company_name ||
    source.node_id
  )
}
