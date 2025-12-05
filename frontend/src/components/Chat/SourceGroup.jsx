import PropTypes from 'prop-types'
import { getSourceDisplayName } from '@/utils/sources'

/**
 * SourceGroup component - displays a group of sources by type
 * @param {Object} props - Component props
 * @param {string} props.title - Group title (e.g., "Skills", "Jobs")
 * @param {Array} props.sources - Array of source nodes
 */
const SourceGroup = ({ title, sources }) => {
  if (sources.length === 0) return null

  return (
    <div className="source-group mb-2">
      <h4 className="text-xs font-semibold text-gray-700 mb-1">{title}</h4>
      <div className="space-y-1">
        {sources.map((source, idx) => (
          <div
            key={`${source.node_id}-${idx}`}
            className="text-xs text-gray-600 pl-2"
          >
            • {getSourceDisplayName(source)}
          </div>
        ))}
      </div>
    </div>
  )
}

SourceGroup.propTypes = {
  title: PropTypes.string.isRequired,
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      node_type: PropTypes.string.isRequired,
      node_id: PropTypes.string.isRequired,
      properties: PropTypes.object.isRequired
    })
  ).isRequired
}

export default SourceGroup
