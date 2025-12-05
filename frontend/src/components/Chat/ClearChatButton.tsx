import { Trash2 } from 'lucide-react'

/**
 * Props for ClearChatButton component
 */
interface ClearChatButtonProps {
  onClear: () => void
  disabled?: boolean
}

/**
 * ClearChatButton component
 *
 * Displays a button to clear all chat messages with confirmation dialog.
 * Disabled when there are no messages to clear.
 *
 * @param onClear - Callback function to clear messages
 * @param disabled - Whether the button should be disabled
 */
const ClearChatButton = ({ onClear, disabled = false }: ClearChatButtonProps) => {
  const handleClick = () => {
    if (window.confirm('Are you sure you want to clear all messages? This cannot be undone.')) {
      onClear()
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      className="inline-flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
      title="Clear chat history"
      aria-label="Clear chat history"
    >
      <Trash2 className="w-4 h-4 mr-2" />
      Clear Chat
    </button>
  )
}

export default ClearChatButton
