import { useState } from 'react';
import { Clock, CheckCircle, XCircle, ChevronDown, ChevronUp, Code } from 'lucide-react';
import PropTypes from 'prop-types';

export default function QueryList({ queries }) {
  const [expandedQuery, setExpandedQuery] = useState(null);

  const getStatusColor = (status) => {
    return status === 'success' 
      ? 'text-green-600 bg-green-50' 
      : 'text-red-600 bg-red-50';
  };

  const getOperationColor = (type) => {
    const colors = {
      'READ': 'text-blue-600 bg-blue-50',
      'WRITE': 'text-purple-600 bg-purple-50',
      'VECTOR_SEARCH': 'text-pink-600 bg-pink-50',
      'GRAPH_TRAVERSAL': 'text-indigo-600 bg-indigo-50',
      'OTHER': 'text-slate-600 bg-slate-50'
    };
    return colors[type] || colors['OTHER'];
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const truncateQuery = (query, maxLength = 100) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  };

  if (!queries || queries.length === 0) {
    return (
      <div className="glass rounded-2xl p-12 border border-purple-100 text-center">
        <Database className="w-16 h-16 text-slate-300 mx-auto mb-4" />
        <p className="text-slate-600 text-lg">No queries found</p>
        <p className="text-slate-400 text-sm mt-2">Queries will appear here as they are executed</p>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-6 border border-purple-100">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
          <Code className="w-5 h-5 text-white" />
        </div>
        <h2 className="text-xl font-bold text-slate-800">Query Logs</h2>
        <span className="ml-auto text-sm text-slate-500">{queries.length} queries</span>
      </div>

      <div className="space-y-3">
        {queries.map((query, index) => {
          const isExpanded = expandedQuery === query.id;
          
          return (
            <div
              key={query.id || index}
              className="bg-white rounded-xl border border-slate-200 hover:border-purple-200 transition-all duration-200"
            >
              <div
                className="p-4 cursor-pointer"
                onClick={() => setExpandedQuery(isExpanded ? null : query.id)}
              >
                <div className="flex items-start gap-4">
                  {/* Status Icon */}
                  <div className={`p-2 rounded-lg ${getStatusColor(query.status)}`}>
                    {query.status === 'success' ? (
                      <CheckCircle className="w-5 h-5" />
                    ) : (
                      <XCircle className="w-5 h-5" />
                    )}
                  </div>

                  {/* Query Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getOperationColor(query.operation_type)}`}>
                        {query.operation_type}
                      </span>
                      
                      <div className="flex items-center gap-1 text-sm text-slate-600">
                        <Clock className="w-4 h-4" />
                        <span className="font-medium">{query.execution_time_ms?.toFixed(1)}ms</span>
                      </div>

                      {query.result_count !== null && query.result_count !== undefined && (
                        <span className="text-sm text-slate-500">
                          {query.result_count} results
                        </span>
                      )}

                      <span className="ml-auto text-xs text-slate-400">
                        {formatTimestamp(query.timestamp || query.created_at)}
                      </span>
                    </div>

                    <div className="font-mono text-sm text-slate-700 bg-slate-50 rounded-lg p-3 overflow-x-auto">
                      {isExpanded ? query.query_text : truncateQuery(query.query_text)}
                    </div>

                    {query.source && (
                      <div className="mt-2 text-xs text-slate-500">
                        Source: <span className="font-medium">{query.source}</span>
                      </div>
                    )}
                  </div>

                  {/* Expand Icon */}
                  <div className="flex-shrink-0">
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
                    {query.parameters && Object.keys(query.parameters).length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Parameters</h4>
                        <pre className="font-mono text-xs bg-slate-50 rounded-lg p-3 overflow-x-auto">
                          {JSON.stringify(query.parameters, null, 2)}
                        </pre>
                      </div>
                    )}

                    {query.error_message && (
                      <div>
                        <h4 className="text-sm font-semibold text-red-700 mb-2">Error</h4>
                        <div className="text-sm text-red-600 bg-red-50 rounded-lg p-3">
                          {query.error_message}
                        </div>
                      </div>
                    )}

                    {query.metadata && Object.keys(query.metadata).length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-2">Metadata</h4>
                        <pre className="font-mono text-xs bg-slate-50 rounded-lg p-3 overflow-x-auto">
                          {JSON.stringify(query.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

QueryList.propTypes = {
  queries: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string,
    query_text: PropTypes.string.isRequired,
    operation_type: PropTypes.string.isRequired,
    execution_time_ms: PropTypes.number,
    result_count: PropTypes.number,
    status: PropTypes.string.isRequired,
    timestamp: PropTypes.string,
    created_at: PropTypes.string,
    source: PropTypes.string,
    parameters: PropTypes.object,
    error_message: PropTypes.string,
    metadata: PropTypes.object
  })).isRequired
};
