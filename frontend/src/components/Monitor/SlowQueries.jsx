import { AlertCircle, Clock, Database } from 'lucide-react';
import PropTypes from 'prop-types';

export default function SlowQueries({ queries, detailed = false }) {
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
      minute: '2-digit'
    });
  };

  const truncateQuery = (query, maxLength = detailed ? 200 : 100) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  };

  const getTimeColor = (ms) => {
    if (ms > 2000) return 'text-red-600 bg-red-50';
    if (ms > 1000) return 'text-orange-600 bg-orange-50';
    return 'text-yellow-600 bg-yellow-50';
  };

  if (!queries || queries.length === 0) {
    return (
      <div className="glass rounded-2xl p-8 border border-purple-100">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg">
            <AlertCircle className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-xl font-bold text-slate-800">Slow Queries</h2>
        </div>
        <div className="text-center py-8">
          <Database className="w-12 h-12 text-green-300 mx-auto mb-3" />
          <p className="text-slate-600">No slow queries detected</p>
          <p className="text-slate-400 text-sm mt-1">All queries are performing well! 🎉</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-6 border border-orange-100">
      {!detailed && (
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg">
            <AlertCircle className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-xl font-bold text-slate-800">Slow Queries</h2>
        </div>
      )}

      <div className="space-y-3">
        {queries.map((query, index) => (
          <div
            key={query.id || index}
            className="bg-white rounded-xl border border-orange-200 p-4 hover:shadow-lg transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              {/* Time Badge */}
              <div className={`px-3 py-2 rounded-lg font-bold ${getTimeColor(query.execution_time_ms)}`}>
                <Clock className="w-4 h-4 inline mb-1 mr-1" />
                {query.execution_time_ms?.toFixed(0)}ms
              </div>

              {/* Query Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getOperationColor(query.operation_type)}`}>
                    {query.operation_type}
                  </span>

                  {query.result_count !== null && query.result_count !== undefined && (
                    <span className="text-xs text-slate-500">
                      {query.result_count} results
                    </span>
                  )}

                  <span className="ml-auto text-xs text-slate-400">
                    {formatTimestamp(query.timestamp || query.created_at)}
                  </span>
                </div>

                <div className="font-mono text-sm text-slate-700 bg-slate-50 rounded-lg p-3 overflow-x-auto">
                  {truncateQuery(query.query_text)}
                </div>

                {detailed && query.source && (
                  <div className="mt-2 text-xs text-slate-500">
                    Source: <span className="font-medium">{query.source}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Performance Warning */}
            {query.execution_time_ms > 2000 && (
              <div className="mt-3 flex items-start gap-2 text-xs text-red-600 bg-red-50 rounded-lg p-3 border border-red-100">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Critical Performance Issue:</span> This query took over 2 seconds to execute. Consider optimizing the query or adding appropriate indexes.
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

SlowQueries.propTypes = {
  queries: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string,
    query_text: PropTypes.string.isRequired,
    operation_type: PropTypes.string.isRequired,
    execution_time_ms: PropTypes.number.isRequired,
    result_count: PropTypes.number,
    timestamp: PropTypes.string,
    created_at: PropTypes.string,
    source: PropTypes.string
  })),
  detailed: PropTypes.bool
};
