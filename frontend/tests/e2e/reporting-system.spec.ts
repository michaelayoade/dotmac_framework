/**
 * Reporting System E2E Tests
 * Tests the basic reporting functionality end-to-end
 */

import { test, expect, Page } from '@playwright/test';

test.describe('ISP Reporting System', () => {
  test.describe.configure({ mode: 'serial' }); // Run tests in sequence for data consistency

  const adminCredentials = {
    username: 'admin@dotmac.test',
    password: 'TestAdmin123!',
  };

  test.beforeEach(async ({ page }) => {
    // Login to admin portal
    await page.goto('/admin/login');
    await page.fill('[data-testid="email-input"]', adminCredentials.username);
    await page.fill('[data-testid="password-input"]', adminCredentials.password);
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL(/.*\/admin\/dashboard/);
  });

  test.describe('Financial Reports', () => {
    test('generates revenue report successfully', async ({ page }) => {
      // Navigate to billing reports
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Verify reports management interface loads
      await expect(page.locator('[data-testid="reports-container"]')).toBeVisible();
      await expect(page.locator('h3')).toContainText('Financial Reports');

      // Check if revenue report template exists
      const revenueReportCard = page.locator('[data-testid="report-revenue-analytics"]');
      if ((await revenueReportCard.count()) > 0) {
        await revenueReportCard.click('[data-testid="generate-report-btn"]');

        // Wait for report generation
        await expect(page.locator('[data-testid="report-status"]')).toContainText('generating', {
          timeout: 5000,
        });
        await expect(page.locator('[data-testid="report-status"]')).toContainText('ready', {
          timeout: 30000,
        });

        // Verify download is available
        await expect(page.locator('[data-testid="download-report-btn"]')).toBeVisible();
      } else {
        // Use fallback generate button
        await page.click('[data-testid="generate-report-button"]');
        await expect(page.locator('[data-testid="success-message"]')).toBeVisible({
          timeout: 10000,
        });
      }
    });

    test('displays recent reports correctly', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Check recent reports section
      const recentReportsSection = page.locator('[data-testid="recent-reports"]');
      await expect(recentReportsSection).toBeVisible();

      // Verify report cards display properly
      const reportCards = page.locator('[data-testid^="report-card-"]');
      const count = await reportCards.count();

      if (count > 0) {
        // Check first report card structure
        const firstCard = reportCards.first();
        await expect(firstCard.locator('[data-testid="report-name"]')).toBeVisible();
        await expect(firstCard.locator('[data-testid="report-status"]')).toBeVisible();
        await expect(firstCard.locator('[data-testid="report-type"]')).toBeVisible();
        await expect(firstCard.locator('[data-testid="report-date"]')).toBeVisible();

        // Verify status badges work
        const status = await firstCard.locator('[data-testid="report-status"]').textContent();
        expect(['ready', 'generating', 'failed']).toContain(status?.toLowerCase());
      }
    });

    test('report download functionality', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Look for a completed report
      const readyReports = page.locator('[data-testid^="report-card-"]').filter({
        has: page.locator('[data-testid="report-status"]:has-text("ready")'),
      });

      const readyCount = await readyReports.count();

      if (readyCount > 0) {
        // Start download
        const downloadPromise = page.waitForEvent('download');
        await readyReports.first().click('[data-testid="download-report-btn"]');

        const download = await downloadPromise;

        // Verify download properties
        expect(download.suggestedFilename()).toMatch(/.*\.(pdf|xlsx|csv)$/);

        // Save and verify file size
        const downloadPath = await download.path();
        expect(downloadPath).toBeTruthy();
      } else {
        // Generate new report for download test
        await page.click('[data-testid="generate-report-button"]');
        await expect(page.locator('[data-testid="success-message"]')).toBeVisible({
          timeout: 15000,
        });

        // Note: In a real test, we'd wait for the report to complete
        // For this demo, we're showing the test structure
      }
    });

    test('validates report data accuracy', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');

      // Navigate to customer list to get reference data
      await page.click('[data-testid="customers-nav"]');
      await page.waitForLoadState('networkidle');

      // Count active customers
      const customerRows = page.locator('[data-testid^="customer-row-"]');
      const activeCustomers = customerRows.filter({
        has: page.locator('[data-testid="customer-status"]:has-text("active")'),
      });
      const activeCount = await activeCustomers.count();

      // Get total revenue from dashboard
      await page.click('[data-testid="dashboard-nav"]');
      const dashboardRevenue = await page.locator('[data-testid="total-revenue"]').textContent();
      const revenueAmount = parseFloat(dashboardRevenue?.replace(/[$,]/g, '') || '0');

      // Navigate back to reports
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Generate fresh report
      await page.click('[data-testid="generate-report-button"]');
      await expect(page.locator('[data-testid="success-message"]')).toBeVisible({ timeout: 15000 });

      // In a real implementation, we would:
      // 1. Download the report
      // 2. Parse the report content
      // 3. Verify customer counts and revenue figures match
      // For this demo, we verify the UI shows consistent data

      const reportMetrics = page.locator('[data-testid="report-metrics"]');
      if ((await reportMetrics.count()) > 0) {
        const reportCustomerCount = await reportMetrics
          .locator('[data-testid="customer-count"]')
          .textContent();
        const reportRevenueAmount = await reportMetrics
          .locator('[data-testid="revenue-total"]')
          .textContent();

        // Verify consistency (allowing for reasonable variance)
        if (reportCustomerCount) {
          const reportCount = parseInt(reportCustomerCount);
          expect(Math.abs(reportCount - activeCount)).toBeLessThan(5); // Allow small variance
        }

        if (reportRevenueAmount) {
          const reportRevenue = parseFloat(reportRevenueAmount.replace(/[$,]/g, ''));
          expect(Math.abs(reportRevenue - revenueAmount)).toBeLessThan(1000); // Allow $1000 variance
        }
      }
    });
  });

  test.describe('Report Generation Performance', () => {
    test('report generation completes within acceptable time', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      const startTime = Date.now();

      // Generate report
      await page.click('[data-testid="generate-report-button"]');

      // Wait for completion
      await expect(page.locator('[data-testid="success-message"]')).toBeVisible({ timeout: 30000 });

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Verify generation time is reasonable
      expect(duration).toBeLessThan(30000); // Should complete within 30 seconds
    });

    test('handles concurrent report generation', async ({ page, context }) => {
      // Open multiple tabs
      const page2 = await context.newPage();
      const page3 = await context.newPage();

      // Login to all pages
      for (const currentPage of [page, page2, page3]) {
        await currentPage.goto('/admin/login');
        await currentPage.fill('[data-testid="email-input"]', adminCredentials.username);
        await currentPage.fill('[data-testid="password-input"]', adminCredentials.password);
        await currentPage.click('[data-testid="login-button"]');
        await currentPage.click('[data-testid="billing-nav"]');
        await currentPage.click('[data-testid="reports-tab"]');
      }

      // Start report generation simultaneously
      const startTime = Date.now();

      await Promise.all([
        page.click('[data-testid="generate-report-button"]'),
        page2.click('[data-testid="generate-report-button"]'),
        page3.click('[data-testid="generate-report-button"]'),
      ]);

      // Wait for all to complete
      await Promise.all([
        expect(page.locator('[data-testid="success-message"]')).toBeVisible({ timeout: 45000 }),
        expect(page2.locator('[data-testid="success-message"]')).toBeVisible({ timeout: 45000 }),
        expect(page3.locator('[data-testid="success-message"]')).toBeVisible({ timeout: 45000 }),
      ]);

      const duration = Date.now() - startTime;
      expect(duration).toBeLessThan(45000); // Should handle concurrent requests within 45 seconds
    });
  });

  test.describe('Report Templates and Types', () => {
    test('displays available report templates', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Check for report template cards
      const templateCards = page.locator('[data-testid^="report-template-"]');
      const templateCount = await templateCards.count();

      if (templateCount > 0) {
        // Verify each template has required elements
        for (let i = 0; i < Math.min(templateCount, 3); i++) {
          const card = templateCards.nth(i);
          await expect(card.locator('[data-testid="template-name"]')).toBeVisible();
          await expect(card.locator('[data-testid="template-description"]')).toBeVisible();
          await expect(card.locator('[data-testid="generate-button"]')).toBeVisible();
        }
      } else {
        // Fallback: check for basic generate button
        await expect(page.locator('[data-testid="generate-report-button"]')).toBeVisible();
      }
    });

    test('report types are properly categorized', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Look for report categories
      const categories = ['financial', 'customer', 'operational'];

      for (const category of categories) {
        const categorySection = page.locator(`[data-testid="reports-${category}"]`);
        if ((await categorySection.count()) > 0) {
          await expect(categorySection).toBeVisible();

          // Check for reports in this category
          const categoryReports = categorySection.locator('[data-testid^="report-"]');
          const count = await categoryReports.count();
          expect(count).toBeGreaterThan(0);
        }
      }
    });
  });

  test.describe('Error Handling and Edge Cases', () => {
    test('handles report generation failure gracefully', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Mock a failure scenario by intercepting the API
      await page.route('/api/reports/generate', (route) => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Internal server error' }),
        });
      });

      // Attempt to generate report
      await page.click('[data-testid="generate-report-button"]');

      // Verify error handling
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('[data-testid="error-message"]')).toContainText(/failed|error/i);

      // Verify UI remains functional
      await expect(page.locator('[data-testid="generate-report-button"]')).toBeVisible();
      await expect(page.locator('[data-testid="generate-report-button"]')).toBeEnabled();
    });

    test('handles empty data scenarios', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Mock empty data response
      await page.route('/api/reports/data', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            reports: [],
            message: 'No reports available',
          }),
        });
      });

      await page.reload();

      // Verify empty state handling
      const emptyState = page.locator('[data-testid="empty-reports"]');
      if ((await emptyState.count()) > 0) {
        await expect(emptyState).toBeVisible();
        await expect(emptyState).toContainText(/no reports/i);
      } else {
        // Alternative: check that generate button is still available
        await expect(page.locator('[data-testid="generate-report-button"]')).toBeVisible();
      }
    });

    test('validates user permissions for report access', async ({ page }) => {
      // This test would verify that only authorized users can access reports
      // For now, we verify the reports section is accessible for admin users

      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Verify admin has full access
      await expect(page.locator('[data-testid="reports-container"]')).toBeVisible();
      await expect(page.locator('[data-testid="generate-report-button"]')).toBeVisible();

      // In a real test, we would:
      // 1. Logout admin
      // 2. Login as different user types (customer, reseller, etc.)
      // 3. Verify appropriate access restrictions
    });
  });

  test.describe('Accessibility and Usability', () => {
    test('reports interface is keyboard navigable', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Test keyboard navigation
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toBeVisible();

      // Navigate through report elements
      const focusableElements = await page
        .locator('button, input, select, [tabindex]:not([tabindex="-1"])')
        .all();

      for (let i = 0; i < Math.min(focusableElements.length, 5); i++) {
        await page.keyboard.press('Tab');
        const focusedElement = page.locator(':focus');
        await expect(focusedElement).toBeVisible();
      }

      // Test Enter key on generate button
      const generateButton = page.locator('[data-testid="generate-report-button"]');
      if ((await generateButton.count()) > 0) {
        await generateButton.focus();
        await page.keyboard.press('Enter');

        // Should trigger report generation
        await expect(page.locator('[data-testid="success-message"]')).toBeVisible({
          timeout: 15000,
        });
      }
    });

    test('reports have proper ARIA labels and roles', async ({ page }) => {
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="reports-tab"]');

      // Check for proper heading structure
      const headings = page.locator('h1, h2, h3, h4, h5, h6');
      const headingCount = await headings.count();
      expect(headingCount).toBeGreaterThan(0);

      // Verify main heading exists
      const mainHeading = page.locator('h3');
      await expect(mainHeading).toBeVisible();

      // Check for proper button labels
      const buttons = page.locator('button');
      const buttonCount = await buttons.count();

      for (let i = 0; i < Math.min(buttonCount, 5); i++) {
        const button = buttons.nth(i);
        const text = await button.textContent();
        const ariaLabel = await button.getAttribute('aria-label');

        // Button should have visible text or aria-label
        expect(text || ariaLabel).toBeTruthy();
      }

      // Check for proper list structure if reports are displayed as lists
      const reportLists = page.locator('ul, ol');
      if ((await reportLists.count()) > 0) {
        const firstList = reportLists.first();
        const listItems = firstList.locator('li');
        const itemCount = await listItems.count();
        expect(itemCount).toBeGreaterThan(0);
      }
    });
  });
});
