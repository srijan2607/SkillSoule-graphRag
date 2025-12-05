/**
 * File Upload Zone Component
 *
 * Drag-and-drop upload zone with file picker fallback.
 * Includes file validation (type, size) and visual feedback.
 *
 * Story 2.7: Frontend CSV Upload UI
 */

import { useRef, useState } from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'

const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500MB

export default function FileUploadZone({ title, onFileSelect, isLoading = false }) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  /**
   * Validate file type and size
   * SECURITY-001: Defense-in-depth validation (extension + MIME type)
   */
  const validateFile = (file) => {
    setError(null)

    // Check extension
    if (!file.name.endsWith('.csv')) {
      setError('Only CSV files are allowed')
      return false
    }

    // Check MIME type (SECURITY-001: prevents extension spoofing)
    if (file.type && file.type !== 'text/csv') {
      setError('Invalid file type. Only CSV files are allowed')
      return false
    }

    // Check size
    if (file.size > MAX_FILE_SIZE) {
      setError('File size exceeds 500MB limit')
      return false
    }

    return true
  }

  /**
   * Handle file drop event
   */
  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)

    if (isLoading) return

    const file = e.dataTransfer.files[0]
    if (file && validateFile(file)) {
      onFileSelect(file)
    }
  }

  /**
   * Handle file input change
   */
  const handleFileInput = (e) => {
    const file = e.target.files?.[0]
    if (file && validateFile(file)) {
      onFileSelect(file)
    }
    // Reset input so same file can be selected again
    e.target.value = ''
  }

  /**
   * Trigger file picker
   */
  const handleClick = () => {
    if (!isLoading) {
      fileInputRef.current?.click()
    }
  }

  /**
   * Prevent default drag behavior
   */
  const handleDragOver = (e) => {
    e.preventDefault()
    if (!isLoading) {
      setIsDragOver(true)
    }
  }

  /**
   * Reset drag over state
   */
  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  return (
    <div className="relative">
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 transition-all
          ${isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
          ${
            isLoading
              ? 'opacity-50 cursor-not-allowed'
              : 'cursor-pointer hover:border-blue-400 hover:bg-gray-50'
          }
        `}
        data-testid="upload-zone"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileInput}
          data-testid="file-input"
          className="hidden"
          disabled={isLoading}
        />

        <div className="flex flex-col items-center justify-center text-center">
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4" />
              <p className="text-gray-600">Uploading...</p>
            </>
          ) : (
            <>
              <Upload className="w-12 h-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-gray-600 mb-4">
                Drag and drop your CSV file here, or click to select
              </p>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <FileText className="w-4 h-4" />
                <span>.csv files only (max 500MB)</span>
              </div>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-3 flex items-center gap-2 text-red-600" data-testid="upload-error">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
        </div>
      )}
    </div>
  )
}
