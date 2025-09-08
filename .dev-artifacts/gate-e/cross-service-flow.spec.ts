/**
 * Gate E: Cross-Service Flow E2E Tests
 * 
 * Tests complete user journeys across service boundaries:
 * Login → CRUD operations → Background jobs → Notifications → Metrics emission
 * 
 * This validates the end-to-end functionality and observability of the DotMac framework.
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import { performance } from 'perf_hooks';

// Test configuration
const API_ONLY = process.env.GATE_E_API_ONLY === 'true';
// Separate UI and API base URLs to avoid coupling on a single origin
const SERVICES = {
  managementApi: { url: process.env.MANAGEMENT_API_URL || 'http://localhost:8000', name: 'management-api' },
  managementUi: { url: process.env.MANAGEMENT_UI_URL || process.env.MANAGEMENT_API_URL || 'http://localhost:8000', name: 'management-ui' },
  isp_admin: { url: process.env.ISP_ADMIN_URL || 'http://localhost:3000', name: 'isp-admin' },
  customer: { url: process.env.CUSTOMER_URL || 'http://localhost:3001', name: 'customer-portal' },
  reseller: { url: process.env.RESELLER_URL || 'http://localhost:3003', name: 'reseller-portal' },
};

const TEST_TIMEOUT = 120000; // 2 minutes for complex flows
const API_TIMEOUT = 30000;   // 30 seconds for API calls

interface TestContext {
  tenantId: string;
  userId: string;
  sessionData: Record<string, any>;
  traceIds: string[];
  metricValues: Record<string, number>;
}

class CrossServiceTestHelper {
  constructor(private page: Page) {}

  /**
   * Setup test tenant with proper licensing
   */
  async setupTestTenant(): Promise<TestContext> {
    const context: TestContext = {
      tenantId: `test-tenant-${Date.now()}`,
      userId: `test-user-${Date.now()}`,
      sessionData: {},
      traceIds: [],
      metricValues: {}
    };

    // Create tenant via management API
    const response = await this.page.request.post(`${SERVICES.managementApi.url}/api/v1/tenants`, {
      data: {
        name: `Test Tenant ${context.tenantId}`,
        plan: 'premium',
        admin_email: `admin+${context.tenantId}@test.com`,
        admin_password: 'TestPassword123!',
        features: ['billing', 'analytics', 'notifications', 'api_access']
      }
    });

    expect(response.ok()).toBeTruthy();
    const tenantData = await response.json();
    context.tenantId = tenantData.tenant_id;
    context.userId = tenantData.admin_user_id;

    return context;
  }

  /**
   * Login to management platform and establish session
   */
  async loginToManagementPlatform(context: TestContext): Promise<void> {
    if (API_ONLY) {
      // In API-only mode, skip UI login. Assume API token/session is not required for subsequent API calls in tests.
      return;
    }
    await this.page.goto(`${SERVICES.managementUi.url}/auth/login`);
    
    // Fill login form
    await this.page.fill('[data-testid="email-input"]', `admin+${context.tenantId}@test.com`);
    await this.page.fill('[data-testid="password-input"]', 'TestPassword123!');
    
    // Capture network activity for tracing
    const tracePromise = this.page.waitForResponse(response => 
      response.url().includes('/auth/login') && response.status() === 200
    );
    
    await this.page.click('[data-testid="login-button"]');
    
    const loginResponse = await tracePromise;
    const traceId = loginResponse.headers()['x-trace-id'];
    if (traceId) {
      context.traceIds.push(traceId);
    }

    // Verify successful login
    await expect(this.page.locator('[data-testid="user-menu"]')).toBeVisible({ timeout: 10000 });
    
    // Store session data
    const sessionToken = await this.page.evaluate(() => localStorage.getItem('auth_token'));
    context.sessionData.authToken = sessionToken;
  }

  /**
   * Perform CRUD operations on customer data
   */
  async performCrudOperations(context: TestContext): Promise<void> {
    if (API_ONLY) {
      return; // Skip UI-driven CRUD in API-only mode
    }
    // Navigate to customers section
    await this.page.click('[data-testid="customers-nav"]');
    await expect(this.page.locator('[data-testid="customers-list"]')).toBeVisible();

    // CREATE: Add new customer
    await test.step('Create Customer', async () => {
      await this.page.click('[data-testid="add-customer-button"]');
      
      const customerData = {
        name: `Test Customer ${Date.now()}`,
        email: `customer+${Date.now()}@test.com`,
        phone: '+1-555-0123',
        address: '123 Test Street, Test City, TC 12345',
        service_plan: 'residential_premium'
      };

      await this.page.fill('[data-testid="customer-name"]', customerData.name);
      await this.page.fill('[data-testid="customer-email"]', customerData.email);
      await this.page.fill('[data-testid="customer-phone"]', customerData.phone);
      await this.page.fill('[data-testid="customer-address"]', customerData.address);
      await this.page.selectOption('[data-testid="service-plan"]', customerData.service_plan);

      // Submit and capture trace
      const createPromise = this.page.waitForResponse(response => 
        response.url().includes('/customers') && response.status() === 201
      );
      
      await this.page.click('[data-testid="save-customer"]');
      
      const createResponse = await createPromise;
      const traceId = createResponse.headers()['x-trace-id'];
      if (traceId) {
        context.traceIds.push(traceId);
      }

      // Verify customer created
      await expect(this.page.locator(`text=${customerData.name}`)).toBeVisible();
      
      const responseData = await createResponse.json();
      context.sessionData.customerId = responseData.customer_id;
    });

    // READ: View customer details
    await test.step('Read Customer Details', async () => {
      await this.page.click(`[data-testid="customer-${context.sessionData.customerId}"]`);
      
      // Verify customer details load
      await expect(this.page.locator('[data-testid="customer-details"]')).toBeVisible();
      await expect(this.page.locator('[data-testid="customer-billing"]')).toBeVisible();
      await expect(this.page.locator('[data-testid="customer-services"]')).toBeVisible();
    });

    // UPDATE: Modify customer information
    await test.step('Update Customer', async () => {
      await this.page.click('[data-testid="edit-customer"]');
      
      const updatedPhone = '+1-555-9999';
      await this.page.fill('[data-testid="customer-phone"]', updatedPhone);
      
      const updatePromise = this.page.waitForResponse(response => 
        response.url().includes(`/customers/${context.sessionData.customerId}`) && 
        response.status() === 200
      );
      
      await this.page.click('[data-testid="save-customer"]');
      
      const updateResponse = await updatePromise;
      const traceId = updateResponse.headers()['x-trace-id'];
      if (traceId) {
        context.traceIds.push(traceId);
      }

      // Verify update
      await expect(this.page.locator(`text=${updatedPhone}`)).toBeVisible();
    });
  }

  /**
   * Trigger background jobs (billing, notifications, analytics)
   */
  async triggerBackgroundJobs(context: TestContext): Promise<void> {
    if (API_ONLY) {
      return; // Skip UI-driven background job steps in API-only mode
    }
    await test.step('Trigger Billing Job', async () => {
      // Navigate to billing section
      await this.page.click('[data-testid="billing-nav"]');
      await expect(this.page.locator('[data-testid="billing-dashboard"]')).toBeVisible();

      // Trigger manual billing run for the customer
      await this.page.click('[data-testid="run-billing"]');
      await this.page.click(`[data-testid="customer-${context.sessionData.customerId}"]`);
      
      const billingPromise = this.page.waitForResponse(response => 
        response.url().includes('/billing/run') && response.status() === 202
      );
      
      await this.page.click('[data-testid="confirm-billing-run"]');
      
      const billingResponse = await billingPromise;
      const traceId = billingResponse.headers()['x-trace-id'];
      if (traceId) {
        context.traceIds.push(traceId);
      }

      // Verify job was queued
      await expect(this.page.locator('[data-testid="billing-job-queued"]')).toBeVisible({ timeout: 10000 });
    });

    await test.step('Trigger Analytics Processing', async () => {
      // Navigate to analytics
      await this.page.click('[data-testid="analytics-nav"]');
      await expect(this.page.locator('[data-testid="analytics-dashboard"]')).toBeVisible();

      // Trigger analytics recalculation
      await this.page.click('[data-testid="refresh-analytics"]');
      
      const analyticsPromise = this.page.waitForResponse(response => 
        response.url().includes('/analytics/refresh') && response.status() === 202
      );
      
      const analyticsResponse = await analyticsPromise;
      const traceId = analyticsResponse.headers()['x-trace-id'];
      if (traceId) {
        context.traceIds.push(traceId);
      }

      // Verify analytics job started
      await expect(this.page.locator('[data-testid="analytics-processing"]')).toBeVisible({ timeout: 5000 });
    });

    // Wait for jobs to complete (simulate processing time)
    await this.page.waitForTimeout(10000);
  }

  /**
   * Verify notification delivery across channels
   */
  async verifyNotifications(context: TestContext): Promise<void> {
    if (!API_ONLY) {
      // Check notification center via UI
      await this.page.click('[data-testid="notifications-button"]');
      await expect(this.page.locator('[data-testid\\="notifications-panel\\"]')).toBeVisible();

      // Verify billing notification
      await expect(
        this.page.locator('[data-testid="notification"][data-type="billing_complete"]')
      ).toBeVisible({ timeout: 15000 });

      // Verify customer notification
      await expect(
        this.page.locator('[data-testid="notification"][data-type="customer_updated"]')
      ).toBeVisible({ timeout: 10000 });
    }

    // Check notification API for delivery confirmation
    const notificationsResponse = await this.page.request.get(
      `${SERVICES.managementApi.url}/api/v1/notifications?tenant_id=${context.tenantId}&limit=10`
    );
    
    expect(notificationsResponse.ok()).toBeTruthy();
    const notifications = await notificationsResponse.json();
    
    // Verify notification delivery
    expect(notifications.items.length).toBeGreaterThan(0);
    expect(notifications.items.some((n: any) => n.type === 'billing_complete')).toBeTruthy();
    expect(notifications.items.some((n: any) => n.type === 'customer_updated')).toBeTruthy();

    // Store notification metrics
    context.metricValues.notificationsSent = notifications.items.length;
  }

  /**
   * Verify metrics emission and collection
   */
  async verifyMetricsEmission(context: TestContext): Promise<void> {
    // Wait for metrics to be collected
    await this.page.waitForTimeout(5000);

    // Check metrics endpoint
    const metricsResponse = await this.page.request.get(
      `${SERVICES.managementApi.url}/metrics?format=json`
    );
    
    expect(metricsResponse.ok()).toBeTruthy();
    const metricsText = await metricsResponse.text();
    
    // Verify key business metrics are present
    expect(metricsText).toContain('dotmac_customers_total');
    expect(metricsText).toContain('dotmac_billing_runs_total');
    expect(metricsText).toContain('dotmac_api_requests_total');
    expect(metricsText).toContain('dotmac_notifications_sent_total');

    if (!API_ONLY) {
      // Check observability dashboard
      await this.page.goto(`${SERVICES.managementUi.url}/admin/observability`);
      await expect(this.page.locator('[data-testid\\="metrics-dashboard\\"]')).toBeVisible();
    }

    // Verify trace correlation via UI if enabled
    if (!API_ONLY) {
      for (const traceId of context.traceIds) {
        await this.page.fill('[data-testid="trace-search"]', traceId);
        await this.page.click('[data-testid="search-traces"]');
        await expect(this.page.locator(`[data-testid="trace-${traceId}"]`)).toBeVisible({ timeout: 10000 });
      }
    }

    // Store final metrics
    context.metricValues.tracesGenerated = context.traceIds.length;
    context.metricValues.metricsCollected = (metricsText.match(/dotmac_/g) || []).length;
  }

  /**
   * Verify cross-app consistency
   */
  async verifyCrossAppConsistency(context: TestContext): Promise<void> {
    if (API_ONLY) {
      return; // Skip UI checks in API-only mode
    }
    // Check customer portal for updated data
    const customerPortalPage = await this.page.context().newPage();
    await customerPortalPage.goto(`${SERVICES.customer.url}/login`);
    
    // Login as the customer we created
    await customerPortalPage.fill('[data-testid="email-input"]', 'customer@test.com');
    await customerPortalPage.fill('[data-testid="password-input"]', 'password123');
    await customerPortalPage.click('[data-testid="login-button"]');

    // Verify customer can see their updated information
    await expect(customerPortalPage.locator('[data-testid="account-info"]')).toBeVisible();
    await expect(customerPortalPage.locator('text=+1-555-9999')).toBeVisible({ timeout: 15000 });

    // Check reseller portal for commission updates
    const resellerPage = await this.page.context().newPage();
    await resellerPage.goto(`${SERVICES.reseller.url}/login`);
    
    // Login as reseller
    await resellerPage.fill('[data-testid="email-input"]', 'reseller@test.com');
    await resellerPage.fill('[data-testid="password-input"]', 'password123');
    await resellerPage.click('[data-testid="login-button"]');

    // Verify commission data is updated
    await resellerPage.click('[data-testid="commissions-nav"]');
    await expect(resellerPage.locator('[data-testid="commissions-table"]')).toBeVisible();

    // Cleanup
    await customerPortalPage.close();
    await resellerPage.close();
  }

  /**
   * Performance validation
   */
  async validatePerformance(context: TestContext): Promise<void> {
    if (API_ONLY) {
      return; // Skip UI performance checks in API-only mode
    }
    const performanceMetrics = await this.page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        totalLoadTime: navigation.loadEventEnd - navigation.fetchStart,
        apiCalls: performance.getEntriesByType('resource').filter(r => r.name.includes('/api/')).length
      };
    });

    // Performance thresholds
    expect(performanceMetrics.domContentLoaded).toBeLessThan(3000); // < 3s DOM ready
    expect(performanceMetrics.totalLoadTime).toBeLessThan(8000);    // < 8s total load
    expect(performanceMetrics.apiCalls).toBeGreaterThan(5);         // Multiple API calls made

    context.metricValues.performanceScore = Math.max(0, 100 - (performanceMetrics.totalLoadTime / 100));
  }

  /**
   * Cleanup test data
   */
  async cleanup(context: TestContext): Promise<void> {
    // Delete test customer
    if (context.sessionData.customerId) {
      await this.page.request.delete(
        `${SERVICES.management.url}/api/v1/customers/${context.sessionData.customerId}`
      );
    }

    // Delete test tenant
    await this.page.request.delete(
      `${SERVICES.management.url}/api/v1/tenants/${context.tenantId}`
    );
  }
}

