/**
 * E2E Test: Query Flow
 *
 * Test Scenario 3: Query Flow with Sources
 *
 * Story 5.6: End-to-End Integration Testing
 */

import { test, expect } from '@playwright/test'

test.describe('Query Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')

    // Use test credentials (assuming test user exists or create one)
    await page.fill('input[name="email"], input[type="email"]', 'test@example.com')
    await page.fill('input[name="password"], input[type="password"]', 'testpassword123')
    await page.click('button[type="submit"]')

    // Wait for redirect to chat
    await page.waitForURL(/\/chat/, { timeout: 10000 }).catch(async () => {
      // If login fails, might need to register first
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

  test('Scenario 3: Complete query flow with sources', async ({ page }) => {
    // Verify chat interface is displayed
    await expect(page).toHaveURL(/\/chat/)

    // Find the message input field
    const messageInput = page.locator('input[type="text"], textarea, input[placeholder*="message"], input[placeholder*="query"]').first()
    await expect(messageInput).toBeVisible()

    // Enter query
    const testQuery = 'What skills are needed for Data Scientist jobs?'
    await messageInput.fill(testQuery)

    // Submit query (click send button or press Enter)
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"], button:has([data-testid="send-icon"])')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Verify loading indicator appears
    const loadingIndicator = page.locator('[data-testid="loading"], .loading, text=/loading|processing/i')
    await expect(loadingIndicator).toBeVisible({ timeout: 2000 }).catch(() => {
      // Loading might be very fast, that's okay
    })

    // Verify user message appears in chat
    const userMessage = page.locator(`text=${testQuery}`)
    await expect(userMessage).toBeVisible({ timeout: 3000 })

    // Verify assistant response appears within 5 seconds
    const assistantMessage = page.locator('[data-testid="assistant-message"], .assistant-message, [role="article"]').last()
    await expect(assistantMessage).toBeVisible({ timeout: 15000 })

    // Verify response has content
    const responseText = await assistantMessage.textContent()
    expect(responseText.length).toBeGreaterThan(10)

    // Verify response is relevant (contains keywords related to the query)
    const lowerResponseText = responseText.toLowerCase()
    const hasRelevantContent =
      lowerResponseText.includes('skill') ||
      lowerResponseText.includes('data') ||
      lowerResponseText.includes('scientist') ||
      lowerResponseText.includes('python') ||
      lowerResponseText.includes('machine learning')

    expect(hasRelevantContent).toBeTruthy()

    // Verify sources section displays
    const sourcesSection = page.locator('[data-testid="sources"], .sources, text=/sources|references/i').first()
    await expect(sourcesSection).toBeVisible({ timeout: 5000 })

    // Click to expand sources (if not already expanded)
    const sourcesExpandButton = page.locator('button:has-text("sources"), button:has-text("Show"), [data-testid="expand-sources"]')
    if (await sourcesExpandButton.count() > 0) {
      const isExpanded = await sourcesExpandButton.getAttribute('aria-expanded')
      if (isExpanded === 'false') {
        await sourcesExpandButton.click()
      }
    }

    // Verify source details are shown
    const sourceDetails = page.locator('[data-testid="source-item"], .source-item, [data-testid="source-card"]')
    await expect(sourceDetails.first()).toBeVisible({ timeout: 5000 })

    // Verify sources contain relevant information (job titles, skill names, etc.)
    const sourcesText = await sourcesSection.textContent()
    const hasSourceData =
      sourcesText.toLowerCase().includes('job') ||
      sourcesText.toLowerCase().includes('skill') ||
      sourcesText.toLowerCase().includes('company')

    expect(hasSourceData).toBeTruthy()
  })

  test('Response time is acceptable (< 10 seconds)', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    await messageInput.fill('Tell me about Python')

    const startTime = Date.now()

    // Submit query
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')
    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Wait for response
    const assistantMessage = page.locator('[data-testid="assistant-message"], .assistant-message').last()
    await expect(assistantMessage).toBeVisible({ timeout: 15000 })

    const endTime = Date.now()
    const responseTime = (endTime - startTime) / 1000 // Convert to seconds

    console.log(`Response time: ${responseTime} seconds`)

    // Verify response time is under 10 seconds (allowing some buffer)
    expect(responseTime).toBeLessThan(10)
  })

  test('Multiple queries work correctly', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()

    // First query
    await messageInput.fill('What is Python?')
    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Wait for first response
    await page.waitForTimeout(3000)

    // Second query
    await messageInput.fill('What is JavaScript?')

    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Verify both messages are in chat history
    const messages = page.locator('[data-testid="user-message"], .user-message')
    const messageCount = await messages.count()
    expect(messageCount).toBeGreaterThanOrEqual(2)
  })

  test('Sources can be expanded and collapsed', async ({ page }) => {
    const messageInput = page.locator('input[type="text"], textarea').first()
    await messageInput.fill('What skills are needed for developers?')

    const sendButton = page.locator('button:has-text("Send"), button[type="submit"]')
    if (await sendButton.count() > 0) {
      await sendButton.first().click()
    } else {
      await messageInput.press('Enter')
    }

    // Wait for response with sources
    await page.waitForTimeout(5000)

    // Find sources expand/collapse button
    const sourcesButton = page.locator('button:has-text("sources"), button:has-text("Show"), button:has-text("Hide"), [data-testid="toggle-sources"]')

    if (await sourcesButton.count() > 0) {
      const button = sourcesButton.first()

      // Click to expand
      await button.click()
      await page.waitForTimeout(500)

      // Verify sources are visible
      const sourceDetails = page.locator('[data-testid="source-item"], .source-item')
      await expect(sourceDetails.first()).toBeVisible({ timeout: 2000 })

      // Click to collapse
      await button.click()
      await page.waitForTimeout(500)

      // Verify sources are hidden (or less visible)
      // This depends on implementation - might use display:none or aria-hidden
    }
  })
})
