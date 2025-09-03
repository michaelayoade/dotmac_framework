/**
 * DEPRECATED: External Systems Integration E2E Tests
 * 
 * This file has been superseded by plugin-based-integrations.spec.ts
 * The DotMac platform uses a plugin architecture for external service integrations.
 * 
 * @deprecated Use plugin-based-integrations.spec.ts instead
 * @see tests/e2e/plugin-based-integrations.spec.ts
 */

import { test, expect } from '@playwright/test';
import { createTestTenant, cleanupTestTenant } from '../utils/tenant-factory';
import { authenticateAsManagementAdmin, authenticateAsTenant } from '../utils/auth-helpers';
import { 
  setupStripeTestMode, 
  createTestPaymentMethod,
  setupTwilioTestMode,
  setupSendGridTestMode,
  cleanupExternalTestData
} from '../utils/external-service-helpers';

test.describe('Payment Processor Integration - Stripe', () => {
  let testTenantId: string;
  let stripeTestCustomerId: string;

  test.beforeAll(async () => {
    // Setup Stripe test mode
    await setupStripeTestMode();
    
    // Create test tenant
    const tenant = await createTestTenant({
      name: 'Payment Test Corp',
      plan: 'professional',
      billingEnabled: true
    });
    testTenantId = tenant.id;
  });

  test.afterAll(async () => {
    await cleanupTestTenant(testTenantId);
    await cleanupExternalTestData('stripe');
  });

  test('Complete payment flow with real Stripe integration', async ({ page, context }) => {
    // Step 1: Management admin generates invoice
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/billing`);
    await page.click('[data-testid="generate-invoice"]');
    
    // Create invoice for services
    await page.selectOption('[data-testid="billing-period"]', 'current_month');
    await page.fill('[data-testid="invoice-amount"]', '299.99');
    await page.click('[data-testid="confirm-generate-invoice"]');

    const invoiceId = await page.locator('[data-testid="generated-invoice-id"]').textContent();
    await expect(page.locator('.success-message')).toContainText('Invoice generated');

    // Step 2: Tenant processes payment through Stripe
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/login`);

    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain.replace('.dotmac.app', '')}.com`,
      password: 'tenant123'
    });

    await tenantPage.goto('/billing/invoices');
    await tenantPage.click(`[data-testid="pay-invoice-${invoiceId}"]`);

    // Use Stripe test card
    await tenantPage.waitForSelector('[data-testid="stripe-card-element"]');
    
    // Fill Stripe payment form (this will interact with real Stripe test environment)
    const cardFrame = tenantPage.frameLocator('iframe[name*="__privateStripeFrame"]');
    await cardFrame.locator('[data-testid="cardNumber"]').fill('4242424242424242');
    await cardFrame.locator('[data-testid="cardExpiry"]').fill('12/25');
    await cardFrame.locator('[data-testid="cardCvc"]').fill('123');

    await tenantPage.fill('[data-testid="billing-name"]', 'John Smith');
    await tenantPage.fill('[data-testid="billing-email"]', 'john@paymenttestcorp.com');
    
    await tenantPage.click('[data-testid="process-payment"]');

    // Wait for Stripe processing
    await tenantPage.waitForSelector('.payment-success', { timeout: 30000 });
    await expect(tenantPage.locator('.payment-success')).toContainText('Payment successful');

    // Step 3: Verify payment recorded in management system
    await page.bringToFront();
    await page.reload();
    await page.waitForTimeout(5000); // Wait for webhook processing

    await expect(page.locator(`[data-testid="invoice-${invoiceId}"] .status`)).toContainText('Paid');
    
    // Verify Stripe payment details
    await page.click(`[data-testid="invoice-${invoiceId}"] .view-details`);
    await expect(page.locator('[data-testid="payment-method"]')).toContainText('**** 4242');
    await expect(page.locator('[data-testid="stripe-charge-id"]')).not.toBeEmpty();
  });

  test('Payment failure handling and retry workflow', async ({ page, context }) => {
    // Create invoice
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/billing`);
    await page.click('[data-testid="generate-invoice"]');
    await page.fill('[data-testid="invoice-amount"]', '99.99');
    await page.click('[data-testid="confirm-generate-invoice"]');

    const invoiceId = await page.locator('[data-testid="generated-invoice-id"]').textContent();

    // Tenant attempts payment with declined card
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/billing/invoices`);

    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain.replace('.dotmac.app', '')}.com`,
      password: 'tenant123'
    });

    await tenantPage.click(`[data-testid="pay-invoice-${invoiceId}"]`);

    // Use Stripe test card that will be declined
    const cardFrame = tenantPage.frameLocator('iframe[name*="__privateStripeFrame"]');
    await cardFrame.locator('[data-testid="cardNumber"]').fill('4000000000000002'); // Declined card
    await cardFrame.locator('[data-testid="cardExpiry"]').fill('12/25');
    await cardFrame.locator('[data-testid="cardCvc"]').fill('123');

    await tenantPage.click('[data-testid="process-payment"]');

    // Should show payment declined error
    await expect(tenantPage.locator('.payment-error')).toContainText('payment was declined');

    // Retry with valid card
    await cardFrame.locator('[data-testid="cardNumber"]').fill('4242424242424242'); // Valid card
    await tenantPage.click('[data-testid="process-payment"]');

    await expect(tenantPage.locator('.payment-success')).toContainText('Payment successful');
  });

  test('Subscription billing with Stripe recurring payments', async ({ page }) => {
    // Setup recurring billing for tenant
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/subscription`);
    await page.click('[data-testid="setup-recurring-billing"]');
    
    await page.selectOption('[data-testid="billing-frequency"]', 'monthly');
    await page.fill('[data-testid="subscription-amount"]', '199.99');
    await page.click('[data-testid="create-stripe-subscription"]');

    // Wait for Stripe subscription creation
    await page.waitForSelector('.subscription-created');
    const stripeSubscriptionId = await page.locator('[data-testid="stripe-subscription-id"]').textContent();
    
    expect(stripeSubscriptionId).toMatch(/sub_/); // Stripe subscription ID format
    await expect(page.locator('[data-testid="subscription-status"]')).toContainText('Active');
    await expect(page.locator('[data-testid="next-billing-date"]')).not.toBeEmpty();
  });
});

test.describe('Email Notification Integration - SendGrid', () => {
  let testTenantId: string;

  test.beforeAll(async () => {
    await setupSendGridTestMode();
    const tenant = await createTestTenant({
      name: 'Email Test Corp',
      notificationsEnabled: true
    });
    testTenantId = tenant.id;
  });

  test.afterAll(async () => {
    await cleanupTestTenant(testTenantId);
    await cleanupExternalTestData('sendgrid');
  });

  test('Tenant onboarding email sequence', async ({ page }) => {
    // Trigger tenant creation flow
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/tenants/new');
    
    // Create new tenant which should trigger welcome email
    await page.fill('[data-testid="company-name"]', 'Email Integration Test Co');
    await page.fill('[data-testid="admin-email"]', 'test@emailintegrationtestco.com');
    await page.fill('[data-testid="admin-name"]', 'Integration Tester');
    await page.selectOption('[data-testid="plan-select"]', 'professional');
    
    await page.click('[data-testid="create-tenant"]');
    await page.waitForSelector('.tenant-created');

    const newTenantId = await page.locator('[data-testid="new-tenant-id"]').textContent();

    // Verify welcome email was sent via SendGrid
    await page.goto('/system/email-logs');
    await page.fill('[data-testid="search-email"]', 'test@emailintegrationtestco.com');
    await page.click('[data-testid="search"]');

    await expect(page.locator('[data-testid="email-log-row"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="email-subject"]').first()).toContainText('Welcome to DotMac');
    await expect(page.locator('[data-testid="email-status"]').first()).toContainText('Delivered');

    // Check SendGrid delivery status
    await page.click('[data-testid="view-sendgrid-details"]');
    await expect(page.locator('[data-testid="sendgrid-message-id"]')).not.toBeEmpty();
    await expect(page.locator('[data-testid="delivery-status"]')).toContainText('delivered');

    // Cleanup
    await cleanupTestTenant(newTenantId);
  });

  test('Invoice notification emails', async ({ page, context }) => {
    // Generate invoice
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/billing`);
    await page.click('[data-testid="generate-invoice"]');
    await page.fill('[data-testid="invoice-amount"]', '149.99');
    await page.check('[data-testid="send-email-notification"]');
    await page.click('[data-testid="confirm-generate-invoice"]');

    const invoiceNumber = await page.locator('[data-testid="invoice-number"]').textContent();

    // Wait for email processing
    await page.waitForTimeout(5000);

    // Verify invoice email sent
    await page.goto('/system/email-logs');
    await page.fill('[data-testid="search-invoice"]', invoiceNumber);
    await page.click('[data-testid="search"]');

    await expect(page.locator('[data-testid="email-subject"]').first()).toContainText(`Invoice ${invoiceNumber}`);
    await expect(page.locator('[data-testid="email-status"]').first()).toContainText('Delivered');

    // Verify email content
    await page.click('[data-testid="view-email-content"]');
    await expect(page.locator('[data-testid="email-body"]')).toContainText('$149.99');
    await expect(page.locator('[data-testid="email-body"]')).toContainText('Pay Invoice');
  });

  test('System maintenance notification emails', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/system/maintenance');
    await page.click('[data-testid="schedule-maintenance"]');

    // Schedule maintenance and send notifications
    await page.fill('[data-testid="maintenance-title"]', 'Database Upgrade');
    await page.fill('[data-testid="maintenance-description"]', 'Upgrading database for improved performance');
    await page.fill('[data-testid="maintenance-date"]', '2024-12-01');
    await page.fill('[data-testid="maintenance-time"]', '02:00');
    
    await page.check('[data-testid="notify-all-tenants"]');
    await page.selectOption('[data-testid="advance-notice"]', '24_hours');
    
    await page.click('[data-testid="schedule-and-notify"]');

    await page.waitForSelector('.maintenance-scheduled');

    // Verify maintenance emails queued
    await page.goto('/system/email-queue');
    
    const emailCount = await page.locator('[data-testid="maintenance-emails-count"]').textContent();
    expect(parseInt(emailCount!)).toBeGreaterThan(0);

    // Check first email details
    await page.click('[data-testid="view-first-email"]');
    await expect(page.locator('[data-testid="email-template"]')).toContainText('maintenance-notification');
    await expect(page.locator('[data-testid="email-subject"]')).toContainText('Scheduled Maintenance');
  });
});

