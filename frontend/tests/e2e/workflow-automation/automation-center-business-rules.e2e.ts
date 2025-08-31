/**
 * Automation Center E2E Tests
 * Tests complete business rule management and execution workflows
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';

test.describe('Automation Center - ISP Business Rules Management', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'admin');
    await page.goto('/admin/automation-center');
    
    // Wait for automation center to load
    await expect(page.locator('[data-testid="automation-center"]')).toBeVisible();
  });

  test('should create and execute service activation automation rule', async ({ page }) => {
    // Navigate to rules tab
    await page.click('[data-testid="rules-tab"]');
    await expect(page.locator('[data-testid="rules-table"]')).toBeVisible();
    
    // Create new rule using service activation template
    await page.click('[data-testid="new-rule-btn"]');
    await page.click('[data-testid="template-service-activation"]');
    
    // Verify template loaded with pre-configured settings
    await expect(page.locator('[data-testid="rule-name"]')).toHaveValue('Service Activation Rule');
    await expect(page.locator('[data-testid="rule-description"]')).toContainText('Automate service activation');
    
    // Customize rule name
    await page.fill('[data-testid="rule-name"]', 'ISP Internet Service Auto-Activation');
    await page.fill('[data-testid="rule-description"]', 'Automatically activate internet service when payment is confirmed and credit check passes');
    
    // Configure conditions
    await expect(page.locator('[data-testid="condition-0"]')).toBeVisible();
    
    // Verify payment status condition
    await expect(page.locator('[data-testid="condition-field-0"]')).toHaveValue('payment.status');
    await expect(page.locator('[data-testid="condition-operator-0"]')).toHaveValue('equals');
    await expect(page.locator('[data-testid="condition-value-0"]')).toHaveValue('completed');
    
    // Add additional condition for credit score
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-1"]', 'customer.credit_score');
    await page.selectOption('[data-testid="condition-operator-1"]', 'greater_than');
    await page.fill('[data-testid="condition-value-1"]', '650');
    
    // Add condition for service type
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-2"]', 'service.type');
    await page.selectOption('[data-testid="condition-operator-2"]', 'in');
    await page.fill('[data-testid="condition-value-2"]', 'internet,internet_phone');
    
    // Configure condition logic
    await page.selectOption('[data-testid="condition-logic"]', 'all');
    
    // Configure actions
    await expect(page.locator('[data-testid="action-0"]')).toBeVisible();
    
    // Verify activate service action
    await expect(page.locator('[data-testid="action-type-0"]')).toHaveValue('activate_service');
    await page.check('[data-testid="action-notify-customer-0"]');
    
    // Add notification action
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-1"]', 'send_notification');
    await page.selectOption('[data-testid="notification-template-1"]', 'service_activated');
    await page.selectOption('[data-testid="notification-recipients-1"]', 'customer');
    
    // Add task creation action for equipment setup
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-2"]', 'create_task');
    await page.fill('[data-testid="task-title-2"]', 'Schedule Equipment Installation');
    await page.selectOption('[data-testid="task-priority-2"]', 'high');
    await page.selectOption('[data-testid="task-assignee-2"]', 'field_technician');
    
    // Set rule priority and scope
    await page.fill('[data-testid="rule-priority"]', '100');
    await page.check('[data-testid="portal-scope-admin"]');
    await page.check('[data-testid="portal-scope-customer"]');
    
    // Save rule
    await page.click('[data-testid="save-rule-btn"]');
    await expect(page.locator('[data-testid="save-success"]')).toContainText('Rule saved successfully');
    
    // Activate rule
    await page.click('[data-testid="activate-rule-btn"]');
    await expect(page.locator('[data-testid="rule-status"]')).toContainText('active');
    
    // Test rule execution
    await page.click('[data-testid="test-rules-btn"]');
    
    // Configure test context
    await page.fill('[data-testid="test-context-payment-status"]', 'completed');
    await page.fill('[data-testid="test-context-customer-credit-score"]', '700');
    await page.selectOption('[data-testid="test-context-service-type"]', 'internet');
    await page.fill('[data-testid="test-context-customer-id"]', 'CUST-TEST-001');
    
    // Execute test
    await page.click('[data-testid="run-test-btn"]');
    
    // Verify test results
    await page.click('[data-testid="execution-tab"]');
    await expect(page.locator('[data-testid="execution-result"]')).toBeVisible();
    
    const executionResult = page.locator('[data-testid="execution-result-0"]');
    await expect(executionResult).toContainText('ISP Internet Service Auto-Activation');
    await expect(executionResult.locator('[data-testid="rule-matched"]')).toContainText('true');
    await expect(executionResult.locator('[data-testid="conditions-passed"]')).toContainText('3');
    await expect(executionResult.locator('[data-testid="actions-executed"]')).toContainText('3');
    
    // Verify specific actions were executed
    await page.click('[data-testid="view-execution-details"]');
    
    const actionResults = page.locator('[data-testid="action-result"]');
    await expect(actionResults.nth(0)).toContainText('activate_service: Success');
    await expect(actionResults.nth(1)).toContainText('send_notification: Sent to customer');
    await expect(actionResults.nth(2)).toContainText('create_task: Task created for field_technician');
  });

  test('should handle payment overdue escalation workflow', async ({ page }) => {
    // Create payment overdue escalation rule
    await page.click('[data-testid="rules-tab"]');
    await page.click('[data-testid="new-rule-btn"]');
    await page.click('[data-testid="template-payment-overdue"]');
    
    // Customize rule
    await page.fill('[data-testid="rule-name"]', 'Payment Overdue Auto-Escalation');
    await page.fill('[data-testid="rule-description"]', 'Automatically escalate overdue payments and suspend services');
    
    // Verify and adjust conditions
    await expect(page.locator('[data-testid="condition-field-0"]')).toHaveValue('payment.days_overdue');
    await expect(page.locator('[data-testid="condition-operator-0"]')).toHaveValue('greater_than');
    await page.fill('[data-testid="condition-value-0"]', '15'); // Reduced from 30 to 15 days
    
    // Add condition for account status
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-1"]', 'account.status');
    await page.selectOption('[data-testid="condition-operator-1"]', 'equals');
    await page.fill('[data-testid="condition-value-1"]', 'active');
    
    // Add condition to exclude VIP customers
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-2"]', 'customer.tier');
    await page.selectOption('[data-testid="condition-operator-2"]', 'not_in');
    await page.fill('[data-testid="condition-value-2"]', 'vip,enterprise');
    
    // Configure escalation actions
    await page.selectOption('[data-testid="action-type-0"]', 'send_notification');
    await page.selectOption('[data-testid="notification-template-0"]', 'payment_overdue_warning');
    await page.selectOption('[data-testid="notification-recipients-0"]', 'customer');
    
    // Add service suspension action
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-1"]', 'suspend_service');
    await page.fill('[data-testid="suspension-grace-period-1"]', '7'); // 7 days grace
    await page.fill('[data-testid="suspension-reason-1"]', 'Payment overdue - account suspended');
    
    // Add collections task creation
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-2"]', 'create_task');
    await page.fill('[data-testid="task-title-2"]', 'Collections Follow-up Required');
    await page.selectOption('[data-testid="task-priority-2"]', 'high');
    await page.selectOption('[data-testid="task-assignee-2"]', 'collections_team');
    
    // Set rule to high priority
    await page.fill('[data-testid="rule-priority"]', '150');
    
    // Save and activate rule
    await page.click('[data-testid="save-rule-btn"]');
    await page.click('[data-testid="activate-rule-btn"]');
    
    // Test with overdue payment scenario
    await page.click('[data-testid="test-rules-btn"]');
    
    await page.fill('[data-testid="test-context-payment-days-overdue"]', '20');
    await page.fill('[data-testid="test-context-account-status"]', 'active');
    await page.fill('[data-testid="test-context-customer-tier"]', 'standard');
    await page.fill('[data-testid="test-context-customer-id"]', 'CUST-OVERDUE-001');
    
    await page.click('[data-testid="run-test-btn"]');
    
    // Verify escalation actions executed
    await page.click('[data-testid="execution-tab"]');
    const result = page.locator('[data-testid="execution-result-0"]');
    await expect(result.locator('[data-testid="rule-matched"]')).toContainText('true');
    await expect(result.locator('[data-testid="actions-executed"]')).toContainText('3');
    
    // Test with VIP customer (should be excluded)
    await page.click('[data-testid="rules-tab"]');
    await page.click('[data-testid="test-rules-btn"]');
    
    await page.fill('[data-testid="test-context-customer-tier"]', 'vip');
    await page.click('[data-testid="run-test-btn"]');
    
    await page.click('[data-testid="execution-tab"]');
    const vipResult = page.locator('[data-testid="execution-result-0"]');
    await expect(vipResult.locator('[data-testid="rule-matched"]')).toContainText('false');
  });

  test('should manage technical support escalation automation', async ({ page }) => {
    // Create technical support escalation rule
    await page.click('[data-testid="rules-tab"]');
    await page.click('[data-testid="new-rule-btn"]');
    await page.click('[data-testid="template-technical-support"]');
    
    // Customize for ISP technical support
    await page.fill('[data-testid="rule-name"]', 'Critical Technical Issue Auto-Escalation');
    await page.fill('[data-testid="rule-description"]', 'Auto-escalate critical technical tickets to senior technicians');
    
    // Configure conditions for critical issues
    await expect(page.locator('[data-testid="condition-field-0"]')).toHaveValue('ticket.priority');
    await expect(page.locator('[data-testid="condition-value-0"]')).toHaveValue('critical');
    
    // Reduce escalation time for critical issues
    await page.fill('[data-testid="condition-value-1"]', '2'); // 2 hours instead of 4
    
    // Add condition for ticket type
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-2"]', 'ticket.category');
    await page.selectOption('[data-testid="condition-operator-2"]', 'in');
    await page.fill('[data-testid="condition-value-2"]', 'network_outage,service_down,security_incident');
    
    // Configure escalation actions
    await page.selectOption('[data-testid="action-type-0"]', 'escalate');
    await page.selectOption('[data-testid="escalation-level-0"]', 'senior_tech');
    await page.check('[data-testid="escalation-notify-0"]');
    
    // Add manager notification
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-1"]', 'send_notification');
    await page.selectOption('[data-testid="notification-recipients-1"]', 'tech_manager');
    await page.selectOption('[data-testid="notification-template-1"]', 'critical_escalation');
    
    // Add customer notification
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-2"]', 'send_notification');
    await page.selectOption('[data-testid="notification-recipients-2"]', 'customer');
    await page.selectOption('[data-testid="notification-template-2"]', 'escalation_acknowledgment');
    
    // Set high priority
    await page.fill('[data-testid="rule-priority"]', '200');
    
    // Save and activate
    await page.click('[data-testid="save-rule-btn"]');
    await page.click('[data-testid="activate-rule-btn"]');
    
    // Test with network outage scenario
    await page.click('[data-testid="test-rules-btn"]');
    
    await page.selectOption('[data-testid="test-context-ticket-priority"]', 'critical');
    await page.fill('[data-testid="test-context-ticket-age-hours"]', '3');
    await page.selectOption('[data-testid="test-context-ticket-category"]', 'network_outage');
    await page.fill('[data-testid="test-context-ticket-id"]', 'TKT-CRITICAL-001');
    
    await page.click('[data-testid="run-test-btn"]');
    
    // Verify escalation executed
    await page.click('[data-testid="execution-tab"]');
    const result = page.locator('[data-testid="execution-result-0"]');
    await expect(result.locator('[data-testid="actions-executed"]')).toContainText('3');
    
    await page.click('[data-testid="view-execution-details"]');
    const actions = page.locator('[data-testid="action-result"]');
    await expect(actions.nth(0)).toContainText('escalate: Escalated to senior_tech');
    await expect(actions.nth(1)).toContainText('send_notification: Sent to tech_manager');
    await expect(actions.nth(2)).toContainText('send_notification: Sent to customer');
  });

  test('should provide comprehensive rule analytics and monitoring', async ({ page }) => {
    // Navigate to analytics tab
    await page.click('[data-testid="analytics-tab"]');
    await expect(page.locator('[data-testid="analytics-dashboard"]')).toBeVisible();
    
    // Verify key metrics are displayed
    await expect(page.locator('[data-testid="total-rules"]')).toBeVisible();
    await expect(page.locator('[data-testid="active-rules"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-executions"]')).toBeVisible();
    await expect(page.locator('[data-testid="success-rate"]')).toBeVisible();
    
    // Check metrics have reasonable values
    const totalRules = await page.locator('[data-testid="total-rules"]').textContent();
    const activeRules = await page.locator('[data-testid="active-rules"]').textContent();
    
    expect(parseInt(totalRules || '0')).toBeGreaterThanOrEqual(0);
    expect(parseInt(activeRules || '0')).toBeLessThanOrEqual(parseInt(totalRules || '0'));
    
    // Test date range filtering
    await page.click('[data-testid="date-range-selector"]');
    await page.click('[data-testid="last-7-days"]');
    
    // Verify metrics update
    await expect(page.locator('[data-testid="analytics-loading"]')).toBeVisible();
    await expect(page.locator('[data-testid="analytics-loading"]')).not.toBeVisible();
    
    // Check execution log
    await page.click('[data-testid="execution-tab"]');
    await expect(page.locator('[data-testid="execution-log"]')).toBeVisible();
    
    // Verify execution entries show relevant information
    const executionEntries = page.locator('[data-testid="execution-entry"]');
    if (await executionEntries.count() > 0) {
      const firstEntry = executionEntries.first();
      await expect(firstEntry.locator('[data-testid="rule-name"]')).toBeVisible();
      await expect(firstEntry.locator('[data-testid="execution-time"]')).toBeVisible();
      await expect(firstEntry.locator('[data-testid="execution-status"]')).toBeVisible();
    }
    
    // Test rule performance analysis
    await page.click('[data-testid="performance-analysis"]');
    
    // Verify performance metrics
    if (await executionEntries.count() > 0) {
      await expect(page.locator('[data-testid="avg-execution-time"]')).toBeVisible();
      await expect(page.locator('[data-testid="success-rate-chart"]')).toBeVisible();
      await expect(page.locator('[data-testid="rule-usage-chart"]')).toBeVisible();
    }
  });

  test('should handle rule conflicts and priority resolution', async ({ page }) => {
    // Create first rule with medium priority
    await page.click('[data-testid="rules-tab"]');
    await page.click('[data-testid="new-rule-btn"]');
    
    await page.fill('[data-testid="rule-name"]', 'Medium Priority Payment Rule');
    await page.fill('[data-testid="rule-description"]', 'Medium priority rule for payment processing');
    
    // Set condition for payment amount
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-0"]', 'payment.amount');
    await page.selectOption('[data-testid="condition-operator-0"]', 'greater_than');
    await page.fill('[data-testid="condition-value-0"]', '1000');
    
    // Set action
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-0"]', 'send_notification');
    await page.selectOption('[data-testid="notification-template-0"]', 'large_payment_alert');
    
    // Set medium priority
    await page.fill('[data-testid="rule-priority"]', '100');
    
    await page.click('[data-testid="save-rule-btn"]');
    await page.click('[data-testid="activate-rule-btn"]');
    
    // Create second rule with higher priority for same condition
    await page.click('[data-testid="new-rule-btn"]');
    
    await page.fill('[data-testid="rule-name"]', 'High Priority VIP Payment Rule');
    await page.fill('[data-testid="rule-description"]', 'High priority rule for VIP customer payments');
    
    // Same payment condition
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-0"]', 'payment.amount');
    await page.selectOption('[data-testid="condition-operator-0"]', 'greater_than');
    await page.fill('[data-testid="condition-value-0"]', '1000');
    
    // Additional VIP condition
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-1"]', 'customer.tier');
    await page.selectOption('[data-testid="condition-operator-1"]', 'equals');
    await page.fill('[data-testid="condition-value-1"]', 'vip');
    
    // Different action
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-0"]', 'send_notification');
    await page.selectOption('[data-testid="notification-template-0"]', 'vip_payment_processing');
    
    // Set higher priority
    await page.fill('[data-testid="rule-priority"]', '200');
    
    await page.click('[data-testid="save-rule-btn"]');
    await page.click('[data-testid="activate-rule-btn"]');
    
    // Test with VIP customer large payment
    await page.click('[data-testid="test-rules-btn"]');
    
    await page.fill('[data-testid="test-context-payment-amount"]', '2000');
    await page.fill('[data-testid="test-context-customer-tier"]', 'vip');
    
    await page.click('[data-testid="run-test-btn"]');
    
    // Verify higher priority rule executed first
    await page.click('[data-testid="execution-tab"]');
    
    const results = page.locator('[data-testid="execution-result"]');
    await expect(results).toHaveCount(2);
    
    // First result should be higher priority rule
    await expect(results.nth(0).locator('[data-testid="rule-name"]')).toContainText('High Priority VIP Payment Rule');
    await expect(results.nth(1).locator('[data-testid="rule-name"]')).toContainText('Medium Priority Payment Rule');
    
    // Test with non-VIP customer (only medium priority should trigger)
    await page.click('[data-testid="rules-tab"]');
    await page.click('[data-testid="test-rules-btn"]');
    
    await page.fill('[data-testid="test-context-payment-amount"]', '2000');
    await page.fill('[data-testid="test-context-customer-tier"]', 'standard');
    
    await page.click('[data-testid="run-test-btn"]');
    
    await page.click('[data-testid="execution-tab"]');
    
    // Should only have one result (medium priority rule)
    const standardResults = page.locator('[data-testid="execution-result"]');
    await expect(standardResults).toHaveCount(1);
    await expect(standardResults.nth(0).locator('[data-testid="rule-name"]')).toContainText('Medium Priority Payment Rule');
  });

  test('should validate rule export and import functionality', async ({ page }) => {
    // Create a rule to export
    await page.click('[data-testid="rules-tab"]');
    await page.click('[data-testid="new-rule-btn"]');
    
    await page.fill('[data-testid="rule-name"]', 'Export Test Rule');
    await page.fill('[data-testid="rule-description"]', 'Rule created for export testing');
    await page.selectOption('[data-testid="rule-category"]', 'billing');
    
    // Add condition
    await page.click('[data-testid="add-condition-btn"]');
    await page.selectOption('[data-testid="condition-field-0"]', 'invoice.amount');
    await page.selectOption('[data-testid="condition-operator-0"]', 'greater_than');
    await page.fill('[data-testid="condition-value-0"]', '500');
    
    // Add action
    await page.click('[data-testid="add-action-btn"]');
    await page.selectOption('[data-testid="action-type-0"]', 'send_notification');
    await page.selectOption('[data-testid="notification-template-0"]', 'large_invoice_alert');
    
    await page.click('[data-testid="save-rule-btn"]');
    
    // Export rule
    await page.click('[data-testid="export-rule-btn"]');
    
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="confirm-export"]');
    const download = await downloadPromise;
    
    expect(download.suggestedFilename()).toMatch(/export-test-rule.*\.json$/);
    
    // Test bulk export
    await page.check('[data-testid="select-rule-0"]');
    await page.click('[data-testid="bulk-export-btn"]');
    
    const bulkDownloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="confirm-bulk-export"]');
    const bulkDownload = await bulkDownloadPromise;
    
    expect(bulkDownload.suggestedFilename()).toMatch(/automation-rules.*\.json$/);
    
    // Test import functionality
    await page.click('[data-testid="import-rules-btn"]');
    
    const fileInput = page.locator('[data-testid="rules-file-input"]');
    await fileInput.setInputFiles({
      name: 'imported-rule.json',
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({
        name: 'Imported Test Rule',
        description: 'This rule was imported from file',
        category: 'support',
        status: 'draft',
        priority: 150,
        conditions: [
          {
            field: 'ticket.status',
            operator: 'equals',
            value: 'urgent'
          }
        ],
        actions: [
          {
            type: 'escalate',
            level: 'manager',
            notify: true
          }
        ]
      }))
    });
    
    await page.click('[data-testid="confirm-import"]');
    
    // Verify imported rule appears
    await expect(page.locator('[data-testid="import-success"]')).toContainText('Rule imported successfully');
    await expect(page.locator('[data-testid="rule-item"]')).toContainText('Imported Test Rule');
    
    // Verify imported rule can be edited
    await page.click('[data-testid="edit-imported-rule"]');
    await expect(page.locator('[data-testid="rule-name"]')).toHaveValue('Imported Test Rule');
    await expect(page.locator('[data-testid="rule-category"]')).toHaveValue('support');
  });
});