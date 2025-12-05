/**
 * CSVPreviewModal Component Tests
 *
 * Tests for CSV preview modal with table display.
 * Story 2.7: Frontend CSV Upload UI - Test Coverage
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CSVPreviewModal from './CSVPreviewModal'

describe('CSVPreviewModal', () => {
  const mockOnConfirm = vi.fn()
  const mockOnCancel = vi.fn()

  const mockPreviewData = {
    columns: ['id', 'name', 'description'],
    preview_rows: [
      { id: '1', name: 'JavaScript', description: 'Programming language' },
      { id: '2', name: 'React', description: 'UI framework' },
      { id: '3', name: 'Node.js', description: 'Runtime environment' },
    ],
    total_rows: 100,
    has_more: true,
    file_type: 'skills',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should not render when previewData is null', () => {
      const { container } = render(
        <CSVPreviewModal
          previewData={null}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(container).toBeEmptyDOMElement()
    })

    it('should render modal with preview data', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('CSV Preview')).toBeInTheDocument()
      expect(screen.getByText('100 skills found')).toBeInTheDocument()
    })

    it('should display correct file type label for skills', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('100 skills found')).toBeInTheDocument()
    })

    it('should display correct file type label for jobs', () => {
      const jobsData = {
        ...mockPreviewData,
        file_type: 'jobs',
      }

      render(
        <CSVPreviewModal
          previewData={jobsData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('100 jobs found')).toBeInTheDocument()
    })

    it('should format large total_rows with commas', () => {
      const largeData = {
        ...mockPreviewData,
        total_rows: 123456,
      }

      render(
        <CSVPreviewModal
          previewData={largeData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('123,456 skills found')).toBeInTheDocument()
    })
  })

  describe('Table Display', () => {
    it('should render table headers from columns', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('columnheader', { name: /id/i })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: /name/i })).toBeInTheDocument()
      expect(screen.getByRole('columnheader', { name: /description/i })).toBeInTheDocument()
    })

    it('should render all preview rows', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('JavaScript')).toBeInTheDocument()
      expect(screen.getByText('React')).toBeInTheDocument()
      expect(screen.getByText('Node.js')).toBeInTheDocument()
    })

    it('should render all cells for each row', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      // First row
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('JavaScript')).toBeInTheDocument()
      expect(screen.getByText('Programming language')).toBeInTheDocument()

      // Second row
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('React')).toBeInTheDocument()
      expect(screen.getByText('UI framework')).toBeInTheDocument()
    })

    it('should show dash for empty/null cell values', () => {
      const dataWithNulls = {
        columns: ['id', 'name', 'description'],
        preview_rows: [
          { id: '1', name: 'Test', description: null },
          { id: '2', name: null, description: 'Desc' },
        ],
        total_rows: 2,
        has_more: false,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={dataWithNulls}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const dashes = screen.getAllByText('-')
      expect(dashes.length).toBeGreaterThanOrEqual(2)
    })

    it('should convert cell values to strings', () => {
      const dataWithNumbers = {
        columns: ['id', 'count', 'active'],
        preview_rows: [
          { id: 123, count: 456, active: true },
        ],
        total_rows: 1,
        has_more: false,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={dataWithNumbers}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('123')).toBeInTheDocument()
      expect(screen.getByText('456')).toBeInTheDocument()
      expect(screen.getByText('true')).toBeInTheDocument()
    })

    it('should add title attribute with full text to cells', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const cells = screen.getAllByRole('cell')
      const javascriptCell = cells.find(cell => cell.textContent === 'JavaScript')
      expect(javascriptCell).toHaveAttribute('title', 'JavaScript')
    })
  })

  describe('Pagination Information', () => {
    it('should show "more rows" message when has_more is true', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('Showing first 3 rows of 100 total records')).toBeInTheDocument()
    })

    it('should not show "more rows" message when has_more is false', () => {
      const completeData = {
        ...mockPreviewData,
        has_more: false,
      }

      render(
        <CSVPreviewModal
          previewData={completeData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.queryByText(/Showing first/)).not.toBeInTheDocument()
    })

    it('should calculate correct preview count', () => {
      const tenRowsData = {
        columns: ['id'],
        preview_rows: Array.from({ length: 10 }, (_, i) => ({ id: i + 1 })),
        total_rows: 1000,
        has_more: true,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={tenRowsData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('Showing first 10 rows of 1,000 total records')).toBeInTheDocument()
    })
  })

  describe('Action Buttons', () => {
    it('should render Cancel button', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const cancelButtons = screen.getAllByRole('button', { name: /cancel/i })
      expect(cancelButtons.length).toBeGreaterThan(0)
    })

    it('should render Confirm Upload button', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByRole('button', { name: /confirm upload/i })).toBeInTheDocument()
    })

    it('should call onConfirm when Confirm button is clicked', async () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const confirmButton = screen.getByRole('button', { name: /confirm upload/i })
      await userEvent.click(confirmButton)

      expect(mockOnConfirm).toHaveBeenCalled()
    })

    it('should call onCancel when Cancel button is clicked', async () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const cancelButton = screen.getByRole('button', { name: /^cancel$/i })
      await userEvent.click(cancelButton)

      expect(mockOnCancel).toHaveBeenCalled()
    })

    it('should call onCancel when close X button is clicked', async () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const closeButton = screen.getByRole('button', { name: /close preview/i })
      await userEvent.click(closeButton)

      expect(mockOnCancel).toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have accessible close button', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const closeButton = screen.getByRole('button', { name: /close preview/i })
      expect(closeButton).toHaveAccessibleName('Close preview')
    })

    it('should render table with proper structure', () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const table = screen.getByRole('table')
      expect(table).toBeInTheDocument()

      const headers = screen.getAllByRole('columnheader')
      expect(headers).toHaveLength(3)

      const rows = screen.getAllByRole('row')
      expect(rows.length).toBeGreaterThan(1) // Header + data rows
    })

    it('should have clickable buttons', async () => {
      render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const confirmButton = screen.getByRole('button', { name: /confirm upload/i })
      const cancelButton = screen.getByRole('button', { name: /^cancel$/i })
      const closeButton = screen.getByRole('button', { name: /close preview/i })

      expect(confirmButton).toBeEnabled()
      expect(cancelButton).toBeEnabled()
      expect(closeButton).toBeEnabled()
    })
  })

  describe('Modal Overlay', () => {
    it('should render modal with backdrop', () => {
      const { container } = render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const backdrop = container.querySelector('.bg-black.bg-opacity-50')
      expect(backdrop).toBeInTheDocument()
    })

    it('should render modal with proper z-index', () => {
      const { container } = render(
        <CSVPreviewModal
          previewData={mockPreviewData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const backdrop = container.querySelector('.z-50')
      expect(backdrop).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty preview_rows array', () => {
      const emptyData = {
        columns: ['id', 'name'],
        preview_rows: [],
        total_rows: 0,
        has_more: false,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={emptyData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      expect(screen.getByText('0 skills found')).toBeInTheDocument()
      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    it('should handle single column', () => {
      const singleColumnData = {
        columns: ['name'],
        preview_rows: [{ name: 'Test' }],
        total_rows: 1,
        has_more: false,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={singleColumnData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const headers = screen.getAllByRole('columnheader')
      expect(headers).toHaveLength(1)
      expect(screen.getByText('Test')).toBeInTheDocument()
    })

    it('should handle many columns', () => {
      const manyColumnsData = {
        columns: ['col1', 'col2', 'col3', 'col4', 'col5', 'col6', 'col7', 'col8'],
        preview_rows: [
          {
            col1: '1',
            col2: '2',
            col3: '3',
            col4: '4',
            col5: '5',
            col6: '6',
            col7: '7',
            col8: '8',
          },
        ],
        total_rows: 1,
        has_more: false,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={manyColumnsData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const headers = screen.getAllByRole('columnheader')
      expect(headers).toHaveLength(8)
    })

    it('should handle special characters in data', () => {
      const specialCharsData = {
        columns: ['name'],
        preview_rows: [
          { name: 'Test <script>alert("XSS")</script>' },
          { name: 'Test & Ampersand' },
          { name: "Test 'quotes'" },
        ],
        total_rows: 3,
        has_more: false,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={specialCharsData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      // React should escape these automatically
      expect(screen.getByText(/Test <script>/)).toBeInTheDocument()
      expect(screen.getByText(/Test & Ampersand/)).toBeInTheDocument()
    })

    it('should handle very long text in cells', () => {
      const longText = 'A'.repeat(500)
      const longTextData = {
        columns: ['description'],
        preview_rows: [{ description: longText }],
        total_rows: 1,
        has_more: false,
        file_type: 'skills',
      }

      render(
        <CSVPreviewModal
          previewData={longTextData}
          onConfirm={mockOnConfirm}
          onCancel={mockOnCancel}
        />
      )

      const cell = screen.getByText(longText)
      expect(cell).toHaveClass('truncate')
      expect(cell).toHaveAttribute('title', longText)
    })
  })
})
