/**
 * useUploadFlow Hook Tests
 *
 * Tests for the upload flow state machine.
 * Story 2.7: Frontend CSV Upload UI - Test Coverage
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useUploadFlow } from './useUploadFlow'
import { uploadService } from '../services/uploadService'

// Mock the upload service
vi.mock('../services/uploadService', () => ({
  uploadService: {
    uploadCSV: vi.fn(),
    confirmUpload: vi.fn(),
  },
}))

// Mock logger
vi.mock('../utils/logger', () => ({
  logError: vi.fn(),
}))

describe('useUploadFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Initial State', () => {
    it('should initialize with idle state', () => {
      const { result } = renderHook(() => useUploadFlow())

      expect(result.current.state).toBe('idle')
      expect(result.current.previewData).toBeNull()
      expect(result.current.jobId).toBeNull()
      expect(result.current.summary).toBeNull()
      expect(result.current.error).toBeNull()
    })
  })

  describe('File Upload Flow', () => {
    it('should transition from idle to uploading to previewing on successful upload', async () => {
      const mockPreviewData = {
        is_valid: true,
        file_hash: 'abc123',
        file_type: 'skills',
        preview_rows: [{ id: 1, name: 'Test' }],
        total_rows: 100,
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)

      const { result } = renderHook(() => useUploadFlow())

      expect(result.current.state).toBe('idle')

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('previewing')
        expect(result.current.previewData).toEqual(mockPreviewData)
        expect(result.current.error).toBeNull()
      })
    })

    it('should transition to error state when upload fails', async () => {
      const mockError = {
        response: {
          data: {
            detail: 'Invalid CSV format',
          },
        },
      }

      uploadService.uploadCSV.mockRejectedValue(mockError)

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('error')
        expect(result.current.error).toBe('Invalid CSV format')
      })
    })

    it('should transition to error state when validation fails', async () => {
      const mockPreviewData = {
        is_valid: false,
        validation_errors: ['Missing required column: name', 'Invalid data type in row 5'],
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('error')
        expect(result.current.error).toContain('Missing required column')
      })
    })
  })

  describe('Confirmation Flow', () => {
    it('should transition from previewing to processing on confirm', async () => {
      const mockPreviewData = {
        is_valid: true,
        file_hash: 'abc123',
        file_type: 'skills',
        preview_rows: [],
        total_rows: 100,
      }

      const mockIngestionResponse = {
        ingestion_job_id: 'job-123',
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)
      uploadService.confirmUpload.mockResolvedValue(mockIngestionResponse)

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('previewing')
      })

      await act(async () => {
        await result.current.handleConfirmUpload()
      })

      await waitFor(() => {
        expect(result.current.state).toBe('processing')
        expect(result.current.jobId).toBe('job-123')
      })
    })

    it('should transition to error state if confirmation fails', async () => {
      const mockPreviewData = {
        is_valid: true,
        file_hash: 'abc123',
        file_type: 'skills',
      }

      const mockError = {
        response: {
          data: {
            detail: 'Server error',
          },
        },
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)
      uploadService.confirmUpload.mockRejectedValue(mockError)

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('previewing')
      })

      await act(async () => {
        await result.current.handleConfirmUpload()
      })

      await waitFor(() => {
        expect(result.current.state).toBe('error')
        expect(result.current.error).toBe('Server error')
      })
    })
  })

  describe('Cancel Flow', () => {
    it('should reset to idle state when upload is cancelled', async () => {
      const mockPreviewData = {
        is_valid: true,
        file_hash: 'abc123',
        file_type: 'skills',
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('previewing')
      })

      act(() => {
        result.current.handleCancelUpload()
      })

      expect(result.current.state).toBe('idle')
      expect(result.current.previewData).toBeNull()
      expect(result.current.error).toBeNull()
    })
  })

  describe('Completion Flow', () => {
    it('should transition to completed state with summary', () => {
      const { result } = renderHook(() => useUploadFlow())

      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 100,
        processed_records: 100,
        failed_records: 0,
      }

      act(() => {
        result.current.handleComplete(mockSummary)
      })

      expect(result.current.state).toBe('completed')
      expect(result.current.summary).toEqual(mockSummary)
    })
  })

  describe('Reset Flow', () => {
    it('should reset all state to initial values', async () => {
      const mockPreviewData = {
        is_valid: true,
        file_hash: 'abc123',
        file_type: 'skills',
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('previewing')
      })

      act(() => {
        result.current.resetFlow()
      })

      expect(result.current.state).toBe('idle')
      expect(result.current.previewData).toBeNull()
      expect(result.current.jobId).toBeNull()
      expect(result.current.summary).toBeNull()
      expect(result.current.error).toBeNull()
    })
  })

  describe('Error Handling', () => {
    it('should handle upload errors without response data', async () => {
      uploadService.uploadCSV.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('error')
        expect(result.current.error).toBe('Failed to upload file. Please try again.')
      })
    })

    it('should handle confirmation errors without response data', async () => {
      const mockPreviewData = {
        is_valid: true,
        file_hash: 'abc123',
        file_type: 'skills',
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)
      uploadService.confirmUpload.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useUploadFlow())

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })

      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      await waitFor(() => {
        expect(result.current.state).toBe('previewing')
      })

      await act(async () => {
        await result.current.handleConfirmUpload()
      })

      await waitFor(() => {
        expect(result.current.state).toBe('error')
        expect(result.current.error).toBe('Failed to start ingestion. Please try again.')
      })
    })
  })

  describe('State Machine Integrity', () => {
    it('should maintain state integrity through complete happy path', async () => {
      const mockPreviewData = {
        is_valid: true,
        file_hash: 'abc123',
        file_type: 'skills',
      }

      const mockIngestionResponse = {
        ingestion_job_id: 'job-123',
      }

      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 100,
        processed_records: 100,
        failed_records: 0,
      }

      uploadService.uploadCSV.mockResolvedValue(mockPreviewData)
      uploadService.confirmUpload.mockResolvedValue(mockIngestionResponse)

      const { result } = renderHook(() => useUploadFlow())

      // Initial: idle
      expect(result.current.state).toBe('idle')

      // Upload file
      const file = new File(['test'], 'test.csv', { type: 'text/csv' })
      await act(async () => {
        await result.current.handleFileSelect(file, 'skills')
      })

      // After upload: previewing
      await waitFor(() => {
        expect(result.current.state).toBe('previewing')
        expect(result.current.previewData).toBeTruthy()
      })

      // Confirm upload
      await act(async () => {
        await result.current.handleConfirmUpload()
      })

      // After confirm: processing
      await waitFor(() => {
        expect(result.current.state).toBe('processing')
        expect(result.current.jobId).toBe('job-123')
      })

      // Complete processing
      act(() => {
        result.current.handleComplete(mockSummary)
      })

      // After complete: completed
      expect(result.current.state).toBe('completed')
      expect(result.current.summary).toEqual(mockSummary)

      // Reset
      act(() => {
        result.current.resetFlow()
      })

      // After reset: back to idle
      expect(result.current.state).toBe('idle')
    })
  })
})
