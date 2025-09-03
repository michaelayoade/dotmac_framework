/**
 * Real-Time Data Synchronization E2E Tests
 * Tests real-time data sync across portals and services with WebSocket integration
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';

test.describe('Real-Time Data Synchronization', () => {
  test.describe.configure({ mode: 'serial' });

  let adminPage: Page;
  let customerPage: Page;
  let technicianPage: Page;

  test.beforeAll(async ({ browser }) => {
    const adminContext = await browser.newContext();
    const customerContext = await browser.newContext();
    const technicianContext = await browser.newContext();

    adminPage = await adminContext.newPage();
    customerPage = await customerContext.newPage();
    technicianPage = await technicianContext.newPage();

    await setupAuth(adminPage, 'admin');
    await setupAuth(customerPage, 'customer');
    await setupAuth(technicianPage, 'technician');
  });

  test('real-time service status updates', async () => {
    // Test real-time service status propagation across portals

    // Setup WebSocket monitoring
    let adminWebSocketMessages: any[] = [];
    let customerWebSocketMessages: any[] = [];

    adminPage.on('websocket', (ws) => {
      ws.on('framereceived', (event) => {
        try {
          const data = JSON.parse(event.payload);
          adminWebSocketMessages.push(data);
        } catch (e) {
          // Ignore non-JSON messages
        }
      });
    });

    customerPage.on('websocket', (ws) => {
      ws.on('framereceived', (event) => {
        try {
          const data = JSON.parse(event.payload);
          customerWebSocketMessages.push(data);
        } catch (e) {
          // Ignore non-JSON messages
        }
      });
    });

    // Navigate to monitoring pages
    await adminPage.goto('/admin/services/monitoring');
    await customerPage.goto('/customer/dashboard');

    // Wait for WebSocket connections
    await expect(adminPage.locator('[data-testid="websocket-connected"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(customerPage.locator('[data-testid="websocket-connected"]')).toBeVisible({
      timeout: 10000,
    });

    // Simulate service outage from admin side
    await adminPage.fill('[data-testid="service-search"]', 'customer-test-service-001');
    await adminPage.click('[data-testid="search-btn"]');

    const serviceRow = adminPage.locator('[data-testid="service-customer-test-service-001"]');
    await expect(serviceRow).toBeVisible();

    // Trigger maintenance mode
    await serviceRow.click();
    await adminPage.click('[data-testid="maintenance-mode-btn"]');
    await adminPage.fill('[data-testid="maintenance-reason"]', 'Scheduled router firmware update');
    await adminPage.fill('[data-testid="estimated-duration"]', '30');
    await adminPage.click('[data-testid="confirm-maintenance"]');

    // Verify admin sees real-time status change
    await expect(adminPage.locator('[data-testid="service-status"]')).toContainText('Maintenance', {
      timeout: 5000,
    });
    await expect(adminPage.locator('[data-testid="status-indicator"]')).toHaveClass(/maintenance/);

    // Verify customer portal receives real-time update
    await expect(customerPage.locator('[data-testid="service-status-alert"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(customerPage.locator('[data-testid="maintenance-notice"]')).toContainText(
      'scheduled maintenance'
    );
    await expect(customerPage.locator('[data-testid="estimated-completion"]')).toContainText(
      '30 minutes'
    );

    // Verify WebSocket messages were received
    await adminPage.waitForTimeout(2000); // Allow time for messages

    const adminServiceUpdates = adminWebSocketMessages.filter(
      (msg) => msg.type === 'service_status_update' && msg.serviceId === 'customer-test-service-001'
    );
    expect(adminServiceUpdates.length).toBeGreaterThan(0);
    expect(adminServiceUpdates[0].status).toBe('maintenance');

    const customerNotifications = customerWebSocketMessages.filter(
      (msg) => msg.type === 'service_notification' && msg.category === 'maintenance'
    );
    expect(customerNotifications.length).toBeGreaterThan(0);

    // Complete maintenance and verify restoration
    await adminPage.click('[data-testid="complete-maintenance-btn"]');
    await adminPage.fill(
      '[data-testid="completion-notes"]',
      'Firmware update completed successfully'
    );
    await adminPage.click('[data-testid="confirm-completion"]');

    // Verify service restoration
    await expect(adminPage.locator('[data-testid="service-status"]')).toContainText('Active', {
      timeout: 5000,
    });
    await expect(customerPage.locator('[data-testid="service-restored-notice"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(customerPage.locator('[data-testid="service-status-indicator"]')).toHaveClass(
      /active/
    );
  });

  test('real-time ticket updates across portals', async () => {
    // Test real-time ticket status and comment synchronization

    // Customer creates ticket
    await customerPage.goto('/customer/support/tickets/new');
    await customerPage.fill('[data-testid="ticket-subject"]', 'Speed performance degradation');
    await customerPage.selectOption('[data-testid="category"]', 'technical_support');
    await customerPage.fill(
      '[data-testid="description"]',
      'Internet speed has dropped to 50% of advertised speed over the past week'
    );
    await customerPage.click('[data-testid="submit-ticket"]');

    const ticketId = await customerPage.locator('[data-testid="ticket-id"]').textContent();
    await expect(customerPage.locator('[data-testid="ticket-created"]')).toBeVisible();

    // Admin receives ticket in real-time
    await adminPage.goto('/admin/support/dashboard');

    // Verify new ticket appears without refresh
    await expect(adminPage.locator('[data-testid="new-ticket-alert"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(adminPage.locator(`[data-testid="ticket-${ticketId}"]`)).toBeVisible({
      timeout: 5000,
    });

    // Admin adds internal note
    await adminPage.click(`[data-testid="ticket-${ticketId}"]`);
    await adminPage.fill(
      '[data-testid="internal-note"]',
      'Checking line diagnostics - possible signal degradation'
    );
    await adminPage.check('[data-testid="internal-note-flag"]');
    await adminPage.click('[data-testid="add-note"]');

    // Verify internal note doesn't appear to customer
    await customerPage.goto(`/customer/support/tickets/${ticketId}`);
    await expect(customerPage.locator('[data-testid="ticket-updates"]')).not.toContainText(
      'line diagnostics'
    );

    // Admin adds public response
    await adminPage.fill(
      '[data-testid="public-response"]',
      'We have identified the issue and are dispatching a technician to check your connection. Expected resolution within 24 hours.'
    );
    await adminPage.click('[data-testid="send-response"]');

    // Verify customer receives real-time update
    await expect(customerPage.locator('[data-testid="new-response-alert"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(customerPage.locator('[data-testid="latest-response"]')).toContainText(
      'dispatching a technician',
      { timeout: 5000 }
    );

    // Test technician assignment notification
    await adminPage.click('[data-testid="assign-technician"]');
    await adminPage.selectOption('[data-testid="technician-list"]', 'tech-001');
    await adminPage.fill(
      '[data-testid="assignment-notes"]',
      'Check signal strength and line quality at customer premises'
    );
    await adminPage.click('[data-testid="confirm-assignment"]');

    // Verify technician receives assignment
    await technicianPage.goto('/technician/dashboard');
    await expect(technicianPage.locator('[data-testid="new-assignment-alert"]')).toBeVisible({
      timeout: 10000,
    });

    const assignmentCard = technicianPage.locator(`[data-testid="assignment-${ticketId}"]`);
    await expect(assignmentCard).toBeVisible({ timeout: 5000 });
    await expect(assignmentCard).toContainText('Speed performance degradation');

    // Technician updates status
    await assignmentCard.click();
    await technicianPage.selectOption('[data-testid="status-update"]', 'en_route');
    await technicianPage.click('[data-testid="update-status"]');

    // Verify customer receives technician status update
    await expect(customerPage.locator('[data-testid="technician-status"]')).toContainText(
      'en route',
      { timeout: 10000 }
    );
  });

  test('real-time billing and payment sync', async () => {
    // Test real-time billing updates across customer and admin portals

    // Admin processes payment from backend
    await adminPage.goto('/admin/billing/payments');
    await adminPage.fill('[data-testid="customer-search"]', 'billing-test@example.com');
    await adminPage.click('[data-testid="search-customer"]');

    const customerAccount = adminPage.locator('[data-testid="customer-account-0"]');
    await expect(customerAccount).toBeVisible();
    await customerAccount.click();

    // Record manual payment
    await adminPage.click('[data-testid="record-payment"]');
    await adminPage.fill('[data-testid="payment-amount"]', '149.99');
    await adminPage.selectOption('[data-testid="payment-method"]', 'bank_transfer');
    await adminPage.fill('[data-testid="reference-number"]', 'BT20240201001');
    await adminPage.click('[data-testid="confirm-payment"]');

    await expect(adminPage.locator('[data-testid="payment-recorded"]')).toBeVisible();

    // Verify customer portal receives real-time payment confirmation
    await customerPage.goto('/customer/billing/payments');
    await expect(customerPage.locator('[data-testid="payment-confirmation-alert"]')).toBeVisible({
      timeout: 10000,
    });

    const latestPayment = customerPage.locator('[data-testid="payment-0"]');
    await expect(latestPayment).toContainText('$149.99', { timeout: 5000 });
    await expect(latestPayment).toContainText('BT20240201001');
    await expect(latestPayment).toContainText('Processed');

    // Test account balance update
    await expect(customerPage.locator('[data-testid="account-balance"]')).toContainText('$0.00', {
      timeout: 5000,
    });

    // Admin issues credit adjustment
    await adminPage.click('[data-testid="issue-credit"]');
    await adminPage.fill('[data-testid="credit-amount"]', '25.00');
    await adminPage.fill('[data-testid="credit-reason"]', 'Service outage compensation');
    await adminPage.click('[data-testid="apply-credit"]');

    // Verify customer sees credit in real-time
    await expect(customerPage.locator('[data-testid="credit-alert"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(customerPage.locator('[data-testid="account-credit"]')).toContainText('$25.00', {
      timeout: 5000,
    });
    await expect(customerPage.locator('[data-testid="credit-reason"]')).toContainText(
      'Service outage compensation'
    );
  });

  test('real-time network performance monitoring', async () => {
    // Test real-time network metrics synchronization

    // Setup performance monitoring pages
    await adminPage.goto('/admin/network/monitoring');
    await technicianPage.goto('/technician/network/diagnostics');

    // Wait for real-time data connections
    await expect(adminPage.locator('[data-testid="realtime-metrics-active"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(technicianPage.locator('[data-testid="diagnostics-connected"]')).toBeVisible({
      timeout: 10000,
    });

    // Simulate network alert trigger
    await adminPage.click('[data-testid="simulate-alert"]');
    await adminPage.selectOption('[data-testid="alert-type"]', 'latency_spike');
    await adminPage.fill('[data-testid="affected-nodes"]', '10');
    await adminPage.fill('[data-testid="latency-value"]', '250ms');
    await adminPage.click('[data-testid="trigger-alert"]');

    // Verify real-time alert propagation
    await expect(adminPage.locator('[data-testid="network-alert"]')).toBeVisible({ timeout: 5000 });
    await expect(adminPage.locator('[data-testid="alert-severity"]')).toContainText('High');

    // Verify technician receives alert
    await expect(technicianPage.locator('[data-testid="network-alert-notification"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(technicianPage.locator('[data-testid="alert-details"]')).toContainText(
      'latency spike'
    );
    await expect(technicianPage.locator('[data-testid="affected-area"]')).toContainText('10 nodes');

    // Test metrics chart updates
    const metricsChart = adminPage.locator('[data-testid="latency-chart"]');
    await expect(metricsChart).toBeVisible();

    // Wait for chart data update
    await adminPage.waitForTimeout(5000);

    // Verify chart shows spike
    const latencyValue = await adminPage.locator('[data-testid="current-latency"]').textContent();
    expect(latencyValue).toContain('250ms');

    // Test alert resolution
    await adminPage.click('[data-testid="resolve-alert"]');
    await adminPage.fill(
      '[data-testid="resolution-notes"]',
      'Latency normalized after router optimization'
    );
    await adminPage.click('[data-testid="confirm-resolution"]');

    // Verify resolution propagates
    await expect(technicianPage.locator('[data-testid="alert-resolved"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(adminPage.locator('[data-testid="alert-status"]')).toContainText('Resolved');
  });

  test('real-time inventory and equipment tracking', async () => {
    // Test real-time inventory updates across portals

    await adminPage.goto('/admin/inventory/dashboard');
    await technicianPage.goto('/technician/inventory/mobile');

    // Admin updates inventory levels
    await adminPage.fill('[data-testid="equipment-search"]', 'ONT-FIBER-1000');
    await adminPage.click('[data-testid="search-inventory"]');

    const equipmentItem = adminPage.locator('[data-testid="equipment-ONT-FIBER-1000"]');
    await expect(equipmentItem).toBeVisible();

    // Update stock levels
    await equipmentItem.click();
    await adminPage.click('[data-testid="adjust-stock"]');
    await adminPage.fill('[data-testid="adjustment-quantity"]', '-5');
    await adminPage.fill(
      '[data-testid="adjustment-reason"]',
      'Field deployment - technician assignment'
    );
    await adminPage.click('[data-testid="confirm-adjustment"]');

    // Verify technician app reflects change
    await expect(technicianPage.locator('[data-testid="inventory-update-alert"]')).toBeVisible({
      timeout: 10000,
    });

    await technicianPage.fill('[data-testid="equipment-search"]', 'ONT-FIBER-1000');
    const techInventoryItem = technicianPage.locator('[data-testid="equipment-ONT-FIBER-1000"]');
    await expect(techInventoryItem).toBeVisible();

    const updatedQuantity = await techInventoryItem
      .locator('[data-testid="available-quantity"]')
      .textContent();
    expect(Number(updatedQuantity)).toBeGreaterThanOrEqual(0);

    // Technician checks out equipment
    await techInventoryItem.click();
    await technicianPage.click('[data-testid="checkout-equipment"]');
    await technicianPage.fill('[data-testid="checkout-quantity"]', '2');
    await technicianPage.fill('[data-testid="job-reference"]', 'INSTALL-2024-0001');
    await technicianPage.click('[data-testid="confirm-checkout"]');

    // Verify admin sees real-time checkout
    await expect(adminPage.locator('[data-testid="equipment-checkout-alert"]')).toBeVisible({
      timeout: 10000,
    });

    const checkoutLog = adminPage.locator('[data-testid="recent-checkouts"]');
    await expect(checkoutLog).toContainText('ONT-FIBER-1000');
    await expect(checkoutLog).toContainText('INSTALL-2024-0001');
    await expect(checkoutLog).toContainText('2 units');

    // Test low stock alert
    if (Number(updatedQuantity) <= 10) {
      await expect(adminPage.locator('[data-testid="low-stock-alert"]')).toBeVisible({
        timeout: 5000,
      });
      await expect(adminPage.locator('[data-testid="reorder-suggestion"]')).toBeVisible();
    }
  });

  test('real-time workflow execution monitoring', async () => {
    // Test real-time workflow execution status across portals

    await adminPage.goto('/admin/workflows/monitoring');
    await customerPage.goto('/customer/dashboard');

    // Trigger customer workflow
    await customerPage.click('[data-testid="request-service-upgrade"]');
    await customerPage.selectOption('[data-testid="upgrade-plan"]', 'business_premium');
    await customerPage.fill('[data-testid="requested-date"]', '2024-03-01');
    await customerPage.click('[data-testid="submit-upgrade-request"]');

    const workflowId = await customerPage.locator('[data-testid="workflow-id"]').textContent();

    // Verify admin sees workflow in real-time
    await expect(adminPage.locator('[data-testid="new-workflow-alert"]')).toBeVisible({
      timeout: 10000,
    });

    const workflowRow = adminPage.locator(`[data-testid="workflow-${workflowId}"]`);
    await expect(workflowRow).toBeVisible({ timeout: 5000 });
    await expect(workflowRow).toContainText('Service Upgrade Request');

    // Monitor workflow steps in real-time
    const workflowSteps = [
      'customer_eligibility_check',
      'credit_verification',
      'service_availability_check',
      'upgrade_scheduling',
    ];

    await workflowRow.click();
    await expect(adminPage.locator('[data-testid="workflow-details"]')).toBeVisible();

    for (const step of workflowSteps) {
      await expect(adminPage.locator(`[data-testid="step-${step}"]`)).toBeVisible({
        timeout: 15000,
      });
      await expect(adminPage.locator(`[data-testid="step-${step}-status"]`)).toContainText(
        'Completed',
        { timeout: 10000 }
      );

      // Verify customer sees progress updates
      await expect(customerPage.locator(`[data-testid="progress-${step}"]`)).toBeVisible({
        timeout: 5000,
      });
    }

    // Verify workflow completion
    await expect(adminPage.locator('[data-testid="workflow-completed"]')).toBeVisible({
      timeout: 30000,
    });
    await expect(customerPage.locator('[data-testid="upgrade-approved"]')).toBeVisible({
      timeout: 10000,
    });

    const scheduledDate = await customerPage
      .locator('[data-testid="scheduled-upgrade-date"]')
      .textContent();
    expect(scheduledDate).toContain('2024-03-01');
  });

  test.afterAll(async () => {
    await adminPage.context().close();
    await customerPage.context().close();
    await technicianPage.context().close();
  });
});