test.describe('Gate E: Cross-Service Flow Tests', () => {
  let helper: CrossServiceTestHelper;
  let testContext: TestContext;

  test.beforeEach(async ({ page }) => {
    helper = new CrossServiceTestHelper(page);
    
    // Set longer timeout for complex operations
    test.setTimeout(TEST_TIMEOUT);
    
    // Setup test environment
    testContext = await helper.setupTestTenant();
  });

  test.afterEach(async () => {
    // Cleanup after each test
    if (testContext) {
      await helper.cleanup(testContext);
    }
  });

  test('Complete User Journey: Login → CRUD → Jobs → Notifications → Metrics', async ({ page }) => {
    await test.step('1. User Authentication', async () => {
      await helper.loginToManagementPlatform(testContext);
      expect(testContext.sessionData.authToken).toBeTruthy();
    });

    await test.step('2. CRUD Operations', async () => {
      await helper.performCrudOperations(testContext);
      expect(testContext.sessionData.customerId).toBeTruthy();
    });

    await test.step('3. Background Job Execution', async () => {
      await helper.triggerBackgroundJobs(testContext);
      expect(testContext.traceIds.length).toBeGreaterThan(3);
    });

    await test.step('4. Notification Delivery', async () => {
      await helper.verifyNotifications(testContext);
      expect(testContext.metricValues.notificationsSent).toBeGreaterThan(0);
    });

    await test.step('5. Metrics Collection', async () => {
      await helper.verifyMetricsEmission(testContext);
      expect(testContext.metricValues.tracesGenerated).toBeGreaterThan(0);
      expect(testContext.metricValues.metricsCollected).toBeGreaterThan(10);
    });

    await test.step('6. Cross-App Consistency', async () => {
      await helper.verifyCrossAppConsistency(testContext);
    });

    await test.step('7. Performance Validation', async () => {
      await helper.validatePerformance(testContext);
      if (!API_ONLY) {
        expect(testContext.metricValues.performanceScore).toBeGreaterThan(70);
      }
    });

    // Final assertions
    if (!API_ONLY) {
      expect(testContext.traceIds.length).toBeGreaterThanOrEqual(4);
      expect(testContext.metricValues.notificationsSent).toBeGreaterThanOrEqual(2);
      expect(testContext.metricValues.tracesGenerated).toBeGreaterThanOrEqual(4);
    }
  });

  test('Multi-Tenant Isolation Verification', async ({ page }) => {
    // Create second tenant
    const secondTenant = await helper.setupTestTenant();
    
    await test.step('Login to first tenant', async () => {
      await helper.loginToManagementPlatform(testContext);
    });

    await test.step('Create customer in first tenant', async () => {
      await helper.performCrudOperations(testContext);
    });

    await test.step('Login to second tenant', async () => {
      // Logout from first tenant
      await page.click('[data-testid="user-menu"]');
      await page.click('[data-testid="logout"]');
      
      // Login to second tenant
      await helper.loginToManagementPlatform(secondTenant);
    });

    await test.step('Verify tenant isolation', async () => {
      // Navigate to customers - should be empty
      await page.click('[data-testid="customers-nav"]');
      await expect(page.locator('[data-testid="empty-customers"]')).toBeVisible();
      
      // Should not see customers from first tenant
      await expect(
        page.locator(`[data-testid="customer-${testContext.sessionData.customerId}"]`)
      ).not.toBeVisible();
    });

    // Cleanup second tenant
    await helper.cleanup(secondTenant);
  });

  test('Error Handling and Recovery', async ({ page }) => {
    if (API_ONLY) test.skip();
    await helper.loginToManagementPlatform(testContext);

    await test.step('Handle API errors gracefully', async () => {
      // Navigate to customers
      await page.click('[data-testid="customers-nav"]');
      
      // Try to create customer with invalid data
      await page.click('[data-testid="add-customer-button"]');
      await page.fill('[data-testid="customer-name"]', '');
      await page.fill('[data-testid="customer-email"]', 'invalid-email');
      
      await page.click('[data-testid="save-customer"]');
      
      // Should show validation errors
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('text=Invalid email')).toBeVisible();
    });

    await test.step('Verify error tracking in observability', async () => {
      // Check that errors are logged in metrics
      const metricsResponse = await page.request.get(`${SERVICES.managementApi.url}/metrics`);
      const metricsText = await metricsResponse.text();
      
      expect(metricsText).toContain('dotmac_api_errors_total');
    });
  });

  test('Real-time Features and WebSocket Communication', async ({ page }) => {
    if (API_ONLY) test.skip();
    await helper.loginToManagementPlatform(testContext);

    await test.step('Verify real-time notifications', async () => {
      // Open notifications panel
      await page.click('[data-testid="notifications-button"]');
      
      // Create customer to trigger notification
      await helper.performCrudOperations(testContext);
      
      // Should see real-time notification appear
      await expect(
        page.locator('[data-testid="realtime-notification"]')
      ).toBeVisible({ timeout: 10000 });
    });

    await test.step('Verify WebSocket health', async () => {
      // Check WebSocket connection status
      const wsStatus = await page.evaluate(() => {
        return (window as any).wsConnection?.readyState === 1; // WebSocket.OPEN
      });
      
      expect(wsStatus).toBeTruthy();
    });
  });
});

