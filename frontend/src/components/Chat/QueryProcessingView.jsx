import { useState, useEffect } from 'react';
import { Database, Clock, CheckCircle, Loader, ChevronDown, ChevronUp } from 'lucide-react';
import PropTypes from 'prop-types';

export default function QueryProcessingView({ sessionId }) {
  const [queries, setQueries] = useState([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    if (!sessionId) return;

    // Connect to WebSocket for this specific session
    const wsUrl = `ws://127.0.0.1:8000/monitor/live`;
    let ws = null;
    let pingInterval = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Connected to query monitoring for session:', sessionId);
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const queryLog = JSON.parse(event.data);
          
          // Ignore connection messages
          if (queryLog.type === 'connection_established') {
            return;
          }

          // Only show queries from this session
          if (queryLog.session_id === sessionId) {
            setQueries(prev => [...prev, queryLog]);
          }
        } catch (error) {
          console.error('Failed to parse query log:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };

      ws.onclose = () => {
        console.log('Disconnected from query monitoring');
        setWsConnected(false);
      };

      // Keep-alive ping
      pingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 30000);
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setWsConnected(false);
    }

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (ws) {
        try {
          ws.close();
        } catch (e) {
          console.error('Error closing WebSocket:', e);
        }
      }
    };
  }, [sessionId]);

  const getOperationColor = (type) => {
    const colors = {
      'READ': 'text-blue-600 bg-blue-50 border-blue-200',
      'WRITE': 'text-purple-600 bg-purple-50 border-purple-200',
      'VECTOR_SEARCH': 'text-pink-600 bg-pink-50 border-pink-200',
      'GRAPH_TRAVERSAL': 'text-indigo-600 bg-indigo-50 border-indigo-200',
      'OTHER': 'text-slate-600 bg-slate-50 border-slate-200'
    };
    return colors[type] || colors['OTHER'];
  };

  const getStatusIcon = (status) => {
    return status === 'success' 
      ? <CheckCircle className="w-4 h-4 text-green-600" />
      : <span className="w-4 h-4 text-red-600">✗</span>;
  };

  const truncateQuery = (query, maxLength = 80) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  };

  if (!sessionId) return null;

  return (
    <div className="mt-4 glass rounded-xl border border-purple-200 overflow-hidden animate-slide-up">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between bg-gradient-to-r from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 transition-all duration-200"
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <Database className="w-5 h-5 text-primary-600" />
            {wsConnected && (
              <span className="absolute -top-1 -right-1 flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
            )}
          </div>
          <div className="text-left">
            <div className="text-sm font-semibold text-slate-800">
              Query Processing
            </div>
            <div className="text-xs text-slate-500">
              {queries.length === 0 ? 'Waiting for queries...' : `${queries.length} queries executed`}
            </div>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-slate-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-400" />
        )}
      </button>

      {/* Query List */}
      {isExpanded && (
        <div className="p-3 space-y-2 max-h-64 overflow-y-auto custom-scrollbar bg-white">
          {queries.length === 0 ? (
            <div className="flex items-center justify-center py-6 text-slate-400">
              <Loader className="w-5 h-5 animate-spin mr-2" />
              <span className="text-sm">Processing your query...</span>
            </div>
          ) : (
            queries.map((query, index) => (
              <div
                key={index}
                className="p-3 bg-slate-50 rounded-lg border border-slate-200 hover:border-purple-200 transition-all duration-200"
              >
                <div className="flex items-start gap-2 mb-2">
                  {getStatusIcon(query.status)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getOperationColor(query.operation_type)}`}>
                        {query.operation_type}
                      </span>
                      <div className="flex items-center gap-1 text-xs text-slate-600">
                        <Clock className="w-3 h-3" />
                        <span>{query.execution_time_ms?.toFixed(1)}ms</span>
                      </div>
                      {query.result_count !== null && query.result_count !== undefined && (
                        <span className="text-xs text-slate-500">
                          {query.result_count} results
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-xs text-slate-700 bg-white rounded px-2 py-1 border border-slate-200">
                      {truncateQuery(query.query_text)}
                    </div>
                    {query.source && (
                      <div className="mt-1 text-xs text-slate-500">
                        <span className="font-medium">{query.source}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Summary Footer */}
      {isExpanded && queries.length > 0 && (
        <div className="px-4 py-2 bg-gradient-to-r from-slate-50 to-purple-50 border-t border-slate-200">
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span>
              Total Time: <span className="font-semibold text-primary-600">
                {queries.reduce((sum, q) => sum + (q.execution_time_ms || 0), 0).toFixed(1)}ms
              </span>
            </span>
            <span>
              Success Rate: <span className="font-semibold text-green-600">
                {queries.length > 0 
                  ? ((queries.filter(q => q.status === 'success').length / queries.length) * 100).toFixed(0)
                  : 0
                }%
              </span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

QueryProcessingView.propTypes = {
  sessionId: PropTypes.string
};
