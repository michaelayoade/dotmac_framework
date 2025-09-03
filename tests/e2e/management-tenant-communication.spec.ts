/**
 * Management-to-Tenant Communication E2E Tests
 * 
 * Tests the communication flow from Management Platform to Tenant Containers
 * ensuring that changes made in the management portal properly propagate
 * to isolated tenant environments.
 */

import { test, expect } from '@playwright/test';
import { createTestTenant, cleanupTestTenant } from '../utils/tenant-factory';
import { authenticateAsManagementAdmin, authenticateAsTenant } from '../utils/auth-helpers';
import { waitForEventPropagation, mockWebSocketConnection } from '../utils/communication-helpers';

test.describe('Management-to-Tenant Communication', () => {
  let testTenantId: string;
  let tenantDomain: string;

  test.beforeAll(async () => {
    // Create a test tenant for communication testing
    const tenant = await createTestTenant({
      name: 'Communication Test Corp',
      plan: 'professional',
      apps: ['isp_framework', 'crm']
    });
    testTenantId = tenant.id;
    tenantDomain = tenant.domain;
  });

  test.afterAll(async () => {
    await cleanupTestTenant(testTenantId);
  });

  test('Management admin setting changes propagate to tenant container', async ({ page, context }) => {
    // Step 1: Login to Management Admin Portal
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    // Navigate to tenant management
    await page.goto('/tenants');
    await page.click(`[data-testid="tenant-row-${testTenantId}"]`);
    await page.click('[data-testid="edit-tenant-settings"]');

    // Step 2: Update tenant settings
    const newCompanyName = 'Communication Test Corp Updated';
    const newTimeZone = 'America/Los_Angeles';
    
    await page.fill('[data-testid="company-name-input"]', newCompanyName);
    await page.selectOption('[data-testid="timezone-select"]', newTimeZone);
    await page.click('[data-testid="save-settings-button"]');

    // Verify success message in management portal
    await expect(page.locator('.success-message')).toContainText('Settings updated successfully');

    // Step 3: Wait for propagation
    await waitForEventPropagation(5000); // 5 second propagation delay

    // Step 4: Verify changes in tenant container
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@communicationtestcorp.com',
      password: 'tenant123'
    });

    await tenantPage.goto('/settings/organization');

    // Verify the changes propagated
    await expect(tenantPage.locator('[data-testid="company-name-display"]')).toContainText(newCompanyName);
    await expect(tenantPage.locator('[data-testid="timezone-display"]')).toContainText('Pacific Time');
  });

  test('License changes propagate to tenant containers', async ({ page, context }) => {
    // Login to Management Admin
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    // Navigate to tenant licenses
    await page.goto(`/tenants/${testTenantId}/licenses`);

    // Step 1: Add E-commerce app license
    await page.click('[data-testid="add-app-license"]');
    await page.selectOption('[data-testid="app-select"]', 'e_commerce');
    await page.selectOption('[data-testid="plan-select"]', 'standard');
    await page.click('[data-testid="confirm-license-add"]');

    await expect(page.locator('.success-message')).toContainText('License added successfully');

    // Wait for license propagation
    await waitForEventPropagation(3000);

    // Step 2: Verify in tenant container
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@communicationtestcorp.com',
      password: 'tenant123'
    });

    // Check that E-commerce app is now available
    await expect(tenantPage.locator('[data-testid="app-menu-ecommerce"]')).toBeVisible();
    await tenantPage.click('[data-testid="app-menu-ecommerce"]');
    await expect(tenantPage).toHaveURL(/.*\/ecommerce/);

    // Verify app functionality is available
    await expect(tenantPage.locator('h1')).toContainText('E-commerce Dashboard');
    await expect(tenantPage.locator('[data-testid="create-product-button"]')).toBeVisible();

    // Step 3: Remove license and verify removal
    await page.bringToFront();
    await page.click(`[data-testid="remove-license-e_commerce"]`);
    await page.click('[data-testid="confirm-license-removal"]');

    await waitForEventPropagation(3000);

    // Verify app is no longer accessible in tenant
    await tenantPage.bringToFront();
    await tenantPage.reload();
    await expect(tenantPage.locator('[data-testid="app-menu-ecommerce"]')).not.toBeVisible();
  });

  test('System notifications delivery to tenants', async ({ page, context }) => {
    // Setup WebSocket connection monitoring
    const wsMessages: any[] = [];
    await mockWebSocketConnection(context, (message) => {
      wsMessages.push(message);
    });

    // Step 1: Management admin sends system notification
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/system/notifications');
    await page.click('[data-testid="create-notification-button"]');

    const notificationTitle = 'Scheduled Maintenance Notice';
    const notificationMessage = 'System maintenance scheduled for tomorrow 2 AM EST';

    await page.fill('[data-testid="notification-title"]', notificationTitle);
    await page.fill('[data-testid="notification-message"]', notificationMessage);
    await page.selectOption('[data-testid="notification-type"]', 'maintenance');
    await page.selectOption('[data-testid="notification-priority"]', 'high');
    
    // Select specific tenant
    await page.click('[data-testid="target-specific-tenants"]');
    await page.check(`[data-testid="tenant-checkbox-${testTenantId}"]`);
    
    await page.click('[data-testid="send-notification-button"]');

    await expect(page.locator('.success-message')).toContainText('Notification sent successfully');

    // Step 2: Verify notification received in tenant
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@communicationtestcorp.com',
      password: 'tenant123'
    });

    // Check for notification in tenant dashboard
    await expect(tenantPage.locator('[data-testid="notification-bell"]')).toHaveAttribute('data-has-notifications', 'true');
    
    await tenantPage.click('[data-testid="notification-bell"]');
    await expect(tenantPage.locator('[data-testid="notification-dropdown"]')).toBeVisible();
    
    await expect(tenantPage.locator('[data-testid="notification-item"]').first()).toContainText(notificationTitle);
    await expect(tenantPage.locator('[data-testid="notification-item"]').first()).toContainText(notificationMessage);

    // Verify WebSocket message was received
    await page.waitForTimeout(2000);
    const wsNotification = wsMessages.find(msg => msg.type === 'notification' && msg.title === notificationTitle);
    expect(wsNotification).toBeTruthy();
  });

  test('Billing updates and payment processing communication', async ({ page, context }) => {
    // Step 1: Management admin updates billing information
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/billing`);

    // Generate a test invoice
    await page.click('[data-testid="generate-invoice-button"]');
    await page.selectOption('[data-testid="billing-period"]', 'current_month');
    await page.click('[data-testid="confirm-generate-invoice"]');

    const invoiceNumber = await page.locator('[data-testid="generated-invoice-number"]').textContent();
    await expect(page.locator('.success-message')).toContainText('Invoice generated successfully');

    // Step 2: Verify invoice appears in tenant billing
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@communicationtestcorp.com',
      password: 'tenant123'
    });

    await tenantPage.goto('/billing/invoices');

    // Wait for billing sync
    await waitForEventPropagation(5000);

    await expect(tenantPage.locator(`[data-testid="invoice-${invoiceNumber}"]`)).toBeVisible();
    await expect(tenantPage.locator(`[data-testid="invoice-${invoiceNumber}"] .status`)).toContainText('Pending');

    // Step 3: Process payment in tenant
    await tenantPage.click(`[data-testid="pay-invoice-${invoiceNumber}"]`);
    await tenantPage.click('[data-testid="payment-method-card"]');
    await tenantPage.fill('[data-testid="card-number"]', '4242424242424242');
    await tenantPage.fill('[data-testid="card-expiry"]', '12/25');
    await tenantPage.fill('[data-testid="card-cvc"]', '123');
    await tenantPage.click('[data-testid="process-payment-button"]');

    await expect(tenantPage.locator('.success-message')).toContainText('Payment processed successfully');

    // Step 4: Verify payment status updates in management
    await page.bringToFront();
    await page.reload();
    await waitForEventPropagation(3000);

    await expect(page.locator(`[data-testid="invoice-${invoiceNumber}"] .status`)).toContainText('Paid');
    await expect(page.locator(`[data-testid="invoice-${invoiceNumber}"] .payment-date`)).not.toBeEmpty();
  });

  test('Emergency maintenance notifications', async ({ page, context }) => {
    // Setup real-time notification monitoring
    const notifications: any[] = [];
    
    await context.route('**/api/v1/notifications/stream', async route => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"type": "connection_established"}\n\n'
      });
    });

    // Step 1: Send emergency notification
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/system/emergency');
    await page.click('[data-testid="emergency-notification-button"]');

    await page.fill('[data-testid="emergency-title"]', 'URGENT: Security Patch Required');
    await page.fill('[data-testid="emergency-message"]', 'Critical security patch will be applied in 15 minutes. Save your work.');
    await page.selectOption('[data-testid="emergency-severity"]', 'critical');
    
    await page.click('[data-testid="send-emergency-notification"]');
    await page.click('[data-testid="confirm-emergency"]');

    // Step 2: Verify immediate notification in tenant
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@communicationtestcorp.com',
      password: 'tenant123'
    });

    // Emergency notifications should appear immediately
    await expect(tenantPage.locator('[data-testid="emergency-banner"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="emergency-banner"]')).toContainText('URGENT: Security Patch Required');
    await expect(tenantPage.locator('[data-testid="emergency-banner"]')).toHaveClass(/.*critical.*/);

    // Verify modal popup for critical notifications
    await expect(tenantPage.locator('[data-testid="emergency-modal"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="emergency-modal-title"]')).toContainText('URGENT');
    
    // User must acknowledge emergency notification
    await tenantPage.click('[data-testid="acknowledge-emergency"]');
    await expect(tenantPage.locator('[data-testid="emergency-modal"]')).not.toBeVisible();
    
    // Banner should remain visible
    await expect(tenantPage.locator('[data-testid="emergency-banner"]')).toBeVisible();
  });
});

test.describe('Configuration Propagation', () => {
  let testTenantId: string;

  test.beforeEach(async () => {
    const tenant = await createTestTenant({
      name: 'Config Test Tenant',
      plan: 'enterprise'
    });
    testTenantId = tenant.id;
  });

  test.afterEach(async () => {
    await cleanupTestTenant(testTenantId);
  });

  test('Feature flag configuration propagates correctly', async ({ page, context }) => {
    // Step 1: Management admin enables beta features
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/features`);
    
    // Enable beta feature
    await page.check('[data-testid="feature-advanced-analytics"]');
    await page.check('[data-testid="feature-ai-insights"]');
    await page.click('[data-testid="save-features"]');

    await waitForEventPropagation(2000);

    // Step 2: Verify features are available in tenant
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/login`);

    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain}`,
      password: 'tenant123'
    });

    // Check that beta features are visible
    await expect(tenantPage.locator('[data-testid="menu-advanced-analytics"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="menu-ai-insights"]')).toBeVisible();

    // Test feature functionality
    await tenantPage.click('[data-testid="menu-advanced-analytics"]');
    await expect(tenantPage).toHaveURL(/.*\/analytics\/advanced/);
    await expect(tenantPage.locator('[data-testid="advanced-charts"]')).toBeVisible();
  });

  test('Security policy updates propagate', async ({ page, context }) => {
    // Step 1: Update security policies in management
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/security`);
    
    // Enable stricter password policy
    await page.check('[data-testid="require-mfa"]');
    await page.selectOption('[data-testid="password-complexity"]', 'high');
    await page.fill('[data-testid="session-timeout"]', '30'); // 30 minutes
    await page.click('[data-testid="save-security-policy"]');

    await waitForEventPropagation(3000);

    // Step 2: Verify policy enforcement in tenant
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/login`);

    // Try to create a user with weak password
    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain}`,
      password: 'tenant123'
    });

    await tenantPage.goto('/users/new');
    await tenantPage.fill('[data-testid="user-email"]', 'newuser@test.com');
    await tenantPage.fill('[data-testid="user-password"]', 'weak123'); // Should fail
    await tenantPage.click('[data-testid="create-user"]');

    // Should show password complexity error
    await expect(tenantPage.locator('.error-message')).toContainText('Password does not meet complexity requirements');

    // Try with strong password
    await tenantPage.fill('[data-testid="user-password"]', 'StrongP@ssw0rd123!');
    await tenantPage.click('[data-testid="create-user"]');

    // Should prompt for MFA setup
    await expect(tenantPage.locator('[data-testid="mfa-setup-required"]')).toBeVisible();
  });
});

// Helper function to get tenant details
async function getTenantDetails(tenantId: string) {
  // This would typically make an API call to get tenant details
  return {
    id: tenantId,
    domain: `tenant-${tenantId}.dotmac.app`,
    name: 'Config Test Tenant'
  };
}