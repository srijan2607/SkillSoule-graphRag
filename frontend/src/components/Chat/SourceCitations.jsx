import { useState } from 'react'
import PropTypes from 'prop-types'
import SourceGroup from './SourceGroup'
import { groupSourcesByType, formatSourceSummary } from '@/utils/sources'

/**
 * SourceCitations component - displays expandable source citations
 * Shows summary count by default, expands to show detailed source list
 * @param {Object} props - Component props
 * @param {Array} props.sources - Array of source nodes from query response
 */
const SourceCitations = ({ sources }) => {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  const grouped = groupSourcesByType(sources)
  const summary = formatSourceSummary(grouped)

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      toggleExpanded()
    }
  }

  return (
    <div className="source-citations mt-3 pt-3 border-t border-gray-200">
      <button
        onClick={toggleExpanded}
        onKeyDown={handleKeyDown}
        className="flex items-center text-sm text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded transition-colors"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? 'Collapse sources' : 'Expand sources'}
      >
        <svg
          className={`w-4 h-4 mr-2 transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path d="M19 9l-7 7-7-7" />
        </svg>
        <span className="font-medium">{summary}</span>
      </button>

      {isExpanded && (
        <div
          className="mt-3 space-y-2 animate-fadeIn"
          role="region"
          aria-label="Source details"
        >
          {grouped.Skills.length > 0 && (
            <SourceGroup title="Skills" sources={grouped.Skills} />
          )}
          {grouped.Jobs.length > 0 && (
            <SourceGroup title="Jobs" sources={grouped.Jobs} />
          )}
          {grouped.Companies.length > 0 && (
            <SourceGroup title="Companies" sources={grouped.Companies} />
          )}
        </div>
      )}
    </div>
  )
}

SourceCitations.propTypes = {
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      node_type: PropTypes.string.isRequired,
      node_id: PropTypes.string.isRequired,
      properties: PropTypes.object.isRequired
    })
  )
}

export default SourceCitations
