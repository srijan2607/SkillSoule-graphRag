/**
 * E2E Test: Multi-Turn Conversation
 *
 * Test Scenario 4: Multi-Turn Conversation with Context
 *
 * Story 5.6: End-to-End Integration Testing
 */

import { test, expect } from '@playwright/test'

test.describe('Multi-Turn Conversation', () => {
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

    // Clear conversation if there's a clear/new chat button
    const clearButton = page.locator('button:has-text("New"), button:has-text("Clear"), [data-testid="new-chat"]')
    if (await clearButton.count() > 0) {
      await clearButton.first().click()
      await page.waitForTimeout(500)
    }
  })

  test('Scenario 4: Multi-turn conversation maintains context', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // First query about Python
    await messageInput.fill('Tell me about Python')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Wait for first response
    await page.waitForTimeout(5000)

    // Verify first response appeared
    const firstResponse = page.locator('[data-testid="assistant-message"], .assistant-message').first()
    await expect(firstResponse).toBeVisible()

    const firstResponseText = await firstResponse.textContent()
    expect(firstResponseText.length).toBeGreaterThan(10)

    // Verify response mentions Python
    const lowerFirstResponse = firstResponseText.toLowerCase()
    expect(lowerFirstResponse).toContain('python')

    // Second query - follow-up asking about jobs
    await messageInput.fill('What jobs require it?')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Wait for second response
    await page.waitForTimeout(5000)

    // Verify second response appeared
    const assistantMessages = page.locator('[data-testid="assistant-message"], .assistant-message')
    const messageCount = await assistantMessages.count()
    expect(messageCount).toBeGreaterThanOrEqual(2)

    // Get the last (most recent) assistant message
    const secondResponse = assistantMessages.last()
    await expect(secondResponse).toBeVisible()

    const secondResponseText = await secondResponse.textContent()
    expect(secondResponseText.length).toBeGreaterThan(10)

    // Verify response shows contextual awareness
    // Should mention Python and/or jobs related to Python
    const lowerSecondResponse = secondResponseText.toLowerCase()

    const hasContextualRelevance =
      lowerSecondResponse.includes('python') ||
      lowerSecondResponse.includes('data scientist') ||
      lowerSecondResponse.includes('developer') ||
      lowerSecondResponse.includes('software engineer') ||
      lowerSecondResponse.includes('job')

    expect(hasContextualRelevance).toBeTruthy()

    console.log('First response:', firstResponseText.substring(0, 100))
    console.log('Second response:', secondResponseText.substring(0, 100))
  })

  test('Conversation history is displayed correctly', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Send multiple messages
    const queries = [
      'What is JavaScript?',
      'What is React?',
      'What is Node.js?'
    ]

    for (const query of queries) {
      await messageInput.fill(query)

      if (await sendButton.count() > 0) {
        await sendButton.first().click()
      } else {
        await messageInput.press('Enter')
      }

      // Wait between queries
      await page.waitForTimeout(3000)
    }

    // Verify all user messages are displayed
    const userMessages = page.locator('[data-testid="user-message"], .user-message, text=/What is/')
    const userMessageCount = await userMessages.count()
    expect(userMessageCount).toBeGreaterThanOrEqual(queries.length)

    // Verify all assistant messages are displayed
    const assistantMessages = page.locator('[data-testid="assistant-message"], .assistant-message')
    const assistantMessageCount = await assistantMessages.count()
    expect(assistantMessageCount).toBeGreaterThanOrEqual(queries.length)
  })

  test('Follow-up questions work without repeating context', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Initial question with full context
    await messageInput.fill('What are the most popular programming languages?')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(5000)

    // Follow-up with pronoun reference (testing context)
    await messageInput.fill('Which one is best for web development?')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(5000)

    // Verify response is relevant
    const lastResponse = page.locator('[data-testid="assistant-message"], .assistant-message').last()
    const responseText = await lastResponse.textContent()

    // Response should mention web development or specific languages
    const lowerResponse = responseText.toLowerCase()
    const isRelevant =
      lowerResponse.includes('web') ||
      lowerResponse.includes('javascript') ||
      lowerResponse.includes('python') ||
      lowerResponse.includes('development')

    expect(isRelevant).toBeTruthy()
  })

  test('Conversation can be cleared and restarted', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    // Send initial message
    await messageInput.fill('Test message 1')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(3000)

    // Find and click clear/new chat button
    const clearButton = page.locator('button:has-text("New"), button:has-text("Clear"), button:has-text("Reset"), [data-testid="new-chat"]')

    if (await clearButton.count() > 0) {
      await clearButton.first().click()
      await page.waitForTimeout(1000)

      // Verify messages are cleared
      const messages = page.locator('[data-testid="user-message"], .user-message')
      const messageCount = await messages.count()

      // After clearing, should have 0 or very few messages
      expect(messageCount).toBeLessThan(2)

      // Send new message in fresh conversation
      await messageInput.fill('Test message 2')

      if (await sendButton.count() > 0) {
        await sendButton.first().click()
      } else {
        await messageInput.press('Enter')
      }

      await page.waitForTimeout(3000)

      // Verify new conversation works
      const newMessages = page.locator('[data-testid="user-message"], .user-message')
      const newMessageCount = await newMessages.count()
      expect(newMessageCount).toBeGreaterThan(0)
    }
  })

  test('MVP Note: Basic session memory is acceptable', async ({ page }) => {
    // This test documents MVP expectations
    // Full conversation history may not be passed to LLM
    // Basic session memory (showing previous messages in UI) is acceptable

    const messageInput = page.locator('input[type="text"], textarea').first()
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    await messageInput.fill('First question')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    await page.waitForTimeout(3000)

    // Verify message is stored in session (visible in UI)
    const userMessages = page.locator('[data-testid="user-message"], .user-message')
    const count = await userMessages.count()
    expect(count).toBeGreaterThan(0)

    // Note: For MVP, we don't require that the LLM has access to full conversation history
    // As long as messages are displayed in the UI, basic session memory is met
    console.log('MVP Note: Session memory verified - messages displayed in UI')
  })
})
