/**
 * Ingestion Summary Component
 *
 * Displays completion summary after ingestion finishes.
 * Shows success/failure stats and provides download for error logs.
 * Allows user to upload another file or navigate to explore data.
 *
 * Story 2.7: Frontend CSV Upload UI
 */

import { CheckCircle, AlertCircle, Download, Upload } from 'lucide-react'
import { uploadService } from '../services/uploadService'
import { logError } from '../utils/logger'

export default function IngestionSummary({ summary, onUploadAnother, onViewData }) {
  if (!summary) return null

  const hasErrors = summary.failed_records > 0
  const isSuccess = summary.status === 'completed'
  const isPartialSuccess = summary.status === 'completed_with_errors'

  /**
   * Download error log
   * UX-001: Direct download without popup blockers
   */
  const handleDownloadErrors = async () => {
    try {
      // Fetch CSV with authentication
      const response = await fetch(uploadService.getErrorLogUrl(summary.job_id), {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (!response.ok) throw new Error('Failed to download error log')

      // Create blob and download
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ingestion_errors_${summary.job_id}.csv`
      document.body.appendChild(a)
      a.click()

      // Cleanup
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      logError('Error downloading log:', err)
      // Fallback to window.open if direct download fails
      window.open(uploadService.getErrorLogUrl(summary.job_id), '_blank')
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          {isSuccess ? (
            <CheckCircle className="w-8 h-8 text-green-600" />
          ) : (
            <AlertCircle className="w-8 h-8 text-yellow-600" />
          )}
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              {isSuccess ? 'Upload Complete!' : 'Upload Completed with Errors'}
            </h2>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="bg-gray-50 rounded-lg p-6 mb-6">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total Records</p>
              <p className="text-2xl font-bold text-gray-900">
                {summary.total_records.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Successfully Processed</p>
              <p className="text-2xl font-bold text-green-600">
                {summary.processed_records.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Failed</p>
              <p className="text-2xl font-bold text-red-600">
                {summary.failed_records.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        {/* Success Message */}
        {isSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <p className="text-green-800">
              All {summary.total_records.toLocaleString()} records ingested successfully!
            </p>
          </div>
        )}

        {/* Partial Success Message */}
        {isPartialSuccess && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <p className="text-yellow-800 mb-3">
              {summary.processed_records.toLocaleString()} / {summary.total_records.toLocaleString()}{' '}
              records ingested successfully ({summary.failed_records.toLocaleString()} failed).
            </p>
            {hasErrors && (
              <button
                onClick={handleDownloadErrors}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition"
              >
                <Download className="w-4 h-4" />
                Download Error Log
              </button>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={onUploadAnother}
            className="flex items-center gap-2 px-6 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition"
          >
            <Upload className="w-4 h-4" />
            Upload Another File
          </button>
          {onViewData && (
            <button
              onClick={onViewData}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              View Data
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
