/**
 * Ingestion Progress Component
 *
 * Displays real-time progress of CSV ingestion job.
 * Polls backend every 2 seconds for status updates.
 * Shows progress bar, stats, and estimated time remaining.
 *
 * Story 2.7: Frontend CSV Upload UI
 */

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { uploadService } from '../services/uploadService'
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react'

/**
 * Format seconds to human-readable time
 */
function formatTime(seconds) {
  if (!seconds) return 'Calculating...'
  if (seconds < 60) return `${seconds}s`

  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}m ${secs}s`
}

export default function IngestionProgress({ jobId, onComplete }) {
  const {
    data: status,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['ingestion-status', jobId],
    queryFn: () => uploadService.getIngestionStatus(jobId),
    refetchInterval: (data) => {
      // Stop polling when completed
      if (
        data?.status === 'completed' ||
        data?.status === 'completed_with_errors' ||
        data?.status === 'failed'
      ) {
        return false
      }
      return 2000 // Poll every 2 seconds
    },
    enabled: !!jobId,
    retry: 3, // Retry failed requests 3 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
  })

  // Notify parent when complete
  useEffect(() => {
    if (status?.status === 'completed' || status?.status === 'completed_with_errors') {
      onComplete(status)
    }
  }, [status, onComplete])

  // RELIABILITY-001: Network failure UX
  if (isError) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-800 mb-2">
                Connection Error
              </h3>
              <p className="text-red-600 mb-4">
                Unable to check ingestion status. Please check your internet connection.
              </p>
              <button
                onClick={() => refetch()}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                <RefreshCw className="w-4 h-4" />
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="flex items-center gap-3 mb-6">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <h2 className="text-2xl font-bold text-gray-900">Processing CSV</h2>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm font-medium text-blue-600">
              {status.progress_percentage.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-blue-600 h-full transition-all duration-300"
              style={{ width: `${status.progress_percentage}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Processed</p>
            <p className="text-2xl font-bold text-gray-900">
              {status.processed_records.toLocaleString()}
              <span className="text-sm font-normal text-gray-500 ml-2">
                / {status.total_records.toLocaleString()}
              </span>
            </p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-1">Failed</p>
            <p className="text-2xl font-bold text-red-600">
              {status.failed_records.toLocaleString()}
            </p>
          </div>
        </div>

        {/* Batch Info */}
        {status.current_batch && status.total_batches && (
          <div className="mb-6 text-center">
            <p className="text-sm text-gray-600">
              Batch {status.current_batch} of {status.total_batches}
            </p>
          </div>
        )}

        {/* ETA */}
        {status.estimated_time_remaining && (
          <div className="text-center">
            <p className="text-sm text-gray-600">
              Estimated time remaining:{' '}
              <span className="font-medium text-gray-900">
                {formatTime(status.estimated_time_remaining)}
              </span>
            </p>
            {status.processing_speed && (
              <p className="text-xs text-gray-500 mt-1">
                Processing {status.processing_speed.toFixed(1)} records/sec
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
