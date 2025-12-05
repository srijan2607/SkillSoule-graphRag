import { Database, CheckCircle, XCircle, Zap, TrendingUp } from 'lucide-react';
import PropTypes from 'prop-types';

export default function StatsCards({ stats }) {
  if (!stats) return null;

  const cards = [
    {
      label: 'Total Queries',
      value: stats.total_queries?.toLocaleString() || '0',
      icon: Database,
      gradient: 'from-blue-500 to-indigo-600',
      bgGradient: 'from-blue-50 to-indigo-50'
    },
    {
      label: 'Successful',
      value: stats.successful_queries?.toLocaleString() || '0',
      icon: CheckCircle,
      gradient: 'from-green-500 to-emerald-600',
      bgGradient: 'from-green-50 to-emerald-50'
    },
    {
      label: 'Failed',
      value: stats.failed_queries?.toLocaleString() || '0',
      icon: XCircle,
      gradient: 'from-red-500 to-rose-600',
      bgGradient: 'from-red-50 to-rose-50'
    },
    {
      label: 'Avg Time',
      value: `${stats.avg_execution_time_ms?.toFixed(1) || 0}ms`,
      icon: Zap,
      gradient: 'from-purple-500 to-pink-600',
      bgGradient: 'from-purple-50 to-pink-50'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card, index) => {
        const Icon = card.icon;
        return (
          <div
            key={index}
            className="glass rounded-2xl p-6 border border-purple-100 hover:shadow-xl transition-all duration-300 animate-scale-in"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 bg-gradient-to-br ${card.gradient} rounded-xl shadow-lg`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
            </div>
            
            <div className={`text-4xl font-bold bg-gradient-to-r ${card.gradient} bg-clip-text text-transparent mb-2`}>
              {card.value}
            </div>
            
            <div className="text-sm text-slate-600 font-medium">
              {card.label}
            </div>
          </div>
        );
      })}

      {/* Operation Breakdown */}
      {stats.operation_counts && (
        <div className="glass rounded-2xl p-6 border border-purple-100 md:col-span-2 lg:col-span-4 animate-fade-in">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">Query Type Distribution</h3>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Object.entries(stats.operation_counts).map(([type, count], index) => (
              <div
                key={type}
                className="bg-gradient-to-br from-slate-50 to-purple-50/50 rounded-xl p-4 border border-purple-100/50 hover:shadow-lg transition-all duration-300"
              >
                <div className="text-2xl font-bold text-primary-600 mb-1">
                  {count.toLocaleString()}
                </div>
                <div className="text-xs font-medium text-slate-600 uppercase tracking-wide">
                  {type.replace('_', ' ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

StatsCards.propTypes = {
  stats: PropTypes.shape({
    total_queries: PropTypes.number,
    successful_queries: PropTypes.number,
    failed_queries: PropTypes.number,
    avg_execution_time_ms: PropTypes.number,
    operation_counts: PropTypes.object
  })
};