test.describe('SMS Notification Integration - Twilio', () => {
  test.beforeAll(async () => {
    await setupTwilioTestMode();
  });

  test.afterAll(async () => {
    await cleanupExternalTestData('twilio');
  });

  test('Emergency SMS notifications', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/system/emergency');
    
    // Create emergency that should trigger SMS
    await page.click('[data-testid="create-emergency"]');
    await page.fill('[data-testid="emergency-title"]', 'Service Outage Alert');
    await page.fill('[data-testid="emergency-message"]', 'Critical service outage detected. ETA 30 minutes for resolution.');
    
    // Enable SMS notifications
    await page.check('[data-testid="send-sms-notifications"]');
    await page.selectOption('[data-testid="sms-recipients"]', 'admin_contacts');
    
    await page.click('[data-testid="send-emergency-alert"]');
    await page.click('[data-testid="confirm-emergency"]');

    // Wait for SMS processing
    await page.waitForTimeout(10000);

    // Verify SMS sent via Twilio
    await page.goto('/system/sms-logs');
    
    await expect(page.locator('[data-testid="sms-log-row"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="sms-message"]').first()).toContainText('Service Outage Alert');
    await expect(page.locator('[data-testid="sms-status"]').first()).toContainText('delivered');

    // Check Twilio delivery details
    await page.click('[data-testid="view-twilio-details"]');
    await expect(page.locator('[data-testid="twilio-sid"]')).toMatch(/SM[a-f0-9]{32}/); // Twilio Message SID format
    await expect(page.locator('[data-testid="twilio-status"]')).toContainText('delivered');
  });

  test('2FA SMS verification', async ({ page, context }) => {
    // Create tenant with SMS 2FA enabled
    const tenant = await createTestTenant({
      name: 'SMS 2FA Test',
      mfaRequired: true,
      mfaMethod: 'sms'
    });

    // Tenant attempts login with 2FA
    const tenantPage = await context.newPage();
    await tenantPage.goto(`https://${tenant.domain}/login`);

    await tenantPage.fill('[data-testid="email"]', `admin@${tenant.domain.replace('.dotmac.app', '')}.com`);
    await tenantPage.fill('[data-testid="password"]', 'tenant123');
    await tenantPage.click('[data-testid="login"]');

    // Should prompt for phone number for 2FA setup
    await expect(tenantPage.locator('[data-testid="2fa-sms-setup"]')).toBeVisible();
    await tenantPage.fill('[data-testid="phone-number"]', '+15551234567');
    await tenantPage.click('[data-testid="send-sms-code"]');

    await expect(tenantPage.locator('.sms-sent-message')).toContainText('SMS code sent');

    // Verify SMS was sent via Twilio (check admin panel)
    await page.goto('/system/sms-logs');
    await page.fill('[data-testid="search-phone"]', '+15551234567');
    await page.click('[data-testid="search"]');

    await expect(page.locator('[data-testid="sms-message"]').first()).toContainText('verification code');
    
    // Get the verification code from SMS log (for testing purposes)
    const verificationCode = await page.locator('[data-testid="sms-verification-code"]').first().textContent();

    // Complete 2FA setup
    await tenantPage.bringToFront();
    await tenantPage.fill('[data-testid="verification-code"]', verificationCode!);
    await tenantPage.click('[data-testid="verify-and-login"]');

    await expect(tenantPage).toHaveURL(/.*\/dashboard/);
    await expect(tenantPage.locator('.welcome-message')).toContainText('Welcome');

    await cleanupTestTenant(tenant.id);
  });
});

