/**
 * API Configuration Constants
 * 
 * Centralized configuration for API calls, timeouts, and error messages
 */

/**
 * API timeout configuration (in milliseconds)
 *
 * Increased to 210 seconds (3.5 minutes) to support reasoning models like:
 * - DeepSeek-R1 (30-120s response time)
 * - OpenAI o1-preview (20-90s response time)
 * - OpenAI o1-mini (15-60s response time)
 *
 * This includes:
 * - Backend workflow timeout: 200s
 * - Network overhead buffer: 10s
 */
export const API_TIMEOUT_MS = 210000; // 3.5 minutes for reasoning models

/**
 * API base URL from environment or default
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * API endpoints
 */
export const API_ENDPOINTS = {
  QUERY: "/query/ask",
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
} as const;

/**
 * User-friendly error messages for different scenarios
 */
export const ERROR_MESSAGES = {
  // Authentication errors
  NOT_AUTHENTICATED: "Not authenticated. Please log in.",
  AUTHENTICATION_FAILED: "Invalid email or password.",
  TOKEN_EXPIRED: "Your session has expired. Please log in again.",
  
  // API errors
  INVALID_QUERY: "Invalid query. Please try again.",
  SERVER_ERROR: "Server error. Please try again later.",
  TIMEOUT: "Request timed out. This query is very complex - please try breaking it into smaller questions.",
  CONNECTION_ERROR: "Connection error. Please check your internet.",
  
  // Generic errors
  UNEXPECTED_ERROR: "An unexpected error occurred. Please try again.",
  PROCESSING_ERROR: "Sorry, I couldn't process that. Please try again.",
  
  // Validation errors
  EMPTY_MESSAGE: "Please enter a message.",
  MISSING_TOKEN: "Authentication token missing.",
} as const;

/**
 * HTTP status code messages
 */
export const HTTP_STATUS_MESSAGES: Record<number, string> = {
  400: ERROR_MESSAGES.INVALID_QUERY,
  401: ERROR_MESSAGES.NOT_AUTHENTICATED,
  403: "Access denied.",
  404: "Resource not found.",
  500: ERROR_MESSAGES.SERVER_ERROR,
  502: "Service temporarily unavailable.",
  503: "Service unavailable.",
};

/**
 * Token redirect delay (in milliseconds)
 * Delay before redirecting to login after 401 error
 */
export const TOKEN_REDIRECT_DELAY_MS = 2000; // 2 seconds
