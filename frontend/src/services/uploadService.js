/**
 * Upload Service
 *
 * Handles CSV upload, preview, confirmation, and status polling.
 * Story 2.7: Frontend CSV Upload UI
 */

import api from './api'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class UploadService {
  /**
   * Upload CSV file for preview validation
   * @param {File} file - CSV file to upload
   * @param {'skills' | 'jobs'} fileType - Type of CSV file
   * @returns {Promise<CSVPreviewResponse>} Preview data with validation results
   */
  async uploadCSV(file, fileType) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post(`/ingest/${fileType}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    return response.data
  }

  /**
   * Confirm upload and start ingestion job
   * @param {string} fileHash - File hash from preview response
   * @param {string} fileType - CSV type: 'skills' or 'jobs'
   * @returns {Promise<{ingestion_job_id: string}>} Job ID for status tracking
   */
  async confirmUpload(fileHash, fileType) {
    const response = await api.post('/ingest/confirm', {
      file_hash: fileHash,
      file_type: fileType,
    })

    return response.data
  }

  /**
   * Get ingestion job status
   * @param {string} jobId - Ingestion job ID
   * @returns {Promise<IngestionStatusResponse>} Current job status and progress
   */
  async getIngestionStatus(jobId) {
    const response = await api.get(`/ingest/status/${jobId}`)
    return response.data
  }

  /**
   * Get error log download URL
   * @param {string} jobId - Ingestion job ID
   * @returns {string} URL to download error log CSV
   */
  getErrorLogUrl(jobId) {
    const token = localStorage.getItem('token')
    return `${API_BASE_URL}/ingest/errors/${jobId}?token=${token}`
  }
}

export const uploadService = new UploadService()
