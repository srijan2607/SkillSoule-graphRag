/**
 * useChat Hook
 *
 * Custom hook for managing chat state and API interactions.
 * Implements optimistic UI, loading states, error handling, and localStorage persistence.
 */

import { useState, useCallback, useEffect } from "react";
import { sendQuery, APIError } from "@/utils/api";
import { Message } from "@/types/chat";
import { generateMessageId } from "@/utils/chat";
import { logError, logInfo } from "@/utils/logger";
import { ERROR_MESSAGES, TOKEN_REDIRECT_DELAY_MS } from "@/constants/api";

const STORAGE_KEY = "chat_messages";

/**
 * Return type for useChat hook
 */
export interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  currentSessionId: string | null;
}

/**
 * Custom hook for chat functionality
 *
 * Features:
 * - Optimistic UI: User messages appear immediately
 * - Loading states: Disable input while processing
 * - Error handling: Display user-friendly error messages
 * - Timeout handling: 10-second request timeout
 * - localStorage persistence: Messages persist across page reloads
 *
 * @returns Chat state and control functions
 */
export function useChat(): UseChatReturn {
  // Load messages from localStorage on mount
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          // Convert timestamp strings back to Date objects
          return parsed.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          }));
        }
      } catch (e) {
        logError("Failed to parse stored messages from localStorage", e);
      }
    }
    return [];
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        if (messages.length > 0) {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
          logInfo("Messages saved to localStorage", { count: messages.length });
        } else {
          // Clear localStorage if no messages
          localStorage.removeItem(STORAGE_KEY);
        }
      } catch (e) {
        logError("Failed to save messages to localStorage", e);
        // Handle quota exceeded error
        if (e instanceof Error && e.name === "QuotaExceededError") {
          logError("localStorage quota exceeded - clearing old messages", e);
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    }
  }, [messages]);

  /**
   * Send a message to the chat API
   *
   * Implements optimistic UI pattern:
   * 1. Add user message immediately
   * 2. Set loading state
   * 3. Call API
   * 4. Add assistant response or error message
   * 5. Clear loading state
   */
  const sendMessage = useCallback(async (content: string) => {
    // Validate input
    if (!content.trim()) {
      logError("sendMessage called with empty content", null);
      return;
    }

    // Get authentication token
    const token = localStorage.getItem("token");
    if (!token) {
      const errorMsg = ERROR_MESSAGES.NOT_AUTHENTICATED;
      setError(errorMsg);

      // Add error message to chat
      const errorMessage: Message = {
        id: generateMessageId(),
        role: "assistant",
        content: errorMsg,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);

      logError("Authentication token missing", null);
      return;
    }

    // Optimistic UI: Add user message immediately
    const userMessage: Message = {
      id: generateMessageId(),
      role: "user",
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    logInfo("User message added to chat", { content: content.trim() });

    // Set loading state (disables input, shows typing indicator)
    setIsLoading(true);
    setError(null);

    // Generate a unique session ID for this query to track backend processing
    const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setCurrentSessionId(sessionId);

    try {
      // Call query API with timeout handling
      logInfo("Sending query to API", { query: content.trim(), sessionId });
      const response = await sendQuery(content.trim(), token, sessionId);

      logInfo("Query response received", {
        responseLength: response.response.length,
        sourcesCount: response.sources.length,
        processingTime: response.processing_time_ms,
      });

      // Add assistant message with response and sources
      const assistantMessage: Message = {
        id: generateMessageId(),
        role: "assistant",
        content: response.response,
        timestamp: new Date(),
        sources: response.sources,
        metadata: response.metadata,
        processingTime: response.processing_time_ms,
      };

      setMessages((prev) => [...prev, assistantMessage]);

    } catch (err) {
      // Handle API errors
      let errorContent = ERROR_MESSAGES.PROCESSING_ERROR;
      if (err instanceof APIError) {
        // Use specific error message from APIError
        errorContent = err.message;

        // Handle 401 - token expired/invalid
        if (err.statusCode === 401) {
          // Clear token and redirect to login
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          setTimeout(() => {
            window.location.href = "/login";
          }, TOKEN_REDIRECT_DELAY_MS);
        }

        logError("API error in chat", err);
      } else {
        logError("Unexpected error in chat", err);
      }

      // Add error message to chat
      const errorMessage: Message = {
        id: generateMessageId(),
        role: "assistant",
        content: errorContent,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
      setError(errorContent);

    } finally {
      // Always clear loading state
      setIsLoading(false);
      setCurrentSessionId(null);
    }
  }, []);

  /**
   * Clear all messages from chat and localStorage
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem(STORAGE_KEY);
    }
    logInfo("Chat messages cleared", null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    currentSessionId,
  };
}
