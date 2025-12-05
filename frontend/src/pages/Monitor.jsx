import { useState, useEffect, useRef } from 'react';
import { Activity, Database, Zap, AlertCircle, Clock, TrendingUp, Filter, Search } from 'lucide-react';
import api from '../services/api';
import StatsCards from '../components/Monitor/StatsCards';
import QueryList from '../components/Monitor/QueryList';
import LiveQueries from '../components/Monitor/LiveQueries';
import SlowQueries from '../components/Monitor/SlowQueries';
import FilterPanel from '../components/Monitor/FilterPanel';

export default function Monitor() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [queries, setQueries] = useState([]);
  const [slowQueries, setSlowQueries] = useState([]);
  const [liveQueries, setLiveQueries] = useState([]);
  const [filters, setFilters] = useState({
    operation_type: '',
    status: '',
    source: '',
    limit: 50
  });
  const [loading, setLoading] = useState(true);
  const wsRef = useRef(null);

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await api.get('/monitor/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  // Fetch recent queries
  const fetchQueries = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.operation_type) params.append('operation_type', filters.operation_type);
      if (filters.status) params.append('status', filters.status);
      if (filters.source) params.append('source', filters.source);
      params.append('limit', filters.limit);

      const response = await api.get(`/monitor/queries?${params.toString()}`);
      setQueries(response.data.queries);
    } catch (error) {
      console.error('Failed to fetch queries:', error);
    }
  };

  // Fetch slow queries
  const fetchSlowQueries = async () => {
    try {
      const response = await api.get('/monitor/queries/slow?threshold_ms=500&limit=10');
      setSlowQueries(response.data.slow_queries);
    } catch (error) {
      console.error('Failed to fetch slow queries:', error);
    }
  };

  // Connect to WebSocket for live monitoring
  const connectWebSocket = () => {
    const wsUrl = 'ws://127.0.0.1:8000/monitor/live';
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to query monitoring stream');
    };

    ws.onmessage = (event) => {
      try {
        const queryLog = JSON.parse(event.data);
        
        // Ignore connection messages
        if (queryLog.type === 'connection_established') {
          return;
        }

        // Add to live queries (keep last 50)
        setLiveQueries(prev => [queryLog, ...prev].slice(0, 50));

        // Update stats and queries list
        fetchStats();
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Disconnected from query monitoring stream');
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        if (activeTab === 'live') {
          connectWebSocket();
        }
      }, 3000);
    };

    // Keep-alive ping
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    wsRef.current = { ws, pingInterval };
  };

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchStats(),
        fetchQueries(),
        fetchSlowQueries()
      ]);
      setLoading(false);
    };

    loadData();
  }, []);

  // Refresh data when filters change
  useEffect(() => {
    if (!loading) {
      fetchQueries();
    }
  }, [filters]);

  // WebSocket connection management
  useEffect(() => {
    if (activeTab === 'live') {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        clearInterval(wsRef.current.pingInterval);
        wsRef.current.ws.close();
      }
    };
  }, [activeTab]);

  // Auto-refresh stats every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStats();
      if (activeTab === 'overview') {
        fetchSlowQueries();
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [activeTab]);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'queries', label: 'Query Logs', icon: Database },
    { id: 'live', label: 'Live Monitor', icon: Zap },
    { id: 'slow', label: 'Slow Queries', icon: Clock }
  ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-purple-50/30 to-blue-50/30">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin text-primary-500 mx-auto mb-4" />
          <p className="text-slate-600">Loading monitoring data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-purple-50/30 to-blue-50/30">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 via-primary-700 to-blue-600 text-white shadow-xl">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-3 bg-white/20 backdrop-blur-sm rounded-xl">
              <Activity className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Neo4j Query Monitor</h1>
              <p className="text-purple-100 text-sm mt-1">Real-time database query monitoring and performance analytics</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-2 border-t border-white/10 pt-4">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-3 rounded-t-xl font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-slate-50 text-primary-700 shadow-lg'
                      : 'bg-white/10 text-white hover:bg-white/20 backdrop-blur-sm'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <StatsCards stats={stats} />
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SlowQueries queries={slowQueries} />
              
              <div className="glass rounded-2xl p-6 border border-purple-100">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-white" />
                  </div>
                  <h2 className="text-xl font-bold text-slate-800">Performance Insights</h2>
                </div>

                {stats && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl">
                      <span className="text-sm text-slate-700 font-medium">Success Rate</span>
                      <span className="text-lg font-bold text-green-600">
                        {stats.total_queries > 0 
                          ? ((stats.successful_queries / stats.total_queries) * 100).toFixed(1)
                          : 0
                        }%
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl">
                      <span className="text-sm text-slate-700 font-medium">Avg Execution Time</span>
                      <span className="text-lg font-bold text-blue-600">
                        {stats.avg_execution_time_ms?.toFixed(1) || 0}ms
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl">
                      <span className="text-sm text-slate-700 font-medium">Cache Size</span>
                      <span className="text-lg font-bold text-purple-600">
                        {stats.cache_size?.toLocaleString() || 0}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gradient-to-r from-orange-50 to-amber-50 rounded-xl">
                      <span className="text-sm text-slate-700 font-medium">Active Connections</span>
                      <span className="text-lg font-bold text-orange-600">
                        {stats.websocket_connections || 0}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'queries' && (
          <div className="space-y-6">
            <FilterPanel filters={filters} setFilters={setFilters} onRefresh={fetchQueries} />
            <QueryList queries={queries} />
          </div>
        )}

        {activeTab === 'live' && (
          <LiveQueries queries={liveQueries} />
        )}

        {activeTab === 'slow' && (
          <div className="space-y-6">
            <div className="glass rounded-2xl p-6 border border-orange-100">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-800">Slow Queries</h2>
                  <p className="text-sm text-slate-600 mt-1">Queries taking longer than 500ms</p>
                </div>
              </div>
            </div>
            <SlowQueries queries={slowQueries} detailed />
          </div>
        )}
      </div>
    </div>
  );
}
