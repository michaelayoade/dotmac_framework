/**
 * E2E tests for customer portal dashboard
 * Following backend E2E testing patterns
 */

import { expect, test } from '@playwright/test';

import { createTestHelpers } from '../utils/test-helpers';

test.describe('Customer Portal Dashboard', () => {
  let helpers: ReturnType<typeof createTestHelpers>;

  test.beforeEach(async ({ page: _page }) => {
    helpers = createTestHelpers(_page);
    await helpers.loginAs('customer');
  });

  test.afterEach(async ({ page: _page }) => {
    await helpers.logout();
  });

  test.describe('Dashboard Overview', () => {
    test('displays customer dashboard with key metrics', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Verify dashboard elements
      await expect(page.locator('[data-testid="dashboard-title"]')).toContainText('Dashboard');

      // Check service overview cards
      await expect(page.locator('[data-testid="service-status-card"]')).toBeVisible();
      await expect(page.locator('[data-testid="usage-card"]')).toBeVisible();
      await expect(page.locator('[data-testid="billing-card"]')).toBeVisible();
      await expect(page.locator('[data-testid="support-card"]')).toBeVisible();
    });

    test('shows current usage metrics', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Verify usage metrics are displayed
      await expect(page.locator('[data-testid="current-usage"]')).toBeVisible();
      await expect(page.locator('[data-testid="usage-percentage"]')).toBeVisible();
      await expect(page.locator('[data-testid="usage-chart"]')).toBeVisible();
    });

    test('displays recent activity', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Check recent activity section
      await expect(page.locator('[data-testid="recent-activity"]')).toBeVisible();
      await expect(page.locator('[data-testid="activity-item"]').first()).toBeVisible();
    });

    test('shows billing information', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Verify billing info
      await expect(page.locator('[data-testid="current-balance"]')).toBeVisible();
      await expect(page.locator('[data-testid="next-bill-date"]')).toBeVisible();
      await expect(page.locator('[data-testid="last-payment"]')).toBeVisible();
    });
  });

  test.describe('Service Status', () => {
    test('displays service connection status', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      const serviceStatus = page.locator('[data-testid="service-status"]');
      await expect(serviceStatus).toBeVisible();

      // Should show online/offline status
      await expect(serviceStatus.locator('[data-testid="connection-indicator"]')).toBeVisible();
    });

    test('allows running speed test', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Click speed test button
      await page.click('[data-testid="speed-test-button"]');

      // Wait for speed test modal
      await helpers.waitForModal('speed-test-modal');

      // Start speed test
      await page.click('[data-testid="start-speed-test"]');

      // Wait for test to complete
      await expect(page.locator('[data-testid="speed-test-results"]')).toBeVisible({
        timeout: 30000,
      });

      // Verify results are shown
      await expect(page.locator('[data-testid="download-speed"]')).toBeVisible();
      await expect(page.locator('[data-testid="upload-speed"]')).toBeVisible();
    });

    test('shows service details and plan information', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/services');

      // Verify service details
      await expect(page.locator('[data-testid="service-name"]')).toBeVisible();
      await expect(page.locator('[data-testid="service-plan"]')).toBeVisible();
      await expect(page.locator('[data-testid="service-speed"]')).toBeVisible();
      await expect(page.locator('[data-testid="monthly-price"]')).toBeVisible();
    });
  });

  test.describe('Usage Analytics', () => {
    test('displays usage history chart', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/usage');

      // Wait for chart to load
      await expect(page.locator('[data-testid="usage-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="chart-legend"]')).toBeVisible();
    });

    test('allows filtering usage by time period', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/usage');

      // Select different time period
      await page.selectOption('[data-testid="period-select"]', '7d');

      // Wait for chart to update
      await helpers.waitForLoadingToComplete();

      // Verify chart updated
      await expect(page.locator('[data-testid="usage-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="period-indicator"]')).toContainText('7 days');
    });

    test('shows usage breakdown by device', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/usage');

      // Click device breakdown tab
      await page.click('[data-testid="devices-tab"]');

      // Verify device breakdown
      await expect(page.locator('[data-testid="device-list"]')).toBeVisible();
      await expect(page.locator('[data-testid="device-item"]').first()).toBeVisible();
    });

    test('allows exporting usage data', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/usage');

      // Click export button
      await page.click('[data-testid="export-usage-button"]');

      // Wait for export modal
      await helpers.waitForModal('export-modal');

      // Select export format
      await page.selectOption('[data-testid="export-format"]', 'csv');

      // Confirm export
      await page.click('[data-testid="confirm-export"]');

      // Verify success message
      await helpers.expectSuccessMessage('Usage data exported successfully');
    });
  });

  test.describe('Billing Management', () => {
    test('displays current billing information', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/billing');

      // Verify billing overview
      await expect(page.locator('[data-testid="current-balance"]')).toBeVisible();
      await expect(page.locator('[data-testid="next-bill-amount"]')).toBeVisible();
      await expect(page.locator('[data-testid="next-bill-date"]')).toBeVisible();
    });

    test('shows invoice history', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/billing');

      // Click invoices tab
      await page.click('[data-testid="invoices-tab"]');

      // Verify invoice list
      await expect(page.locator('[data-testid="invoice-list"]')).toBeVisible();
      await expect(page.locator('[data-testid="invoice-item"]').first()).toBeVisible();
    });

    test('allows downloading individual invoices', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/billing');
      await page.click('[data-testid="invoices-tab"]');

      // Click download button for first invoice
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="download-invoice-button"]');
      const download = await downloadPromise;

      // Verify download started
      expect(download.suggestedFilename()).toContain('.pdf');
    });

    test('allows updating payment method', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/billing');

      // Click payment methods tab
      await page.click('[data-testid="payment-methods-tab"]');

      // Add new payment method
      await page.click('[data-testid="add-payment-method"]');

      // Wait for payment form
      await helpers.waitForModal('payment-method-modal');

      // Fill payment form
      await helpers.fillForm({
        'card-number': '4242424242424242',
        expiry: '12/25',
        cvc: '123',
        name: 'Test Customer',
      });

      // Submit payment method
      await helpers.submitForm('save-payment-method');

      // Verify success
      await helpers.expectSuccessMessage('Payment method added successfully');
    });
  });

  test.describe('Support Center', () => {
    test('displays support options', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/support');

      // Verify support options
      await expect(page.locator('[data-testid="create-ticket-button"]')).toBeVisible();
      await expect(page.locator('[data-testid="knowledge-base"]')).toBeVisible();
      await expect(page.locator('[data-testid="live-chat-button"]')).toBeVisible();
    });

    test('allows creating support ticket', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/support');

      // Click create ticket
      await page.click('[data-testid="create-ticket-button"]');

      // Fill ticket form
      await helpers.fillForm({
        'ticket-subject': 'E2E Test Ticket',
        'ticket-description': 'This is a test ticket created during E2E testing',
        'ticket-priority': 'medium',
      });

      // Submit ticket
      await helpers.submitForm('create-ticket-submit');

      // Verify ticket created
      await helpers.expectSuccessMessage('Support ticket created successfully');
      await expect(page.locator('[data-testid="ticket-number"]')).toBeVisible();
    });

    test('shows existing support tickets', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/support');

      // Click my tickets tab
      await page.click('[data-testid="my-tickets-tab"]');

      // Verify ticket list
      await expect(page.locator('[data-testid="ticket-list"]')).toBeVisible();
    });

    test('allows searching knowledge base', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/support');

      // Search knowledge base
      await helpers.searchTable('internet connection', 'kb-search');

      // Wait for search results
      await helpers.waitForLoadingToComplete();

      // Verify search results
      await expect(page.locator('[data-testid="kb-results"]')).toBeVisible();
      await expect(page.locator('[data-testid="kb-article"]').first()).toBeVisible();
    });
  });

  test.describe('Account Settings', () => {
    test('displays account information', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/account');

      // Verify account details
      await expect(page.locator('[data-testid="account-name"]')).toBeVisible();
      await expect(page.locator('[data-testid="account-email"]')).toBeVisible();
      await expect(page.locator('[data-testid="account-phone"]')).toBeVisible();
    });

    test('allows updating profile information', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/account');

      // Click edit profile
      await page.click('[data-testid="edit-profile-button"]');

      // Update profile
      await helpers.fillForm({
        'profile-name': 'Updated E2E Customer',
        'profile-phone': '+1 (555) 987-6543',
      });

      // Save changes
      await helpers.submitForm('save-profile');

      // Verify success
      await helpers.expectSuccessMessage('Profile updated successfully');
    });

    test('allows changing password', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/account');

      // Click security tab
      await page.click('[data-testid="security-tab"]');

      // Click change password
      await page.click('[data-testid="change-password-button"]');

      // Fill password form
      await helpers.fillForm({
        'current-password': 'customer-password',
        'new-password': 'new-password-123',
        'confirm-password': 'new-password-123',
      });

      // Submit password change
      await helpers.submitForm('change-password-submit');

      // Verify success
      await helpers.expectSuccessMessage('Password changed successfully');
    });
  });

  test.describe('Performance and Accessibility', () => {
    test('meets performance benchmarks', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Measure page load time
      const loadTime = await helpers.measurePageLoadTime();
      expect(loadTime).toBeLessThan(3000); // 3 seconds max

      // Get Core Web Vitals
      const vitals = await helpers.getCoreWebVitals();

      // FCP should be under 1.8s
      if (vitals.fcp) {
        expect(vitals.fcp).toBeLessThan(1800);
      }

      // LCP should be under 2.5s
      if (vitals.lcp) {
        expect(vitals.lcp).toBeLessThan(2500);
      }

      // CLS should be under 0.1
      if (vitals.cls) {
        expect(vitals.cls).toBeLessThan(0.1);
      }
    });

    test('passes accessibility audit', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Inject axe-core
      await page.addScriptTag({ url: 'https://unpkg.com/axe-core@4.8.3/axe.min.js' });

      // Run accessibility audit
      const violations = await helpers.checkA11y();

      // Should have no violations
      expect(violations.length).toBe(0);
    });

    test('works on mobile viewports', async ({ page: _page }) => {
      await helpers.setMobileViewport();
      await helpers.navigateTo('customer', '/dashboard');

      // Verify mobile layout
      await expect(page.locator('[data-testid="mobile-nav"]')).toBeVisible();
      await expect(page.locator('[data-testid="dashboard-mobile"]')).toBeVisible();

      // Test mobile navigation
      await page.click('[data-testid="mobile-menu-button"]');
      await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible();
    });
  });

  test.describe('Error Scenarios', () => {
    test('handles API errors gracefully', async ({ page: _page }) => {
      // Mock API error
      await helpers.mockApiError('/api/v1/usage', 500);

      await helpers.navigateTo('customer', '/usage');

      // Should show error message
      await helpers.expectErrorMessage('Unable to load usage data');

      // Should show retry button
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    });

    test('handles network connectivity issues', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Simulate network disconnect
      await page.context().setOffline(true);

      // Try to navigate to another page
      await page.click('[data-testid="nav-usage"]');

      // Should show offline message
      await expect(page.locator('[data-testid="offline-message"]')).toBeVisible();

      // Reconnect
      await page.context().setOffline(false);

      // Should recover automatically
      await helpers.waitForElement('[data-testid="usage-chart"]');
    });

    test('handles session expiration', async ({ page: _page }) => {
      await helpers.navigateTo('customer', '/dashboard');

      // Mock 401 response
      await helpers.mockApiError('/api/v1/**', 401, 'Session expired');

      // Try to make an API call
      await page.click('[data-testid="refresh-data"]');

      // Should redirect to login
      await page.waitForURL('/login');
      await expect(page.locator('[data-testid="session-expired-message"]')).toBeVisible();
    });
  });
});
