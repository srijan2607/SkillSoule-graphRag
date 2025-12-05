/**
 * Upload Page Component
 *
 * Main page for CSV upload workflow.
 * Manages state transitions: idle → uploading → previewing → processing → completed
 *
 * Story 2.7: Frontend CSV Upload UI
 */

import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import FileUploadZone from '../components/FileUploadZone'
import CSVPreviewModal from '../components/CSVPreviewModal'
import IngestionProgress from '../components/IngestionProgress'
import IngestionSummary from '../components/IngestionSummary'
import { useUploadFlow } from '../hooks/useUploadFlow'
import { AlertCircle } from 'lucide-react'

export default function UploadPage() {
  const navigate = useNavigate()
  const {
    state,
    previewData,
    jobId,
    summary,
    error,
    handleFileSelect,
    handleConfirmUpload,
    handleCancelUpload,
    handleComplete,
    resetFlow,
  } = useUploadFlow()

  return (
    <Layout>
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">CSV Data Upload</h1>
          <p className="text-gray-600 mt-2">
            Upload skills or jobs taxonomy CSV files for processing
          </p>
        </div>

        {/* Idle State: Upload Zones */}
        {state === 'idle' && (
          <div className="grid md:grid-cols-2 gap-6">
            <FileUploadZone
              title="Upload Skills CSV"
              fileType="skills"
              onFileSelect={(file) => handleFileSelect(file, 'skills')}
              isLoading={false}
            />
            <FileUploadZone
              title="Upload Jobs CSV"
              fileType="jobs"
              onFileSelect={(file) => handleFileSelect(file, 'jobs')}
              isLoading={false}
            />
          </div>
        )}

        {/* Uploading State */}
        {state === 'uploading' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg p-8 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
              <p className="text-gray-600">Uploading and validating CSV...</p>
            </div>
          </div>
        )}

        {/* Preview State: Modal */}
        {state === 'previewing' && previewData && (
          <CSVPreviewModal
            previewData={previewData}
            onConfirm={handleConfirmUpload}
            onCancel={handleCancelUpload}
          />
        )}

        {/* Processing State: Progress */}
        {state === 'processing' && jobId && (
          <IngestionProgress jobId={jobId} onComplete={handleComplete} />
        )}

        {/* Completed State: Summary */}
        {state === 'completed' && summary && (
          <IngestionSummary
            summary={summary}
            onUploadAnother={resetFlow}
            onViewData={() => navigate('/chat')}
          />
        )}

        {/* Error State */}
        {state === 'error' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-red-800 mb-2">Upload Failed</h3>
                  <p className="text-red-600 mb-4">{error || 'An error occurred during upload. Please try again.'}</p>
                  <button
                    onClick={resetFlow}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
