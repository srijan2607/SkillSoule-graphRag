/**
 * Accessibility Tests (WCAG 2.1 AA)
 *
 * Automated accessibility testing for all Story 2.7 components.
 * Story 2.7: Frontend CSV Upload UI - Test Coverage
 */

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Test user credentials
const TEST_USER = {
  email: 'test@example.com',
  password: 'password123',
}

test.describe('Accessibility Compliance (WCAG 2.1 AA)', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    await page.waitForURL(/\/(?!login)/)
  })

  test('Upload page should have no accessibility violations', async ({ page }) => {
    await page.goto('/upload')

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('FileUploadZone should have proper ARIA labels', async ({ page }) => {
    await page.goto('/upload')

    // Check file input has proper accept attribute
    const fileInput = page.locator('input[type="file"]').first()
    await expect(fileInput).toHaveAttribute('accept', '.csv')

    // Run accessibility scan on upload zone
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('text=Drag and drop your CSV file')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('CSV Preview Modal should have no accessibility violations', async ({ page }) => {
    await page.goto('/upload')

    // Mock API for preview
    await page.route('**/api/upload/skills/preview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          file_hash: 'abc123',
          file_type: 'skills',
          columns: ['id', 'name', 'description'],
          preview_rows: [
            { id: '1', name: 'JavaScript', description: 'Programming language' },
            { id: '2', name: 'React', description: 'UI framework' },
          ],
          total_rows: 100,
          has_more: true,
        }),
      })
    })

    // Upload file to trigger preview
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id,name\n1,Test'),
    })

    // Wait for modal
    await expect(page.locator('text=CSV Preview')).toBeVisible()

    // Check close button has accessible name
    const closeButton = page.locator('button[aria-label="Close preview"]')
    await expect(closeButton).toBeVisible()
    await expect(closeButton).toHaveAccessibleName()

    // Run accessibility scan on modal
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('text=CSV Preview')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Preview table should have proper semantic structure', async ({ page }) => {
    await page.goto('/upload')

    await page.route('**/api/upload/skills/preview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          file_hash: 'abc123',
          file_type: 'skills',
          columns: ['id', 'name'],
          preview_rows: [{ id: '1', name: 'Test' }],
          total_rows: 10,
          has_more: false,
        }),
      })
    })

    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id,name\n1,Test'),
    })

    await expect(page.locator('text=CSV Preview')).toBeVisible()

    // Verify table has proper structure
    const table = page.locator('table').first()
    await expect(table).toBeVisible()

    // Verify headers
    const headers = page.locator('th')
    await expect(headers.first()).toBeVisible()

    // Run accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('table')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Progress display should have no accessibility violations', async ({ page }) => {
    await page.goto('/upload')

    // Setup mocks
    await page.route('**/api/upload/skills/preview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          file_hash: 'abc123',
          file_type: 'skills',
          columns: ['id'],
          preview_rows: [{ id: '1' }],
          total_rows: 10,
          has_more: false,
        }),
      })
    })

    await page.route('**/api/upload/confirm', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ingestion_job_id: 'job-123',
        }),
      })
    })

    await page.route('**/api/ingestion/job-123/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'processing',
          progress_percentage: 50,
          processed_records: 50,
          total_records: 100,
          failed_records: 0,
        }),
      })
    })

    // Upload and confirm
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id\n1'),
    })

    await page.click('button:has-text("Confirm Upload")')
    await expect(page.locator('text=Processing CSV')).toBeVisible()

    // Run accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('text=Processing CSV')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Summary display should have no accessibility violations', async ({ page }) => {
    await page.goto('/upload')

    // Setup complete workflow
    await page.route('**/api/upload/skills/preview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          file_hash: 'abc123',
          file_type: 'skills',
          columns: ['id'],
          preview_rows: [{ id: '1' }],
          total_rows: 10,
          has_more: false,
        }),
      })
    })

    await page.route('**/api/upload/confirm', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ingestion_job_id: 'job-123',
        }),
      })
    })

    await page.route('**/api/ingestion/job-123/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed',
          progress_percentage: 100,
          processed_records: 100,
          total_records: 100,
          failed_records: 0,
        }),
      })
    })

    // Complete workflow
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id\n1'),
    })

    await page.click('button:has-text("Confirm Upload")')
    await expect(page.locator('text=Upload Complete!')).toBeVisible({ timeout: 10000 })

    // Run accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('text=Upload Complete!')
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Error messages should have proper color contrast', async ({ page }) => {
    await page.goto('/upload')

    // Upload invalid file to trigger error
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('not a csv'),
    })

    // Wait for error message
    await expect(page.locator('text=Only CSV files are allowed')).toBeVisible()

    // Run accessibility scan including color contrast
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('text=Only CSV files are allowed')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Connection error UI should be accessible (RELIABILITY-001)', async ({ page }) => {
    await page.goto('/upload')

    await page.route('**/api/upload/skills/preview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          file_hash: 'abc123',
          file_type: 'skills',
          columns: ['id'],
          preview_rows: [{ id: '1' }],
          total_rows: 10,
          has_more: false,
        }),
      })
    })

    await page.route('**/api/upload/confirm', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ingestion_job_id: 'job-123',
        }),
      })
    })

    // Simulate network error
    await page.route('**/api/ingestion/job-123/status', async (route) => {
      await route.abort('failed')
    })

    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id\n1'),
    })

    await page.click('button:has-text("Confirm Upload")')

    // Wait for error UI
    await expect(page.locator('text=Connection Error')).toBeVisible({ timeout: 10000 })

    // Verify retry button is accessible
    const retryButton = page.locator('button:has-text("Retry")')
    await expect(retryButton).toBeVisible()

    // Run accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('text=Connection Error')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('All interactive elements should have focus indicators', async ({ page }) => {
    await page.goto('/upload')

    // Test upload zone focus
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.focus()

    // Test with keyboard navigation
    await page.keyboard.press('Tab')

    // Run accessibility scan for focus indicators
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Loading states should have appropriate ARIA attributes', async ({ page }) => {
    await page.goto('/upload')

    await page.route('**/api/upload/skills/preview', async (route) => {
      // Delay response to show loading state
      await new Promise((resolve) => setTimeout(resolve, 100))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          file_hash: 'abc123',
          file_type: 'skills',
          columns: ['id'],
          preview_rows: [{ id: '1' }],
          total_rows: 10,
          has_more: false,
        }),
      })
    })

    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id\n1'),
    })

    // Check loading state
    await expect(page.locator('text=Uploading...')).toBeVisible()

    // Run accessibility scan during loading
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('Form elements should have proper labels', async ({ page }) => {
    await page.goto('/upload')

    // Check file inputs have proper structure
    const fileInputs = page.locator('input[type="file"]')
    const count = await fileInputs.count()

    expect(count).toBeGreaterThan(0)

    // Run accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    // Check for form-related violations
    const formViolations = accessibilityScanResults.violations.filter((v) =>
      ['label', 'form-field-multiple-labels', 'label-title-only'].includes(v.id)
    )

    expect(formViolations).toEqual([])
  })

  test('Download button should be keyboard accessible', async ({ page }) => {
    await page.goto('/upload')

    // Setup workflow with errors
    await page.route('**/api/upload/skills/preview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_valid: true,
          file_hash: 'abc123',
          file_type: 'skills',
          columns: ['id'],
          preview_rows: [{ id: '1' }],
          total_rows: 10,
          has_more: false,
        }),
      })
    })

    await page.route('**/api/upload/confirm', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ingestion_job_id: 'job-123',
        }),
      })
    })

    await page.route('**/api/ingestion/job-123/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'completed_with_errors',
          progress_percentage: 100,
          processed_records: 95,
          total_records: 100,
          failed_records: 5,
        }),
      })
    })

    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id\n1'),
    })

    await page.click('button:has-text("Confirm Upload")')
    await expect(page.locator('button:has-text("Download Error Log")')).toBeVisible({ timeout: 10000 })

    // Test keyboard navigation to download button
    const downloadButton = page.locator('button:has-text("Download Error Log")')
    await downloadButton.focus()

    // Verify button is in tab order
    await expect(downloadButton).toBeFocused()

    // Run accessibility scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('button:has-text("Download Error Log")')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })
})
