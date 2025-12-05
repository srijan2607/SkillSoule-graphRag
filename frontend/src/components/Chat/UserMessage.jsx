import PropTypes from 'prop-types'
import { User } from 'lucide-react'

/**
 * UserMessage component - Beautiful purple gradient user messages
 * Right-aligned with avatar and smooth animations
 */
const UserMessage = ({ content, timestamp }) => {
  const formatTime = (date) => {
    if (!date) return ''
    return new Date(date).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  return (
    <div className="flex justify-end mb-4 animate-slide-up">
      <div className="max-w-[75%] flex items-start gap-3">
        <div className="flex-1">
          <div className="rounded-2xl px-5 py-3 shadow-lg transition-all duration-300 hover:shadow-xl" style={{
            background: 'linear-gradient(135deg, #8B5CF6, #7C3AED, #6D28D9)',
            animation: 'scale-in 0.3s ease-out'
          }}>
            <p className="text-[15px] leading-relaxed text-white whitespace-pre-wrap break-words">
              {content}
            </p>
          </div>
          {timestamp && (
            <p className="text-xs text-gray-500 mt-1.5 text-right">
              {formatTime(timestamp)}
            </p>
          )}
        </div>
        {/* User Avatar */}
        <div className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 shadow-md" style={{
          background: 'linear-gradient(135deg, #8B5CF6, #6D28D9)'
        }}>
          <User className="w-5 h-5 text-white" />
        </div>
      </div>
    </div>
  )
}

UserMessage.propTypes = {
  content: PropTypes.string.isRequired,
  timestamp: PropTypes.oneOfType([
    PropTypes.instanceOf(Date),
    PropTypes.string
  ])
}

export default UserMessage
