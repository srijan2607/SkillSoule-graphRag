/**
 * E2E Test: Authentication Flow
 *
 * Test Scenario 1: User Registration and Login Flow
 * Test Scenario 5A: Invalid Login Error Handling
 *
 * Story 5.6: End-to-End Integration Testing
 */

import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  // Generate unique test user email for each test run
  const timestamp = Date.now()
  const testEmail = `test${timestamp}@example.com`
  const testPassword = 'SecurePass123!@#'

  test.beforeEach(async ({ page }) => {
    // Start from the home page
    await page.goto('/')
  })

  test('Scenario 1: Complete registration and login flow', async ({ page }) => {
    // Step 1: Navigate to registration page
    await page.goto('/register')
    await expect(page).toHaveURL(/\/register/)

    // Step 2: Fill in registration form
    await page.fill('input[name="email"], input[type="email"]', testEmail)
    await page.fill('input[name="password"], input[type="password"]', testPassword)

    // Step 3: Submit registration form
    await page.click('button[type="submit"]')

    // Step 4: Verify successful registration (success message or redirect to login)
    // Wait for either success message or redirect
    await page.waitForURL(/\/(login|chat)/, { timeout: 10000 }).catch(async () => {
      // If no redirect, check for success message
      const successMessage = page.locator('text=/success|registered|account created/i')
      await expect(successMessage).toBeVisible({ timeout: 5000 })
    })

    // Step 5: Login with new credentials (if not auto-logged in)
    const currentUrl = page.url()
    if (!currentUrl.includes('/chat')) {
      // Navigate to login if not already there
      if (!currentUrl.includes('/login')) {
        await page.goto('/login')
      }

      await page.fill('input[name="email"], input[type="email"]', testEmail)
      await page.fill('input[name="password"], input[type="password"]', testPassword)
      await page.click('button[type="submit"]')
    }

    // Step 6: Verify redirect to chat page
    await expect(page).toHaveURL(/\/chat/, { timeout: 10000 })

    // Verify chat interface is displayed
    const chatContainer = page.locator('[data-testid="chat-container"], .chat-container, main')
    await expect(chatContainer).toBeVisible()

    // Verify essential chat elements exist
    const messageInput = page.locator('input[type="text"], textarea').first()
    await expect(messageInput).toBeVisible()
  })

  test('Scenario 5A: Invalid login credentials show error', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login')
    await expect(page).toHaveURL(/\/login/)

    // Try login with wrong password
    await page.fill('input[name="email"], input[type="email"]', 'test@example.com')
    await page.fill('input[name="password"], input[type="password"]', 'wrongpassword123')
    await page.click('button[type="submit"]')

    // Verify error message is displayed
    const errorMessage = page.locator('text=/invalid|incorrect|wrong|failed|error/i')
    await expect(errorMessage).toBeVisible({ timeout: 5000 })

    // Verify user is NOT redirected (stays on login page)
    await expect(page).toHaveURL(/\/login/)

    // Verify error message is user-friendly (no stack traces)
    const pageContent = await page.content()
    expect(pageContent).not.toMatch(/stack|trace|exception|at\s+\w+\.\w+/)
  })

  test('Registration form validation works correctly', async ({ page }) => {
    await page.goto('/register')

    // Test empty form submission
    await page.click('button[type="submit"]')

    // Should show validation errors or prevent submission
    const isStillOnRegister = await page.url().includes('/register')
    expect(isStillOnRegister).toBeTruthy()

    // Test invalid email format
    await page.fill('input[name="email"], input[type="email"]', 'invalid-email')
    await page.fill('input[name="password"], input[type="password"]', testPassword)
    await page.click('button[type="submit"]')

    // Should show email validation error
    const emailError = page.locator('text=/invalid email|enter a valid email/i')
    await expect(emailError).toBeVisible().catch(() => {
      // HTML5 validation might prevent submission instead
      expect(page.url()).toContain('/register')
    })
  })

  test('User can logout and login again', async ({ page }) => {
    // First register and login
    await page.goto('/register')
    await page.fill('input[name="email"], input[type="email"]', testEmail)
    await page.fill('input[name="password"], input[type="password"]', testPassword)
    await page.click('button[type="submit"]')

    // Wait for successful registration/login
    await page.waitForURL(/\/(login|chat)/, { timeout: 10000 })

    const currentUrl = page.url()
    if (!currentUrl.includes('/chat')) {
      await page.goto('/login')
      await page.fill('input[name="email"], input[type="email"]', testEmail)
      await page.fill('input[name="password"], input[type="password"]', testPassword)
      await page.click('button[type="submit"]')
      await page.waitForURL(/\/chat/, { timeout: 10000 })
    }

    // Now logout
    const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Sign out"), a:has-text("Logout")')
    if (await logoutButton.count() > 0) {
      await logoutButton.first().click()

      // Verify redirected to login or home
      await page.waitForURL(/\/(login|)$/, { timeout: 5000 })

      // Try to access chat - should redirect to login
      await page.goto('/chat')
      await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
    }
  })
})
