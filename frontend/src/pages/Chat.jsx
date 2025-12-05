import { useRef, useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useChat } from '../hooks/useChat'
import Navigation from '../components/Layout/Navigation'
import UserMessage from '../components/Chat/UserMessage'
import AssistantMessage from '../components/Chat/AssistantMessage'
import ChatInput from '../components/Chat/ChatInput'
import TypingIndicator from '../components/Chat/TypingIndicator'
import ClearChatButton from '../components/Chat/ClearChatButton'
import ErrorResponseModal from '../components/Chat/ErrorResponseModal'
import { MessageCircle, Sparkles } from 'lucide-react'

const Chat = () => {
  const { user } = useAuth()
  const { messages, isLoading, sendMessage, clearMessages, currentSessionId } = useChat()
  const messagesEndRef = useRef(null)
  const [errorModalData, setErrorModalData] = useState(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Check for error responses and show modal
  useEffect(() => {
    const lastMessage = messages[messages.length - 1]
    if (lastMessage && lastMessage.role === 'assistant') {
      const isError =
        lastMessage.metadata?.response_generation_failed ||
        lastMessage.metadata?.response_generation_skipped ||
        lastMessage.content.includes('⚠️')

      if (isError) {
        setErrorModalData({
          message: lastMessage.content,
          metadata: lastMessage.metadata,
        })
      }
    }
  }, [messages])

  return (
    <div className="h-screen flex flex-col" style={{
      background: 'linear-gradient(to bottom right, #f8fafc, rgba(243, 232, 255, 0.3), rgba(239, 246, 255, 0.3))'
    }}>
      {/* Navigation */}
      <Navigation />

      {/* Chat Header with Clear Button */}
      <div className="shadow-lg" style={{
        background: 'linear-gradient(to right, #8B5CF6, #7C3AED, #3B82F6)',
        backdropFilter: 'blur(12px)'
      }}>
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{
                background: 'rgba(255, 255, 255, 0.2)',
                backdropFilter: 'blur(8px)'
              }}>
                <MessageCircle className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white">
                Graph RAG Chat
              </h2>
            </div>
            <div className="flex items-center space-x-4">
              <ClearChatButton
                onClear={clearMessages}
                disabled={messages.length === 0}
              />
              <span className="text-sm text-white/90">
                {user?.email}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Container - Scrollable */}
      <main className="flex-1 overflow-y-auto px-4 py-8 max-w-5xl mx-auto w-full" data-testid="chat-messages">
        {messages.length === 0 ? (
          // Empty State - Beautiful centered design
          <div className="flex items-center justify-center h-full">
            <div className="text-center animate-fade-in">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl mb-6 shadow-lg animate-float" style={{
                background: 'linear-gradient(135deg, #8B5CF6, #3B82F6)'
              }}>
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                <span className="gradient-text">Ask me anything!</span>
              </h2>
              <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
                I can help you explore careers, discover skills, find jobs, and navigate your career path.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                {[
                  "What skills do I need for data science?",
                  "Show me jobs for Python developers",
                  "Which companies hire ML engineers?",
                  "What's the career path for designers?"
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(suggestion)}
                    className="px-4 py-3 rounded-xl text-sm text-left transition-all duration-200 hover:scale-105 animate-slide-up"
                    style={{
                      background: 'rgba(255, 255, 255, 0.8)',
                      backdropFilter: 'blur(8px)',
                      border: '1px solid rgba(139, 92, 246, 0.2)',
                      boxShadow: '0 4px 12px rgba(139, 92, 246, 0.1)',
                      animationDelay: `${idx * 0.1}s`
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background = 'rgba(139, 92, 246, 0.1)'
                      e.target.style.borderColor = 'rgba(139, 92, 246, 0.4)'
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = 'rgba(255, 255, 255, 0.8)'
                      e.target.style.borderColor = 'rgba(139, 92, 246, 0.2)'
                    }}
                  >
                    <span className="text-gray-700">{suggestion}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          // Messages List
          <div className="space-y-4">
            {messages.map((msg) =>
              msg.role === 'user' ? (
                <UserMessage
                  key={msg.id}
                  content={msg.content}
                  timestamp={msg.timestamp}
                />
              ) : (
                <AssistantMessage
                  key={msg.id}
                  content={msg.content}
                  timestamp={msg.timestamp}
                  sources={msg.sources}
                  metadata={msg.metadata}
                />
              )
            )}
            {isLoading && (
              <TypingIndicator
                message="AI is deeply analyzing your question... (this may take 1-2 minutes for complex queries)"
                showElapsedTime={true}
                sessionId={currentSessionId}
              />
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </main>

      {/* Input Container - Fixed Bottom - Cleaner Design */}
      <div className="px-4 py-5 max-w-4xl mx-auto w-full" style={{
        background: 'transparent'
      }}>
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>

      {/* Error Response Modal */}
      {errorModalData && (
        <ErrorResponseModal
          isOpen={true}
          onClose={() => setErrorModalData(null)}
          errorMessage={errorModalData.message}
          metadata={errorModalData.metadata}
        />
      )}
    </div>
  )
}

export default Chat
