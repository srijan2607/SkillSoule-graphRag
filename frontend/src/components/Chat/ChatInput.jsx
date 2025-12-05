import { useState } from 'react'
import PropTypes from 'prop-types'
import { Send, Sparkles } from 'lucide-react'

/**
 * ChatInput component - Sleek unified input bar with integrated send button
 * Supports Enter to send, Shift+Enter for new line
 */
const ChatInput = ({ onSend, disabled = false }) => {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (message.trim() && !disabled) {
      onSend(message.trim())
      setMessage('')
    }
  }

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
    // Allow Shift+Enter for new line (default textarea behavior)
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      {/* Unified Input Container */}
      <div 
        className="relative rounded-2xl transition-all duration-300 shadow-lg"
        style={{
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.98))',
          backdropFilter: 'blur(20px)',
          border: isFocused
            ? '2px solid #8B5CF6'
            : '2px solid rgba(139, 92, 246, 0.15)',
          boxShadow: isFocused
            ? '0 8px 32px rgba(139, 92, 246, 0.25), 0 0 0 4px rgba(139, 92, 246, 0.08)'
            : '0 4px 20px rgba(0, 0, 0, 0.08)'
        }}
      >
        {/* Sparkle Icon - Left Side */}
        <div className="absolute left-5 top-1/2 -translate-y-1/2 pointer-events-none">
          <Sparkles 
            className={`w-5 h-5 transition-all duration-300 ${
              isFocused ? 'text-primary-500' : 'text-gray-400'
            }`}
            style={{
              animation: isFocused ? 'pulse 2s ease-in-out infinite' : 'none'
            }}
          />
        </div>

        {/* Textarea */}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          disabled={disabled}
          placeholder="Ask me anything about careers, skills, or jobs..."
          rows={1}
          data-testid="chat-input"
          className="w-full resize-none bg-transparent px-14 py-4 text-[15px] text-gray-900 placeholder-gray-400 focus:outline-none disabled:cursor-not-allowed transition-colors duration-200"
          style={{
            maxHeight: '120px',
            minHeight: '56px'
          }}
          aria-label="Message input"
        />

        {/* Send Button - Right Side - Integrated */}
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          data-testid="chat-send"
          className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex items-center justify-center w-12 h-12 rounded-xl text-white focus:outline-none disabled:cursor-not-allowed transition-all duration-300 hover:scale-110 active:scale-95"
          style={{
            background: disabled || !message.trim()
              ? 'linear-gradient(135deg, #D1D5DB, #9CA3AF)'
              : 'linear-gradient(135deg, #8B5CF6, #7C3AED, #6D28D9)',
            boxShadow: !disabled && message.trim()
              ? '0 4px 16px rgba(139, 92, 246, 0.4)'
              : 'none',
            opacity: disabled || !message.trim() ? 0.5 : 1
          }}
          aria-label="Send message"
        >
          <Send className={`w-5 h-5 transition-transform duration-300 ${
            !disabled && message.trim() ? 'scale-100' : 'scale-90'
          }`} />
        </button>

        {/* Glow Effect on Focus */}
        {isFocused && (
          <div 
            className="absolute -inset-[2px] rounded-2xl pointer-events-none -z-10"
            style={{
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1))',
              filter: 'blur(8px)'
            }}
          />
        )}
      </div>

      {/* Helper Text */}
      <p className="text-xs text-gray-500 mt-2 text-center">
        Press <kbd className="px-1.5 py-0.5 rounded bg-gray-100 border border-gray-300 text-gray-700 font-mono text-[10px]">Enter</kbd> to send, 
        <kbd className="px-1.5 py-0.5 ml-1 rounded bg-gray-100 border border-gray-300 text-gray-700 font-mono text-[10px]">Shift + Enter</kbd> for new line
      </p>
    </form>
  )
}

ChatInput.propTypes = {
  onSend: PropTypes.func.isRequired,
  disabled: PropTypes.bool
}

export default ChatInput
