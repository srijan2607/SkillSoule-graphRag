import { Zap, Radio, CheckCircle, XCircle, Clock } from 'lucide-react';
import PropTypes from 'prop-types';

export default function LiveQueries({ queries }) {
  const getStatusColor = (status) => {
    return status === 'success'
      ? 'text-green-600 bg-green-50 border-green-200'
      : 'text-red-600 bg-red-50 border-red-200';
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

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  const truncateQuery = (query, maxLength = 120) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  };

  return (
    <div className="space-y-6">
      {/* Live Status Banner */}
      <div className="glass rounded-2xl p-6 border border-green-200 bg-gradient-to-r from-green-50 to-emerald-50">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Radio className="w-6 h-6 text-green-600" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-800">Live Query Stream</h2>
            <p className="text-sm text-slate-600 mt-1">
              Monitoring queries in real-time • {queries.length} queries captured
            </p>
          </div>
        </div>
      </div>

      {/* Live Queries List */}
      <div className="glass rounded-2xl p-6 border border-purple-100">
        {queries.length === 0 ? (
          <div className="text-center py-12">
            <Zap className="w-16 h-16 text-slate-300 mx-auto mb-4 animate-pulse" />
            <p className="text-slate-600 text-lg font-medium">Waiting for queries...</p>
            <p className="text-slate-400 text-sm mt-2">New queries will appear here in real-time</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
            {queries.map((query, index) => (
              <div
                key={`${query.timestamp}-${index}`}
                className="bg-white rounded-xl border border-slate-200 p-4 animate-slide-up shadow-sm hover:shadow-md transition-all duration-200"
                style={{ animationDelay: '0ms' }}
              >
                <div className="flex items-start gap-3">
                  {/* Status Indicator */}
                  <div className={`p-2 rounded-lg border ${getStatusColor(query.status)}`}>
                    {query.status === 'success' ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <XCircle className="w-4 h-4" />
                    )}
                  </div>

                  {/* Query Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getOperationColor(query.operation_type)}`}>
                        {query.operation_type}
                      </span>

                      <div className="flex items-center gap-1 text-sm text-slate-600">
                        <Clock className="w-3.5 h-3.5" />
                        <span className="font-medium">{query.execution_time_ms?.toFixed(1)}ms</span>
                      </div>

                      {query.result_count !== null && query.result_count !== undefined && (
                        <span className="text-xs text-slate-500">
                          {query.result_count} results
                        </span>
                      )}

                      <span className="ml-auto text-xs text-slate-400 font-mono">
                        {formatTime(query.timestamp)}
                      </span>
                    </div>

                    <div className="font-mono text-xs text-slate-700 bg-slate-50 rounded-lg p-3 overflow-x-auto">
                      {truncateQuery(query.query_text)}
                    </div>

                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                      {query.source && (
                        <span>
                          Source: <span className="font-medium">{query.source}</span>
                        </span>
                      )}
                      {query.session_id && (
                        <span>
                          Session: <span className="font-mono font-medium">{query.session_id.slice(0, 8)}</span>
                        </span>
                      )}
                    </div>

                    {query.error_message && (
                      <div className="mt-2 text-xs text-red-600 bg-red-50 rounded-lg p-2 border border-red-100">
                        {query.error_message}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

LiveQueries.propTypes = {
  queries: PropTypes.arrayOf(PropTypes.shape({
    query_text: PropTypes.string.isRequired,
    operation_type: PropTypes.string.isRequired,
    execution_time_ms: PropTypes.number,
    result_count: PropTypes.number,
    status: PropTypes.string.isRequired,
    timestamp: PropTypes.string.isRequired,
    source: PropTypes.string,
    session_id: PropTypes.string,
    error_message: PropTypes.string
  })).isRequired
};
