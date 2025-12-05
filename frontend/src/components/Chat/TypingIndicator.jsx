import { useState, useEffect } from 'react'
import { Brain, Sparkles, Clock } from 'lucide-react'
import PropTypes from 'prop-types'
import QueryProcessingView from './QueryProcessingView'
import ErrorBoundary from '../ErrorBoundary'

/**
 * TypingIndicator component - Beautiful "AI is thinking" animation
 * Shows animated brain icon with sparkles and pulsing dots
 *
 * @param {string} message - Loading message to display (default: "AI is thinking...")
 * @param {boolean} showElapsedTime - Whether to show elapsed time (default: false)
 * @param {string} sessionId - Session ID to track query processing
 */
const TypingIndicator = ({
  message = "AI is thinking...",
  showElapsedTime = false,
  sessionId = null
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  // Track elapsed time if showElapsedTime is enabled
  useEffect(() => {
    if (!showElapsedTime) return

    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1)
    }, 1000)

    return () => {
      clearInterval(interval)
      setElapsedSeconds(0)
    }
  }, [showElapsedTime])

  // Format elapsed time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex justify-start mb-4 animate-fade-in">
      <div className="max-w-[80%]">
        <div className="rounded-2xl px-5 py-4 shadow-lg" style={{
          background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1))',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(139, 92, 246, 0.2)'
        }}>
          <div className="flex items-center gap-3">
            {/* Animated Brain Icon */}
            <div className="relative">
              <div className="absolute inset-0 rounded-full animate-ping" style={{
                background: 'radial-gradient(circle, rgba(139, 92, 246, 0.4), transparent)',
                animationDuration: '1.5s'
              }}></div>
              <div className="relative w-10 h-10 rounded-full flex items-center justify-center" style={{
                background: 'linear-gradient(135deg, #8B5CF6, #3B82F6)',
                animation: 'float 2s ease-in-out infinite'
              }}>
                <Brain className="w-5 h-5 text-white" />
              </div>
              {/* Sparkle effect */}
              <Sparkles className="absolute -top-1 -right-1 w-4 h-4 text-yellow-400 animate-pulse" />
            </div>

            {/* Text and Dots */}
            <div className="flex-1">
              <p className="text-sm font-medium text-primary-700 mb-1">{message}</p>
              {showElapsedTime && elapsedSeconds > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-primary-600 mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{formatTime(elapsedSeconds)}</span>
                </div>
              )}
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full animate-bounce" style={{
                  background: 'linear-gradient(135deg, #8B5CF6, #7C3AED)',
                  animationDelay: '0ms',
                  animationDuration: '1s'
                }}></div>
                <div className="w-2.5 h-2.5 rounded-full animate-bounce" style={{
                  background: 'linear-gradient(135deg, #7C3AED, #6D28D9)',
                  animationDelay: '200ms',
                  animationDuration: '1s'
                }}></div>
                <div className="w-2.5 h-2.5 rounded-full animate-bounce" style={{
                  background: 'linear-gradient(135deg, #6D28D9, #3B82F6)',
                  animationDelay: '400ms',
                  animationDuration: '1s'
                }}></div>
              </div>
            </div>
          </div>

          {/* Shimmer effect overlay */}
          <div className="absolute inset-0 rounded-2xl overflow-hidden pointer-events-none">
            <div className="absolute inset-0 animate-shimmer" style={{
              background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 2s infinite'
            }}></div>
          </div>
        </div>

        {/* Query Processing View - Temporarily disabled for debugging */}
        {/* {sessionId && (
          <ErrorBoundary>
            <QueryProcessingView sessionId={sessionId} />
          </ErrorBoundary>
        )} */}
      </div>
    </div>
  )
}

TypingIndicator.propTypes = {
  message: PropTypes.string,
  showElapsedTime: PropTypes.bool,
  sessionId: PropTypes.string
}

export default TypingIndicator
