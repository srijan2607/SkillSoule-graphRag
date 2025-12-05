import PropTypes from 'prop-types'
import { Trash2 } from 'lucide-react'

/**
 * ClearChatButton component - Beautiful white button on purple header
 *
 * Displays a button to clear all chat messages with confirmation dialog.
 * Disabled when there are no messages to clear.
 *
 * @param {Function} onClear - Callback function to clear messages
 * @param {boolean} disabled - Whether the button should be disabled
 */
const ClearChatButton = ({ onClear, disabled = false }) => {
  const handleClick = () => {
    if (window.confirm('Are you sure you want to clear all messages? This cannot be undone.')) {
      onClear()
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
      style={{
        background: disabled 
          ? 'rgba(255, 255, 255, 0.1)' 
          : 'rgba(255, 255, 255, 0.2)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255, 255, 255, 0.3)',
        color: 'white'
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.target.style.background = 'rgba(255, 255, 255, 0.3)'
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled) {
          e.target.style.background = 'rgba(255, 255, 255, 0.2)'
        }
      }}
      title="Clear chat history"
      aria-label="Clear chat history"
    >
      <Trash2 className="w-4 h-4 mr-2" />
      Clear Chat
    </button>
  )
}

ClearChatButton.propTypes = {
  onClear: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}

export default ClearChatButton
