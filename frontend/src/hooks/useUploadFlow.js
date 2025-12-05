/**
 * Upload Flow State Machine Hook
 *
 * Manages the complete CSV upload workflow:
 * idle → uploading → previewing → processing → completed/error
 *
 * Story 2.7: Frontend CSV Upload UI
 */

import { useState } from 'react'
import { uploadService } from '../services/uploadService'
import { logError } from '../utils/logger'

/**
 * @typedef {'idle' | 'uploading' | 'previewing' | 'processing' | 'completed' | 'error'} UploadState
 */

export function useUploadFlow() {
  const [state, setState] = useState('idle')
  const [previewData, setPreviewData] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  /**
   * Handle file selection and upload for preview
   * @param {File} file - Selected CSV file
   * @param {'skills' | 'jobs'} fileType - Type of CSV
   */
  const handleFileSelect = async (file, fileType) => {
    try {
      setState('uploading')
      setError(null)

      const preview = await uploadService.uploadCSV(file, fileType)

      if (!preview.is_valid) {
        // Validation failed
        setError(preview.validation_errors.join(', '))
        setState('error')
        return
      }

      setPreviewData(preview)
      setState('previewing')
    } catch (err) {
      logError('Upload error:', err)
      setError(err.response?.data?.detail || 'Failed to upload file. Please try again.')
      setState('error')
    }
  }

  /**
   * Confirm upload and start ingestion
   */
  const handleConfirmUpload = async () => {
    if (!previewData) return

    try {
      setState('processing')

      const { ingestion_job_id } = await uploadService.confirmUpload(
        previewData.file_hash,
        previewData.file_type
      )

      setJobId(ingestion_job_id)
    } catch (err) {
      logError('Confirmation error:', err)
      setError(err.response?.data?.detail || 'Failed to start ingestion. Please try again.')
      setState('error')
    }
  }

  /**
   * Cancel upload during preview
   */
  const handleCancelUpload = () => {
    setPreviewData(null)
    setError(null)
    setState('idle')
  }

  /**
   * Handle completion from progress component
   * @param {object} completionSummary - Final status from polling
   */
  const handleComplete = (completionSummary) => {
    setSummary(completionSummary)
    setState('completed')
  }

  /**
   * Reset flow to start over
   */
  const resetFlow = () => {
    setState('idle')
    setPreviewData(null)
    setJobId(null)
    setSummary(null)
    setError(null)
  }

  return {
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
  }
}
