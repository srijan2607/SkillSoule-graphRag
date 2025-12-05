import { Filter, RefreshCw } from 'lucide-react';
import PropTypes from 'prop-types';

export default function FilterPanel({ filters, setFilters, onRefresh }) {
  const operationTypes = ['', 'READ', 'WRITE', 'VECTOR_SEARCH', 'GRAPH_TRAVERSAL', 'OTHER'];
  const statusOptions = ['', 'success', 'error'];
  const limitOptions = [20, 50, 100, 200];

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="glass rounded-2xl p-6 border border-purple-100">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg">
          <Filter className="w-5 h-5 text-white" />
        </div>
        <h2 className="text-xl font-bold text-slate-800">Filters</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Operation Type */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Operation Type
          </label>
          <select
            value={filters.operation_type}
            onChange={(e) => handleFilterChange('operation_type', e.target.value)}
            className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
          >
            <option value="">All Types</option>
            {operationTypes.slice(1).map(type => (
              <option key={type} value={type}>
                {type.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Status
          </label>
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange('status', e.target.value)}
            className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
          >
            <option value="">All Status</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
          </select>
        </div>

        {/* Source */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Source
          </label>
          <input
            type="text"
            value={filters.source}
            onChange={(e) => handleFilterChange('source', e.target.value)}
            placeholder="Filter by source..."
            className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
          />
        </div>

        {/* Limit */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Limit
          </label>
          <select
            value={filters.limit}
            onChange={(e) => handleFilterChange('limit', Number(e.target.value))}
            className="w-full px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
          >
            {limitOptions.map(limit => (
              <option key={limit} value={limit}>
                {limit} queries
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mt-4 pt-4 border-t border-slate-100">
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary-600 to-blue-600 text-white rounded-xl font-medium hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>

        <button
          onClick={() => setFilters({ operation_type: '', status: '', source: '', limit: 50 })}
          className="px-4 py-2 bg-slate-100 text-slate-700 rounded-xl font-medium hover:bg-slate-200 transition-all duration-200"
        >
          Clear Filters
        </button>

        <span className="ml-auto text-sm text-slate-500">
          Showing up to {filters.limit} queries
        </span>
      </div>
    </div>
  );
}

FilterPanel.propTypes = {
  filters: PropTypes.shape({
    operation_type: PropTypes.string,
    status: PropTypes.string,
    source: PropTypes.string,
    limit: PropTypes.number
  }).isRequired,
  setFilters: PropTypes.func.isRequired,
  onRefresh: PropTypes.func.isRequired
};
