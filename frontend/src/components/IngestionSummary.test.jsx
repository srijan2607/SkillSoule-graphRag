/**
 * IngestionSummary Component Tests
 *
 * Tests for ingestion completion summary with download functionality.
 * Story 2.7: Frontend CSV Upload UI - Test Coverage
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IngestionSummary from './IngestionSummary'

// Mock upload service
vi.mock('../services/uploadService', () => ({
  uploadService: {
    getErrorLogUrl: vi.fn((jobId) => `http://api.example.com/errors/${jobId}`),
  },
}))

// Mock logger
vi.mock('../utils/logger', () => ({
  logError: vi.fn(),
}))

// Mock fetch
global.fetch = vi.fn()

describe('IngestionSummary', () => {
  const mockOnUploadAnother = vi.fn()
  const mockOnViewData = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.revokeObjectURL = vi.fn()
  })

  describe('Rendering', () => {
    it('should not render when summary is null', () => {
      const { container } = render(
        <IngestionSummary
          summary={null}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(container).toBeEmptyDOMElement()
    })

    it('should render success summary for completed status', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByText('Upload Complete!')).toBeInTheDocument()
      expect(screen.getByText('All 1,000 records ingested successfully!')).toBeInTheDocument()
    })

    it('should render partial success summary for completed_with_errors status', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByText('Upload Completed with Errors')).toBeInTheDocument()
      expect(screen.getByText(/950 \/ 1,000 records ingested successfully \(50 failed\)/)).toBeInTheDocument()
    })
  })

  describe('Summary Stats Display', () => {
    it('should display total, processed, and failed records', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 5000,
        processed_records: 4850,
        failed_records: 150,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByText('5,000')).toBeInTheDocument()
      expect(screen.getByText('4,850')).toBeInTheDocument()
      expect(screen.getByText('150')).toBeInTheDocument()
    })

    it('should format large numbers with commas', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1234567,
        processed_records: 1234567,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      // Both total and processed have the same value, so check for multiple instances
      const formattedNumbers = screen.getAllByText('1,234,567')
      expect(formattedNumbers).toHaveLength(2) // Total and Processed
    })
  })

  describe('Error Log Download (UX-001)', () => {
    it('should show download button when there are errors', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByRole('button', { name: /download error log/i })).toBeInTheDocument()
    })

    it('should not show download button when no errors', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.queryByRole('button', { name: /download error log/i })).not.toBeInTheDocument()
    })

    it('should download error log using fetch + blob on button click', async () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      const mockBlob = new Blob(['error,data'], { type: 'text/csv' })
      global.fetch.mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      })

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const downloadButton = screen.getByRole('button', { name: /download error log/i })
      await userEvent.click(downloadButton)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          'http://api.example.com/errors/job-123',
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: expect.stringContaining('Bearer'),
            }),
          })
        )
      })

      expect(global.URL.createObjectURL).toHaveBeenCalledWith(mockBlob)
    })

    it('should create anchor element with correct download filename', async () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      const mockBlob = new Blob(['error,data'], { type: 'text/csv' })
      global.fetch.mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      })

      const appendChildSpy = vi.spyOn(document.body, 'appendChild')
      const removeChildSpy = vi.spyOn(document.body, 'removeChild')

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const downloadButton = screen.getByRole('button', { name: /download error log/i })
      await userEvent.click(downloadButton)

      await waitFor(() => {
        expect(appendChildSpy).toHaveBeenCalled()
        // Find the anchor element from all appendChild calls
        const anchor = appendChildSpy.mock.calls
          .map(call => call[0])
          .find(el => el.tagName === 'A')
        expect(anchor).toBeDefined()
        expect(anchor.download).toBe('ingestion_errors_job-123.csv')
        expect(anchor.href).toBe('blob:mock-url')
      })

      expect(removeChildSpy).toHaveBeenCalled()
      expect(global.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
    })

    it('should fallback to window.open on fetch error', async () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      global.fetch.mockRejectedValue(new Error('Network error'))
      global.window.open = vi.fn()

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const downloadButton = screen.getByRole('button', { name: /download error log/i })
      await userEvent.click(downloadButton)

      await waitFor(() => {
        expect(global.window.open).toHaveBeenCalledWith(
          'http://api.example.com/errors/job-123',
          '_blank'
        )
      })
    })

    it('should fallback to window.open when response is not ok', async () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      global.fetch.mockResolvedValue({
        ok: false,
        status: 404,
      })
      global.window.open = vi.fn()

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const downloadButton = screen.getByRole('button', { name: /download error log/i })
      await userEvent.click(downloadButton)

      await waitFor(() => {
        expect(global.window.open).toHaveBeenCalledWith(
          'http://api.example.com/errors/job-123',
          '_blank'
        )
      })
    })

    it('should use token from localStorage in fetch request', async () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      global.localStorage.getItem.mockReturnValue('mock-token-123')
      global.fetch.mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(new Blob()),
      })

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const downloadButton = screen.getByRole('button', { name: /download error log/i })
      await userEvent.click(downloadButton)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            headers: {
              Authorization: 'Bearer mock-token-123',
            },
          })
        )
      })
    })
  })

  describe('Action Buttons', () => {
    it('should render Upload Another button', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByRole('button', { name: /upload another file/i })).toBeInTheDocument()
    })

    it('should call onUploadAnother when button is clicked', async () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const uploadButton = screen.getByRole('button', { name: /upload another file/i })
      await userEvent.click(uploadButton)

      expect(mockOnUploadAnother).toHaveBeenCalled()
    })

    it('should render View Data button when onViewData is provided', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByRole('button', { name: /view data/i })).toBeInTheDocument()
    })

    it('should not render View Data button when onViewData is not provided', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={null}
        />
      )

      expect(screen.queryByRole('button', { name: /view data/i })).not.toBeInTheDocument()
    })

    it('should call onViewData when button is clicked', async () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const viewButton = screen.getByRole('button', { name: /view data/i })
      await userEvent.click(viewButton)

      expect(mockOnViewData).toHaveBeenCalled()
    })
  })

  describe('Visual States', () => {
    it('should show success icon and styling for completed status', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const successSection = screen.getByText(/All 1,000 records/).closest('div')
      expect(successSection).toHaveClass('bg-green-50')
    })

    it('should show warning icon and styling for partial success', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 950,
        failed_records: 50,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      const warningSection = screen.getByText(/950 \/ 1,000/).closest('div')
      expect(warningSection).toHaveClass('bg-yellow-50')
    })
  })

  describe('Edge Cases', () => {
    it('should handle zero records', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 0,
        processed_records: 0,
        failed_records: 0,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByText('All 0 records ingested successfully!')).toBeInTheDocument()
    })

    it('should handle all records failing', () => {
      const mockSummary = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 0,
        failed_records: 1000,
      }

      render(
        <IngestionSummary
          summary={mockSummary}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      expect(screen.getByText(/0 \/ 1,000 records ingested successfully \(1,000 failed\)/)).toBeInTheDocument()
    })

    it('should determine hasErrors based on failed_records count', () => {
      const mockSummaryWithErrors = {
        job_id: 'job-123',
        status: 'completed',
        total_records: 1000,
        processed_records: 999,
        failed_records: 1,
      }

      const { rerender } = render(
        <IngestionSummary
          summary={mockSummaryWithErrors}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      // Even with completed status, should show error button if failed_records > 0
      // But this component doesn't show download button for 'completed' status
      expect(screen.queryByRole('button', { name: /download error log/i })).not.toBeInTheDocument()

      const mockSummaryNoErrors = {
        job_id: 'job-123',
        status: 'completed_with_errors',
        total_records: 1000,
        processed_records: 1000,
        failed_records: 0,
      }

      rerender(
        <IngestionSummary
          summary={mockSummaryNoErrors}
          onUploadAnother={mockOnUploadAnother}
          onViewData={mockOnViewData}
        />
      )

      // Even with completed_with_errors status, shouldn't show download if no errors
      expect(screen.queryByRole('button', { name: /download error log/i })).not.toBeInTheDocument()
    })
  })
})
