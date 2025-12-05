/**
 * Chat utility functions
 */

/**
 * Generate a unique message ID
 *
 * Uses crypto.randomUUID() if available (modern browsers),
 * falls back to timestamp + random string for older browsers.
 *
 * @returns Unique message ID string
 */
export function generateMessageId(): string {
  // Modern browsers support crypto.randomUUID()
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    try {
      const uuid = crypto.randomUUID();
      if (uuid) {
        return uuid;
      }
    } catch (e) {
      // Fall through to fallback
    }
  }

  // Fallback: timestamp + random string
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}
