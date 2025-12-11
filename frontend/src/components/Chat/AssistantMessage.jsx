import PropTypes from 'prop-types'
import { Bot, Sparkles } from 'lucide-react'
import SourceCitations from './SourceCitations'
import EnhancedResponse from './EnhancedResponse'
import React, { lazy, Suspense } from 'react'

// Lazy load NetworkInsightsPanel
const NetworkInsightsPanel = lazy(() => import('./NetworkInsightsPanel'))

/**
 * AssistantMessage component - Beautiful AI assistant messages
 * Left-aligned with bot avatar and glassmorphism effect
 * Now displays enhanced responses with Graph Insights
 */
const AssistantMessage = ({ content, timestamp, sources, metadata }) => {
  const formatTime = (date) => {
    if (!date) return ''
    return new Date(date).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  return (
    <div className="flex justify-start mb-4 animate-slide-up">
      <div className="max-w-[75%] flex items-start gap-3">
        {/* AI Avatar */}
        <div className="relative w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg" style={{
          background: 'linear-gradient(135deg, #3B82F6, #2563EB)'
        }}>
          <Bot className="w-5 h-5 text-white" />
          <Sparkles className="absolute -top-1 -right-1 w-3.5 h-3.5 text-yellow-400 animate-pulse" />
        </div>

        <div className="flex-1">
          <div className="rounded-2xl px-5 py-3.5 shadow-lg transition-all duration-300 hover:shadow-xl" style={{
            background: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(139, 92, 246, 0.15)',
            animation: 'scale-in 0.3s ease-out'
          }}>
            {/* Enhanced Response with Graph Insights */}
            <EnhancedResponse content={content} metadata={metadata} />

            {/* Network Insights Panel */}
            {metadata?.network_insights && (
              <Suspense fallback={<div className="mt-4 h-32 bg-gray-50 rounded-xl animate-pulse" />}>
                <NetworkInsightsPanel insights={metadata.network_insights} />
              </Suspense>
            )}
            
            {/* Source Citations */}
            <SourceCitations sources={sources} />
          </div>
          {timestamp && (
            <p className="text-xs text-gray-500 mt-1.5">
              {formatTime(timestamp)}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

AssistantMessage.propTypes = {
  content: PropTypes.string.isRequired,
  timestamp: PropTypes.oneOfType([
    PropTypes.instanceOf(Date),
    PropTypes.string
  ]),
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      node_type: PropTypes.string.isRequired,
      node_id: PropTypes.string.isRequired,
      properties: PropTypes.object
    })
  ),
  metadata: PropTypes.shape({
    intent: PropTypes.string,
    graph_nodes_count: PropTypes.number,
    graph_relationships_count: PropTypes.number,
    metrics: PropTypes.object,
    network_insights: PropTypes.shape({
      skill_paths: PropTypes.array,
      similar_jobs: PropTypes.array,
      top_skills: PropTypes.array
    })
  })
}

export default AssistantMessage
