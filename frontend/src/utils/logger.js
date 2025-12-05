/**
 * Logger Utility
 *
 * Centralized logging that can be configured for different environments.
 * CODE-001: Replaces console.error for production-safe error logging.
 */

const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development'

/**
 * Log error messages
 * In production, this could be replaced with a service like Sentry, LogRocket, etc.
 */
export const logError = (message, error) => {
  if (isDevelopment) {
    console.error(message, error)
  }

  // In production, send to logging service
  // Example: Sentry.captureException(error, { extra: { message } })
}

/**
 * Log warning messages
 */
export const logWarning = (message, data) => {
  if (isDevelopment) {
    console.warn(message, data)
  }

  // In production, send to logging service
}

/**
 * Log info messages
 */
export const logInfo = (message, data) => {
  if (isDevelopment) {
    console.log(message, data)
  }

  // In production, send to logging service
}

export default {
  error: logError,
  warning: logWarning,
  info: logInfo,
}
