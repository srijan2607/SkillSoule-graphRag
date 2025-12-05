import { useState } from 'react';
import PropTypes from 'prop-types';
import { TrendingUp, ChevronDown, ChevronUp, BarChart3, Clock, Target } from 'lucide-react';

/**
 * EnhancedResponse - Parse and display backend responses with Graph Insights highlighted
 * Handles the new response format with sections: Direct Answer, Key Insights, Graph Insights, etc.
 */
const EnhancedResponse = ({ content, metadata }) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  // Parse response sections
  const parseSections = () => {
    const sections = {
      directAnswer: '',
      keyInsights: [],
      graphInsights: [],
      supportingData: [],
      nextSteps: [],
      technicalDetails: '',
      hasStructuredFormat: false,
    };

    // Check if response uses the new structured format
    if (content.includes('**Direct answer**') || content.includes('**Key insights**') || content.includes('**Direct Answer**')) {
      sections.hasStructuredFormat = true;

      // Extract technical details first and remove from content
      let mainContent = content;
      const detailsMatch = content.match(/<details>[\s\S]*?<\/details>/);
      if (detailsMatch) {
        sections.technicalDetails = detailsMatch[0]
          .replace(/<details>/g, '')
          .replace(/<\/details>/g, '')
          .replace(/<summary>.*?<\/summary>/g, '')
          .trim();
        mainContent = content.replace(detailsMatch[0], '').trim();
      }

      // Split by section headers (bold text that appears at the start of a line)
      const sectionRegex = /\n\*\*([^*]+)\*\*\s*\n/g;
      const sectionHeaders = [];
      const sectionContents = [];
      
      let lastIndex = 0;
      let match;
      
      while ((match = sectionRegex.exec(mainContent)) !== null) {
        const header = match[1].toLowerCase().trim();
        const contentBefore = mainContent.substring(lastIndex, match.index).trim();
        
        if (contentBefore && sectionHeaders.length > 0) {
          sectionContents.push(contentBefore);
        }
        
        sectionHeaders.push(header);
        lastIndex = match.index + match[0].length;
      }
      
      // Add the last section's content
      if (lastIndex < mainContent.length) {
        sectionContents.push(mainContent.substring(lastIndex).trim());
      }

      // Map sections to their content
      for (let i = 0; i < sectionHeaders.length; i++) {
        const header = sectionHeaders[i];
        const text = sectionContents[i] || '';
        
        if (header === 'direct answer') {
          sections.directAnswer = text;
        } else if (header === 'key insights') {
          sections.keyInsights = text
            .split('\n')
            .filter(line => line.trim().startsWith('-') || line.trim().startsWith('•'))
            .map(line => line.replace(/^[-•]\s*/, '').trim())
            .filter(Boolean);
        } else if (header === 'graph insights') {
          sections.graphInsights = text
            .split('\n')
            .filter(line => line.trim().startsWith('-') || line.trim().startsWith('•') || line.includes('Graph analysis'))
            .map(line => line.replace(/^[-•]\s*/, '').trim())
            .filter(Boolean);
        } else if (header === 'supporting data') {
          sections.supportingData = text
            .split('\n')
            .filter(line => line.trim().startsWith('-') || line.trim().startsWith('•'))
            .map(line => line.replace(/^[-•]\s*/, '').trim())
            .filter(Boolean);
        } else if (header === 'next steps') {
          // Parse numbered list
          sections.nextSteps = text
            .split(/\n\d+\.\s+/)
            .map(line => line.trim())
            .filter(Boolean);
        }
      }
    }

    return sections;
  };

  const sections = parseSections();

  // Render metadata badges
  const renderMetadataBadges = () => {
    if (!metadata) return null;

    return (
      <div className="flex flex-wrap gap-2 mt-4">
        {metadata.intent && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
            <Target className="w-3.5 h-3.5" />
            {metadata.intent}
          </span>
        )}
        {metadata.graph_nodes_count !== undefined && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
            <BarChart3 className="w-3.5 h-3.5" />
            {metadata.graph_nodes_count} nodes
          </span>
        )}
        {metadata.graph_relationships_count !== undefined && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
            🔗 {metadata.graph_relationships_count} relationships
          </span>
        )}
      </div>
    );
  };

  // If not structured format, return plain text
  if (!sections.hasStructuredFormat) {
    return (
      <div className="space-y-4">
        <p className="text-[15px] leading-relaxed text-gray-800 whitespace-pre-wrap break-words">
          {content}
        </p>
        {metadata && renderMetadataBadges()}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Direct Answer */}
      {sections.directAnswer && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Direct Answer</h4>
          <p className="text-[15px] leading-relaxed text-gray-800">
            {sections.directAnswer}
          </p>
        </div>
      )}

      {/* Key Insights */}
      {sections.keyInsights.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Key Insights</h4>
          <ul className="space-y-2">
            {sections.keyInsights.map((insight, idx) => (
              <li key={idx} className="flex gap-2 text-[15px] text-gray-800">
                <span className="text-purple-600 font-bold">•</span>
                <span className="flex-1" dangerouslySetInnerHTML={{ __html: formatText(insight) }} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Graph Insights - HIGHLIGHTED */}
      {sections.graphInsights.length > 0 && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-blue-600 rounded-r-lg p-4 my-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-white" />
            </div>
            <h4 className="text-sm font-semibold text-blue-900">Graph Insights</h4>
          </div>
          <ul className="space-y-2.5">
            {sections.graphInsights.map((insight, idx) => (
              <li key={idx} className="flex gap-2 text-[15px] text-blue-900">
                <span className="text-blue-600 font-bold mt-1">•</span>
                <span className="flex-1" dangerouslySetInnerHTML={{ __html: formatText(insight) }} />
              </li>
            ))}
          </ul>

          {/* Graph Statistics Badges */}
          {renderMetadataBadges()}
        </div>
      )}

      {/* Supporting Data */}
      {sections.supportingData.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Supporting Data</h4>
          <ul className="space-y-2">
            {sections.supportingData.map((data, idx) => (
              <li key={idx} className="flex gap-2 text-[15px] text-gray-700">
                <span className="text-gray-400">•</span>
                <span className="flex-1" dangerouslySetInnerHTML={{ __html: formatText(data) }} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next Steps */}
      {sections.nextSteps.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-green-900 mb-2">Next Steps</h4>
          <ol className="space-y-2">
            {sections.nextSteps.map((step, idx) => (
              <li key={idx} className="flex gap-2 text-[15px] text-green-900">
                <span className="font-semibold min-w-[20px]">{idx + 1}.</span>
                <span className="flex-1">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Technical Details - Collapsible */}
      {sections.technicalDetails && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between text-sm font-medium text-gray-700"
          >
            <span className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              📊 Technical Details
            </span>
            {showTechnicalDetails ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
          {showTechnicalDetails && (
            <div className="px-4 py-3 bg-white border-t border-gray-200">
              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                {sections.technicalDetails}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Performance Metrics (if available) */}
      {metadata?.metrics?.stage_timings && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h4 className="text-xs font-semibold text-gray-600 mb-2">Pipeline Performance</h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Object.entries(metadata.metrics.stage_timings).map(([stage, time]) => (
              <div key={stage} className="text-xs">
                <span className="text-gray-500">{formatStageName(stage)}:</span>{' '}
                <span className="font-semibold text-gray-700">{time?.toFixed(0)}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Helper function to format text with bold markers
function formatText(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

// Helper function to format stage names
function formatStageName(stage) {
  return stage
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

EnhancedResponse.propTypes = {
  content: PropTypes.string.isRequired,
  metadata: PropTypes.shape({
    intent: PropTypes.string,
    graph_nodes_count: PropTypes.number,
    graph_relationships_count: PropTypes.number,
    metrics: PropTypes.shape({
      stage_timings: PropTypes.object,
    }),
  }),
};

export default EnhancedResponse;
