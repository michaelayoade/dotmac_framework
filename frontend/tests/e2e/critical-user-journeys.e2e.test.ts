/**
 * Critical User Journey E2E Tests
 * Tests complete user workflows across all portals
 */

import { test, expect } from '@playwright/test';
import { UserJourneyHelper } from '../utils/user-journey-helper';
import { DataFactory } from '../utils/data-factory';

test.describe('Critical User Journeys', () => {
  let journeyHelper: UserJourneyHelper;
  let dataFactory: DataFactory;

  test.beforeAll(async () => {
    journeyHelper = new UserJourneyHelper();
    dataFactory = new DataFactory();
  });

  test.describe('ISP Customer Onboarding Journey', () => {
    test('Complete customer signup and activation', async ({ page }) => {
      // Generate test customer data
      const customerData = dataFactory.generateCustomerData();

      // Step 1: Customer visits landing page
      await page.goto('/customer/signup');
      await expect(page.locator('h1')).toContainText('Get Started');

      // Step 2: Fill out signup form
      await page.fill('[data-testid="email"]', customerData.email);
      await page.fill('[data-testid="company-name"]', customerData.companyName);
      await page.fill('[data-testid="phone"]', customerData.phone);
      await page.selectOption('[data-testid="plan"]', customerData.plan);
      await page.click('[data-testid="signup-submit"]');

      // Step 3: Verify email
      await expect(page.locator('.success-message')).toContainText('Check your email');
      const verificationLink = await journeyHelper.getEmailVerificationLink(customerData.email);
      await page.goto(verificationLink);

      // Step 4: Complete profile setup
      await page.fill('[data-testid="address"]', customerData.address);
      await page.fill('[data-testid="city"]', customerData.city);
      await page.selectOption('[data-testid="state"]', customerData.state);
      await page.fill('[data-testid="zip"]', customerData.zipCode);
      await page.click('[data-testid="profile-complete"]');

      // Step 5: Service activation
      await expect(page.locator('.dashboard')).toBeVisible();
      await expect(page.locator('[data-testid="service-status"]')).toContainText('Active');

      // Step 6: Initial login test
      await page.click('[data-testid="logout"]');
      await page.fill('[data-testid="login-email"]', customerData.email);
      await page.fill('[data-testid="login-password"]', customerData.password);
      await page.click('[data-testid="login-submit"]');

      await expect(page.locator('.dashboard')).toBeVisible();
    });

    test('Customer billing setup and payment', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();

      // Login as customer
      await journeyHelper.customerLogin(page, customer);

      // Navigate to billing
      await page.click('[data-testid="billing-nav"]');

      // Add payment method
      await page.click('[data-testid="add-payment-method"]');
      await page.fill('[data-testid="card-number"]', '4242424242424242');
      await page.fill('[data-testid="expiry"]', '12/25');
      await page.fill('[data-testid="cvc"]', '123');
      await page.fill('[data-testid="name"]', customer.name);
      await page.click('[data-testid="save-card"]');

      // Verify payment method added
      await expect(page.locator('[data-testid="payment-methods"]')).toContainText('****4242');

      // Check invoice generation
      await page.click('[data-testid="invoices-tab"]');
      await expect(page.locator('[data-testid="invoice-list"]')).toBeVisible();

      // Test payment
      await page.click('[data-testid="pay-invoice"]');
      await expect(page.locator('.payment-success')).toBeVisible();
    });
  });

  test.describe('Admin User Management Journey', () => {
    test('Admin creates and manages users', async ({ page }) => {
      const admin = await journeyHelper.createTestAdmin();

      // Login as admin
      await journeyHelper.adminLogin(page, admin);

      // Navigate to user management
      await page.click('[data-testid="admin-nav"]');
      await page.click('[data-testid="users-section"]');

      // Create new user
      await page.click('[data-testid="create-user"]');
      const userData = dataFactory.generateUserData();
      await page.fill('[data-testid="user-email"]', userData.email);
      await page.fill('[data-testid="user-name"]', userData.name);
      await page.selectOption('[data-testid="user-role"]', userData.role);
      await page.click('[data-testid="save-user"]');

      // Verify user created
      await expect(page.locator('[data-testid="user-list"]')).toContainText(userData.email);

      // Edit user permissions
      await page.click(`[data-testid="edit-user-${userData.email}"]`);
      await page.check('[data-testid="permission-read"]');
      await page.check('[data-testid="permission-write"]');
      await page.click('[data-testid="update-permissions"]');

      // Test user login
      await page.click('[data-testid="logout"]');
      await journeyHelper.userLogin(page, userData);
      await expect(page.locator('.dashboard')).toBeVisible();
    });

    test('Admin configures tenant settings', async ({ page }) => {
      const admin = await journeyHelper.createTestAdmin();

      await journeyHelper.adminLogin(page, admin);

      // Navigate to tenant settings
      await page.click('[data-testid="tenant-settings"]');

      // Update branding
      await page.fill('[data-testid="tenant-name"]', 'Updated Company Name');
      await page.fill('[data-testid="support-email"]', 'support@updated.com');
      await page.setInputFiles('[data-testid="logo-upload"]', 'test-logo.png');
      await page.click('[data-testid="save-branding"]');

      // Configure security settings
      await page.click('[data-testid="security-tab"]');
      await page.check('[data-testid="enable-2fa"]');
      await page.selectOption('[data-testid="session-timeout"]', '480'); // 8 hours
      await page.click('[data-testid="save-security"]');

      // Test settings persistence
      await page.reload();
      await expect(page.locator('[data-testid="tenant-name"]')).toHaveValue('Updated Company Name');
    });
  });

  test.describe('Network Management Journey', () => {
    test('Admin manages network devices', async ({ page }) => {
      const admin = await journeyHelper.createTestAdmin();

      await journeyHelper.adminLogin(page, admin);

      // Navigate to network management
      await page.click('[data-testid="network-nav"]');
      await page.click('[data-testid="devices-section"]');

      // Add new device
      await page.click('[data-testid="add-device"]');
      const deviceData = dataFactory.generateDeviceData();
      await page.fill('[data-testid="device-name"]', deviceData.name);
      await page.fill('[data-testid="device-ip"]', deviceData.ip);
      await page.selectOption('[data-testid="device-type"]', deviceData.type);
      await page.fill('[data-testid="device-location"]', deviceData.location);
      await page.click('[data-testid="save-device"]');

      // Verify device added
      await expect(page.locator('[data-testid="device-list"]')).toContainText(deviceData.name);

      // Test device monitoring
      await page.click(`[data-testid="monitor-device-${deviceData.name}"]`);
      await expect(page.locator('[data-testid="device-metrics"]')).toBeVisible();
      await expect(page.locator('[data-testid="uptime-chart"]')).toBeVisible();

      // Configure alerts
      await page.click('[data-testid="alerts-config"]');
      await page.check('[data-testid="alert-offline"]');
      await page.check('[data-testid="alert-high-usage"]');
      await page.fill('[data-testid="alert-threshold"]', '90');
      await page.click('[data-testid="save-alerts"]');
    });

    test('Real-time network monitoring', async ({ page }) => {
      const admin = await journeyHelper.createTestAdmin();

      await journeyHelper.adminLogin(page, admin);

      // Navigate to network dashboard
      await page.click('[data-testid="network-dashboard"]');

      // Verify real-time updates
      await expect(page.locator('[data-testid="live-devices"]')).toBeVisible();
      await expect(page.locator('[data-testid="network-topology"]')).toBeVisible();

      // Test device status updates (simulate real-time)
      const initialStatus = await page.locator('[data-testid="device-status"]').first().textContent();

      // Wait for potential status update (in real scenario, this would be WebSocket driven)
      await page.waitForTimeout(2000);

      // Verify monitoring data is current
      await expect(page.locator('[data-testid="last-updated"]')).toBeVisible();
      await expect(page.locator('[data-testid="bandwidth-chart"]')).toBeVisible();
    });
  });

  test.describe('Support Ticket Journey', () => {
    test('Customer creates and tracks support ticket', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();

      await journeyHelper.customerLogin(page, customer);

      // Navigate to support
      await page.click('[data-testid="support-nav"]');

      // Create new ticket
      await page.click('[data-testid="create-ticket"]');
      await page.selectOption('[data-testid="ticket-category"]', 'technical');
      await page.selectOption('[data-testid="ticket-priority"]', 'medium');
      await page.fill('[data-testid="ticket-subject"]', 'Internet connectivity issue');
      await page.fill('[data-testid="ticket-description"]', 'Unable to access internet for the past 2 hours');
      await page.setInputFiles('[data-testid="ticket-attachments"]', 'network-logs.txt');
      await page.click('[data-testid="submit-ticket"]');

      // Verify ticket created
      await expect(page.locator('.ticket-success')).toContainText('Ticket created successfully');

      // Navigate to ticket list
      await page.click('[data-testid="my-tickets"]');
      await expect(page.locator('[data-testid="ticket-list"]')).toContainText('Internet connectivity issue');

      // View ticket details
      await page.click('[data-testid="ticket-item"]').first();
      await expect(page.locator('[data-testid="ticket-status"]')).toContainText('Open');
      await expect(page.locator('[data-testid="ticket-priority"]')).toContainText('Medium');
    });

    test('Admin processes support ticket', async ({ page }) => {
      const admin = await journeyHelper.createTestAdmin();
      const ticket = await journeyHelper.createTestTicket();

      await journeyHelper.adminLogin(page, admin);

      // Navigate to support tickets
      await page.click('[data-testid="admin-nav"]');
      await page.click('[data-testid="support-tickets"]');

      // Find and open ticket
      await page.fill('[data-testid="ticket-search"]', ticket.id);
      await page.click('[data-testid="search-submit"]');
      await page.click(`[data-testid="ticket-${ticket.id}"]`);

      // Add response
      await page.fill('[data-testid="ticket-response"]', 'We are investigating the connectivity issue. Please try restarting your router.');
      await page.selectOption('[data-testid="ticket-status"]', 'in-progress');
      await page.click('[data-testid="send-response"]');

      // Verify response added
      await expect(page.locator('[data-testid="ticket-responses"]')).toContainText('We are investigating');

      // Update ticket status
      await page.selectOption('[data-testid="ticket-status"]', 'resolved');
      await page.click('[data-testid="update-status"]');

      // Verify status update
      await expect(page.locator('[data-testid="ticket-status"]')).toContainText('Resolved');
    });
  });

  test.describe('Billing and Payment Journey', () => {
    test('Customer views and pays invoice', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      const invoice = await journeyHelper.createTestInvoice(customer);

      await journeyHelper.customerLogin(page, customer);

      // Navigate to billing
      await page.click('[data-testid="billing-nav"]');

      // View invoices
      await page.click('[data-testid="invoices-tab"]');
      await expect(page.locator('[data-testid="invoice-list"]')).toContainText(invoice.id);

      // Open invoice details
      await page.click(`[data-testid="invoice-${invoice.id}"]`);
      await expect(page.locator('[data-testid="invoice-amount"]')).toContainText(invoice.amount);
      await expect(page.locator('[data-testid="invoice-status"]')).toContainText('Unpaid');

      // Make payment
      await page.click('[data-testid="pay-now"]');
      await page.fill('[data-testid="card-number"]', '4242424242424242');
      await page.fill('[data-testid="expiry"]', '12/25');
      await page.fill('[data-testid="cvc"]', '123');
      await page.click('[data-testid="complete-payment"]');

      // Verify payment success
      await expect(page.locator('.payment-success')).toContainText('Payment successful');
      await expect(page.locator('[data-testid="invoice-status"]')).toContainText('Paid');
    });

    test('Admin manages billing and subscriptions', async ({ page }) => {
      const admin = await journeyHelper.createTestAdmin();
      const customer = await journeyHelper.createTestCustomer();

      await journeyHelper.adminLogin(page, admin);

      // Navigate to billing management
      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="customer-billing"]');

      // Search for customer
      await page.fill('[data-testid="customer-search"]', customer.email);
      await page.click('[data-testid="search-customer"]');

      // View customer billing
      await page.click(`[data-testid="customer-${customer.id}"]`);
      await expect(page.locator('[data-testid="billing-history"]')).toBeVisible();

      // Modify subscription
      await page.click('[data-testid="modify-subscription"]');
      await page.selectOption('[data-testid="new-plan"]', 'professional');
      await page.click('[data-testid="apply-changes"]');

      // Verify plan change
      await expect(page.locator('[data-testid="current-plan"]')).toContainText('Professional');

      // Generate invoice
      await page.click('[data-testid="generate-invoice"]');
      await expect(page.locator('.invoice-generated')).toContainText('Invoice created');
    });
  });

  test.describe('Cross-Portal Data Synchronization', () => {
    test('Data consistency across portals', async ({ page, context }) => {
      const customer = await journeyHelper.createTestCustomer();

      // Open multiple portal tabs
      const adminPage = await context.newPage();
      const customerPage = await context.newPage();

      // Admin creates customer record
      await journeyHelper.adminLogin(adminPage, await journeyHelper.createTestAdmin());
      await adminPage.click('[data-testid="customers-nav"]');
      await adminPage.fill('[data-testid="customer-search"]', customer.email);
      await adminPage.click('[data-testid="edit-customer"]');
      await adminPage.fill('[data-testid="customer-notes"]', 'VIP customer');
      await adminPage.click('[data-testid="save-customer"]');

      // Customer logs in and checks profile
      await journeyHelper.customerLogin(customerPage, customer);
      await customerPage.click('[data-testid="profile-nav"]');
      await customerPage.reload(); // Force refresh to test data sync

      // Verify data consistency (this would test real-time sync in production)
      await expect(customerPage.locator('[data-testid="profile-info"]')).toContainText(customer.email);

      await adminPage.close();
      await customerPage.close();
    });
  });

  test.describe('Error Handling and Recovery', () => {
    test('Graceful error handling for network failures', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();

      await journeyHelper.customerLogin(page, customer);

      // Simulate network failure
      await page.route('**/api/**', route => route.abort());
      await page.reload();

      // Verify error handling
      await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();

      // Test recovery
      await page.unroute('**/api/**');
      await page.click('[data-testid="retry-button"]');
      await expect(page.locator('.dashboard')).toBeVisible();
    });

    test('Form validation and error messages', async ({ page }) => {
      await page.goto('/customer/signup');

      // Submit empty form
      await page.click('[data-testid="signup-submit"]');

      // Verify validation messages
      await expect(page.locator('[data-testid="email-error"]')).toContainText('Email is required');
      await expect(page.locator('[data-testid="company-error"]')).toContainText('Company name is required');

      // Fill invalid data
      await page.fill('[data-testid="email"]', 'invalid-email');
      await page.click('[data-testid="signup-submit"]');

      // Verify format validation
      await expect(page.locator('[data-testid="email-error"]')).toContainText('Invalid email format');
    });
  });
});