/**
 * Specialized tests for observability validation
 */
test.describe('Gate E: Observability Integration', () => {
  test('Distributed Tracing Across Services', async ({ page }) => {
    const helper = new CrossServiceTestHelper(page);
    const context = await helper.setupTestTenant();
    
    await helper.loginToManagementPlatform(context);
    
    // Perform operation that spans multiple services
    await helper.performCrudOperations(context);
    await helper.triggerBackgroundJobs(context);
    
    // Verify trace correlation
    await page.goto(`${SERVICES.management.url}/admin/observability/traces`);
    
    for (const traceId of context.traceIds) {
      await page.fill('[data-testid="trace-search"]', traceId);
      await page.click('[data-testid="search-button"]');
      
      // Should see trace with multiple spans
      await expect(page.locator(`[data-testid="trace-${traceId}"]`)).toBeVisible();
      
      // Click to view details
      await page.click(`[data-testid="trace-${traceId}"]`);
      
      // Should see multiple service spans
      await expect(page.locator('[data-testid="span"][data-service="api"]')).toBeVisible();
      await expect(page.locator('[data-testid="span"][data-service="database"]')).toBeVisible();
      await expect(page.locator('[data-testid="span"][data-service="queue"]')).toBeVisible();
    }
    
    await helper.cleanup(context);
  });

  test('Metrics Dashboard and Alerting', async ({ page }) => {
    const helper = new CrossServiceTestHelper(page);
    const context = await helper.setupTestTenant();
    
    await helper.loginToManagementPlatform(context);
    
    // Generate some activity
    await helper.performCrudOperations(context);
    
    // Check metrics dashboard
    await page.goto(`${SERVICES.management.url}/admin/observability/metrics`);
    
    // Verify key metrics are displayed
    await expect(page.locator('[data-testid="metric-customers-total"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-api-requests"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-response-time"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-error-rate"]')).toBeVisible();
    
    // Verify metric values are reasonable
    const customerCount = await page.locator('[data-testid="metric-customers-total"] .value').textContent();
    expect(parseInt(customerCount || '0')).toBeGreaterThan(0);
    
    await helper.cleanup(context);
  });
});
