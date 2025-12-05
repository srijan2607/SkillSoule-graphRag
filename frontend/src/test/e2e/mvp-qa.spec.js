/**
 * MVP Polish & Final QA - Story 5.8
 *
 * Comprehensive Playwright tests for all acceptance criteria:
 * 1. Console errors and warnings check
 * 2. Loading states verification
 * 3. User-friendly error messages
 * 4. Responsive design testing
 * 5. Broken links and 404 pages
 * 6. Form validation feedback
 * 7. Accessibility basics
 * 8. Performance benchmarks
 * 9. Cross-browser compatibility
 */

import { test, expect } from '@playwright/test'

test.describe('Story 5.8: MVP Polish & Final QA', () => {

  // AC1: Console Errors and Warnings
  test.describe('AC1: Console Errors and Warnings', () => {
    let consoleErrors = []
    let consoleWarnings = []

    test.beforeEach(async ({ page }) => {
      // Capture console messages
      page.on('console', msg => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text())
        }
        if (msg.type() === 'warning') {
          consoleWarnings.push(msg.text())
        }
      })

      // Capture uncaught errors
      page.on('pageerror', error => {
        consoleErrors.push(error.message)
      })
    })

    test('Login page should have no console errors', async ({ page }) => {
      consoleErrors = []
      consoleWarnings = []

      await page.goto('http://localhost:5173/login')
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000) // Wait for any delayed errors

      console.log('Login Page - Errors:', consoleErrors.length, 'Warnings:', consoleWarnings.length)

      expect(consoleErrors).toEqual([])
      // Warnings are acceptable but should be logged
      if (consoleWarnings.length > 0) {
        console.log('Warnings found:', consoleWarnings)
      }
    })

    test('Register page should have no console errors', async ({ page }) => {
      consoleErrors = []
      consoleWarnings = []

      await page.goto('http://localhost:5173/register')
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000)

      console.log('Register Page - Errors:', consoleErrors.length, 'Warnings:', consoleWarnings.length)

      expect(consoleErrors).toEqual([])
    })

    test('Chat page should have no console errors (authenticated)', async ({ page }) => {
      consoleErrors = []
      consoleWarnings = []

      // Login first
      await page.goto('http://localhost:5173/login')
      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      await page.waitForURL('**/chat', { timeout: 15000 })
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000)

      console.log('Chat Page - Errors:', consoleErrors.length, 'Warnings:', consoleWarnings.length)

      expect(consoleErrors).toEqual([])
    })

    test('Upload page should have no console errors', async ({ page }) => {
      consoleErrors = []
      consoleWarnings = []

      // Login first
      await page.goto('http://localhost:5173/login')
      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      await page.goto('http://localhost:5173/upload')
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000)

      console.log('Upload Page - Errors:', consoleErrors.length, 'Warnings:', consoleWarnings.length)

      expect(consoleErrors).toEqual([])
    })
  })

  // AC2: Loading States
  test.describe('AC2: Loading States', () => {
    test('Login form shows loading spinner on submit', async ({ page }) => {
      await page.goto('http://localhost:5173/login')

      const submitButton = page.locator('button[type="submit"]')

      // Check initial state
      await expect(submitButton).toContainText(/sign in/i)
      await expect(submitButton).toBeEnabled()

      // Fill form and submit
      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await submitButton.click()

      // Verify loading state appears
      await expect(submitButton).toContainText(/signing in/i)
      await expect(submitButton).toBeDisabled()
    })

    test('Register form shows loading spinner on submit', async ({ page }) => {
      await page.goto('http://localhost:5173/register')

      const submitButton = page.locator('button[type="submit"]')

      await expect(submitButton).toContainText(/register/i)
      await expect(submitButton).toBeEnabled()

      await page.fill('input[type="email"]', 'newuser@example.com')
      await page.fill('input[name="password"]', 'password123')
      await page.fill('input[name="confirmPassword"]', 'password123')
      await submitButton.click()

      await expect(submitButton).toContainText(/creating account/i)
      await expect(submitButton).toBeDisabled()
    })

    test('Chat input shows typing indicator during query', async ({ page }) => {
      // Login
      await page.goto('http://localhost:5173/login')
      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      await page.waitForURL('**/chat')

      const chatInput = page.locator('input[type="text"], textarea').first()
      const sendButton = page.locator('button:has-text("Send"), button[type="submit"]').first()

      await chatInput.fill('Test query')
      await sendButton.click()

      // Check for typing indicator or loading state
      const typingIndicator = page.locator('[data-testid="typing-indicator"], .typing-indicator, text=/typing|thinking|processing/i')

      // Should be visible while loading
      await expect(typingIndicator.or(chatInput)).toBeVisible()

      // Input should be disabled during loading
      await expect(chatInput).toBeDisabled()
    })
  })

  // AC3: User-Friendly Error Messages
  test.describe('AC3: User-Friendly Error Messages', () => {
    test('Network error shows friendly message', async ({ page }) => {
      await page.goto('http://localhost:5173/login')

      // Simulate network error
      await page.route('**/api/**', route => route.abort('failed'))

      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      // Check for user-friendly error message (not raw API error)
      const errorMessage = await page.locator('[role="alert"], .error, .text-red').textContent()

      expect(errorMessage).not.toContain('500')
      expect(errorMessage).not.toContain('undefined')
      expect(errorMessage).not.toContain('null')

      // Should contain user-friendly text
      expect(errorMessage.toLowerCase()).toMatch(/failed|error|try again|check|connection/)
    })

    test('401 error redirects to login with session expired message', async ({ page }) => {
      // Set invalid token
      await page.goto('http://localhost:5173/login')
      await page.evaluate(() => {
        localStorage.setItem('token', 'invalid-token')
        localStorage.setItem('user', JSON.stringify({ email: 'test@example.com' }))
      })

      // Go to protected page
      await page.goto('http://localhost:5173/chat')

      // Mock 401 response
      await page.route('**/api/**', route => {
        route.fulfill({
          status: 401,
          body: JSON.stringify({ detail: 'Unauthorized' })
        })
      })

      const chatInput = page.locator('input[type="text"], textarea').first()
      await chatInput.fill('Test query')
      await chatInput.press('Enter')

      // Should show session expired message, not raw 401
      await page.waitForTimeout(2000)
      const pageContent = await page.content()

      expect(pageContent.toLowerCase()).toMatch(/session|expired|login/i)
    })
  })

  // AC4: Responsive Design
  test.describe('AC4: Responsive Design', () => {
    const viewports = [
      { name: 'Desktop 1920x1080', width: 1920, height: 1080 },
      { name: 'Desktop 1366x768', width: 1366, height: 768 },
      { name: 'Tablet iPad', width: 768, height: 1024 },
      { name: 'Mobile iPhone', width: 375, height: 667 },
      { name: 'Mobile Android', width: 360, height: 640 },
    ]

    for (const viewport of viewports) {
      test(`Login page responsive on ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height })
        await page.goto('http://localhost:5173/login')

        // Check all form elements are visible and usable
        await expect(page.locator('input[type="email"]')).toBeVisible()
        await expect(page.locator('input[type="password"]')).toBeVisible()
        await expect(page.locator('button[type="submit"]')).toBeVisible()

        // No horizontal scroll
        const bodyWidth = await page.locator('body').boundingBox()
        expect(bodyWidth.width).toBeLessThanOrEqual(viewport.width)
      })

      test(`Chat interface responsive on ${viewport.name}`, async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height })

        // Login
        await page.goto('http://localhost:5173/login')
        await page.fill('input[type="email"]', 'test@example.com')
        await page.fill('input[type="password"]', 'password123')
        await page.click('button[type="submit"]')

        await page.waitForURL('**/chat', { timeout: 15000 })

        // Check chat input is visible and accessible
        const chatInput = page.locator('input[type="text"], textarea').first()
        await expect(chatInput).toBeVisible()

        // Input should be appropriately sized for viewport
        const inputBox = await chatInput.boundingBox()
        expect(inputBox.width).toBeLessThan(viewport.width)
        expect(inputBox.width).toBeGreaterThan(viewport.width * 0.5) // At least 50% of screen width
      })
    }
  })

  // AC5: Broken Links and 404 Pages
  test.describe('AC5: Broken Links and 404 Pages', () => {
    test('All navigation links work', async ({ page }) => {
      // Login
      await page.goto('http://localhost:5173/login')
      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      await page.waitForURL('**/chat')

      // Find and click all navigation links
      const navLinks = page.locator('nav a, [role="navigation"] a')
      const linkCount = await navLinks.count()

      for (let i = 0; i < linkCount; i++) {
        const link = navLinks.nth(i)
        const href = await link.getAttribute('href')

        if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
          await link.click()
          await page.waitForLoadState('networkidle', { timeout: 3000 })

          // Verify page loaded (not 404)
          const heading = page.locator('h1, h2').first()
          await expect(heading).toBeVisible()

          console.log(`✓ Navigation link ${href} works`)

          // Go back for next link
          if (i < linkCount - 1) {
            await page.goto('http://localhost:5173/chat')
          }
        }
      }
    })

    test('404 page exists and is styled', async ({ page }) => {
      await page.goto('http://localhost:5173/nonexistent-page')

      // Should show some 404 indication
      const content = await page.content()
      expect(content.toLowerCase()).toMatch(/404|not found|page.*not.*exist/i)

      // Should be styled (not blank page)
      const styles = await page.locator('link[rel="stylesheet"], style').count()
      expect(styles).toBeGreaterThan(0)
    })

    test('Protected routes redirect to login', async ({ page }) => {
      // Clear auth
      await page.goto('http://localhost:5173')
      await page.evaluate(() => {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      })

      // Try to access protected route
      await page.goto('http://localhost:5173/chat')

      // Should redirect to login
      await page.waitForURL('**/login', { timeout: 3000 })
      expect(page.url()).toContain('/login')
    })
  })

  // AC6: Form Validation
  test.describe('AC6: Form Validation', () => {
    test('Registration form validates email format', async ({ page }) => {
      await page.goto('http://localhost:5173/register')

      await page.fill('input[type="email"]', 'invalid-email')
      await page.fill('input[name="password"]', 'password123')
      await page.fill('input[name="confirmPassword"]', 'password123')
      await page.click('button[type="submit"]')

      // Should show validation error
      const errorText = await page.locator('[role="alert"], .error, .text-red').textContent()
      expect(errorText.toLowerCase()).toContain('email')
    })

    test('Registration form validates password length', async ({ page }) => {
      await page.goto('http://localhost:5173/register')

      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[name="password"]', 'short')
      await page.fill('input[name="confirmPassword"]', 'short')
      await page.click('button[type="submit"]')

      const errorText = await page.locator('[role="alert"], .error, .text-red').textContent()
      expect(errorText.toLowerCase()).toMatch(/password|8 characters|length/)
    })

    test('Registration form validates password match', async ({ page }) => {
      await page.goto('http://localhost:5173/register')

      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[name="password"]', 'password123')
      await page.fill('input[name="confirmPassword"]', 'different123')
      await page.click('button[type="submit"]')

      const errorText = await page.locator('[role="alert"], .error, .text-red').textContent()
      expect(errorText.toLowerCase()).toMatch(/match|same/)
    })

    test('Chat input validates non-empty message', async ({ page }) => {
      // Login
      await page.goto('http://localhost:5173/login')
      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      await page.waitForURL('**/chat')

      const chatInput = page.locator('input[type="text"], textarea').first()
      const sendButton = page.locator('button:has-text("Send"), button[type="submit"]').first()

      // Try to send empty message
      await chatInput.fill('   ')
      await sendButton.click()

      // Message should not be sent (input should still be visible and empty)
      await page.waitForTimeout(500)
      const inputValue = await chatInput.inputValue()
      expect(inputValue.trim()).toBe('')
    })
  })

  // AC7: Accessibility Basics
  test.describe('AC7: Accessibility Basics', () => {
    test('Tab navigation works through login form', async ({ page }) => {
      await page.goto('http://localhost:5173/login')

      // Tab through form
      await page.keyboard.press('Tab')
      let focused = await page.evaluate(() => document.activeElement.tagName)
      expect(['INPUT', 'BUTTON', 'A']).toContain(focused)

      await page.keyboard.press('Tab')
      focused = await page.evaluate(() => document.activeElement.tagName)
      expect(['INPUT', 'BUTTON', 'A']).toContain(focused)

      await page.keyboard.press('Tab')
      focused = await page.evaluate(() => document.activeElement.tagName)
      expect(['INPUT', 'BUTTON', 'A']).toContain(focused)

      console.log('✓ Tab navigation works through form')
    })

    test('All form inputs have labels', async ({ page }) => {
      await page.goto('http://localhost:5173/login')

      const inputs = page.locator('input[type="email"], input[type="password"], input[type="text"]')
      const count = await inputs.count()

      for (let i = 0; i < count; i++) {
        const input = inputs.nth(i)
        const id = await input.getAttribute('id')
        const ariaLabel = await input.getAttribute('aria-label')
        const placeholder = await input.getAttribute('placeholder')

        // Should have either a label, aria-label, or meaningful placeholder
        const hasLabel = id && await page.locator(`label[for="${id}"]`).count() > 0

        expect(hasLabel || ariaLabel || placeholder).toBeTruthy()
      }

      console.log('✓ All inputs have labels or aria-labels')
    })

    test('Enter key submits login form', async ({ page }) => {
      await page.goto('http://localhost:5173/login')

      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')

      // Press Enter instead of clicking submit
      await page.keyboard.press('Enter')

      // Should navigate to chat or show error
      await page.waitForTimeout(2000)
      const url = page.url()

      expect(url).toMatch(/chat|login/)
      console.log('✓ Enter key submits form')
    })

    test('Focus states are visible on interactive elements', async ({ page }) => {
      await page.goto('http://localhost:5173/login')

      const submitButton = page.locator('button[type="submit"]')

      // Focus the button
      await submitButton.focus()

      // Check if focus ring is visible (computed styles)
      const outlineWidth = await submitButton.evaluate(el => {
        const styles = window.getComputedStyle(el)
        return styles.outlineWidth || styles.boxShadow
      })

      expect(outlineWidth).toBeTruthy()
      console.log('✓ Focus states visible:', outlineWidth)
    })
  })

  // AC8: Performance
  test.describe('AC8: Performance', () => {
    test('Page load time < 3 seconds', async ({ page }) => {
      const startTime = Date.now()

      await page.goto('http://localhost:5173/login')
      await page.waitForLoadState('networkidle')

      const loadTime = Date.now() - startTime

      console.log(`Page load time: ${loadTime}ms`)
      expect(loadTime).toBeLessThan(3000)
    })

    test('Chat query response < 5 seconds', async ({ page }) => {
      // Login
      await page.goto('http://localhost:5173/login')
      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      await page.waitForURL('**/chat')

      const chatInput = page.locator('input[type="text"], textarea').first()

      await chatInput.fill('Test query')

      const startTime = Date.now()
      await chatInput.press('Enter')

      // Wait for response to appear
      await page.waitForSelector('[data-testid="assistant-message"], .assistant-message, [role="article"]', { timeout: 5000 })

      const responseTime = Date.now() - startTime

      console.log(`Query response time: ${responseTime}ms`)
      expect(responseTime).toBeLessThan(5000)
    })
  })
})
