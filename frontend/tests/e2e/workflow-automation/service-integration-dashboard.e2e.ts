/**
 * Service Integration Dashboard E2E Tests
 * Tests complete integration monitoring and management workflows
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';

test.describe('Service Integration Dashboard - Complete Monitoring Experience', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin');
    await page.goto('/admin/service-integration-dashboard');

    // Wait for dashboard to load
    await expect(page.locator('[data-testid="integration-dashboard"]')).toBeVisible();
  });

  test('should display comprehensive integration overview with real metrics', async ({ page }) => {
    // Verify overview tab loads with key metrics
    await page.click('[data-testid="overview-tab"]');
    await expect(page.locator('[data-testid="overview-content"]')).toBeVisible();

    // Check key performance indicators
    await expect(page.locator('[data-testid="active-integrations"]')).toBeVisible();
    await expect(page.locator('[data-testid="success-rate"]')).toBeVisible();
    await expect(page.locator('[data-testid="avg-response-time"]')).toBeVisible();
    await expect(page.locator('[data-testid="avg-uptime"]')).toBeVisible();

    // Verify metrics have reasonable values
    const activeIntegrations = await page
      .locator('[data-testid="active-integrations"]')
      .textContent();
    const successRate = await page.locator('[data-testid="success-rate"]').textContent();
    const responseTime = await page.locator('[data-testid="avg-response-time"]').textContent();
    const uptime = await page.locator('[data-testid="avg-uptime"]').textContent();

    expect(parseInt(activeIntegrations || '0')).toBeGreaterThanOrEqual(0);
    expect(parseFloat(successRate?.replace('%', '') || '0')).toBeLessThanOrEqual(100);
    expect(parseInt(responseTime?.replace('ms', '') || '0')).toBeGreaterThan(0);
    expect(parseFloat(uptime?.replace('%', '') || '0')).toBeLessThanOrEqual(100);

    // Check integration status indicators
    await expect(page.locator('[data-testid="integration-status-list"]')).toBeVisible();

    const statusItems = page.locator('[data-testid="integration-status-item"]');
    const itemCount = await statusItems.count();
    expect(itemCount).toBeGreaterThan(0);

    // Verify each integration has required status information
    for (let i = 0; i < Math.min(itemCount, 3); i++) {
      const item = statusItems.nth(i);
      await expect(item.locator('[data-testid="integration-name"]')).toBeVisible();
      await expect(item.locator('[data-testid="integration-status-badge"]')).toBeVisible();
      await expect(item.locator('[data-testid="last-sync-time"]')).toBeVisible();
    }

    // Test recent activity feed
    await expect(page.locator('[data-testid="recent-activity"]')).toBeVisible();

    const activityItems = page.locator('[data-testid="activity-item"]');
    if ((await activityItems.count()) > 0) {
      const firstActivity = activityItems.first();
      await expect(firstActivity.locator('[data-testid="activity-integration"]')).toBeVisible();
      await expect(firstActivity.locator('[data-testid="activity-timestamp"]')).toBeVisible();
    }
  });

  test('should manage ISP service integrations with filtering and testing', async ({ page }) => {
    // Navigate to integrations tab
    await page.click('[data-testid="integrations-tab"]');
    await expect(page.locator('[data-testid="integrations-table"]')).toBeVisible();

    // Test filtering functionality
    await page.selectOption('[data-testid="status-filter"]', 'active');
    await expect(page.locator('[data-testid="integrations-table"]')).toBeVisible();

    const activeIntegrations = page.locator(
      '[data-testid="integration-row"][data-status="active"]'
    );
    const activeCount = await activeIntegrations.count();

    await page.selectOption('[data-testid="type-filter"]', 'api');
    await expect(page.locator('[data-testid="integrations-table"]')).toBeVisible();

    // Reset filters
    await page.selectOption('[data-testid="status-filter"]', 'all');
    await page.selectOption('[data-testid="type-filter"]', 'all');

    // Verify integration table columns
    await expect(page.locator('[data-testid="integration-header-name"]')).toContainText('Name');
    await expect(page.locator('[data-testid="integration-header-type"]')).toContainText('Type');
    await expect(page.locator('[data-testid="integration-header-status"]')).toContainText('Status');
    await expect(page.locator('[data-testid="integration-header-response-time"]')).toContainText(
      'Response Time'
    );
    await expect(page.locator('[data-testid="integration-header-uptime"]')).toContainText('Uptime');

    // Test individual integration management
    const integrationRows = page.locator('[data-testid="integration-row"]');
    if ((await integrationRows.count()) > 0) {
      const firstIntegration = integrationRows.first();

      // Test toggle integration
      const toggleButton = firstIntegration.locator('[data-testid="toggle-integration"]');
      await toggleButton.click();

      // Verify confirmation dialog
      await expect(page.locator('[data-testid="toggle-confirm-dialog"]')).toBeVisible();
      await page.click('[data-testid="confirm-toggle"]');

      // Test integration testing
      const testButton = firstIntegration.locator('[data-testid="test-integration"]');
      await testButton.click();

      // Verify test results dialog
      await expect(page.locator('[data-testid="test-results-dialog"]')).toBeVisible();
      await expect(page.locator('[data-testid="test-status"]')).toBeVisible();

      // Check test results content
      const testStatus = await page.locator('[data-testid="test-status"]').textContent();
      expect(['Success', 'Failed', 'Timeout'].some((status) => testStatus?.includes(status))).toBe(
        true
      );

      await page.click('[data-testid="close-test-results"]');

      // Test edit integration
      const editButton = firstIntegration.locator('[data-testid="edit-integration"]');
      await editButton.click();

      // Verify edit dialog opens
      await expect(page.locator('[data-testid="edit-integration-dialog"]')).toBeVisible();
      await expect(page.locator('[data-testid="integration-name-input"]')).toBeVisible();
      await expect(page.locator('[data-testid="integration-type-select"]')).toBeVisible();

      await page.click('[data-testid="cancel-edit"]');
    }
  });

  test('should create and configure new ISP service integration', async ({ page }) => {
    // Navigate to integrations tab
    await page.click('[data-testid="integrations-tab"]');

    // Create new integration
    await page.click('[data-testid="add-integration-btn"]');
    await expect(page.locator('[data-testid="new-integration-dialog"]')).toBeVisible();

    // Fill integration details
    await page.fill('[data-testid="integration-name-input"]', 'ISP Billing Gateway');
    await page.selectOption('[data-testid="integration-type-select"]', 'external');
    await page.fill('[data-testid="integration-endpoint"]', 'https://api.billing-provider.com');
    await page.fill(
      '[data-testid="integration-description"]',
      'External billing system integration for ISP customers'
    );

    // Configure integration settings
    await page.fill('[data-testid="timeout-setting"]', '30000');
    await page.fill('[data-testid="retry-attempts"]', '3');
    await page.check('[data-testid="enable-logging"]');

    // Add authentication details
    await page.click('[data-testid="auth-tab"]');
    await page.selectOption('[data-testid="auth-type"]', 'bearer');
    await page.fill('[data-testid="auth-token"]', 'test-billing-api-token-12345');

    // Add health check configuration
    await page.click('[data-testid="health-check-tab"]');
    await page.fill('[data-testid="health-check-endpoint"]', '/api/health');
    await page.fill('[data-testid="health-check-interval"]', '300'); // 5 minutes

    // Save integration
    await page.click('[data-testid="save-integration"]');
    await expect(page.locator('[data-testid="integration-saved"]')).toContainText(
      'Integration saved successfully'
    );

    // Verify integration appears in table
    await expect(page.locator('[data-testid="integration-row"]')).toContainText(
      'ISP Billing Gateway'
    );

    // Test the new integration
    const newIntegrationRow = page.locator('[data-testid="integration-row"]', {
      hasText: 'ISP Billing Gateway',
    });
    await newIntegrationRow.locator('[data-testid="test-integration"]').click();

    // Mock successful test response
    await page.route('https://api.billing-provider.com/api/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          version: '2.1.0',
          uptime: 99.9,
          last_check: new Date().toISOString(),
        }),
      });
    });

    // Verify test results
    await expect(page.locator('[data-testid="test-results-dialog"]')).toBeVisible();
    await expect(page.locator('[data-testid="test-status"]')).toContainText('Success');
    await expect(page.locator('[data-testid="test-response-time"]')).toBeVisible();

    await page.click('[data-testid="close-test-results"]');
  });

  test('should monitor integration performance and handle alerts', async ({ page }) => {
    // Navigate to monitoring tab
    await page.click('[data-testid="monitoring-tab"]');
    await expect(page.locator('[data-testid="monitoring-content"]')).toBeVisible();

    // Verify monitoring cards for each integration
    const monitoringCards = page.locator('[data-testid="integration-monitoring-card"]');
    const cardCount = await monitoringCards.count();
    expect(cardCount).toBeGreaterThan(0);

    // Test first monitoring card
    const firstCard = monitoringCards.first();
    await expect(firstCard.locator('[data-testid="integration-name"]')).toBeVisible();
    await expect(firstCard.locator('[data-testid="integration-status-badge"]')).toBeVisible();

    // Check uptime progress bar
    await expect(firstCard.locator('[data-testid="uptime-progress"]')).toBeVisible();
    const uptimeValue = await firstCard.locator('[data-testid="uptime-percentage"]').textContent();
    const uptime = parseFloat(uptimeValue?.replace('%', '') || '0');
    expect(uptime).toBeLessThanOrEqual(100);
    expect(uptime).toBeGreaterThanOrEqual(0);

    // Check metrics
    await expect(firstCard.locator('[data-testid="requests-count"]')).toBeVisible();
    await expect(firstCard.locator('[data-testid="errors-count"]')).toBeVisible();
    await expect(firstCard.locator('[data-testid="avg-response-time"]')).toBeVisible();

    const requestsCount = await firstCard.locator('[data-testid="requests-count"]').textContent();
    const errorsCount = await firstCard.locator('[data-testid="errors-count"]').textContent();
    const avgResponseTime = await firstCard
      .locator('[data-testid="avg-response-time"]')
      .textContent();

    expect(parseInt(requestsCount || '0')).toBeGreaterThanOrEqual(0);
    expect(parseInt(errorsCount || '0')).toBeGreaterThanOrEqual(0);
    expect(parseInt(avgResponseTime?.replace('ms', '') || '0')).toBeGreaterThan(0);

    // Test alert simulation
    await page.click('[data-testid="simulate-alert-btn"]');
    await page.selectOption('[data-testid="alert-integration"]', '1'); // First integration
    await page.selectOption('[data-testid="alert-type"]', 'high_response_time');
    await page.fill('[data-testid="alert-threshold"]', '5000');

    await page.click('[data-testid="trigger-alert"]');

    // Verify alert appears
    await expect(page.locator('[data-testid="alert-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="alert-message"]')).toContainText(
      'High response time detected'
    );

    // Test alert acknowledgment
    await page.click('[data-testid="acknowledge-alert"]');
    await expect(page.locator('[data-testid="alert-acknowledged"]')).toContainText(
      'Alert acknowledged'
    );

    // Test metric refresh
    await page.click('[data-testid="refresh-metrics-btn"]');
    await expect(page.locator('[data-testid="metrics-refreshed"]')).toBeVisible();
  });

  test('should display performance analytics with charts and trends', async ({ page }) => {
    // Navigate to analytics tab
    await page.click('[data-testid="analytics-tab"]');
    await expect(page.locator('[data-testid="analytics-content"]')).toBeVisible();

    // Verify performance chart is displayed
    await expect(page.locator('[data-testid="performance-chart"]')).toBeVisible();

    // Test time range selection
    await page.click('[data-testid="time-range-selector"]');
    await page.click('[data-testid="last-24-hours"]');

    // Verify chart updates
    await expect(page.locator('[data-testid="chart-loading"]')).toBeVisible();
    await expect(page.locator('[data-testid="chart-loading"]')).not.toBeVisible();

    // Check chart data is displayed
    const chartCanvas = page.locator('[data-testid="performance-chart"] canvas');
    await expect(chartCanvas).toBeVisible();

    // Test different chart views
    await page.click('[data-testid="chart-type-response-time"]');
    await expect(page.locator('[data-testid="response-time-chart"]')).toBeVisible();

    await page.click('[data-testid="chart-type-error-rate"]');
    await expect(page.locator('[data-testid="error-rate-chart"]')).toBeVisible();

    await page.click('[data-testid="chart-type-throughput"]');
    await expect(page.locator('[data-testid="throughput-chart"]')).toBeVisible();

    // Verify integration comparison table
    await expect(page.locator('[data-testid="integration-comparison"]')).toBeVisible();

    const comparisonRows = page.locator('[data-testid="comparison-row"]');
    const comparisonCount = await comparisonRows.count();

    if (comparisonCount > 0) {
      const firstRow = comparisonRows.first();
      await expect(firstRow.locator('[data-testid="integration-name"]')).toBeVisible();
      await expect(firstRow.locator('[data-testid="avg-response-time"]')).toBeVisible();
      await expect(firstRow.locator('[data-testid="success-rate"]')).toBeVisible();
      await expect(firstRow.locator('[data-testid="uptime"]')).toBeVisible();
    }

    // Test export functionality
    await page.click('[data-testid="export-analytics"]');

    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="export-csv"]');
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/integration-analytics.*\.csv$/);
  });

  test('should handle integration failures and recovery scenarios', async ({ page }) => {
    // Navigate to integrations tab
    await page.click('[data-testid="integrations-tab"]');

    // Create integration for failure testing
    await page.click('[data-testid="add-integration-btn"]');
    await page.fill('[data-testid="integration-name-input"]', 'Test Failure Integration');
    await page.selectOption('[data-testid="integration-type-select"]', 'api');
    await page.fill('[data-testid="integration-endpoint"]', 'https://api.test-failure.com');
    await page.click('[data-testid="save-integration"]');

    // Mock failure response
    await page.route('https://api.test-failure.com/**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Internal Server Error',
          code: 'SERVER_ERROR',
          message: 'Service temporarily unavailable',
        }),
      });
    });

    // Test the failing integration
    const failureIntegrationRow = page.locator('[data-testid="integration-row"]', {
      hasText: 'Test Failure Integration',
    });
    await failureIntegrationRow.locator('[data-testid="test-integration"]').click();

    // Verify failure is handled gracefully
    await expect(page.locator('[data-testid="test-results-dialog"]')).toBeVisible();
    await expect(page.locator('[data-testid="test-status"]')).toContainText('Failed');
    await expect(page.locator('[data-testid="error-message"]')).toContainText(
      'Service temporarily unavailable'
    );
    await expect(page.locator('[data-testid="error-code"]')).toContainText('SERVER_ERROR');

    await page.click('[data-testid="close-test-results"]');

    // Verify integration status shows as error
    await expect(failureIntegrationRow.locator('[data-testid="integration-status"]')).toContainText(
      'error'
    );

    // Test recovery by mocking successful response
    await page.route('https://api.test-failure.com/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          message: 'Service restored',
        }),
      });
    });

    // Test integration again
    await failureIntegrationRow.locator('[data-testid="test-integration"]').click();

    // Verify recovery
    await expect(page.locator('[data-testid="test-status"]')).toContainText('Success');
    await expect(page.locator('[data-testid="test-message"]')).toContainText('Service restored');

    await page.click('[data-testid="close-test-results"]');

    // Test bulk health check
    await page.click('[data-testid="bulk-health-check"]');
    await expect(page.locator('[data-testid="health-check-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="health-check-results"]')).toBeVisible();

    // Verify health check results
    const healthResults = page.locator('[data-testid="health-result-item"]');
    const healthCount = await healthResults.count();
    expect(healthCount).toBeGreaterThan(0);

    if (healthCount > 0) {
      const firstResult = healthResults.first();
      await expect(firstResult.locator('[data-testid="integration-name"]')).toBeVisible();
      await expect(firstResult.locator('[data-testid="health-status"]')).toBeVisible();
      await expect(firstResult.locator('[data-testid="response-time"]')).toBeVisible();
    }
  });

  test('should configure integration webhooks and event handling', async ({ page }) => {
    // Navigate to integrations tab and create webhook integration
    await page.click('[data-testid="integrations-tab"]');
    await page.click('[data-testid="add-integration-btn"]');

    await page.fill('[data-testid="integration-name-input"]', 'Customer Portal Webhook');
    await page.selectOption('[data-testid="integration-type-select"]', 'webhook');
    await page.fill('[data-testid="integration-endpoint"]', '/webhooks/customer-events');
    await page.fill(
      '[data-testid="integration-description"]',
      'Webhook for customer portal events'
    );

    // Configure webhook settings
    await page.click('[data-testid="webhook-settings-tab"]');
    await page.selectOption('[data-testid="webhook-method"]', 'POST');
    await page.fill('[data-testid="webhook-secret"]', 'webhook-secret-key-123');
    await page.check('[data-testid="enable-retries"]');
    await page.fill('[data-testid="max-retries"]', '3');

    // Configure event filters
    await page.check('[data-testid="event-customer-signup"]');
    await page.check('[data-testid="event-payment-completed"]');
    await page.check('[data-testid="event-service-activated"]');

    // Add custom headers
    await page.click('[data-testid="add-header-btn"]');
    await page.fill('[data-testid="header-name-0"]', 'X-API-Version');
    await page.fill('[data-testid="header-value-0"]', '2.1');

    await page.click('[data-testid="add-header-btn"]');
    await page.fill('[data-testid="header-name-1"]', 'X-Client-ID');
    await page.fill('[data-testid="header-value-1"]', 'isp-portal-client');

    await page.click('[data-testid="save-integration"]');
    await expect(page.locator('[data-testid="integration-saved"]')).toBeVisible();

    // Test webhook delivery
    const webhookRow = page.locator('[data-testid="integration-row"]', {
      hasText: 'Customer Portal Webhook',
    });
    await webhookRow.locator('[data-testid="test-integration"]').click();

    // Mock webhook endpoint
    await page.route('/webhooks/customer-events', async (route) => {
      const request = route.request();
      const headers = request.headers();

      // Verify required headers are present
      expect(headers['x-api-version']).toBe('2.1');
      expect(headers['x-client-id']).toBe('isp-portal-client');
      expect(headers['content-type']).toBe('application/json');

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          received: true,
          processed_at: new Date().toISOString(),
        }),
      });
    });

    // Verify webhook test succeeds
    await expect(page.locator('[data-testid="test-status"]')).toContainText('Success');
    await expect(page.locator('[data-testid="webhook-delivered"]')).toContainText('true');

    await page.click('[data-testid="close-test-results"]');

    // Test webhook event simulation
    await page.click('[data-testid="simulate-webhook-event"]');
    await page.selectOption('[data-testid="event-type"]', 'customer_signup');
    await page.fill(
      '[data-testid="event-payload"]',
      JSON.stringify({
        customer_id: 'CUST-TEST-001',
        email: 'test@customer.com',
        plan: 'Premium 500Mbps',
        signup_date: new Date().toISOString(),
      })
    );

    await page.click('[data-testid="send-webhook-event"]');

    // Verify event was processed
    await expect(page.locator('[data-testid="webhook-event-sent"]')).toContainText(
      'Event sent successfully'
    );

    // Check webhook delivery log
    await page.click('[data-testid="view-webhook-log"]');
    await expect(page.locator('[data-testid="webhook-log-dialog"]')).toBeVisible();

    const logEntries = page.locator('[data-testid="webhook-log-entry"]');
    const logCount = await logEntries.count();
    expect(logCount).toBeGreaterThan(0);

    if (logCount > 0) {
      const latestEntry = logEntries.first();
      await expect(latestEntry.locator('[data-testid="event-type"]')).toContainText(
        'customer_signup'
      );
      await expect(latestEntry.locator('[data-testid="delivery-status"]')).toContainText(
        'delivered'
      );
      await expect(latestEntry.locator('[data-testid="response-code"]')).toContainText('200');
    }

    await page.click('[data-testid="close-webhook-log"]');
  });
});
