/**
 * Plugin-Based External Integration E2E Tests
 * 
 * Tests the DotMac plugin architecture for external service integrations.
 * Validates plugin installation, configuration, activation, and usage across
 * payment processors, communication services, and infrastructure orchestration.
 */

import { test, expect } from '@playwright/test';
import { createTestTenant, cleanupTestTenant } from '../utils/tenant-factory';
import { authenticateAsManagementAdmin, authenticateAsTenant } from '../utils/auth-helpers';
import { waitForEventPropagation } from '../utils/communication-helpers';

test.describe('Plugin System External Integrations', () => {
  let testTenantId: string;
  let tenantDomain: string;

  test.beforeAll(async () => {
    // Create tenant with plugin management capabilities
    const tenant = await createTestTenant({
      name: 'Plugin Integration Test Corp',
      plan: 'enterprise',
      apps: ['isp_framework', 'plugin_manager'],
      billingEnabled: true,
      notificationsEnabled: true
    });
    testTenantId = tenant.id;
    tenantDomain = tenant.domain;
  });

  test.afterAll(async () => {
    await cleanupTestTenant(testTenantId);
  });

  test('Plugin marketplace and installation workflow', async ({ page, context }) => {
    // Step 1: Management admin accesses plugin marketplace
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/plugins/marketplace');
    
    // Verify plugin marketplace loads
    await expect(page.locator('[data-testid="plugin-marketplace"]')).toBeVisible();
    await expect(page.locator('[data-testid="plugin-categories"]')).toBeVisible();

    // Step 2: Browse payment processor plugins
    await page.click('[data-testid="category-payments"]');
    await expect(page.locator('[data-testid="plugin-list"]')).toBeVisible();

    // Check available payment plugins (Stripe, PayPal, Square, etc.)
    await expect(page.locator('[data-testid="plugin-stripe"]')).toBeVisible();
    await expect(page.locator('[data-testid="plugin-paypal"]')).toBeVisible();
    await expect(page.locator('[data-testid="plugin-square"]')).toBeVisible();

    // Step 3: Install Stripe payment plugin
    await page.click('[data-testid="plugin-stripe"] [data-testid="install-plugin"]');
    
    // Configure plugin settings
    await page.fill('[data-testid="stripe-publishable-key"]', 'pk_test_mock_key_123');
    await page.fill('[data-testid="stripe-secret-key"]', 'sk_test_mock_key_456');
    await page.selectOption('[data-testid="stripe-webhook-endpoint"]', 'auto-generate');
    await page.check('[data-testid="enable-test-mode"]');
    
    await page.click('[data-testid="save-plugin-config"]');
    await expect(page.locator('.success-message')).toContainText('Stripe plugin installed successfully');

    // Step 4: Assign plugin to tenant
    await page.goto(`/tenants/${testTenantId}/plugins`);
    await page.click('[data-testid="assign-plugin-button"]');
    await page.selectOption('[data-testid="plugin-select"]', 'stripe-payments');
    await page.selectOption('[data-testid="license-tier"]', 'professional');
    await page.click('[data-testid="confirm-plugin-assignment"]');

    await expect(page.locator('.success-message')).toContainText('Plugin assigned to tenant');

    // Wait for plugin propagation
    await waitForEventPropagation(5000);

    // Step 5: Verify plugin is available in tenant container
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@pluginintegrationtestcorp.com',
      password: 'tenant123'
    });

    // Check plugin is available in tenant
    await tenantPage.goto('/plugins/installed');
    await expect(tenantPage.locator('[data-testid="installed-plugin-stripe"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="plugin-status-stripe"]')).toContainText('Active');

    // Test plugin functionality
    await tenantPage.goto('/billing/payment-methods');
    await expect(tenantPage.locator('[data-testid="add-card-stripe"]')).toBeVisible();
  });

  test('Communication plugins installation and usage', async ({ page, context }) => {
    // Step 1: Install SMS plugin (generic SMS provider plugin)
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="category-communication"]');
    
    // Install configurable SMS plugin
    await page.click('[data-testid="plugin-sms-provider"] [data-testid="install-plugin"]');
    
    // Configure for multiple providers (Twilio, AWS SNS, etc.)
    await page.selectOption('[data-testid="sms-provider-type"]', 'twilio');
    await page.fill('[data-testid="twilio-account-sid"]', 'AC_test_account_sid');
    await page.fill('[data-testid="twilio-auth-token"]', 'test_auth_token');
    await page.fill('[data-testid="sender-phone"]', '+1234567890');
    await page.check('[data-testid="enable-fallback-provider"]');
    await page.selectOption('[data-testid="fallback-provider"]', 'aws-sns');
    
    await page.click('[data-testid="test-sms-config"]');
    await expect(page.locator('.config-test-success')).toContainText('SMS configuration valid');
    
    await page.click('[data-testid="save-plugin-config"]');
    
    // Step 2: Install Email plugin
    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="plugin-email-provider"] [data-testid="install-plugin"]');
    
    await page.selectOption('[data-testid="email-provider-type"]', 'sendgrid');
    await page.fill('[data-testid="sendgrid-api-key"]', 'SG.test_api_key');
    await page.fill('[data-testid="sender-email"]', 'noreply@dotmac.com');
    await page.fill('[data-testid="sender-name"]', 'DotMac Platform');
    
    await page.click('[data-testid="test-email-config"]');
    await expect(page.locator('.config-test-success')).toContainText('Email configuration valid');
    
    await page.click('[data-testid="save-plugin-config"]');

    // Step 3: Assign communication plugins to tenant
    await page.goto(`/tenants/${testTenantId}/plugins`);
    
    // Assign SMS plugin
    await page.click('[data-testid="assign-plugin-button"]');
    await page.selectOption('[data-testid="plugin-select"]', 'sms-provider');
    await page.selectOption('[data-testid="license-tier"]', 'basic');
    await page.click('[data-testid="confirm-plugin-assignment"]');
    
    // Assign Email plugin
    await page.click('[data-testid="assign-plugin-button"]');
    await page.selectOption('[data-testid="plugin-select"]', 'email-provider');
    await page.selectOption('[data-testid="license-tier"]', 'basic');
    await page.click('[data-testid="confirm-plugin-assignment"]');

    await waitForEventPropagation(3000);

    // Step 4: Test plugin usage in tenant
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@pluginintegrationtestcorp.com',
      password: 'tenant123'
    });

    // Test SMS plugin
    await tenantPage.goto('/notifications/send-sms');
    await tenantPage.fill('[data-testid="recipient-phone"]', '+1987654321');
    await tenantPage.fill('[data-testid="sms-message"]', 'Test SMS via plugin system');
    await tenantPage.click('[data-testid="send-sms"]');
    
    await expect(tenantPage.locator('.success-message')).toContainText('SMS sent successfully');

    // Test Email plugin
    await tenantPage.goto('/notifications/send-email');
    await tenantPage.fill('[data-testid="recipient-email"]', 'test@example.com');
    await tenantPage.fill('[data-testid="email-subject"]', 'Test Email via Plugin');
    await tenantPage.fill('[data-testid="email-body"]', 'This email was sent via the plugin system');
    await tenantPage.click('[data-testid="send-email"]');
    
    await expect(tenantPage.locator('.success-message')).toContainText('Email sent successfully');
  });

  test('Infrastructure plugins for container orchestration', async ({ page }) => {
    // Step 1: Install Kubernetes orchestration plugin
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="category-infrastructure"]');
    
    await page.click('[data-testid="plugin-kubernetes"] [data-testid="install-plugin"]');
    
    // Configure Kubernetes plugin
    await page.selectOption('[data-testid="k8s-provider"]', 'aws-eks');
    await page.fill('[data-testid="cluster-endpoint"]', 'https://test-cluster.us-west-2.eks.amazonaws.com');
    await page.fill('[data-testid="cluster-ca-cert"]', 'LS0tLS1CRUdJTi...');
    await page.selectOption('[data-testid="auth-method"]', 'service-account');
    await page.fill('[data-testid="service-account-token"]', 'eyJhbGciOiJSUzI1N...');
    
    await page.click('[data-testid="test-k8s-connection"]');
    await expect(page.locator('.connection-test-success')).toContainText('Kubernetes connection successful');
    
    await page.click('[data-testid="save-plugin-config"]');

    // Step 2: Configure auto-scaling plugin
    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="plugin-auto-scaler"] [data-testid="install-plugin"]');
    
    await page.fill('[data-testid="min-replicas"]', '1');
    await page.fill('[data-testid="max-replicas"]', '10');
    await page.fill('[data-testid="cpu-threshold"]', '70');
    await page.fill('[data-testid="memory-threshold"]', '80');
    await page.check('[data-testid="enable-predictive-scaling"]');
    
    await page.click('[data-testid="save-plugin-config"]');

    // Step 3: Test container provisioning
    await page.goto(`/tenants/${testTenantId}/infrastructure`);
    
    // Trigger container scaling operation
    await page.click('[data-testid="scale-tenant-resources"]');
    await page.selectOption('[data-testid="scaling-operation"]', 'scale-up');
    await page.fill('[data-testid="target-cpu"]', '4');
    await page.fill('[data-testid="target-memory"]', '8Gi');
    await page.click('[data-testid="confirm-scaling"]');

    await expect(page.locator('.success-message')).toContainText('Scaling operation initiated');
    
    // Monitor scaling progress
    await page.waitForSelector('[data-testid="scaling-complete"]', { timeout: 60000 });
    await expect(page.locator('[data-testid="current-replicas"]')).not.toContainText('1');
  });

  test('Plugin dependency management and conflicts', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    // Step 1: Try to install plugin with missing dependencies
    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="category-analytics"]');
    
    await page.click('[data-testid="plugin-advanced-analytics"] [data-testid="install-plugin"]');
    
    // Should show dependency warning
    await expect(page.locator('[data-testid="dependency-warning"]')).toBeVisible();
    await expect(page.locator('[data-testid="missing-dependencies"]')).toContainText('Database Analytics Engine');
    
    // Install required dependency first
    await page.click('[data-testid="install-dependencies-first"]');
    await page.click('[data-testid="plugin-db-analytics"] [data-testid="install-plugin"]');
    await page.click('[data-testid="save-plugin-config"]');

    // Step 2: Now install the dependent plugin
    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="plugin-advanced-analytics"] [data-testid="install-plugin"]');
    
    // Should succeed without dependency warning
    await expect(page.locator('[data-testid="dependency-warning"]')).not.toBeVisible();
    await page.click('[data-testid="save-plugin-config"]');

    // Step 3: Test plugin conflict detection
    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="plugin-competing-analytics"] [data-testid="install-plugin"]');
    
    // Should show conflict warning
    await expect(page.locator('[data-testid="conflict-warning"]')).toBeVisible();
    await expect(page.locator('[data-testid="conflicting-plugins"]')).toContainText('Advanced Analytics Plugin');
    
    // Allow conflict resolution
    await page.check('[data-testid="resolve-conflicts"]');
    await page.click('[data-testid="save-plugin-config"]');
  });

  test('Plugin usage analytics and billing integration', async ({ page, context }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    // Step 1: View plugin usage analytics
    await page.goto(`/tenants/${testTenantId}/plugins/analytics`);
    
    // Check usage statistics for installed plugins
    await expect(page.locator('[data-testid="plugin-usage-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="stripe-api-calls"]')).toContainText(/\d+ calls/);
    await expect(page.locator('[data-testid="sms-messages-sent"]')).toContainText(/\d+ messages/);
    await expect(page.locator('[data-testid="emails-sent"]')).toContainText(/\d+ emails/);

    // Step 2: Check usage-based billing
    await page.click('[data-testid="view-plugin-billing"]');
    
    await expect(page.locator('[data-testid="plugin-charges"]')).toBeVisible();
    await expect(page.locator('[data-testid="stripe-usage-cost"]')).toContainText(/\$\d+\.\d{2}/);
    await expect(page.locator('[data-testid="sms-usage-cost"]')).toContainText(/\$\d+\.\d{2}/);

    // Step 3: Set usage limits
    await page.click('[data-testid="configure-limits"]');
    await page.fill('[data-testid="stripe-monthly-limit"]', '1000');
    await page.fill('[data-testid="sms-monthly-limit"]', '500');
    await page.check('[data-testid="alert-on-80-percent"]');
    await page.click('[data-testid="save-limits"]');

    // Step 4: Test usage limit enforcement in tenant
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenantDomain}/login`);
    
    await authenticateAsTenant(tenantPage, {
      email: 'admin@pluginintegrationtestcorp.com',
      password: 'tenant123'
    });

    await tenantPage.goto('/plugins/usage');
    await expect(tenantPage.locator('[data-testid="usage-summary"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="stripe-usage-bar"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="sms-usage-bar"]')).toBeVisible();
  });

  test('Plugin security and sandboxing', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    // Step 1: Install plugin with restricted permissions
    await page.goto('/plugins/marketplace');
    await page.click('[data-testid="category-utilities"]');
    await page.click('[data-testid="plugin-file-processor"] [data-testid="install-plugin"]');
    
    // Configure security restrictions
    await page.check('[data-testid="enable-sandbox"]');
    await page.selectOption('[data-testid="network-access"]', 'restricted');
    await page.selectOption('[data-testid="file-access"]', 'temp-only');
    await page.fill('[data-testid="memory-limit"]', '512MB');
    await page.fill('[data-testid="cpu-limit"]', '0.5');
    
    await page.click('[data-testid="save-plugin-config"]');

    // Step 2: Test security policy enforcement
    await page.goto('/plugins/installed');
    await page.click('[data-testid="plugin-file-processor"] [data-testid="security-audit"]');
    
    await expect(page.locator('[data-testid="sandbox-status"]')).toContainText('Active');
    await expect(page.locator('[data-testid="permission-violations"]')).toContainText('0 violations');

    // Step 3: Monitor plugin resource usage
    await page.goto('/plugins/monitoring');
    await expect(page.locator('[data-testid="resource-usage-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="security-events-log"]')).toBeVisible();
  });

  test('Plugin marketplace curation and approval workflow', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    // Step 1: View pending plugin submissions
    await page.goto('/plugins/admin/pending');
    
    await expect(page.locator('[data-testid="pending-submissions"]')).toBeVisible();
    
    // Step 2: Review plugin submission
    if (await page.locator('[data-testid="plugin-submission"]').first().isVisible()) {
      await page.click('[data-testid="plugin-submission"]');
      
      // Review plugin details
      await expect(page.locator('[data-testid="plugin-metadata"]')).toBeVisible();
      await expect(page.locator('[data-testid="security-scan-results"]')).toBeVisible();
      await expect(page.locator('[data-testid="code-review-status"]')).toBeVisible();
      
      // Approve or reject plugin
      await page.click('[data-testid="approve-plugin"]');
      await page.fill('[data-testid="approval-notes"]', 'Plugin meets security and quality standards');
      await page.click('[data-testid="confirm-approval"]');
      
      await expect(page.locator('.success-message')).toContainText('Plugin approved for marketplace');
    }

    // Step 3: Manage plugin categories
    await page.goto('/plugins/admin/categories');
    await page.click('[data-testid="add-category"]');
    await page.fill('[data-testid="category-name"]', 'Machine Learning');
    await page.fill('[data-testid="category-description"]', 'AI and ML integration plugins');
    await page.click('[data-testid="save-category"]');
  });
});