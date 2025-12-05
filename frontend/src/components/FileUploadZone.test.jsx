/**
 * FileUploadZone Component Tests
 *
 * Tests for drag-and-drop file upload with validation.
 * Story 2.7: Frontend CSV Upload UI - Test Coverage
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FileUploadZone from './FileUploadZone'

describe('FileUploadZone', () => {
  const mockOnFileSelect = vi.fn()
  const defaultProps = {
    title: 'Upload Skills CSV',
    fileType: 'skills',
    onFileSelect: mockOnFileSelect,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('should render upload zone with title', () => {
      render(<FileUploadZone {...defaultProps} />)

      expect(screen.getByText('Upload Skills CSV')).toBeInTheDocument()
      expect(screen.getByText(/Drag and drop your CSV file/)).toBeInTheDocument()
      expect(screen.getByText(/.csv files only \(max 500MB\)/)).toBeInTheDocument()
    })

    it('should show loading state when isLoading is true', () => {
      render(<FileUploadZone {...defaultProps} isLoading={true} />)

      expect(screen.getByText('Uploading...')).toBeInTheDocument()
      expect(screen.queryByText(/Drag and drop/)).not.toBeInTheDocument()
    })

    it('should render hidden file input with correct attributes', () => {
      render(<FileUploadZone {...defaultProps} />)

      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).toBeInTheDocument()
      expect(fileInput).toHaveAttribute('accept', '.csv')
      expect(fileInput).toHaveClass('hidden')
    })
  })

  describe('File Selection via Input', () => {
    it('should call onFileSelect with valid CSV file', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test,data'], 'test.csv', { type: 'text/csv' })
      const input = document.querySelector('input[type="file"]')

      await userEvent.upload(input, file)

      expect(mockOnFileSelect).toHaveBeenCalledWith(file)
    })

    it('should reject file without .csv extension', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test'], 'test.txt', { type: 'text/plain' })
      const input = document.querySelector('input[type="file"]')

      // Simulate change event directly for more control
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      })
      fireEvent.change(input)

      await waitFor(() => {
        expect(mockOnFileSelect).not.toHaveBeenCalled()
        expect(screen.getByText('Only CSV files are allowed')).toBeInTheDocument()
      })
    })

    it('should reject file with wrong MIME type (SECURITY-001)', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test'], 'malicious.csv', { type: 'application/x-msdownload' })
      const input = document.querySelector('input[type="file"]')

      await userEvent.upload(input, file)

      expect(mockOnFileSelect).not.toHaveBeenCalled()
      expect(screen.getByText('Invalid file type. Only CSV files are allowed')).toBeInTheDocument()
    })

    it('should reject file exceeding 500MB limit', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const largeContent = 'x'.repeat(501 * 1024 * 1024)
      const file = new File([largeContent], 'large.csv', { type: 'text/csv' })
      const input = document.querySelector('input[type="file"]')

      await userEvent.upload(input, file)

      expect(mockOnFileSelect).not.toHaveBeenCalled()
      expect(screen.getByText('File size exceeds 500MB limit')).toBeInTheDocument()
    })

    it('should accept CSV file at exactly 500MB', async () => {
      render(<FileUploadZone {...defaultProps} />)

      // Create a file exactly at 500MB limit
      const exactSize = 500 * 1024 * 1024
      const file = new File([''], 'exact.csv', { type: 'text/csv' })
      Object.defineProperty(file, 'size', { value: exactSize })

      const input = document.querySelector('input[type="file"]')

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      })
      fireEvent.change(input)

      expect(mockOnFileSelect).toHaveBeenCalledWith(file)
    })

    it('should reset file input after selection', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })
      const input = document.querySelector('input[type="file"]')

      await userEvent.upload(input, file)

      expect(input.value).toBe('')
    })
  })

  describe('Drag and Drop', () => {
    it('should accept valid CSV file via drag and drop', () => {
      render(<FileUploadZone {...defaultProps} />)

      const dropZone = screen.getByText(/Drag and drop/).closest('div').parentElement

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })
      const dataTransfer = {
        files: [file],
      }

      fireEvent.drop(dropZone, { dataTransfer })

      expect(mockOnFileSelect).toHaveBeenCalledWith(file)
    })

    it('should show drag over visual feedback', () => {
      render(<FileUploadZone {...defaultProps} />)

      const dropZone = screen.getByText(/Drag and drop/).closest('div').parentElement

      fireEvent.dragOver(dropZone)

      expect(dropZone).toHaveClass('border-blue-500', 'bg-blue-50')
    })

    it('should remove drag over feedback on drag leave', () => {
      render(<FileUploadZone {...defaultProps} />)

      const dropZone = screen.getByText(/Drag and drop/).closest('div').parentElement

      fireEvent.dragOver(dropZone)
      expect(dropZone).toHaveClass('border-blue-500')

      fireEvent.dragLeave(dropZone)
      expect(dropZone).not.toHaveClass('border-blue-500')
    })

    it('should remove drag over feedback after drop', () => {
      render(<FileUploadZone {...defaultProps} />)

      const dropZone = screen.getByText(/Drag and drop/).closest('div').parentElement

      fireEvent.dragOver(dropZone)
      expect(dropZone).toHaveClass('border-blue-500')

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })
      fireEvent.drop(dropZone, { dataTransfer: { files: [file] } })

      expect(dropZone).not.toHaveClass('border-blue-500')
    })

    it('should validate dropped file', () => {
      render(<FileUploadZone {...defaultProps} />)

      const dropZone = screen.getByText(/Drag and drop/).closest('div').parentElement

      const file = new File(['test'], 'test.txt', { type: 'text/plain' })
      fireEvent.drop(dropZone, { dataTransfer: { files: [file] } })

      expect(mockOnFileSelect).not.toHaveBeenCalled()
      expect(screen.getByText('Only CSV files are allowed')).toBeInTheDocument()
    })
  })

  describe('Click to Select', () => {
    it('should trigger file input on zone click', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const dropZone = screen.getByText(/Drag and drop/).closest('div').parentElement
      const fileInput = document.querySelector('input[type="file"]')

      const clickSpy = vi.spyOn(fileInput, 'click')

      await userEvent.click(dropZone)

      expect(clickSpy).toHaveBeenCalled()
    })

    it('should not trigger file input when loading', async () => {
      render(<FileUploadZone {...defaultProps} isLoading={true} />)

      const dropZone = screen.getByText('Uploading...').closest('div').parentElement.parentElement
      const fileInput = document.querySelector('input[type="file"]')

      const clickSpy = vi.spyOn(fileInput, 'click')

      await userEvent.click(dropZone)

      expect(clickSpy).not.toHaveBeenCalled()
    })
  })

  describe('Loading State', () => {
    it('should disable interactions when loading', () => {
      render(<FileUploadZone {...defaultProps} isLoading={true} />)

      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).toBeDisabled()

      const dropZone = screen.getByText('Uploading...').closest('div').parentElement
      expect(dropZone).toHaveClass('opacity-50', 'cursor-not-allowed')
    })

    it('should ignore drag events when loading', () => {
      render(<FileUploadZone {...defaultProps} isLoading={true} />)

      const dropZone = screen.getByText('Uploading...').closest('div').parentElement.parentElement

      fireEvent.dragOver(dropZone)
      expect(dropZone).not.toHaveClass('border-blue-500')
    })

    it('should ignore drop events when loading', () => {
      render(<FileUploadZone {...defaultProps} isLoading={true} />)

      const dropZone = screen.getByText('Uploading...').closest('div').parentElement.parentElement

      const file = new File(['test'], 'test.csv', { type: 'text/csv' })
      fireEvent.drop(dropZone, { dataTransfer: { files: [file] } })

      expect(mockOnFileSelect).not.toHaveBeenCalled()
    })
  })

  describe('Error Display', () => {
    it('should show error message with icon', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test'], 'test.txt', { type: 'text/plain' })
      const input = document.querySelector('input[type="file"]')

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      })
      fireEvent.change(input)

      await waitFor(() => {
        const errorMessage = screen.getByText('Only CSV files are allowed')
        expect(errorMessage).toBeInTheDocument()
        expect(errorMessage.parentElement).toHaveClass('text-red-600')
      })
    })

    it('should clear previous error when new valid file is selected', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const input = document.querySelector('input[type="file"]')

      // First, upload invalid file
      const invalidFile = new File(['test'], 'test.txt', { type: 'text/plain' })
      Object.defineProperty(input, 'files', {
        value: [invalidFile],
        writable: false,
        configurable: true, // Allow redefining later
      })
      fireEvent.change(input)

      await waitFor(() => {
        expect(screen.getByText('Only CSV files are allowed')).toBeInTheDocument()
      })

      // Then, upload valid file
      const validFile = new File(['test'], 'test.csv', { type: 'text/csv' })
      Object.defineProperty(input, 'files', {
        value: [validFile],
        writable: false,
        configurable: true,
      })
      fireEvent.change(input)

      await waitFor(() => {
        expect(screen.queryByText('Only CSV files are allowed')).not.toBeInTheDocument()
      })
    })
  })

  describe('Edge Cases', () => {
    it('should handle file with no type (missing MIME)', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test'], 'test.csv', { type: '' })
      const input = document.querySelector('input[type="file"]')

      await userEvent.upload(input, file)

      // Should pass if extension is correct, even without MIME type
      expect(mockOnFileSelect).toHaveBeenCalledWith(file)
    })

    it('should handle file with undefined type', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test'], 'test.csv')
      Object.defineProperty(file, 'type', { value: undefined })

      const input = document.querySelector('input[type="file"]')

      await userEvent.upload(input, file)

      expect(mockOnFileSelect).toHaveBeenCalledWith(file)
    })

    it('should handle drop event with no files', () => {
      render(<FileUploadZone {...defaultProps} />)

      const dropZone = screen.getByText(/Drag and drop/).closest('div').parentElement

      fireEvent.drop(dropZone, { dataTransfer: { files: [] } })

      expect(mockOnFileSelect).not.toHaveBeenCalled()
    })

    it('should handle file input change with no files', () => {
      render(<FileUploadZone {...defaultProps} />)

      const input = document.querySelector('input[type="file"]')

      fireEvent.change(input, { target: { files: [] } })

      expect(mockOnFileSelect).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have accessible file input', () => {
      render(<FileUploadZone {...defaultProps} />)

      const input = document.querySelector('input[type="file"]')
      expect(input).toHaveAttribute('type', 'file')
      expect(input).toHaveAttribute('accept', '.csv')
    })

    it('should show clear error message', async () => {
      render(<FileUploadZone {...defaultProps} />)

      const file = new File(['test'], 'test.txt', { type: 'text/plain' })
      const input = document.querySelector('input[type="file"]')

      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      })
      fireEvent.change(input)

      await waitFor(() => {
        const errorElement = screen.getByText('Only CSV files are allowed')
        expect(errorElement).toBeVisible()
      })
    })
  })

  describe('Multiple File Types Props', () => {
    it('should handle different file types (skills)', () => {
      render(<FileUploadZone {...defaultProps} fileType="skills" />)
      expect(screen.getByText('Upload Skills CSV')).toBeInTheDocument()
    })

    it('should handle different file types (jobs)', () => {
      render(<FileUploadZone {...defaultProps} title="Upload Jobs CSV" fileType="jobs" />)
      expect(screen.getByText('Upload Jobs CSV')).toBeInTheDocument()
    })
  })
})
