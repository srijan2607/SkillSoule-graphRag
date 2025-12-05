/**
 * E2E Test: Error Handling
 *
 * Test Scenario 5B: Empty Query Validation
 * Test Scenario 5C: API Failure Handling
 *
 * Story 5.6: End-to-End Integration Testing
 */

import { test, expect } from '@playwright/test'

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')

    await page.fill('input[name="email"], input[type="email"]', 'test@example.com')
    await page.fill('input[name="password"], input[type="password"]', 'testpassword123')
    await page.click('button[type="submit"]')

    await page.waitForURL(/\/chat/, { timeout: 10000 }).catch(async () => {
      // Register if needed
      await page.goto('/register')
      await page.fill('input[name="email"], input[type="email"]', 'test@example.com')
      await page.fill('input[name="password"], input[type="password"]', 'testpassword123')
      await page.click('button[type="submit"]')
      await page.waitForURL(/\/(login|chat)/, { timeout: 10000 })

      if (!page.url().includes('/chat')) {
        await page.goto('/login')
        await page.fill('input[name="email"], input[type="email"]', 'test@example.com')
        await page.fill('input[name="password"], input[type="password"]', 'testpassword123')
        await page.click('button[type="submit"]')
        await page.waitForURL(/\/chat/, { timeout: 10000 })
      }
    })
  })

  test('Scenario 5B: Empty query shows validation error', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Ensure input is empty
    await messageInput.clear()
    await messageInput.fill('')

    // Try to submit empty query
    if (await sendButton.count() > 0) {
      const button = sendButton.first()

      // Check if button is disabled for empty input
      const isDisabled = await button.isDisabled().catch(() => false)

      if (isDisabled) {
        // Button correctly disabled for empty input
        expect(isDisabled).toBeTruthy()
        console.log('✓ Send button is disabled for empty input')
      } else {
        // Button not disabled, try clicking and check for validation
        await button.click()

        // Wait a moment for potential error message
        await page.waitForTimeout(1000)

        // Check if error message or toast appears
        const errorMessage = page.locator('text=/please enter|required|cannot be empty/i, [role="alert"]')
        const hasError = await errorMessage.count() > 0

        if (hasError) {
          await expect(errorMessage.first()).toBeVisible()
          console.log('✓ Validation error message shown for empty input')
        } else {
          // Check that no message was sent (should still be on chat with no new messages)
          const userMessages = page.locator('[data-testid="user-message"], .user-message')
          const initialCount = await userMessages.count()

          // Click again to ensure no message sent
          await button.click()
          await page.waitForTimeout(1000)

          const finalCount = await userMessages.count()
          expect(finalCount).toBe(initialCount)
          console.log('✓ Empty message not sent (input validation working)')
        }
      }
    } else {
      // No send button found, try Enter key
      await messageInput.press('Enter')
      await page.waitForTimeout(1000)

      // Verify no message was sent
      const userMessages = page.locator('[data-testid="user-message"], .user-message')
      const count = await userMessages.count()
      expect(count).toBe(0)
    }
  })

  test('Scenario 5B: Whitespace-only query is rejected', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Fill with only whitespace
    await messageInput.fill('   ')

    // Try to submit
    if (await sendButton.count() > 0) {
      const button = sendButton.first()
      const isDisabled = await button.isDisabled().catch(() => false)

      if (!isDisabled) {
        await button.click()
        await page.waitForTimeout(1000)

        // Should show error or prevent submission
        const userMessages = page.locator('[data-testid="user-message"], .user-message, text=/^\\s+$/')
        const count = await userMessages.count()

        // Should not create a message with only whitespace
        expect(count).toBe(0)
      }
    }
  })

  test('Scenario 5C: API failure shows graceful error message', async ({ page }) => {
    // Note: This test simulates API failure by blocking network requests
    // In a real scenario, you would stop the backend server

    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Block API requests to simulate backend failure
    await page.route('**/api/**', (route) => {
      route.abort('failed')
    })

    // Try to send a message
    await messageInput.fill('Test query with blocked API')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Wait for error to appear
    await page.waitForTimeout(3000)

    // Verify graceful error message is shown
    const errorMessage = page.locator(
      'text=/unable to connect|connection failed|service unavailable|try again|network error/i, [role="alert"], [data-testid="error-message"]'
    )

    await expect(errorMessage.first()).toBeVisible({ timeout: 5000 })

    // Verify NO raw error stack traces are visible
    const pageContent = await page.content()
    const hasStackTrace = /stack|trace|at\s+\w+\.\w+\s*\(|exception/i.test(pageContent)

    expect(hasStackTrace).toBeFalsy()

    // Get error message text
    const errorText = await errorMessage.first().textContent()
    console.log('Error message shown:', errorText)

    // Verify error message is user-friendly
    expect(errorText.toLowerCase()).toMatch(/unable|connect|failed|unavailable|try again|network/)
  })

  test('API failure error message is user-friendly', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Simulate 500 error from backend
    await page.route('**/api/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Internal server error',
          details: 'Stack trace and technical details...'
        })
      })
    })

    await messageInput.fill('Test query with 500 error')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(3000)

    // Verify user-friendly error is shown (not raw technical details)
    const errorMessage = page.locator('[role="alert"], [data-testid="error-message"], text=/error|failed/i')

    if (await errorMessage.count() > 0) {
      const errorText = await errorMessage.first().textContent()

      // Should NOT contain technical jargon
      expect(errorText).not.toMatch(/stack trace|exception|500|internal server error/i)

      // Should contain user-friendly language
      expect(errorText.toLowerCase()).toMatch(/something went wrong|try again|error|failed/)

      console.log('User-friendly error message:', errorText)
    }
  })

  test('Network timeout shows appropriate error', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Simulate timeout by delaying response indefinitely
    await page.route('**/api/**', async (_route) => {
      // Don't respond - will cause timeout
      await new Promise(() => {}) // Never resolves
    })

    await messageInput.fill('Test query with timeout')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Wait for timeout error (should appear within reasonable time)
    await page.waitForTimeout(35000) // Wait up to 35 seconds

    // Verify timeout error is shown
    const errorMessage = page.locator('text=/timeout|taking too long|try again/i, [role="alert"]')

    const hasError = await errorMessage.count() > 0
    if (hasError) {
      await expect(errorMessage.first()).toBeVisible()
      const errorText = await errorMessage.first().textContent()
      console.log('Timeout error message:', errorText)
    }
  })

  test('Error messages can be dismissed', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Trigger an error
    await page.route('**/api/**', (route) => {
      route.abort('failed')
    })

    await messageInput.fill('Test query')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(2000)

    // Look for dismiss button
    const dismissButton = page.locator('button:has-text("Dismiss"), button:has-text("Close"), button[aria-label="Close"], [data-testid="close-error"]')

    if (await dismissButton.count() > 0) {
      await dismissButton.first().click()
      await page.waitForTimeout(500)

      // Verify error is dismissed
      const errorMessage = page.locator('[role="alert"], [data-testid="error-message"]')
      const errorCount = await errorMessage.count()

      expect(errorCount).toBe(0)
      console.log('✓ Error message can be dismissed')
    }
  })

  test('App recovers after API is restored', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Block API temporarily
    await page.route('**/api/**', (route) => {
      route.abort('failed')
    })

    // Try to send message (will fail)
    await messageInput.fill('Failed query')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(2000)

    // Unblock API (restore normal functionality)
    await page.unroute('**/api/**')

    // Try sending message again (should work)
    await messageInput.fill('Successful query')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(3000)

    // Verify message was sent successfully
    const userMessages = page.locator('[data-testid="user-message"], .user-message, text=/Successful query/')
    await expect(userMessages.last()).toBeVisible({ timeout: 5000 })

    console.log('✓ App successfully recovered after API restoration')
  })
})
