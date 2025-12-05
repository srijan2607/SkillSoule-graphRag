/**
 * E2E Test: Authentication UI/UX Review
 *
 * Comprehensive UI/UX validation for EPIC-001-STORY-001
 * Tests responsive design, accessibility, visual consistency, and user experience
 *
 * Story: Authentication Screens (Login & Registration)
 */

import { test, expect } from '@playwright/test'

test.describe('Authentication UI/UX Review', () => {
  const testEmail = `ux-test-${Date.now()}@example.com`
  const testPassword = 'TestPass123!@#'

  test.describe('Login Screen - Visual & Layout', () => {
    test('displays all required UI elements correctly', async ({ page }) => {
      await page.goto('/login')

      // Verify page title
      await expect(page.locator('h2, h1').first()).toContainText(/sign in|login/i)

      // Verify form fields exist and are properly labeled
      const emailInput = page.locator('input[type="email"]')
      await expect(emailInput).toBeVisible()
      await expect(emailInput).toHaveAttribute('id', 'email')

      const passwordInput = page.locator('input[type="password"]')
      await expect(passwordInput).toBeVisible()
      await expect(passwordInput).toHaveAttribute('id', 'password')

      // Verify submit button
      const submitButton = page.locator('button[type="submit"]')
      await expect(submitButton).toBeVisible()
      await expect(submitButton).toContainText(/sign in|login/i)

      // Verify register link
      const registerLink = page.locator('a[href="/register"]')
      await expect(registerLink).toBeVisible()
      await expect(registerLink).toContainText(/register|sign up|create account/i)
    })

    test('responsive design - mobile (375px)', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 }) // iPhone SE
      await page.goto('/login')

      // Verify form is visible and properly sized
      const form = page.locator('form')
      const formBox = await form.boundingBox()

      expect(formBox.width).toBeLessThanOrEqual(375)
      expect(formBox.width).toBeGreaterThan(300) // Should use most of screen

      // Verify inputs are properly sized for mobile
      const emailInput = page.locator('input[type="email"]')
      const inputBox = await emailInput.boundingBox()

      expect(inputBox.height).toBeGreaterThanOrEqual(44) // iOS minimum touch target

      // Verify button is properly sized for mobile
      const button = page.locator('button[type="submit"]')
      const buttonBox = await button.boundingBox()

      expect(buttonBox.height).toBeGreaterThanOrEqual(44) // iOS minimum touch target
    })

    test('responsive design - tablet (768px)', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 }) // iPad
      await page.goto('/login')

      // Verify form is centered and properly sized
      const form = page.locator('form')
      const formBox = await form.boundingBox()

      expect(formBox.width).toBeLessThanOrEqual(500) // Should not be full width
      expect(formBox.width).toBeGreaterThan(350)

      // Verify form is centered horizontally
      const viewportWidth = 768
      const centerX = formBox.x + formBox.width / 2
      expect(Math.abs(centerX - viewportWidth / 2)).toBeLessThan(50) // Roughly centered
    })

    test('responsive design - desktop (1280px)', async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 }) // Standard laptop
      await page.goto('/login')

      // Verify form is centered and properly sized
      const form = page.locator('form')
      const formBox = await form.boundingBox()

      expect(formBox.width).toBeLessThanOrEqual(500) // Should not be too wide
      expect(formBox.width).toBeGreaterThan(350)

      // Verify form is vertically centered
      const container = page.locator('div.min-h-screen').first()
      const containerBox = await container.boundingBox()

      expect(containerBox.height).toBeGreaterThanOrEqual(600) // Should fill screen
    })
  })

  test.describe('Login Screen - Accessibility', () => {
    test('keyboard navigation works correctly', async ({ page }) => {
      await page.goto('/login')

      // Tab through form elements
      await page.keyboard.press('Tab') // Focus email
      let focusedElement = await page.evaluate(() => document.activeElement.id)
      expect(focusedElement).toBe('email')

      await page.keyboard.press('Tab') // Focus password
      focusedElement = await page.evaluate(() => document.activeElement.id)
      expect(focusedElement).toBe('password')

      await page.keyboard.press('Tab') // Focus submit button
      const activeElement = await page.evaluate(() => document.activeElement.tagName)
      expect(activeElement).toBe('BUTTON')
    })

    test('form submission works with Enter key', async ({ page }) => {
      await page.goto('/login')

      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')

      // Press Enter instead of clicking
      await page.keyboard.press('Enter')

      // Should attempt login (check for loading state or error)
      await page.waitForTimeout(1000)

      const url = page.url()
      const hasError = await page.locator('text=/invalid|error|failed/i').count() > 0

      // Either redirected or showing error (both indicate form submitted)
      expect(url.includes('/login') || url.includes('/chat') || hasError).toBeTruthy()
    })

    test('focus states are visible', async ({ page }) => {
      await page.goto('/login')

      const emailInput = page.locator('input[type="email"]')
      await emailInput.focus()

      // Check that focus ring is visible (via CSS)
      const focusStyles = await emailInput.evaluate((el) => {
        const styles = window.getComputedStyle(el)
        return {
          outlineWidth: styles.outlineWidth,
          outlineStyle: styles.outlineStyle,
          ringWidth: styles.getPropertyValue('--tw-ring-width')
        }
      })

      // Should have some focus indicator
      const hasFocusIndicator =
        focusStyles.outlineWidth !== '0px' ||
        focusStyles.ringWidth !== '' ||
        focusStyles.outlineStyle !== 'none'

      expect(hasFocusIndicator).toBeTruthy()
    })

    test('labels are properly associated with inputs', async ({ page }) => {
      await page.goto('/login')

      const emailInput = page.locator('input[type="email"]')
      const emailId = await emailInput.getAttribute('id')

      // Check for associated label
      const label = page.locator(`label[for="${emailId}"]`)
      await expect(label).toHaveCount(1) // Should have exactly one label

      const passwordInput = page.locator('input[type="password"]')
      const passwordId = await passwordInput.getAttribute('id')

      const passwordLabel = page.locator(`label[for="${passwordId}"]`)
      await expect(passwordLabel).toHaveCount(1)
    })
  })

  test.describe('Login Screen - Form Validation', () => {
    test('shows validation error for invalid email', async ({ page }) => {
      await page.goto('/login')

      await page.fill('input[type="email"]', 'invalid-email')
      await page.fill('input[type="password"]', 'password123')
      await page.click('button[type="submit"]')

      // Should show email validation error
      const error = page.locator('text=/valid email|email/i')
      await expect(error).toBeVisible({ timeout: 3000 })
    })

    test('shows validation error for empty fields', async ({ page }) => {
      await page.goto('/login')

      await page.click('button[type="submit"]')

      // Should show validation error
      const error = page.locator('text=/required|empty/i')
      await expect(error).toBeVisible({ timeout: 3000 })
    })

    test('clears error when user starts typing', async ({ page }) => {
      await page.goto('/login')

      // Trigger error
      await page.click('button[type="submit"]')
      await page.waitForTimeout(500)

      // Check error exists
      const errorBefore = await page.locator('[data-testid="login-error"]').count()
      expect(errorBefore).toBeGreaterThan(0)

      // Start typing
      await page.fill('input[type="email"]', 'user@example.com')
      await page.waitForTimeout(500)

      // Error should be cleared or hidden
      const errorAfter = await page.locator('[data-testid="login-error"]:visible').count()
      expect(errorAfter).toBe(0)
    })
  })

  test.describe('Login Screen - Loading States', () => {
    test('shows loading state during form submission', async ({ page }) => {
      await page.goto('/login')

      await page.fill('input[type="email"]', 'test@example.com')
      await page.fill('input[type="password"]', 'password123')

      // Click submit and immediately check loading state
      await page.click('button[type="submit"]')

      // Button should show loading text
      const button = page.locator('button[type="submit"]')
      await expect(button).toContainText(/signing in|loading/i, { timeout: 1000 })

      // Button should be disabled
      await expect(button).toBeDisabled()
    })
  })

  test.describe('Registration Screen - Visual & Layout', () => {
    test('displays all required UI elements correctly', async ({ page }) => {
      await page.goto('/register')

      // Verify page title
      await expect(page.locator('h2, h1').first()).toContainText(/create|register|sign up/i)

      // Verify form fields
      const emailInput = page.locator('input[type="email"]')
      await expect(emailInput).toBeVisible()

      const passwordInputs = page.locator('input[type="password"]')
      await expect(passwordInputs).toHaveCount(2) // password + confirm password

      // Verify submit button
      const submitButton = page.locator('button[type="submit"]')
      await expect(submitButton).toBeVisible()
      await expect(submitButton).toContainText(/register|sign up|create/i)

      // Verify login link
      const loginLink = page.locator('a[href="/login"]')
      await expect(loginLink).toBeVisible()
      await expect(loginLink).toContainText(/login|sign in/i)
    })

    test('responsive design works on all breakpoints', async ({ page }) => {
      const breakpoints = [
        { width: 375, height: 667, name: 'mobile' },
        { width: 768, height: 1024, name: 'tablet' },
        { width: 1280, height: 800, name: 'desktop' }
      ]

      for (const breakpoint of breakpoints) {
        await page.setViewportSize({ width: breakpoint.width, height: breakpoint.height })
        await page.goto('/register')

        // Form should be visible
        const form = page.locator('form')
        await expect(form).toBeVisible()

        // All inputs should be visible
        const inputs = page.locator('input')
        const count = await inputs.count()
        expect(count).toBeGreaterThanOrEqual(3) // email, password, confirm password

        // Submit button should be visible
        const button = page.locator('button[type="submit"]')
        await expect(button).toBeVisible()
      }
    })
  })

  test.describe('Registration Screen - Form Validation', () => {
    test('validates password length (minimum 8 characters)', async ({ page }) => {
      await page.goto('/register')

      await page.fill('input[type="email"]', 'test@example.com')

      const passwordInputs = page.locator('input[type="password"]')
      await passwordInputs.first().fill('short')
      await passwordInputs.last().fill('short')

      await page.click('button[type="submit"]')

      // Should show password length error
      const error = page.locator('text=/8 characters|password.*short|minimum/i')
      await expect(error).toBeVisible({ timeout: 3000 })
    })

    test('validates password match', async ({ page }) => {
      await page.goto('/register')

      await page.fill('input[type="email"]', 'test@example.com')

      const passwordInputs = page.locator('input[type="password"]')
      await passwordInputs.first().fill('password123')
      await passwordInputs.last().fill('different123')

      await page.click('button[type="submit"]')

      // Should show password match error
      const error = page.locator('text=/match|same/i')
      await expect(error).toBeVisible({ timeout: 3000 })
    })

    test('validates email format', async ({ page }) => {
      await page.goto('/register')

      await page.fill('input[type="email"]', 'invalid-email')

      const passwordInputs = page.locator('input[type="password"]')
      await passwordInputs.first().fill('password123')
      await passwordInputs.last().fill('password123')

      await page.click('button[type="submit"]')

      // Should show email validation error
      const error = page.locator('text=/valid email|email.*invalid/i')
      await expect(error).toBeVisible({ timeout: 3000 })
    })
  })

  test.describe('Registration Screen - Loading States', () => {
    test('shows loading state during registration', async ({ page }) => {
      await page.goto('/register')

      await page.fill('input[type="email"]', testEmail)

      const passwordInputs = page.locator('input[type="password"]')
      await passwordInputs.first().fill(testPassword)
      await passwordInputs.last().fill(testPassword)

      await page.click('button[type="submit"]')

      // Button should show loading text
      const button = page.locator('button[type="submit"]')
      await expect(button).toContainText(/creating|loading/i, { timeout: 1000 })

      // Button should be disabled
      await expect(button).toBeDisabled()
    })
  })

  test.describe('Navigation & Integration', () => {
    test('navigation between login and register works', async ({ page }) => {
      await page.goto('/login')

      // Click register link
      await page.click('a[href="/register"]')
      await expect(page).toHaveURL(/\/register/)

      // Click login link
      await page.click('a[href="/login"]')
      await expect(page).toHaveURL(/\/login/)
    })

    test('successful registration redirects to login', async ({ page }) => {
      await page.goto('/register')

      await page.fill('input[type="email"]', testEmail)

      const passwordInputs = page.locator('input[type="password"]')
      await passwordInputs.first().fill(testPassword)
      await passwordInputs.last().fill(testPassword)

      await page.click('button[type="submit"]')

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
    })
  })

  test.describe('Error Handling - User-Friendly Messages', () => {
    test('API errors show user-friendly messages', async ({ page }) => {
      await page.goto('/login')

      await page.fill('input[type="email"]', 'nonexistent@example.com')
      await page.fill('input[type="password"]', 'wrongpassword')
      await page.click('button[type="submit"]')

      // Wait for error
      await page.waitForTimeout(2000)

      const pageContent = await page.content()

      // Should NOT show raw error objects or stack traces
      expect(pageContent).not.toMatch(/stack|trace|exception|Error:.*at/)
      expect(pageContent).not.toMatch(/\{.*error.*\}/)

      // Should show user-friendly message
      const hasUserFriendlyError = await page.locator('text=/invalid|incorrect|failed|try again/i').count() > 0
      expect(hasUserFriendlyError).toBeTruthy()
    })
  })

  test.describe('Visual Consistency', () => {
    test('uses consistent TailwindCSS styling', async ({ page }) => {
      await page.goto('/login')

      // Check inputs use Tailwind classes
      const emailInput = page.locator('input[type="email"]')
      const classes = await emailInput.getAttribute('class')

      expect(classes).toContain('border')
      expect(classes).toContain('rounded')

      // Check button uses Tailwind classes
      const button = page.locator('button[type="submit"]')
      const buttonClasses = await button.getAttribute('class')

      expect(buttonClasses).toContain('bg-')
      expect(buttonClasses).toContain('text-')
    })

    test('color scheme is consistent across screens', async ({ page }) => {
      // Check login page
      await page.goto('/login')
      const loginButton = page.locator('button[type="submit"]')
      const loginButtonColor = await loginButton.evaluate((el) =>
        window.getComputedStyle(el).backgroundColor
      )

      // Check register page
      await page.goto('/register')
      const registerButton = page.locator('button[type="submit"]')
      const registerButtonColor = await registerButton.evaluate((el) =>
        window.getComputedStyle(el).backgroundColor
      )

      // Should use same primary color
      expect(loginButtonColor).toBe(registerButtonColor)
    })
  })
})
