/**
 * CSV Preview Modal Component
 *
 * Displays CSV data preview in a modal table.
 * Shows first 10 rows with column headers and total row count.
 * Provides confirm/cancel actions.
 *
 * Story 2.7: Frontend CSV Upload UI
 */

import { X } from 'lucide-react'

export default function CSVPreviewModal({ previewData, onConfirm, onCancel }) {
  if (!previewData) return null

  const { columns, preview_rows, total_rows, has_more, file_type } = previewData

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b flex-shrink-0">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">CSV Preview</h2>
            <p className="text-gray-600 mt-1">
              {total_rows.toLocaleString()}{' '}
              {file_type === 'skills' ? 'skills' : 'jobs'} found
            </p>
          </div>
          <button
            onClick={onCancel}
            className="p-2 hover:bg-gray-100 rounded-full transition"
            aria-label="Close preview"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Preview Table - Scrollable */}
        <div className="overflow-auto flex-1 p-6">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                {columns.map((col, idx) => (
                  <th
                    key={idx}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {preview_rows.map((row, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  {columns.map((col, colIdx) => (
                    <td
                      key={colIdx}
                      className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate"
                      title={row[col]?.toString() || ''}
                    >
                      {row[col]?.toString() || '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          {has_more && (
            <p className="text-center text-sm text-gray-500 mt-4">
              Showing first {preview_rows.length} rows of {total_rows.toLocaleString()} total
              records
            </p>
          )}
        </div>

        {/* Footer - Always Visible */}
        <div className="flex items-center justify-end gap-4 p-6 border-t bg-gray-50 flex-shrink-0">
          <button
            onClick={onCancel}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Confirm Upload
          </button>
        </div>
      </div>
    </div>
  )
}
