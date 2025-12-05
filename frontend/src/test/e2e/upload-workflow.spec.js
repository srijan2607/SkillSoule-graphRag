/**
 * Upload Workflow E2E Tests
 *
 * End-to-end tests for the complete CSV upload workflow.
 * Story 2.7: Frontend CSV Upload UI - Test Coverage
 */

import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Test user credentials
const TEST_USER = {
  email: 'test@example.com',
  password: 'password123',
}

test.describe('CSV Upload Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto('/login')

    // Login (assuming login functionality exists)
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')

    // Wait for navigation to complete
    await page.waitForURL(/\/(?!login)/)
  })

  test('AC 1: Upload page should be accessible at /upload route (protected)', async ({ page }) => {
    // Navigate to upload page
    await page.goto('/upload')

    // Verify we're on the upload page
    await expect(page).toHaveURL('/upload')

    // Verify protected route - should have auth token
    const hasToken = await page.evaluate(() => localStorage.getItem('token') !== null)
    expect(hasToken).toBeTruthy()
  })

  test('AC 2: Should display two upload zones (Skills and Jobs)', async ({ page }) => {
    await page.goto('/upload')

    // Check for Skills upload zone
    const skillsZone = page.locator('text=Upload Skills CSV').first()
    await expect(skillsZone).toBeVisible()

    // Check for Jobs upload zone
    const jobsZone = page.locator('text=Upload Jobs CSV').first()
    await expect(jobsZone).toBeVisible()
  })

  test('AC 3: Should support drag-and-drop file upload', async ({ page }) => {
    await page.goto('/upload')

    // Create a test CSV file
    const csvContent = 'id,name,description\n1,JavaScript,Programming language'
    const buffer = Buffer.from(csvContent)

    // Find the upload zone
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await expect(uploadZone).toBeVisible()

    // Simulate file drop
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: buffer,
    })

    // Wait for upload to complete
    await page.waitForTimeout(1000)
  })

  test('AC 4: Should validate CSV file type and size', async ({ page }) => {
    await page.goto('/upload')

    // Try to upload non-CSV file
    const txtContent = 'This is not a CSV'
    const txtBuffer = Buffer.from(txtContent)

    const uploadZone = page.locator('text=Drag and drop your CSV file').first()

    await uploadZone.setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: txtBuffer,
    })

    // Should show error message
    await expect(page.locator('text=Only CSV files are allowed')).toBeVisible()
  })

  test('AC 5: Should show preview modal with first rows and allow confirm/cancel', async ({ page }) => {
    await page.goto('/upload')

    // Mock the API response for upload
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

    // Upload CSV file
    const csvContent = 'id,name,description\n1,JavaScript,Programming\n2,React,Framework'
    const buffer = Buffer.from(csvContent)

    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: buffer,
    })

    // Wait for preview modal
    await expect(page.locator('text=CSV Preview')).toBeVisible()

    // Verify preview table content
    await expect(page.locator('text=JavaScript')).toBeVisible()
    await expect(page.locator('text=React')).toBeVisible()

    // Verify row count
    await expect(page.locator('text=100 skills found')).toBeVisible()

    // Test cancel button
    await page.click('button:has-text("Cancel")')
    await expect(page.locator('text=CSV Preview')).not.toBeVisible()
  })

  test('AC 6: Should show real-time progress during ingestion', async ({ page }) => {
    await page.goto('/upload')

    // Mock upload and confirm endpoints
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
          total_rows: 100,
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

    let pollCount = 0
    await page.route('**/api/ingestion/job-123/status', async (route) => {
      pollCount++
      if (pollCount < 3) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'processing',
            progress_percentage: 50,
            processed_records: 50,
            total_records: 100,
            failed_records: 0,
            estimated_time_remaining: 30,
          }),
        })
      } else {
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
      }
    })

    // Upload and confirm
    const csvContent = 'id,name\n1,Test'
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csvContent),
    })

    await expect(page.locator('text=CSV Preview')).toBeVisible()
    await page.click('button:has-text("Confirm Upload")')

    // Verify progress display
    await expect(page.locator('text=Processing CSV')).toBeVisible()
    await expect(page.locator('text=50%')).toBeVisible()

    // Wait for completion
    await expect(page.locator('text=Upload Complete!')).toBeVisible({ timeout: 10000 })
  })

  test('AC 7: Should show success/error summary with stats', async ({ page }) => {
    await page.goto('/upload')

    // Setup mocks for complete workflow
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
          total_rows: 100,
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
          processed_records: 95,
          total_records: 100,
          failed_records: 5,
        }),
      })
    })

    // Complete upload workflow
    const uploadZone = page.locator('text=Drag and drop your CSV file').first()
    await uploadZone.setInputFiles({
      name: 'test.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id\n1'),
    })

    await page.click('button:has-text("Confirm Upload")')

    // Wait for summary
    await expect(page.locator('text=Upload Completed with Errors')).toBeVisible({ timeout: 10000 })

    // Verify stats
    await expect(page.locator('text=100')).toBeVisible() // Total
    await expect(page.locator('text=95')).toBeVisible() // Processed
    await expect(page.locator('text=5')).toBeVisible() // Failed
  })

  test('AC 8: Should provide error log download for partial failures', async ({ page }) => {
    await page.goto('/upload')

    // Complete workflow setup with errors
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
          total_rows: 100,
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

    // Mock error log download
    await page.route('**/api/ingestion/job-123/errors', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/csv',
        body: 'row,error\n6,Invalid data',
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

    // Wait for summary and verify download button
    await expect(page.locator('button:has-text("Download Error Log")')).toBeVisible({ timeout: 10000 })
  })

  test('AC 9: Should allow uploading another file or navigating to chat', async ({ page }) => {
    await page.goto('/upload')

    // Setup complete successful upload
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
          total_rows: 100,
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

    // Wait for completion
    await expect(page.locator('text=Upload Complete!')).toBeVisible({ timeout: 10000 })

    // Verify action buttons
    await expect(page.locator('button:has-text("Upload Another File")')).toBeVisible()
    await expect(page.locator('button:has-text("View Data")')).toBeVisible()

    // Test "Upload Another" button
    await page.click('button:has-text("Upload Another File")')

    // Should reset to initial upload state
    await expect(page.locator('text=Drag and drop your CSV file')).toBeVisible()
  })

  test('AC 10: Should be responsive on different screen sizes', async ({ page }) => {
    await page.goto('/upload')

    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('text=Upload Skills CSV')).toBeVisible()

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('text=Upload Skills CSV')).toBeVisible()

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 })
    await expect(page.locator('text=Upload Skills CSV')).toBeVisible()
  })

  test('Should handle network errors during polling (RELIABILITY-001)', async ({ page }) => {
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
          total_rows: 100,
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

    // Should show connection error UI
    await expect(page.locator('text=Connection Error')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('button:has-text("Retry")')).toBeVisible()
  })
})
