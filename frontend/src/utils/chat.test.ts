import { describe, it, expect, vi, afterEach } from 'vitest'
import { generateMessageId } from './chat'

describe('chat utilities', () => {
  describe('generateMessageId', () => {
    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('uses crypto.randomUUID when available', () => {
      const mockUUID = '123e4567-e89b-12d3-a456-426614174000'
      vi.spyOn(global.crypto, 'randomUUID').mockReturnValue(mockUUID)

      const id = generateMessageId()

      expect(id).toBe(mockUUID)
    })

    it('falls back to timestamp + random when crypto.randomUUID is not available', () => {
      // Mock crypto to not have randomUUID
      vi.spyOn(global.crypto, 'randomUUID').mockImplementation(() => {
        // Simulate undefined or missing randomUUID
        return undefined as any
      })

      const id = generateMessageId()

      // Should be in format: timestamp-randomstring
      expect(id).toMatch(/^\d+-[a-z0-9]{7}$/)
    })

    it('generates unique IDs on consecutive calls', () => {
      const id1 = generateMessageId()
      const id2 = generateMessageId()

      expect(id1).not.toBe(id2)
    })

    it('generates string IDs', () => {
      const id = generateMessageId()

      expect(typeof id).toBe('string')
      expect(id.length).toBeGreaterThan(0)
    })
  })
})
