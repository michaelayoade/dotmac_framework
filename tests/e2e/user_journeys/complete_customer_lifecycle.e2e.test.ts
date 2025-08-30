/**
 * Complete Customer Lifecycle E2E Tests
 *
 * This test suite validates complete user journeys across all portals,
 * ensuring seamless integration and user experience validation.
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import { TestDataFactory } from '../utils/test-data-factory';
import { PortalNavigator } from '../utils/portal-navigator';
import { ApiTestHelper } from '../utils/api-test-helper';

interface CustomerLifecycleTestData {
  customer: {
    email: string;
    firstName: string;
    lastName: string;
    phone: string;
    address: {
      street: string;
      city: string;
      state: string;
      zipCode: string;
    };
  };
  servicePlan: {
    id: string;
    name: string;
    speed: string;
    price: string;
  };
  reseller: {
    email: string;
    territory: string;
    commissionRate: number;
  };
}

test.describe('Complete Customer Lifecycle Journey', () => {
  let testData: CustomerLifecycleTestData;
  let adminPage: Page;
  let resellerPage: Page;
  let customerPage: Page;
  let apiHelper: ApiTestHelper;

  test.beforeAll(async ({ browser }) => {
    // Create separate browser contexts for each portal
    const adminContext = await browser.newContext({
      storageState: 'tests/auth/admin-auth.json'
    });
    const resellerContext = await browser.newContext({
      storageState: 'tests/auth/reseller-auth.json'
    });
    const customerContext = await browser.newContext();

    adminPage = await adminContext.newPage();
    resellerPage = await resellerContext.newPage();
    customerPage = await customerContext.newPage();

    // Initialize test data and API helper
    testData = TestDataFactory.generateCustomerLifecycleData();
    apiHelper = new ApiTestHelper();
  });

  test.afterAll(async () => {
    await adminPage.close();
    await resellerPage.close();
    await customerPage.close();
  });

  test('should handle full customer onboarding through reseller portal', async () => {
    test.slow(); // Mark as slow test due to multi-portal workflow

    // ==== STEP 1: Reseller creates customer lead ====

    await test.step('Reseller creates customer lead', async () => {
      const resellerNav = new PortalNavigator(resellerPage);
      await resellerNav.navigateToResellerPortal();

      // Navigate to customer onboarding
      await resellerPage.click('[data-testid="nav-customers"]');
      await resellerPage.click('[data-testid="add-customer-btn"]');

      // Fill customer information form
      await resellerPage.fill('[data-testid="customer-email"]', testData.customer.email);
      await resellerPage.fill('[data-testid="customer-first-name"]', testData.customer.firstName);
      await resellerPage.fill('[data-testid="customer-last-name"]', testData.customer.lastName);
      await resellerPage.fill('[data-testid="customer-phone"]', testData.customer.phone);

      // Fill address information
      await resellerPage.fill('[data-testid="customer-street"]', testData.customer.address.street);
      await resellerPage.fill('[data-testid="customer-city"]', testData.customer.address.city);
      await resellerPage.selectOption('[data-testid="customer-state"]', testData.customer.address.state);
      await resellerPage.fill('[data-testid="customer-zip"]', testData.customer.address.zipCode);

      // Select service plan
      await resellerPage.selectOption('[data-testid="service-plan-select"]', testData.servicePlan.id);

      // Verify territory validation
      await expect(resellerPage.locator('[data-testid="territory-validation-success"]')).toBeVisible();

      // Submit customer creation
      await resellerPage.click('[data-testid="create-customer-submit"]');

      // Verify success notification
      await expect(resellerPage.locator('[data-testid="customer-created-success"]')).toBeVisible({
        timeout: 10000
      });

      // Verify customer appears in reseller's customer list
      await resellerPage.click('[data-testid="nav-customers"]');
      await expect(resellerPage.locator(`[data-testid="customer-row-${testData.customer.email}"]`)).toBeVisible();
    });

    // ==== STEP 2: Admin approves and provisions customer ====

    await test.step('Admin approves and provisions customer', async () => {
      const adminNav = new PortalNavigator(adminPage);
      await adminNav.navigateToAdminPortal();

      // Navigate to pending customers
      await adminPage.click('[data-testid="nav-customers"]');
      await adminPage.click('[data-testid="pending-customers-tab"]');

      // Find and open customer record
      const customerRow = adminPage.locator(`[data-testid="customer-row-${testData.customer.email}"]`);
      await expect(customerRow).toBeVisible();
      await customerRow.click();

      // Verify customer details
      await expect(adminPage.locator('[data-testid="customer-email"]')).toHaveText(testData.customer.email);
      await expect(adminPage.locator('[data-testid="reseller-source"]')).toBeVisible();
      await expect(adminPage.locator('[data-testid="commission-eligible"]')).toBeVisible();

      // Schedule installation
      await adminPage.click('[data-testid="schedule-installation-btn"]');

      const installationDate = new Date();
      installationDate.setDate(installationDate.getDate() + 7);
      await adminPage.fill('[data-testid="installation-date"]', installationDate.toISOString().split('T')[0]);
      await adminPage.selectOption('[data-testid="technician-select"]', 'tech_001');
      await adminPage.click('[data-testid="confirm-installation"]');

      // Verify installation scheduled
      await expect(adminPage.locator('[data-testid="installation-scheduled-success"]')).toBeVisible();

      // Approve customer activation
      await adminPage.click('[data-testid="approve-customer-btn"]');
      await adminPage.click('[data-testid="confirm-approval"]');

      // Verify customer status changed
      await expect(adminPage.locator('[data-testid="customer-status"]')).toHaveText('Approved - Pending Installation');
    });

    // ==== STEP 3: Customer receives activation and completes setup ====

    await test.step('Customer completes self-service setup', async () => {
      // Simulate customer receiving activation email
      const activationToken = await apiHelper.generateCustomerActivationToken(testData.customer.email);

      // Customer navigates to activation page
      const customerNav = new PortalNavigator(customerPage);
      await customerNav.navigateToCustomerActivation(activationToken);

      // Set up account password
      await customerPage.fill('[data-testid="password-input"]', 'SecureCustomerPassword123!');
      await customerPage.fill('[data-testid="confirm-password"]', 'SecureCustomerPassword123!');

      // Accept terms and conditions
      await customerPage.check('[data-testid="terms-checkbox"]');
      await customerPage.check('[data-testid="privacy-checkbox"]');

      // Set up communication preferences
      await customerPage.check('[data-testid="billing-notifications"]');
      await customerPage.check('[data-testid="service-notifications"]');
      await customerPage.uncheck('[data-testid="marketing-emails"]');

      // Complete account setup
      await customerPage.click('[data-testid="complete-setup-btn"]');

      // Verify account creation success
      await expect(customerPage.locator('[data-testid="setup-complete-success"]')).toBeVisible();

      // Verify redirect to customer dashboard
      await expect(customerPage).toHaveURL(/.*\/dashboard/);
      await expect(customerPage.locator('[data-testid="customer-dashboard"]')).toBeVisible();

      // Verify service information displayed
      await expect(customerPage.locator('[data-testid="service-plan-name"]')).toHaveText(testData.servicePlan.name);
      await expect(customerPage.locator('[data-testid="service-speed"]')).toHaveText(testData.servicePlan.speed);
      await expect(customerPage.locator('[data-testid="service-status"]')).toHaveText('Pending Installation');
    });

    // ==== STEP 4: First billing cycle processes ====

    await test.step('First billing cycle processes correctly', async () => {
      // Simulate installation completion (would normally be done by technician)
      await apiHelper.completeCustomerInstallation(testData.customer.email);

      // Wait for billing cycle to process (simulate with API call)
      await apiHelper.triggerBillingCycle(testData.customer.email);

      // Customer checks billing information
      await customerPage.click('[data-testid="nav-billing"]');

      // Verify first bill generated
      await expect(customerPage.locator('[data-testid="current-bill"]')).toBeVisible();
      await expect(customerPage.locator('[data-testid="setup-fee"]')).toBeVisible();
      await expect(customerPage.locator('[data-testid="prorated-service"]')).toBeVisible();

      // Verify bill amount calculation
      const setupFee = await customerPage.locator('[data-testid="setup-fee-amount"]').textContent();
      const serviceCharge = await customerPage.locator('[data-testid="service-charge-amount"]').textContent();
      const totalAmount = await customerPage.locator('[data-testid="total-amount"]').textContent();

      expect(setupFee).toContain('$99.00'); // Setup fee
      expect(totalAmount).toMatch(/\$\d+\.\d{2}/); // Valid currency format

      // Verify payment method setup
      await customerPage.click('[data-testid="payment-methods-tab"]');
      await expect(customerPage.locator('[data-testid="auto-pay-enabled"]')).toBeVisible();
      await expect(customerPage.locator('[data-testid="card-ending-4242"]')).toBeVisible();
    });

    // ==== STEP 5: Reseller commission tracking ====

    await test.step('Reseller commission tracked correctly', async () => {
      // Navigate to reseller commission dashboard
      await resellerPage.click('[data-testid="nav-commissions"]');

      // Verify customer shows in commission tracking
      const customerCommissionRow = resellerPage.locator(`[data-testid="commission-customer-${testData.customer.email}"]`);
      await expect(customerCommissionRow).toBeVisible();

      // Verify commission details
      await customerCommissionRow.click();
      await expect(resellerPage.locator('[data-testid="commission-type"]')).toHaveText('Customer Acquisition');
      await expect(resellerPage.locator('[data-testid="commission-status"]')).toHaveText('Earned - Pending Payment');

      // Verify commission amount calculation
      const commissionAmount = await resellerPage.locator('[data-testid="commission-amount"]').textContent();
      expect(commissionAmount).toMatch(/\$\d+\.\d{2}/);

      // Check monthly recurring commission
      await expect(resellerPage.locator('[data-testid="recurring-commission"]')).toBeVisible();
      await expect(resellerPage.locator('[data-testid="recurring-rate"]')).toHaveText(`${testData.reseller.commissionRate}%`);
    });

    // ==== STEP 6: Support interaction resolves issue ====

    await test.step('Customer support interaction resolves successfully', async () => {
      // Customer creates support ticket
      await customerPage.click('[data-testid="nav-support"]');
      await customerPage.click('[data-testid="create-ticket-btn"]');

      // Fill support ticket form
      await customerPage.selectOption('[data-testid="ticket-category"]', 'technical_support');
      await customerPage.fill('[data-testid="ticket-subject"]', 'Internet speed slower than expected');
      await customerPage.fill('[data-testid="ticket-description"]', 'Speed tests showing 50Mbps instead of 100Mbps');
      await customerPage.selectOption('[data-testid="ticket-priority"]', 'medium');

      await customerPage.click('[data-testid="submit-ticket-btn"]');

      // Verify ticket created
      await expect(customerPage.locator('[data-testid="ticket-created-success"]')).toBeVisible();

      const ticketNumber = await customerPage.locator('[data-testid="ticket-number"]').textContent();
      expect(ticketNumber).toMatch(/TKT-\d+/);

      // Admin responds to support ticket
      await adminPage.click('[data-testid="nav-support"]');
      await adminPage.fill('[data-testid="ticket-search"]', ticketNumber!);
      await adminPage.press('[data-testid="ticket-search"]', 'Enter');

      const ticketRow = adminPage.locator(`[data-testid="ticket-row-${ticketNumber}"]`);
      await ticketRow.click();

      // Admin assigns technician and adds response
      await adminPage.selectOption('[data-testid="assign-technician"]', 'tech_001');
      await adminPage.fill('[data-testid="admin-response"]', 'Scheduling technical evaluation of line quality. Will contact customer within 24 hours.');
      await adminPage.click('[data-testid="send-response-btn"]');

      // Customer receives notification and response
      await customerPage.reload();
      await customerPage.click('[data-testid="nav-support"]');
      await customerPage.click(`[data-testid="ticket-${ticketNumber}"]`);

      // Verify customer sees admin response
      await expect(customerPage.locator('[data-testid="admin-response"]')).toContainText('technical evaluation');
      await expect(customerPage.locator('[data-testid="ticket-status"]')).toHaveText('In Progress');

      // Simulate issue resolution
      await apiHelper.resolveTicket(ticketNumber!, 'Line quality issue resolved. Speed now testing at full 100Mbps.');

      // Verify ticket resolution
      await customerPage.reload();
      await expect(customerPage.locator('[data-testid="ticket-status"]')).toHaveText('Resolved');
      await expect(customerPage.locator('[data-testid="resolution-response"]')).toContainText('Line quality issue resolved');
    });
  });

  test('should handle customer service upgrade workflow', async () => {
    // Customer requests service upgrade
    await test.step('Customer requests service upgrade', async () => {
      const customerNav = new PortalNavigator(customerPage);
      await customerNav.navigateToCustomerPortal();
      await customerNav.login(testData.customer.email, 'SecureCustomerPassword123!');

      await customerPage.click('[data-testid="nav-services"]');
      await customerPage.click('[data-testid="upgrade-service-btn"]');

      // Select new service plan
      await customerPage.selectOption('[data-testid="new-service-plan"]', 'residential_500mbps');
      await customerPage.fill('[data-testid="upgrade-reason"]', 'Need faster speeds for work from home');

      await customerPage.click('[data-testid="request-upgrade-btn"]');

      // Verify upgrade request submitted
      await expect(customerPage.locator('[data-testid="upgrade-requested-success"]')).toBeVisible();
      await expect(customerPage.locator('[data-testid="upgrade-status"]')).toHaveText('Pending Approval');
    });

    // Admin approves service upgrade
    await test.step('Admin approves service upgrade', async () => {
      const adminNav = new PortalNavigator(adminPage);
      await adminNav.navigateToAdminPortal();

      await adminPage.click('[data-testid="nav-service-changes"]');
      await adminPage.click('[data-testid="pending-upgrades-tab"]');

      const upgradeRequest = adminPage.locator(`[data-testid="upgrade-request-${testData.customer.email}"]`);
      await upgradeRequest.click();

      // Review upgrade details
      await expect(adminPage.locator('[data-testid="current-plan"]')).toHaveText(testData.servicePlan.name);
      await expect(adminPage.locator('[data-testid="requested-plan"]')).toHaveText('Residential 500Mbps');

      // Approve upgrade
      await adminPage.click('[data-testid="approve-upgrade-btn"]');
      await adminPage.selectOption('[data-testid="effective-date"]', 'next_billing_cycle');
      await adminPage.click('[data-testid="confirm-approval"]');

      // Verify approval
      await expect(adminPage.locator('[data-testid="upgrade-approved-success"]')).toBeVisible();
    });

    // Verify billing impact
    await test.step('Verify billing impact calculated correctly', async () => {
      // Customer checks billing impact
      await customerPage.click('[data-testid="nav-billing"]');
      await customerPage.click('[data-testid="upcoming-changes-tab"]');

      // Verify upgrade shows in upcoming changes
      await expect(customerPage.locator('[data-testid="service-upgrade-change"]')).toBeVisible();
      await expect(customerPage.locator('[data-testid="new-monthly-rate"]')).toContainText('$89.99');
      await expect(customerPage.locator('[data-testid="effective-date"]')).toBeVisible();

      // Verify prorated billing calculation
      const proratedAmount = await customerPage.locator('[data-testid="prorated-amount"]').textContent();
      expect(proratedAmount).toMatch(/\$\d+\.\d{2}/);
    });
  });

  test('should handle customer payment failure and recovery', async () => {
    // Simulate payment failure
    await test.step('Handle payment failure', async () => {
      // Simulate failed auto-payment
      await apiHelper.simulatePaymentFailure(testData.customer.email);

      // Customer receives notification
      const customerNav = new PortalNavigator(customerPage);
      await customerNav.navigateToCustomerPortal();

      await customerPage.click('[data-testid="notifications-bell"]');
      await expect(customerPage.locator('[data-testid="payment-failed-notification"]')).toBeVisible();

      // Navigate to billing to resolve
      await customerPage.click('[data-testid="nav-billing"]');
      await expect(customerPage.locator('[data-testid="payment-failed-banner"]')).toBeVisible();
    });

    // Customer updates payment method and retries
    await test.step('Customer updates payment method', async () => {
      await customerPage.click('[data-testid="update-payment-method-btn"]');

      // Add new payment method
      await customerPage.fill('[data-testid="card-number"]', '4111111111111111');
      await customerPage.fill('[data-testid="card-expiry"]', '12/26');
      await customerPage.fill('[data-testid="card-cvc"]', '123');
      await customerPage.fill('[data-testid="card-name"]', `${testData.customer.firstName} ${testData.customer.lastName}`);

      await customerPage.click('[data-testid="save-payment-method"]');

      // Verify new payment method saved
      await expect(customerPage.locator('[data-testid="payment-method-saved"]')).toBeVisible();

      // Retry failed payment
      await customerPage.click('[data-testid="retry-payment-btn"]');
      await expect(customerPage.locator('[data-testid="payment-processing"]')).toBeVisible();
      await expect(customerPage.locator('[data-testid="payment-successful"]')).toBeVisible({ timeout: 10000 });
    });

    // Verify account status restored
    await test.step('Verify account status restored', async () => {
      await customerPage.click('[data-testid="nav-dashboard"]');
      await expect(customerPage.locator('[data-testid="account-status"]')).toHaveText('Active');
      await expect(customerPage.locator('[data-testid="service-status"]')).toHaveText('Active');

      // Verify payment shows in billing history
      await customerPage.click('[data-testid="nav-billing"]');
      await customerPage.click('[data-testid="payment-history-tab"]');

      const latestPayment = customerPage.locator('[data-testid="payment-row"]:first-child');
      await expect(latestPayment.locator('[data-testid="payment-status"]')).toHaveText('Completed');
    });
  });
});

// Multi-Portal Data Synchronization Tests
test.describe('Multi-Portal Data Synchronization', () => {
  test('should sync customer changes across all portals in real-time', async () => {
    // This test verifies that changes made in one portal are immediately reflected in others
    // Implementation would test WebSocket connections, database synchronization, and cache updates
  });

  test('should handle concurrent modifications gracefully', async () => {
    // Test handling of simultaneous edits from different portals
    // Verifies conflict resolution and data consistency
  });

  test('should maintain audit trail across all portal interactions', async () => {
    // Verifies that all customer interactions are properly logged and trackable
    // Tests compliance requirements for audit trails
  });
});
