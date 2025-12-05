import { useState } from 'react';
import PropTypes from 'prop-types';
import { AlertTriangle, Copy, Check, X } from 'lucide-react';

/**
 * ErrorResponseModal - Display pipeline/LLM/unexpected errors in a modal
 * Shows detailed error information with debug instructions
 */
const ErrorResponseModal = ({ isOpen, onClose, errorMessage, metadata }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(errorMessage);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Determine error type
  const getErrorType = () => {
    if (metadata?.pipeline_errors_detected?.length > 0) return 'Pipeline Error';
    if (errorMessage.includes('LLM GENERATION ERROR')) return 'LLM Generation Error';
    return 'Unexpected Error';
  };

  // Parse error sections from the formatted error message
  const parseErrorMessage = () => {
    const lines = errorMessage.split('\n');
    const sections = {
      title: '',
      description: '',
      errorDetails: null,
      debugInstructions: [],
      commonCauses: [],
    };

    let currentSection = '';
    for (const line of lines) {
      if (line.includes('⚠️')) {
        sections.title = line.replace('⚠️', '').trim();
      } else if (line.startsWith('Error Details:')) {
        sections.errorDetails = line.replace('Error Details:', '').trim();
        currentSection = 'errorDetails';
      } else if (line.includes('🔧 DEBUG INSTRUCTIONS:')) {
        currentSection = 'debugInstructions';
      } else if (line.startsWith('Common causes:')) {
        currentSection = 'commonCauses';
      } else if (line.trim() && currentSection === 'debugInstructions' && /^\d+\./.test(line.trim())) {
        sections.debugInstructions.push(line.replace(/^\d+\.\s*/, '').trim());
      } else if (line.trim() && currentSection === 'commonCauses' && line.trim().startsWith('-')) {
        sections.commonCauses.push(line.replace(/^-\s*/, '').trim());
      } else if (!currentSection && line.trim() && !line.includes('❌')) {
        sections.description += line.trim() + ' ';
      }
    }

    return sections;
  };

  const sections = parseErrorMessage();
  const errorType = getErrorType();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] overflow-y-auto"
        style={{
          animation: 'scale-in 0.3s ease-out',
        }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-red-200 px-6 py-4 flex items-start justify-between rounded-t-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-red-900">
                {sections.title || 'Query Processing Error'}
              </h2>
              <p className="text-sm text-gray-600 mt-0.5">
                Error Type: {errorType}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Description */}
          {sections.description && (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r">
              <p className="text-red-900 text-sm leading-relaxed">
                {sections.description}
              </p>
            </div>
          )}

          {/* Pipeline Errors */}
          {metadata?.pipeline_errors_detected && metadata.pipeline_errors_detected.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Failed Pipeline Stages:</h3>
              <div className="space-y-2">
                {metadata.pipeline_errors_detected.map((error, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-100 border border-gray-300 rounded-lg p-3 text-sm font-mono"
                  >
                    <span className="text-red-600">❌</span> {error}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Details */}
          {sections.errorDetails && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Error Details:</h3>
              <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto">
                <code className="text-sm">{sections.errorDetails}</code>
              </div>
            </div>
          )}

          {/* Debug Instructions */}
          {sections.debugInstructions.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                🔧 Debug Instructions:
              </h3>
              <ol className="space-y-2">
                {sections.debugInstructions.map((instruction, idx) => (
                  <li key={idx} className="flex gap-3 text-sm text-gray-700">
                    <span className="font-semibold text-primary-600 min-w-[20px]">
                      {idx + 1}.
                    </span>
                    <span className="flex-1">{instruction}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Common Causes */}
          {sections.commonCauses.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Common Causes:</h3>
              <ul className="space-y-2">
                {sections.commonCauses.map((cause, idx) => (
                  <li key={idx} className="text-sm text-gray-700 flex gap-2">
                    <span className="text-primary-600">•</span>
                    <span className="flex-1">{cause}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex gap-3 justify-end rounded-b-2xl">
          <button
            onClick={handleCopy}
            className="px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-green-600">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                <span>Copy for AI Agent</span>
              </>
            )}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white transition-colors text-sm font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

ErrorResponseModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  errorMessage: PropTypes.string.isRequired,
  metadata: PropTypes.shape({
    pipeline_errors_detected: PropTypes.arrayOf(PropTypes.string),
    response_generation_error: PropTypes.string,
    response_generation_failed: PropTypes.bool,
    response_generation_skipped: PropTypes.bool,
  }),
};

export default ErrorResponseModal;
