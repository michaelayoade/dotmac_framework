/**
 * Cross-Portal Business Workflow E2E Tests
 * Tests complete business workflows that span multiple portals and services
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';

test.describe('Cross-Portal Business Workflows', () => {
  test.describe.configure({ mode: 'serial' });

  let adminPage: Page;
  let customerPage: Page;
  let resellerPage: Page;

  test.beforeAll(async ({ browser }) => {
    // Create separate browser contexts for different portal users
    const adminContext = await browser.newContext();
    const customerContext = await browser.newContext();
    const resellerContext = await browser.newContext();

    adminPage = await adminContext.newPage();
    customerPage = await customerContext.newPage();
    resellerPage = await resellerContext.newPage();

    // Setup authentication for each portal
    await setupAuth(adminPage, 'admin');
    await setupAuth(customerPage, 'customer');
    await setupAuth(resellerPage, 'reseller');
  });

  test('complete customer lifecycle automation workflow', async () => {
    // Test complete customer onboarding from reseller portal through admin approval to service activation

    // Step 1: Reseller creates customer lead
    await resellerPage.goto('/reseller/leads/new');
    await expect(resellerPage.locator('[data-testid="lead-form"]')).toBeVisible();

    await resellerPage.fill('[data-testid="customer-name"]', 'Test Customer Corp');
    await resellerPage.fill('[data-testid="customer-email"]', 'testcustomer@example.com');
    await resellerPage.fill('[data-testid="service-address"]', '123 Main St, Test City, TC 12345');
    await resellerPage.selectOption('[data-testid="service-plan"]', 'business_1gbps');
    await resellerPage.fill('[data-testid="monthly-value"]', '299.99');
    
    await resellerPage.click('[data-testid="submit-lead"]');
    await expect(resellerPage.locator('[data-testid="lead-success"]')).toContainText('Lead created successfully');
    
    // Capture lead ID for cross-portal tracking
    const leadId = await resellerPage.locator('[data-testid="lead-id"]').textContent();
    
    // Step 2: Admin receives and processes lead
    await adminPage.goto('/admin/leads/pending');
    await expect(adminPage.locator('[data-testid="pending-leads"]')).toBeVisible();
    
    // Find the specific lead
    await adminPage.fill('[data-testid="search-leads"]', leadId);
    await adminPage.click('[data-testid="search-btn"]');
    
    const leadRow = adminPage.locator(`[data-testid="lead-row-${leadId}"]`);
    await expect(leadRow).toBeVisible();
    await expect(leadRow).toContainText('Test Customer Corp');
    
    // Review lead details
    await leadRow.click();
    await expect(adminPage.locator('[data-testid="lead-details"]')).toBeVisible();
    
    // Perform credit check automation
    await adminPage.click('[data-testid="run-credit-check"]');
    await expect(adminPage.locator('[data-testid="credit-check-running"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="credit-check-passed"]')).toBeVisible({ timeout: 10000 });
    
    // Approve lead
    await adminPage.fill('[data-testid="approval-notes"]', 'Credit check passed, approved for service activation');
    await adminPage.click('[data-testid="approve-lead"]');
    await expect(adminPage.locator('[data-testid="approval-success"]')).toContainText('Lead approved');
    
    // Step 3: Service provisioning automation
    await adminPage.goto('/admin/provisioning/queue');
    await expect(adminPage.locator('[data-testid="provisioning-queue"]')).toBeVisible();
    
    // Verify service appears in provisioning queue
    const serviceItem = adminPage.locator(`[data-testid="service-${leadId}"]`);
    await expect(serviceItem).toBeVisible();
    await expect(serviceItem).toContainText('business_1gbps');
    
    // Trigger automated provisioning
    await serviceItem.click();
    await adminPage.click('[data-testid="start-provisioning"]');
    
    // Monitor provisioning progress
    await expect(adminPage.locator('[data-testid="provisioning-status"]')).toContainText('In Progress');
    await expect(adminPage.locator('[data-testid="ip-allocation"]')).toBeVisible({ timeout: 15000 });
    await expect(adminPage.locator('[data-testid="router-configuration"]')).toBeVisible({ timeout: 15000 });
    await expect(adminPage.locator('[data-testid="service-activation"]')).toBeVisible({ timeout: 20000 });
    
    // Verify provisioning completion
    await expect(adminPage.locator('[data-testid="provisioning-complete"]')).toBeVisible({ timeout: 30000 });
    
    // Step 4: Customer portal access creation
    await adminPage.click('[data-testid="create-customer-portal"]');
    await expect(adminPage.locator('[data-testid="portal-creation-success"]')).toBeVisible();
    
    const customerLoginUrl = await adminPage.locator('[data-testid="customer-portal-url"]').textContent();
    const customerCredentials = await adminPage.locator('[data-testid="customer-credentials"]').textContent();
    
    // Step 5: Customer receives and uses portal access
    await customerPage.goto(customerLoginUrl || '/customer/login');
    
    // Verify customer can login with generated credentials
    await customerPage.fill('[data-testid="username"]', 'testcustomer@example.com');
    await customerPage.fill('[data-testid="password"]', customerCredentials?.split(': ')[1] || 'temppass123');
    await customerPage.click('[data-testid="login-btn"]');
    
    // Verify customer dashboard shows activated service
    await expect(customerPage.locator('[data-testid="customer-dashboard"]')).toBeVisible();
    await expect(customerPage.locator('[data-testid="active-services"]')).toContainText('Business 1Gbps');
    await expect(customerPage.locator('[data-testid="service-status"]')).toContainText('Active');
    
    // Step 6: Verify reseller receives commission notification
    await resellerPage.goto('/reseller/commissions');
    await expect(resellerPage.locator('[data-testid="commission-alerts"]')).toBeVisible();
    
    const commissionItem = resellerPage.locator(`[data-testid="commission-${leadId}"]`);
    await expect(commissionItem).toBeVisible();
    await expect(commissionItem).toContainText('$89.97'); // 30% of $299.99
    await expect(commissionItem).toContainText('Pending');
  });

  test('service provisioning automation workflow', async () => {
    // Test automated service provisioning with IPAM integration

    await adminPage.goto('/admin/services/new');
    
    // Configure new service
    await adminPage.fill('[data-testid="customer-search"]', 'existing-customer@test.com');
    await adminPage.click('[data-testid="customer-result-0"]');
    
    await adminPage.selectOption('[data-testid="service-type"]', 'residential_fiber');
    await adminPage.selectOption('[data-testid="speed-tier"]', '500mbps');
    await adminPage.fill('[data-testid="installation-address"]', '456 Oak Ave, Test City, TC 54321');
    
    // Enable automation
    await adminPage.check('[data-testid="enable-automation"]');
    await adminPage.selectOption('[data-testid="automation-profile"]', 'standard_residential');
    
    await adminPage.click('[data-testid="create-service"]');
    
    // Verify automation workflow starts
    await expect(adminPage.locator('[data-testid="automation-started"]')).toBeVisible();
    
    // Monitor automated steps
    const automationSteps = [
      { step: 'address-validation', timeout: 5000 },
      { step: 'coverage-check', timeout: 8000 },
      { step: 'ip-allocation', timeout: 10000 },
      { step: 'vlan-assignment', timeout: 12000 },
      { step: 'equipment-reservation', timeout: 15000 },
      { step: 'installation-scheduling', timeout: 18000 }
    ];

    for (const { step, timeout } of automationSteps) {
      await expect(adminPage.locator(`[data-testid="automation-${step}"]`)).toBeVisible({ timeout });
      await expect(adminPage.locator(`[data-testid="automation-${step}-complete"]`)).toBeVisible({ timeout: timeout + 5000 });
    }
    
    // Verify final automation results
    await expect(adminPage.locator('[data-testid="automation-complete"]')).toBeVisible({ timeout: 25000 });
    
    const serviceId = await adminPage.locator('[data-testid="service-id"]').textContent();
    const assignedIP = await adminPage.locator('[data-testid="assigned-ip"]').textContent();
    const installationDate = await adminPage.locator('[data-testid="installation-date"]').textContent();
    
    expect(assignedIP).toMatch(/\d+\.\d+\.\d+\.\d+/);
    expect(installationDate).toBeTruthy();
    
    // Verify technician assignment
    await adminPage.goto('/admin/technicians/schedule');
    const technicianTask = adminPage.locator(`[data-testid="task-${serviceId}"]`);
    await expect(technicianTask).toBeVisible();
    await expect(technicianTask).toContainText('Fiber Installation');
  });

  test('billing automation workflow', async () => {
    // Test automated billing cycle processing

    await adminPage.goto('/admin/billing/automation');
    
    // Configure billing automation run
    await adminPage.selectOption('[data-testid="billing-cycle"]', 'monthly');
    await adminPage.fill('[data-testid="invoice-date"]', '2024-01-01');
    await adminPage.check('[data-testid="auto-send-invoices"]');
    await adminPage.check('[data-testid="auto-process-payments"]');
    
    await adminPage.click('[data-testid="start-billing-automation"]');
    
    // Monitor billing automation progress
    await expect(adminPage.locator('[data-testid="billing-automation-running"]')).toBeVisible();
    
    const billingSteps = [
      'customer-data-collection',
      'usage-calculation',
      'invoice-generation',
      'tax-calculation',
      'payment-processing',
      'notification-sending'
    ];
    
    for (const step of billingSteps) {
      await expect(adminPage.locator(`[data-testid="billing-${step}"]`)).toBeVisible({ timeout: 15000 });
    }
    
    // Verify automation summary
    await expect(adminPage.locator('[data-testid="billing-automation-complete"]')).toBeVisible({ timeout: 60000 });
    
    const processedCount = await adminPage.locator('[data-testid="processed-invoices"]').textContent();
    const successfulPayments = await adminPage.locator('[data-testid="successful-payments"]').textContent();
    const failedPayments = await adminPage.locator('[data-testid="failed-payments"]').textContent();
    
    expect(Number(processedCount)).toBeGreaterThan(0);
    expect(Number(successfulPayments)).toBeGreaterThanOrEqual(0);
    expect(Number(failedPayments)).toBeGreaterThanOrEqual(0);
    
    // Verify customer receives invoice
    await customerPage.goto('/customer/billing/invoices');
    await expect(customerPage.locator('[data-testid="latest-invoice"]')).toBeVisible();
    await expect(customerPage.locator('[data-testid="invoice-date"]')).toContainText('2024-01-01');
    
    // Test payment automation failure handling
    if (Number(failedPayments) > 0) {
      await adminPage.goto('/admin/billing/failed-payments');
      await expect(adminPage.locator('[data-testid="failed-payment-list"]')).toBeVisible();
      
      const firstFailedPayment = adminPage.locator('[data-testid="failed-payment-0"]');
      await firstFailedPayment.click();
      
      // Verify retry automation is available
      await expect(adminPage.locator('[data-testid="retry-payment-btn"]')).toBeVisible();
      await expect(adminPage.locator('[data-testid="escalation-rules"]')).toBeVisible();
    }
  });

  test('technical support escalation workflow', async () => {
    // Test automated technical support escalation across portals

    // Customer creates support ticket
    await customerPage.goto('/customer/support/tickets/new');
    
    await customerPage.fill('[data-testid="ticket-subject"]', 'Internet connection intermittent issues');
    await customerPage.selectOption('[data-testid="ticket-category"]', 'technical_support');
    await customerPage.selectOption('[data-testid="priority"]', 'high');
    await customerPage.fill('[data-testid="ticket-description"]', 'Internet has been cutting out every few hours for the past 3 days. Speed tests show inconsistent results.');
    
    await customerPage.click('[data-testid="submit-ticket"]');
    
    const ticketId = await customerPage.locator('[data-testid="ticket-id"]').textContent();
    await expect(customerPage.locator('[data-testid="ticket-created"]')).toBeVisible();
    
    // Verify automated initial response
    await expect(customerPage.locator('[data-testid="auto-response"]')).toBeVisible({ timeout: 10000 });
    await expect(customerPage.locator('[data-testid="auto-response"]')).toContainText('automated diagnostic');
    
    // Admin receives and processes ticket
    await adminPage.goto('/admin/support/tickets/queue');
    
    const ticketRow = adminPage.locator(`[data-testid="ticket-${ticketId}"]`);
    await expect(ticketRow).toBeVisible();
    await expect(ticketRow).toContainText('Internet connection intermittent');
    
    await ticketRow.click();
    await expect(adminPage.locator('[data-testid="ticket-details"]')).toBeVisible();
    
    // Verify automated diagnostics ran
    await expect(adminPage.locator('[data-testid="auto-diagnostics"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="ping-test-results"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="connection-history"]')).toBeVisible();
    
    // Simulate escalation trigger (no resolution after 2 hours)
    await adminPage.click('[data-testid="simulate-escalation"]');
    
    // Verify escalation automation
    await expect(adminPage.locator('[data-testid="escalation-triggered"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="escalation-level"]')).toContainText('Level 2 Technical');
    
    // Verify technician dispatch automation
    await adminPage.goto('/admin/technicians/dispatch');
    
    const dispatchRequest = adminPage.locator(`[data-testid="dispatch-${ticketId}"]`);
    await expect(dispatchRequest).toBeVisible();
    await expect(dispatchRequest).toContainText('Field Investigation Required');
    
    // Verify customer notification of escalation
    await customerPage.goto(`/customer/support/tickets/${ticketId}`);
    await expect(customerPage.locator('[data-testid="escalation-notice"]')).toBeVisible();
    await expect(customerPage.locator('[data-testid="technician-dispatch"]')).toContainText('technician has been assigned');
  });

  test('payment overdue escalation workflow', async () => {
    // Test automated payment overdue handling

    await adminPage.goto('/admin/billing/overdue-automation');
    
    // Setup test scenario with overdue account
    await adminPage.fill('[data-testid="test-customer-email"]', 'overdue-customer@test.com');
    await adminPage.fill('[data-testid="overdue-days"]', '15');
    await adminPage.fill('[data-testid="overdue-amount"]', '299.99');
    await adminPage.click('[data-testid="create-test-scenario"]');
    
    const overdueAccountId = await adminPage.locator('[data-testid="account-id"]').textContent();
    
    // Trigger overdue automation
    await adminPage.click('[data-testid="run-overdue-automation"]');
    
    // Verify escalation steps
    const escalationSteps = [
      { day: 7, action: 'reminder-email' },
      { day: 14, action: 'warning-notification' },
      { day: 21, action: 'service-suspension-notice' },
      { day: 30, action: 'service-suspension' }
    ];
    
    for (const { day, action } of escalationSteps) {
      const stepElement = adminPage.locator(`[data-testid="escalation-${day}-${action}"]`);
      await expect(stepElement).toBeVisible({ timeout: 10000 });
      
      if (day <= 15) {
        await expect(stepElement).toContainText('Executed');
      } else {
        await expect(stepElement).toContainText('Scheduled');
      }
    }
    
    // Verify customer receives appropriate notifications
    await customerPage.goto('/customer/billing/notifications');
    await expect(customerPage.locator('[data-testid="overdue-warning"]')).toBeVisible();
    await expect(customerPage.locator('[data-testid="payment-reminder"]')).toBeVisible();
    
    // Test payment resolution
    await customerPage.click('[data-testid="pay-now-btn"]');
    await customerPage.fill('[data-testid="payment-amount"]', '299.99');
    await customerPage.selectOption('[data-testid="payment-method"]', 'credit_card');
    await customerPage.click('[data-testid="process-payment"]');
    
    // Verify automation stops after payment
    await expect(customerPage.locator('[data-testid="payment-success"]')).toBeVisible();
    
    await adminPage.goto('/admin/billing/overdue-automation');
    const resolvedAccount = adminPage.locator(`[data-testid="account-${overdueAccountId}"]`);
    await expect(resolvedAccount).toContainText('Resolved');
    await expect(resolvedAccount).toContainText('Escalation Cancelled');
  });

  test('cross-portal data synchronization', async () => {
    // Test real-time data sync between portals

    // Admin updates customer service
    await adminPage.goto('/admin/customers/search');
    await adminPage.fill('[data-testid="search-customer"]', 'sync-test@example.com');
    await adminPage.click('[data-testid="search-btn"]');
    
    await adminPage.click('[data-testid="customer-result-0"]');
    await adminPage.goto('/admin/customers/edit-service');
    
    // Upgrade service plan
    await adminPage.selectOption('[data-testid="service-plan"]', 'premium_1gbps');
    await adminPage.fill('[data-testid="effective-date"]', '2024-02-01');
    await adminPage.click('[data-testid="update-service"]');
    
    await expect(adminPage.locator('[data-testid="service-updated"]')).toBeVisible();
    
    // Verify customer portal reflects changes immediately
    await customerPage.goto('/customer/dashboard');
    await customerPage.reload(); // Simulate user refresh
    
    await expect(customerPage.locator('[data-testid="current-plan"]')).toContainText('Premium 1Gbps', { timeout: 5000 });
    await expect(customerPage.locator('[data-testid="upgrade-effective"]')).toContainText('2024-02-01');
    
    // Verify reseller portal reflects commission changes
    await resellerPage.goto('/reseller/customers');
    await resellerPage.fill('[data-testid="search-customers"]', 'sync-test@example.com');
    await resellerPage.click('[data-testid="search-btn"]');
    
    const customerRow = resellerPage.locator('[data-testid="customer-0"]');
    await expect(customerRow).toContainText('Premium 1Gbps', { timeout: 5000 });
    
    // Test billing synchronization
    await customerPage.goto('/customer/billing/current');
    const newMonthlyCharge = await customerPage.locator('[data-testid="monthly-charge"]').textContent();
    expect(newMonthlyCharge).toContain('$149.99'); // Premium plan pricing
    
    // Test service metrics synchronization
    await adminPage.goto('/admin/services/monitoring');
    const serviceMetrics = adminPage.locator('[data-testid="service-sync-test"]');
    await expect(serviceMetrics).toContainText('Premium 1Gbps', { timeout: 10000 });
    await expect(serviceMetrics).toContainText('Active');
  });

  test.afterAll(async () => {
    // Cleanup browser contexts
    await adminPage.context().close();
    await customerPage.context().close();
    await resellerPage.context().close();
  });
});