/**
 * Simple logging utility for frontend application
 * 
 * Provides structured logging with different levels.
 * In production, error logs could be sent to external monitoring service.
 */

type LogLevel = 'info' | 'warn' | 'error' | 'debug';

interface LogContext {
  [key: string]: unknown;
}

/**
 * Log levels configuration
 */
const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/**
 * Current environment-based log level
 */
const CURRENT_LOG_LEVEL: LogLevel = 
  (import.meta.env.MODE === 'production' ? 'warn' : 'debug') as LogLevel;

/**
 * Format log message with timestamp and context
 */
function formatLog(level: LogLevel, message: string, context: LogContext | null): string {
  const timestamp = new Date().toISOString();
  const contextStr = context ? ` | ${JSON.stringify(context)}` : '';
  return `[${timestamp}] [${level.toUpperCase()}] ${message}${contextStr}`;
}

/**
 * Check if log level should be output
 */
function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[CURRENT_LOG_LEVEL];
}

/**
 * Log info message
 * 
 * @param message - Log message
 * @param context - Optional context object
 */
export function logInfo(message: string, context: LogContext | null): void {
  if (shouldLog('info')) {
    console.info(formatLog('info', message, context));
  }
}

/**
 * Log warning message
 * 
 * @param message - Log message  
 * @param context - Optional context object
 */
export function logWarn(message: string, context: LogContext | null): void {
  if (shouldLog('warn')) {
    console.warn(formatLog('warn', message, context));
  }
}

/**
 * Log error message
 * 
 * @param message - Log message
 * @param error - Error object or context
 */
export function logError(message: string, error: Error | unknown | null): void {
  if (shouldLog('error')) {
    const errorContext = error instanceof Error 
      ? { name: error.name, message: error.message, stack: error.stack }
      : error;
    console.error(formatLog('error', message, errorContext as LogContext));
  }
}

/**
 * Log debug message (only in development)
 * 
 * @param message - Log message
 * @param context - Optional context object
 */
export function logDebug(message: string, context: LogContext | null): void {
  if (shouldLog('debug')) {
    console.debug(formatLog('debug', message, context));
  }
}
