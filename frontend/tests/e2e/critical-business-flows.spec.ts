/**
 * Critical Business Flow E2E Tests
 * Tests key business scenarios end-to-end across all portals
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Critical ISP Business Flows', () => {
  test.describe.configure({ mode: 'parallel' });

  // Setup common test data
  const testCredentials = {
    admin: { username: 'admin@dotmac.test', password: 'TestAdmin123!' },
    customer: { username: 'customer@dotmac.test', password: 'TestCustomer123!' },
    reseller: { username: 'reseller@dotmac.test', password: 'TestReseller123!' },
    technician: { username: 'technician@dotmac.test', password: 'TestTech123!' },
  };

  const testCustomer = {
    name: 'Test Customer Corp',
    email: 'test@customer.com',
    phone: '+1-555-0123',
    address: '123 Test Street, Test City, TS 12345',
    serviceType: 'business',
    plan: 'Business Pro 500Mbps',
  };

  test.describe('Customer Lifecycle Management', () => {
    test('complete customer onboarding flow', async ({ page }) => {
      // Step 1: Admin Portal - Customer Creation
      await page.goto('/admin/login');
      await page.fill('[data-testid="email-input"]', testCredentials.admin.username);
      await page.fill('[data-testid="password-input"]', testCredentials.admin.password);
      await page.click('[data-testid="login-button"]');

      await expect(page).toHaveURL(/.*\/admin\/dashboard/);

      // Navigate to customer management
      await page.click('[data-testid="customers-nav"]');
      await page.click('[data-testid="add-customer-button"]');

      // Fill customer details
      await page.fill('[data-testid="customer-name"]', testCustomer.name);
      await page.fill('[data-testid="customer-email"]', testCustomer.email);
      await page.fill('[data-testid="customer-phone"]', testCustomer.phone);
      await page.fill('[data-testid="customer-address"]', testCustomer.address);
      await page.selectOption('[data-testid="service-type"]', testCustomer.serviceType);
      await page.selectOption('[data-testid="service-plan"]', testCustomer.plan);

      await page.click('[data-testid="create-customer-button"]');

      // Verify customer created
      await expect(page.locator('[data-testid="success-message"]')).toContainText('Customer created successfully');
      const customerId = await page.locator('[data-testid="customer-id"]').textContent();
      expect(customerId).toMatch(/CUST-\d{4}/);

      // Step 2: Verify customer can log into portal
      await page.goto('/customer/login');
      await page.fill('[data-testid="email-input"]', testCustomer.email);
      await page.fill('[data-testid="password-input"]', 'TempPassword123!'); // Default temp password
      await page.click('[data-testid="login-button"]');

      // Should be redirected to password change
      await expect(page).toHaveURL(/.*\/customer\/change-password/);
      await page.fill('[data-testid="current-password"]', 'TempPassword123!');
      await page.fill('[data-testid="new-password"]', testCredentials.customer.password);
      await page.fill('[data-testid="confirm-password"]', testCredentials.customer.password);
      await page.click('[data-testid="change-password-button"]');

      // Verify successful login to dashboard
      await expect(page).toHaveURL(/.*\/customer\/dashboard/);
      await expect(page.locator('[data-testid="welcome-message"]')).toContainText(testCustomer.name);
    });

    test('service installation workflow', async ({ page, context }) => {
      // Admin creates work order
      const adminPage = await context.newPage();
      await adminPage.goto('/admin/login');
      await adminPage.fill('[data-testid="email-input"]', testCredentials.admin.username);
      await adminPage.fill('[data-testid="password-input"]', testCredentials.admin.password);
      await adminPage.click('[data-testid="login-button"]');

      await adminPage.click('[data-testid="field-ops-nav"]');
      await adminPage.click('[data-testid="create-work-order"]');

      // Fill work order details
      await adminPage.fill('[data-testid="customer-search"]', testCustomer.email);
      await adminPage.click('[data-testid="customer-result-0"]');
      await adminPage.selectOption('[data-testid="work-order-type"]', 'installation');
      await adminPage.fill('[data-testid="installation-address"]', testCustomer.address);
      await adminPage.fill('[data-testid="scheduled-date"]', '2024-09-15');
      await adminPage.fill('[data-testid="scheduled-time"]', '10:00');

      await adminPage.click('[data-testid="create-work-order-button"]');

      const workOrderId = await adminPage.locator('[data-testid="work-order-id"]').textContent();
      expect(workOrderId).toMatch(/WO-\d{6}/);

      // Technician receives and completes work order
      const techPage = await context.newPage();
      await techPage.goto('/technician/login');
      await techPage.fill('[data-testid="email-input"]', testCredentials.technician.username);
      await techPage.fill('[data-testid="password-input"]', testCredentials.technician.password);
      await techPage.click('[data-testid="login-button"]');

      // Check work order appears in schedule
      await expect(techPage.locator(`[data-testid="work-order-${workOrderId}"]`)).toBeVisible();
      await techPage.click(`[data-testid="work-order-${workOrderId}"]`);

      // Start work order
      await techPage.click('[data-testid="start-work-button"]');
      await expect(techPage.locator('[data-testid="work-status"]')).toContainText('In Progress');

      // Complete installation steps
      await techPage.check('[data-testid="equipment-installed"]');
      await techPage.check('[data-testid="service-activated"]');
      await techPage.check('[data-testid="customer-trained"]');
      await techPage.fill('[data-testid="completion-notes"]', 'Installation completed successfully. Customer trained on equipment usage.');

      // Upload completion photo
      await techPage.setInputFiles('[data-testid="completion-photo"]', 'test-fixtures/installation-complete.jpg');

      await techPage.click('[data-testid="complete-work-order"]');

      // Verify completion
      await expect(techPage.locator('[data-testid="work-status"]')).toContainText('Completed');

      // Customer receives service activation notification
      const customerPage = await context.newPage();
      await customerPage.goto('/customer/login');
      await customerPage.fill('[data-testid="email-input"]', testCustomer.email);
      await customerPage.fill('[data-testid="password-input"]', testCredentials.customer.password);
      await customerPage.click('[data-testid="login-button"]');

      // Check service is now active
      await expect(customerPage.locator('[data-testid="service-status"]')).toContainText('Active');
      await expect(customerPage.locator('[data-testid="current-plan"]')).toContainText(testCustomer.plan);
    });
  });

  test.describe('Billing and Payment Processing', () => {
    test('invoice generation and payment flow', async ({ page, context }) => {
      // Admin generates invoice
      await page.goto('/admin/login');
      await page.fill('[data-testid="email-input"]', testCredentials.admin.username);
      await page.fill('[data-testid="password-input"]', testCredentials.admin.password);
      await page.click('[data-testid="login-button"]');

      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="generate-invoices"]');

      // Select customers for invoicing
      await page.check('[data-testid="select-all-customers"]');
      await page.selectOption('[data-testid="billing-period"]', '2024-09');
      await page.click('[data-testid="generate-button"]');

      // Wait for invoice generation
      await expect(page.locator('[data-testid="generation-status"]')).toContainText('Completed');
      const invoiceCount = await page.locator('[data-testid="invoice-count"]').textContent();
      expect(parseInt(invoiceCount || '0')).toBeGreaterThan(0);

      // Customer views and pays invoice
      const customerPage = await context.newPage();
      await customerPage.goto('/customer/login');
      await customerPage.fill('[data-testid="email-input"]', testCustomer.email);
      await customerPage.fill('[data-testid="password-input"]', testCredentials.customer.password);
      await customerPage.click('[data-testid="login-button"]');

      await customerPage.click('[data-testid="billing-nav"]');

      // Check pending invoice appears
      await expect(customerPage.locator('[data-testid="pending-invoice"]')).toBeVisible();
      await customerPage.click('[data-testid="view-invoice"]');

      // Verify invoice details
      await expect(customerPage.locator('[data-testid="invoice-amount"]')).toContainText('$');
      await expect(customerPage.locator('[data-testid="due-date"]')).toBeVisible();

      // Make payment
      await customerPage.click('[data-testid="pay-now-button"]');

      // Fill payment details (mock payment gateway)
      await customerPage.fill('[data-testid="card-number"]', '4111111111111111');
      await customerPage.fill('[data-testid="expiry-date"]', '12/25');
      await customerPage.fill('[data-testid="cvv"]', '123');
      await customerPage.fill('[data-testid="cardholder-name"]', 'Test Customer');

      await customerPage.click('[data-testid="submit-payment"]');

      // Verify payment success
      await expect(customerPage.locator('[data-testid="payment-success"]')).toContainText('Payment processed successfully');
      await expect(customerPage.locator('[data-testid="invoice-status"]')).toContainText('Paid');
    });

    test('commission calculation for resellers', async ({ page }) => {
      // Reseller portal commission verification
      await page.goto('/reseller/login');
      await page.fill('[data-testid="email-input"]', testCredentials.reseller.username);
      await page.fill('[data-testid="password-input"]', testCredentials.reseller.password);
      await page.click('[data-testid="login-button"]');

      await page.click('[data-testid="commissions-nav"]');

      // Check current month commissions
      await expect(page.locator('[data-testid="current-month-commission"]')).toBeVisible();
      const commissionAmount = await page.locator('[data-testid="commission-amount"]').textContent();
      expect(commissionAmount).toMatch(/^\$\d+\.\d{2}$/);

      // View commission breakdown
      await page.click('[data-testid="view-breakdown"]');

      // Verify commission tiers and calculations
      await expect(page.locator('[data-testid="commission-tier"]')).toBeVisible();
      await expect(page.locator('[data-testid="base-rate"]')).toContainText('%');
      await expect(page.locator('[data-testid="revenue-total"]')).toContainText('$');

      // Check individual customer commissions
      const customerCommissions = page.locator('[data-testid^="customer-commission-"]');
      const count = await customerCommissions.count();
      expect(count).toBeGreaterThan(0);

      // Verify commission audit trail
      await page.click('[data-testid="audit-trail"]');
      await expect(page.locator('[data-testid="audit-entry"]')).toBeVisible();
    });
  });

  test.describe('Network Operations and Monitoring', () => {
    test('network issue detection and resolution', async ({ page, context }) => {
      // Admin monitoring dashboard detects issue
      await page.goto('/admin/login');
      await page.fill('[data-testid="email-input"]', testCredentials.admin.username);
      await page.fill('[data-testid="password-input"]', testCredentials.admin.password);
      await page.click('[data-testid="login-button"]');

      await page.click('[data-testid="monitoring-nav"]');

      // Check network status dashboard
      await expect(page.locator('[data-testid="network-status"]')).toBeVisible();

      // Simulate network alert
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('network-alert', {
          detail: {
            type: 'latency_high',
            severity: 'warning',
            affected_customers: 25,
            location: 'North District Tower',
            metric_value: 250,
            threshold: 200,
          }
        }));
      });

      // Verify alert appears
      await expect(page.locator('[data-testid="network-alert"]')).toBeVisible();
      await expect(page.locator('[data-testid="alert-severity"]')).toContainText('warning');

      // Create maintenance ticket
      await page.click('[data-testid="create-maintenance-ticket"]');
      await page.fill('[data-testid="ticket-title"]', 'High Latency - North District Tower');
      await page.fill('[data-testid="ticket-description"]', 'Network latency exceeding 250ms threshold');
      await page.selectOption('[data-testid="priority"]', 'high');
      await page.selectOption('[data-testid="assign-technician"]', testCredentials.technician.username);

      await page.click('[data-testid="create-ticket-button"]');

      // Technician receives and addresses issue
      const techPage = await context.newPage();
      await techPage.goto('/technician/login');
      await techPage.fill('[data-testid="email-input"]', testCredentials.technician.username);
      await techPage.fill('[data-testid="password-input"]', testCredentials.technician.password);
      await techPage.click('[data-testid="login-button"]');

      // Check ticket appears in assignments
      await expect(techPage.locator('[data-testid="maintenance-ticket"]')).toBeVisible();
      await techPage.click('[data-testid="accept-ticket"]');

      // Update ticket with resolution
      await techPage.fill('[data-testid="resolution-notes"]', 'Resolved: Updated router configuration and optimized traffic routing');
      await techPage.selectOption('[data-testid="resolution-status"]', 'resolved');
      await techPage.click('[data-testid="update-ticket"]');

      // Verify resolution in admin portal
      await page.reload();
      await expect(page.locator('[data-testid="alert-status"]')).toContainText('Resolved');
    });

    test('customer support ticket escalation', async ({ page, context }) => {
      // Customer creates support ticket
      const customerPage = await context.newPage();
      await customerPage.goto('/customer/login');
      await customerPage.fill('[data-testid="email-input"]', testCustomer.email);
      await customerPage.fill('[data-testid="password-input"]', testCredentials.customer.password);
      await customerPage.click('[data-testid="login-button"]');

      await customerPage.click('[data-testid="support-nav"]');
      await customerPage.click('[data-testid="create-ticket"]');

      await customerPage.fill('[data-testid="ticket-subject"]', 'Intermittent Connection Issues');
      await customerPage.fill('[data-testid="ticket-description"]', 'Internet connection drops frequently during peak hours');
      await customerPage.selectOption('[data-testid="ticket-category"]', 'technical');
      await customerPage.selectOption('[data-testid="priority"]', 'medium');

      await customerPage.click('[data-testid="submit-ticket"]');

      const ticketId = await customerPage.locator('[data-testid="ticket-id"]').textContent();
      expect(ticketId).toMatch(/TKT-\d{6}/);

      // Admin reviews and escalates ticket
      await page.goto('/admin/helpdesk');
      await expect(page.locator(`[data-testid="ticket-${ticketId}"]`)).toBeVisible();
      await page.click(`[data-testid="ticket-${ticketId}"]`);

      // Review ticket details
      await expect(page.locator('[data-testid="ticket-subject"]')).toContainText('Intermittent Connection Issues');
      await expect(page.locator('[data-testid="ticket-priority"]')).toContainText('medium');

      // Escalate to technical team
      await page.click('[data-testid="escalate-ticket"]');
      await page.selectOption('[data-testid="escalate-to"]', 'technical');
      await page.fill('[data-testid="escalation-notes"]', 'Customer reporting connection drops during peak hours. Requires network analysis.');
      await page.click('[data-testid="confirm-escalation"]');

      // Verify escalation
      await expect(page.locator('[data-testid="ticket-status"]')).toContainText('Escalated');
      await expect(page.locator('[data-testid="assigned-team"]')).toContainText('Technical');
    });
  });

  test.describe('Performance and Load Testing', () => {
    test('dashboard performance under load', async ({ page }) => {
      await page.goto('/admin/login');
      await page.fill('[data-testid="email-input"]', testCredentials.admin.username);
      await page.fill('[data-testid="password-input"]', testCredentials.admin.password);
      await page.click('[data-testid="login-button"]');

      // Measure dashboard load time
      const startTime = Date.now();
      await page.waitForLoadState('networkidle');
      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(3000); // Should load within 3 seconds

      // Test rapid navigation between sections
      const navigationTests = [
        '[data-testid="dashboard-nav"]',
        '[data-testid="customers-nav"]',
        '[data-testid="billing-nav"]',
        '[data-testid="monitoring-nav"]',
        '[data-testid="reports-nav"]',
      ];

      for (const nav of navigationTests) {
        const navStartTime = Date.now();
        await page.click(nav);
        await page.waitForLoadState('networkidle');
        const navLoadTime = Date.now() - navStartTime;
        
        expect(navLoadTime).toBeLessThan(2000); // Each section should load within 2 seconds
      }
    });

    test('concurrent user sessions', async ({ browser }) => {
      // Simulate multiple concurrent users
      const contexts = await Promise.all([
        browser.newContext(),
        browser.newContext(),
        browser.newContext(),
        browser.newContext(),
      ]);

      const sessions = [
        { context: contexts[0], credentials: testCredentials.admin, portal: 'admin' },
        { context: contexts[1], credentials: testCredentials.customer, portal: 'customer' },
        { context: contexts[2], credentials: testCredentials.reseller, portal: 'reseller' },
        { context: contexts[3], credentials: testCredentials.technician, portal: 'technician' },
      ];

      // Login all users concurrently
      await Promise.all(sessions.map(async ({ context, credentials, portal }) => {
        const page = await context.newPage();
        await page.goto(`/${portal}/login`);
        await page.fill('[data-testid="email-input"]', credentials.username);
        await page.fill('[data-testid="password-input"]', credentials.password);
        await page.click('[data-testid="login-button"]');
        await expect(page).toHaveURL(new RegExp(`.*/${portal}/dashboard`));
      }));

      // Cleanup
      await Promise.all(contexts.map(context => context.close()));
    });
  });

  test.describe('Data Integrity and Validation', () => {
    test('cross-portal data consistency', async ({ page, context }) => {
      // Create customer in admin portal
      await page.goto('/admin/login');
      await page.fill('[data-testid="email-input"]', testCredentials.admin.username);
      await page.fill('[data-testid="password-input"]', testCredentials.admin.password);
      await page.click('[data-testid="login-button"]');

      await page.click('[data-testid="customers-nav"]');
      await page.click('[data-testid="add-customer-button"]');

      const testCustomer2 = {
        name: 'Data Consistency Test Customer',
        email: 'consistency@test.com',
        phone: '+1-555-0199',
        plan: 'Residential Premium 200Mbps',
      };

      await page.fill('[data-testid="customer-name"]', testCustomer2.name);
      await page.fill('[data-testid="customer-email"]', testCustomer2.email);
      await page.fill('[data-testid="customer-phone"]', testCustomer2.phone);
      await page.selectOption('[data-testid="service-plan"]', testCustomer2.plan);

      await page.click('[data-testid="create-customer-button"]');
      const customerId = await page.locator('[data-testid="customer-id"]').textContent();

      // Verify customer appears in reseller portal (if within reseller territory)
      const resellerPage = await context.newPage();
      await resellerPage.goto('/reseller/login');
      await resellerPage.fill('[data-testid="email-input"]', testCredentials.reseller.username);
      await resellerPage.fill('[data-testid="password-input"]', testCredentials.reseller.password);
      await resellerPage.click('[data-testid="login-button"]');

      await resellerPage.click('[data-testid="customers-nav"]');
      
      // Search for the customer
      await resellerPage.fill('[data-testid="customer-search"]', testCustomer2.email);
      await expect(resellerPage.locator(`[data-testid="customer-${customerId}"]`)).toBeVisible();

      // Verify customer data matches
      await resellerPage.click(`[data-testid="customer-${customerId}"]`);
      await expect(resellerPage.locator('[data-testid="customer-name"]')).toContainText(testCustomer2.name);
      await expect(resellerPage.locator('[data-testid="customer-plan"]')).toContainText(testCustomer2.plan);
    });

    test('billing calculation accuracy', async ({ page }) => {
      await page.goto('/admin/login');
      await page.fill('[data-testid="email-input"]', testCredentials.admin.username);
      await page.fill('[data-testid="password-input"]', testCredentials.admin.password);
      await page.click('[data-testid="login-button"]');

      await page.click('[data-testid="billing-nav"]');
      await page.click('[data-testid="billing-reports"]');

      // Verify revenue calculations
      const totalRevenue = await page.locator('[data-testid="total-revenue"]').textContent();
      const customerCount = await page.locator('[data-testid="active-customers"]').textContent();
      const averageRevenue = await page.locator('[data-testid="average-revenue"]').textContent();

      // Verify mathematical consistency
      const total = parseFloat(totalRevenue?.replace(/[$,]/g, '') || '0');
      const count = parseInt(customerCount || '0');
      const average = parseFloat(averageRevenue?.replace(/[$,]/g, '') || '0');

      if (count > 0) {
        const expectedAverage = total / count;
        expect(Math.abs(average - expectedAverage)).toBeLessThan(0.01); // Allow 1 cent rounding difference
      }
    });
  });
});