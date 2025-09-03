/**
 * Comprehensive E2E Workflow Tests
 * Tests complete user journeys across multiple portals with real API integration
 */

import { test, expect } from '@playwright/test';
import { setupAuth, setupAuthAPIMocks, validateAuthState, TEST_USERS } from '../auth/auth-helpers';
import { APIBehaviorTester } from '../fixtures/api-behaviors';

test.describe('Cross-Portal Workflow Integration', () => {
  test('should complete customer onboarding to service activation workflow', async ({ page }) => {
    const apiTester = new APIBehaviorTester(page, {
      enableMocking: true,
      validateRequests: true,
      simulateLatency: true,
    });

    // Setup customer authentication
    await setupAuth(page, 'customer');
    await setupAuthAPIMocks(page, 'customer');
    await apiTester.setupCustomerAPIMocks();

    // Start customer journey
    await page.goto('/');

    // Verify authentication state
    const authState = await validateAuthState(page, 'customer');
    expect(authState.hasToken).toBe(true);
    expect(authState.sessionActive).toBe(true);

    // Navigate through customer dashboard
    await expect(page.locator('[data-testid="customer-dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="welcome-message"]')).toContainText('Test Customer');

    // Check service status
    await expect(page.locator('[data-testid="service-status"]')).toContainText('Online');
    await expect(page.locator('[data-testid="data-usage"]')).toBeVisible();

    // Navigate to billing
    await page.click('[data-testid="nav-billing"]');
    await expect(page.url()).toContain('/billing');
    await expect(page.locator('[data-testid="billing-overview"]')).toBeVisible();

    // Verify API calls were made correctly
    const requestLog = apiTester.getRequestLog();
    expect(requestLog.some((req) => req.url.includes('/api/v1/customer/dashboard'))).toBe(true);
    expect(requestLog.some((req) => req.url.includes('/api/v1/customer/billing'))).toBe(true);

    // Test support ticket creation flow
    await page.click('[data-testid="nav-support"]');
    await page.click('[data-testid="new-ticket-btn"]');

    await page.fill('[data-testid="ticket-subject"]', 'Service upgrade request');
    await page.fill('[data-testid="ticket-description"]', 'Looking to upgrade to 1Gbps plan');
    await page.selectOption('[data-testid="ticket-priority"]', 'low');

    await page.click('[data-testid="submit-ticket"]');

    // Verify ticket creation
    await expect(page.locator('[data-testid="ticket-success"]')).toBeVisible();
    await expect(page.locator('[data-testid="ticket-id"]')).toContainText('TKT-TEST-NEW');

    // Validate data flows
    await apiTester.validateDataFlows([
      {
        endpoint: '/api/v1/customer/dashboard',
        method: 'GET',
      },
      {
        endpoint: '/api/v1/customer/billing',
        method: 'GET',
      },
      {
        endpoint: '/api/v1/customer/support/tickets',
        method: 'POST',
        requiredFields: ['subject', 'description'],
        dataTransformation: (data) => data.subject === 'Service upgrade request',
      },
    ]);
  });

  test('should handle admin customer management to technician dispatch workflow', async ({
    page,
  }) => {
    const apiTester = new APIBehaviorTester(page, {
      enableMocking: true,
      validateRequests: true,
    });

    // Setup admin authentication
    await setupAuth(page, 'admin');
    await setupAuthAPIMocks(page, 'admin');
    await apiTester.setupAdminAPIMocks();

    let workOrderCreated = false;

    // Mock work order creation API
    await page.route('/api/v1/admin/work-orders', async (route) => {
      if (route.request().method() === 'POST') {
        workOrderCreated = true;
        const requestBody = route.request().postDataJSON();

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'WO-CREATED-001',
            customer_id: requestBody.customer_id,
            type: requestBody.type,
            status: 'pending_assignment',
            created_at: new Date().toISOString(),
          }),
        });
      }
    });

    // Start admin workflow
    await page.goto('/admin');

    // Navigate to customer management
    await page.click('[data-testid="nav-customers"]');
    await expect(page.locator('[data-testid="customers-table"]')).toBeVisible();

    // Select customer and view details
    await page.click('[data-testid="customer-row"]:has-text("John Doe")');
    await expect(page.locator('[data-testid="customer-details"]')).toBeVisible();

    // Create work order for customer
    await page.click('[data-testid="create-work-order"]');
    await page.selectOption('[data-testid="work-order-type"]', 'installation');
    await page.fill('[data-testid="work-order-notes"]', 'Fiber installation for new customer');
    await page.selectOption('[data-testid="work-order-priority"]', 'high');

    await page.click('[data-testid="submit-work-order"]');

    // Verify work order creation
    expect(workOrderCreated).toBe(true);
    await expect(page.locator('[data-testid="work-order-success"]')).toBeVisible();
    await expect(page.locator('[data-testid="work-order-id"]')).toContainText('WO-CREATED-001');
  });

  test('should handle session timeout and re-authentication across portals', async ({ page }) => {
    // Setup initial auth
    await setupAuth(page, 'admin');

    let authRefreshCalled = false;

    // Mock auth validation that fails initially
    await page.route('/api/auth/validate', async (route, request) => {
      const attempt = await page.evaluate(() =>
        parseInt(sessionStorage.getItem('auth_attempts') || '0')
      );

      if (attempt === 0) {
        await page.evaluate(() => sessionStorage.setItem('auth_attempts', '1'));

        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            valid: false,
            error: 'Token expired',
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            valid: true,
            user: TEST_USERS.admin,
          }),
        });
      }
    });

    // Mock refresh endpoint
    await page.route('/api/auth/refresh', async (route) => {
      authRefreshCalled = true;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          token: 'new-admin-token-12345',
          expires_at: Date.now() + 24 * 60 * 60 * 1000,
          user: TEST_USERS.admin,
        }),
      });
    });

    // Navigate to protected admin page
    await page.goto('/admin/dashboard');

    // Should trigger re-authentication flow
    await page.waitForTimeout(2000);
    expect(authRefreshCalled).toBe(true);

    // Should eventually load dashboard
    await expect(page.locator('[data-testid="admin-dashboard"]')).toBeVisible();

    // Verify new token is stored
    const newToken = await page.evaluate(() => localStorage.getItem('admin_auth_token'));
    expect(newToken).toBe('new-admin-token-12345');
  });

  test('should validate API error handling and user feedback', async ({ page }) => {
    await setupAuth(page, 'customer');

    // Test 500 error handling
    await page.route('/api/v1/customer/dashboard', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Database connection failed',
          code: 'DB_CONNECTION_ERROR',
        }),
      });
    });

    await page.goto('/dashboard');

    // Should show error state
    await expect(page.locator('[data-testid="error-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText(
      'Unable to load dashboard'
    );
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();

    // Test retry functionality
    await page.route('/api/v1/customer/dashboard', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          account: { id: 'CUST-TEST-001', name: 'Test Customer' },
          service: { status: 'online', uptime: 99.8 },
        }),
      });
    });

    await page.click('[data-testid="retry-button"]');

    // Should hide error and show content
    await expect(page.locator('[data-testid="error-banner"]')).toBeHidden();
    await expect(page.locator('[data-testid="dashboard-content"]')).toBeVisible();
  });

  test('should validate business logic in API responses', async ({ page }) => {
    const apiTester = new APIBehaviorTester(page, {
      enableMocking: true,
      validateRequests: true,
    });

    await setupAuth(page, 'reseller');
    await apiTester.setupResellerAPIMocks();

    await page.goto('/reseller/dashboard');

    // Verify commission calculations are correct
    await expect(page.locator('[data-testid="total-customers"]')).toContainText('156');

    // Get displayed values and verify calculations
    const monthlyRevenue = await page.locator('[data-testid="monthly-revenue"]').textContent();
    const commissionRate = await page.locator('[data-testid="commission-rate"]').textContent();
    const monthlyCommission = await page
      .locator('[data-testid="monthly-commission"]')
      .textContent();

    // Verify commission calculation: revenue * (rate / 100)
    const revenue = parseFloat(monthlyRevenue?.replace(/[$,]/g, '') || '0');
    const rate = parseFloat(commissionRate?.replace('%', '') || '0');
    const expectedCommission = revenue * (rate / 100);
    const actualCommission = parseFloat(monthlyCommission?.replace(/[$,]/g, '') || '0');

    expect(Math.abs(actualCommission - expectedCommission)).toBeLessThan(1); // Within $1

    // Verify penetration rate calculations
    const penetrationRate = await page.locator('[data-testid="penetration-rate"]').textContent();
    const rate_value = parseFloat(penetrationRate?.replace('%', '') || '0');

    // Should be reasonable (between 0-100%)
    expect(rate_value).toBeGreaterThan(0);
    expect(rate_value).toBeLessThan(100);
  });

  test('should test offline behavior and data persistence', async ({ page }) => {
    await setupAuth(page, 'technician');

    // Load initial data
    await page.goto('/technician/work-orders');
    await expect(page.locator('[data-testid="work-orders-list"]')).toBeVisible();

    // Go offline
    await page.context().setOffline(true);

    // Should show offline banner
    await expect(page.locator('[data-testid="offline-banner"]')).toBeVisible();

    // Should still show cached data
    await expect(page.locator('[data-testid="work-orders-list"]')).toBeVisible();

    // Test offline form submission queuing
    await page.click('[data-testid="work-order-WO-TEST-001"]');
    await page.click('[data-testid="update-status"]');
    await page.selectOption('[data-testid="status-select"]', 'in_progress');
    await page.click('[data-testid="save-status"]');

    // Should show queued message
    await expect(page.locator('[data-testid="update-queued"]')).toBeVisible();

    // Go back online
    await page.context().setOffline(false);

    // Should sync queued changes
    await expect(page.locator('[data-testid="sync-complete"]')).toBeVisible();
    await expect(page.locator('[data-testid="offline-banner"]')).toBeHidden();
  });
});
