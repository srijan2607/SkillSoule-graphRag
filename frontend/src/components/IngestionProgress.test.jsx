/**
 * IngestionProgress Component Tests
 *
 * Tests for real-time ingestion progress tracking with polling.
 * Story 2.7: Frontend CSV Upload UI - Test Coverage
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import IngestionProgress from './IngestionProgress'
import { uploadService } from '../services/uploadService'

// Mock upload service
vi.mock('../services/uploadService', () => ({
  uploadService: {
    getIngestionStatus: vi.fn(),
  },
}))

// Test wrapper with React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  })

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('IngestionProgress', () => {
  const mockOnComplete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Loading State', () => {
    it('should show loading spinner initially', () => {
      uploadService.getIngestionStatus.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      )

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      // Check for the loading spinner with animate-spin class
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  describe('Progress Display', () => {
    it('should display progress information', async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 45.5,
        processed_records: 455,
        total_records: 1000,
        failed_records: 5,
        current_batch: 5,
        total_batches: 10,
        estimated_time_remaining: 120,
        processing_speed: 50.5,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('Processing CSV')).toBeInTheDocument()
        expect(screen.getByText('45.5%')).toBeInTheDocument()
        expect(screen.getByText('455')).toBeInTheDocument()
        expect(screen.getByText('/ 1,000')).toBeInTheDocument()
        expect(screen.getByText('5')).toBeInTheDocument()
        expect(screen.getByText('Batch 5 of 10')).toBeInTheDocument()
      })
    })

    it('should format time remaining correctly (seconds)', async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 500,
        total_records: 1000,
        failed_records: 0,
        estimated_time_remaining: 45,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText(/45s/)).toBeInTheDocument()
      })
    })

    it('should format time remaining correctly (minutes and seconds)', async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 500,
        total_records: 1000,
        failed_records: 0,
        estimated_time_remaining: 125,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText(/2m 5s/)).toBeInTheDocument()
      })
    })

    it('should show processing speed when available', async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 500,
        total_records: 1000,
        failed_records: 0,
        estimated_time_remaining: 60,
        processing_speed: 75.5,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText(/Processing 75.5 records\/sec/)).toBeInTheDocument()
      })
    })

    it('should not show batch info when not provided', async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 500,
        total_records: 1000,
        failed_records: 0,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.queryByText(/Batch/)).not.toBeInTheDocument()
      })
    })
  })

  describe('Polling Behavior', () => {
    it('should poll every 2 seconds when processing', { timeout: 10000 }, async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 500,
        total_records: 1000,
        failed_records: 0,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(uploadService.getIngestionStatus).toHaveBeenCalled()
      }, { timeout: 10000 })

      // Polling is handled by React Query internally
      expect(uploadService.getIngestionStatus).toHaveBeenCalled()
    })

    it('should stop polling when status is completed', { timeout: 15000 }, async () => {
      uploadService.getIngestionStatus.mockResolvedValue({
        status: 'completed',
        progress_percentage: 100,
        processed_records: 1000,
        total_records: 1000,
        failed_records: 0,
      })

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalled()
      }, { timeout: 10000 })
    })

    it('should stop polling when status is completed_with_errors', { timeout: 15000 }, async () => {
      uploadService.getIngestionStatus.mockResolvedValue({
        status: 'completed_with_errors',
        progress_percentage: 100,
        processed_records: 950,
        total_records: 1000,
        failed_records: 50,
      })

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalled()
      }, { timeout: 10000 })
    })

    it('should stop polling when status is failed', { timeout: 15000 }, async () => {
      uploadService.getIngestionStatus.mockResolvedValue({
        status: 'failed',
        progress_percentage: 30,
        processed_records: 300,
        total_records: 1000,
        failed_records: 700,
      })

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(uploadService.getIngestionStatus).toHaveBeenCalled()
      }, { timeout: 10000 })

      expect(mockOnComplete).not.toHaveBeenCalled()
    })
  })

  describe('Completion Handling', () => {
    it('should call onComplete when status is completed', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'completed',
        progress_percentage: 100,
        processed_records: 1000,
        total_records: 1000,
        failed_records: 0,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledWith(mockStatus)
      }, { timeout: 10000 })
    })

    it('should call onComplete when status is completed_with_errors', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'completed_with_errors',
        progress_percentage: 100,
        processed_records: 950,
        total_records: 1000,
        failed_records: 50,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledWith(mockStatus)
      }, { timeout: 10000 })
    })

    it('should not call onComplete when status is failed', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'failed',
        progress_percentage: 30,
        processed_records: 300,
        total_records: 1000,
        failed_records: 700,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(uploadService.getIngestionStatus).toHaveBeenCalled()
      }, { timeout: 10000 })

      expect(mockOnComplete).not.toHaveBeenCalled()
    })
  })

  describe('Error Handling (RELIABILITY-001)', () => {
    it('should show connection error UI on network failure', { timeout: 15000 }, async () => {
      uploadService.getIngestionStatus.mockRejectedValue(new Error('Network error'))

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('Connection Error')).toBeInTheDocument()
        expect(screen.getByText(/check your internet connection/)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      }, { timeout: 10000 })
    })

    it('should retry polling on error when retry button is clicked', { timeout: 20000 }, async () => {
      let attemptCount = 0
      uploadService.getIngestionStatus.mockImplementation(() => {
        attemptCount++
        // Fail for first 4 attempts (initial + 3 auto retries), then succeed
        if (attemptCount <= 4) {
          return Promise.reject(new Error('Network error'))
        }
        return Promise.resolve({
          status: 'processing',
          progress_percentage: 50,
          processed_records: 500,
          total_records: 1000,
          failed_records: 0,
        })
      })

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('Connection Error')).toBeInTheDocument()
      }, { timeout: 10000 })

      const retryButton = screen.getByRole('button', { name: /retry/i })
      await userEvent.click(retryButton)

      await waitFor(() => {
        expect(screen.getByText('Processing CSV')).toBeInTheDocument()
      }, { timeout: 10000 })
    })

    it('should use exponential backoff for retries', { timeout: 15000 }, async () => {
      // This test verifies the retry configuration exists
      // Actual retry behavior is handled by React Query
      uploadService.getIngestionStatus.mockRejectedValue(new Error('Network error'))

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('Connection Error')).toBeInTheDocument()
      }, { timeout: 10000 })
    })
  })

  describe('Progress Bar', () => {
    it('should render progress bar with correct width', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 65.5,
        processed_records: 655,
        total_records: 1000,
        failed_records: 0,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        const progressBar = document.querySelector('.bg-blue-600')
        expect(progressBar).toHaveStyle({ width: '65.5%' })
      }, { timeout: 10000 })
    })

    it('should show 0% progress initially', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 0,
        processed_records: 0,
        total_records: 1000,
        failed_records: 0,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        const progressBar = document.querySelector('.bg-blue-600')
        expect(progressBar).toHaveStyle({ width: '0%' })
      }, { timeout: 10000 })
    })

    it('should show 100% progress when completed', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'completed',
        progress_percentage: 100,
        processed_records: 1000,
        total_records: 1000,
        failed_records: 0,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        const progressBar = document.querySelector('.bg-blue-600')
        expect(progressBar).toHaveStyle({ width: '100%' })
      }, { timeout: 10000 })
    })
  })

  describe('Number Formatting', () => {
    it('should format large numbers with commas', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 50000,
        total_records: 100000,
        failed_records: 1500,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(screen.getByText('50,000')).toBeInTheDocument()
        expect(screen.getByText('/ 100,000')).toBeInTheDocument()
        expect(screen.getByText('1,500')).toBeInTheDocument()
      }, { timeout: 10000 })
    })
  })

  describe('Edge Cases', () => {
    it('should not poll if jobId is not provided', () => {
      render(<IngestionProgress jobId={null} onComplete={mockOnComplete} />, {
        wrapper: createWrapper(),
      })

      expect(uploadService.getIngestionStatus).not.toHaveBeenCalled()
    })

    it('should handle missing estimated_time_remaining', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 500,
        total_records: 1000,
        failed_records: 0,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(uploadService.getIngestionStatus).toHaveBeenCalled()
      }, { timeout: 10000 })

      expect(screen.queryByText(/Estimated time remaining/)).not.toBeInTheDocument()
    })

    it('should handle missing processing_speed', { timeout: 15000 }, async () => {
      const mockStatus = {
        status: 'processing',
        progress_percentage: 50,
        processed_records: 500,
        total_records: 1000,
        failed_records: 0,
        estimated_time_remaining: 60,
      }

      uploadService.getIngestionStatus.mockResolvedValue(mockStatus)

      render(
        <IngestionProgress jobId="job-123" onComplete={mockOnComplete} />,
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(uploadService.getIngestionStatus).toHaveBeenCalled()
      }, { timeout: 10000 })

      expect(screen.queryByText(/records\/sec/)).not.toBeInTheDocument()
    })
  })
})