test.describe('Kubernetes Operations Integration', () => {
  test('Tenant container provisioning via Kubernetes API', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/tenants/new');
    
    // Create tenant that will trigger K8s deployment
    await page.fill('[data-testid="company-name"]', 'K8s Integration Test');
    await page.fill('[data-testid="admin-email"]', 'admin@k8stest.com');
    await page.selectOption('[data-testid="plan-select"]', 'enterprise');
    await page.selectOption('[data-testid="deployment-region"]', 'us-west-2');
    
    await page.click('[data-testid="create-tenant"]');

    // Monitor deployment progress
    await expect(page.locator('[data-testid="deployment-status"]')).toContainText('Provisioning');
    
    // Wait for Kubernetes deployment to complete
    await page.waitForSelector('[data-testid="deployment-complete"]', { timeout: 300000 }); // 5 minutes

    const tenantId = await page.locator('[data-testid="tenant-id"]').textContent();
    
    // Verify K8s resources were created
    await page.goto(`/tenants/${tenantId}/infrastructure`);
    
    await expect(page.locator('[data-testid="k8s-namespace"]')).toContainText(`tenant-${tenantId}`);
    await expect(page.locator('[data-testid="pod-status"]')).toContainText('Running');
    await expect(page.locator('[data-testid="service-status"]')).toContainText('Active');
    await expect(page.locator('[data-testid="ingress-status"]')).toContainText('Ready');

    // Test tenant container accessibility
    const tenantDomain = await page.locator('[data-testid="tenant-domain"]').textContent();
    
    await page.goto(`https://${tenantDomain}/health`);
    await expect(page.locator('body')).toContainText('"status": "healthy"');

    // Cleanup
    await cleanupTestTenant(tenantId!);
  });

  test('Container scaling operations', async ({ page }) => {
    const tenant = await createTestTenant({
      name: 'Scaling Test Tenant',
      plan: 'enterprise'
    });

    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${tenant.id}/infrastructure`);
    
    // Scale up replicas
    await page.click('[data-testid="scale-container"]');
    await page.fill('[data-testid="replica-count"]', '3');
    await page.click('[data-testid="confirm-scaling"]');

    // Wait for scaling operation
    await page.waitForSelector('[data-testid="scaling-complete"]', { timeout: 120000 });
    
    await expect(page.locator('[data-testid="current-replicas"]')).toContainText('3');
    await expect(page.locator('[data-testid="ready-replicas"]')).toContainText('3');

    // Verify all pods are running
    const podStatuses = await page.locator('[data-testid="pod-status"]').allTextContents();
    for (const status of podStatuses) {
      expect(status).toContain('Running');
    }

    // Scale back down
    await page.click('[data-testid="scale-container"]');
    await page.fill('[data-testid="replica-count"]', '1');
    await page.click('[data-testid="confirm-scaling"]');

    await page.waitForSelector('[data-testid="scaling-complete"]', { timeout: 120000 });
    await expect(page.locator('[data-testid="current-replicas"]')).toContainText('1');

    await cleanupTestTenant(tenant.id);
  });

  test('Container resource monitoring and alerting', async ({ page }) => {
    const tenant = await createTestTenant({
      name: 'Monitoring Test',
      plan: 'professional'
    });

    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${tenant.id}/monitoring`);

    // Verify Kubernetes metrics are being collected
    await expect(page.locator('[data-testid="cpu-usage"]')).not.toBeEmpty();
    await expect(page.locator('[data-testid="memory-usage"]')).not.toBeEmpty();
    await expect(page.locator('[data-testid="pod-count"]')).not.toBeEmpty();

    // Set up resource alerts
    await page.click('[data-testid="configure-alerts"]');
    await page.fill('[data-testid="cpu-threshold"]', '80');
    await page.fill('[data-testid="memory-threshold"]', '85');
    await page.check('[data-testid="alert-email-enabled"]');
    await page.click('[data-testid="save-alerts"]');

    await expect(page.locator('.alerts-configured')).toContainText('Resource alerts configured');

    await cleanupTestTenant(tenant.id);
  });
});

// Helper functions
async function getTenantDetails(tenantId: string) {
  return {
    id: tenantId,
    domain: `tenant-${tenantId}.dotmac.app`
  };
}