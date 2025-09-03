/**
 * Workflow Failure and Recovery Scenario E2E Tests
 * Tests error handling, failure recovery, and resilience across workflow systems
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';

test.describe('Workflow Failure and Recovery Scenarios', () => {
  test.describe.configure({ mode: 'serial' });

  let adminPage: Page;
  let customerPage: Page;

  test.beforeAll(async ({ browser }) => {
    const adminContext = await browser.newContext();
    const customerContext = await browser.newContext();

    adminPage = await adminContext.newPage();
    customerPage = await customerContext.newPage();

    await setupAuth(adminPage, 'admin');
    await setupAuth(customerPage, 'customer');
  });

  test('workflow step failure with automatic retry', async () => {
    // Test automatic retry mechanism for failed workflow steps

    await adminPage.goto('/admin/workflows/designer');

    // Create test workflow with failure-prone step
    await adminPage.click('[data-testid="new-workflow-btn"]');
    await adminPage.fill('[data-testid="workflow-name"]', 'Retry Test Workflow');

    // Add API call step that will fail
    await adminPage.click('[data-testid="add-step-action"]');
    await adminPage.fill('[data-testid="step-title"]', 'External Service Integration');
    await adminPage.selectOption('[data-testid="action-type"]', 'api_call');
    await adminPage.fill('[data-testid="api-endpoint"]', '/api/external/unreliable-service');
    await adminPage.selectOption('[data-testid="api-method"]', 'POST');

    // Configure retry settings
    await adminPage.fill('[data-testid="max-retries"]', '3');
    await adminPage.fill('[data-testid="retry-delay"]', '5000');
    await adminPage.selectOption('[data-testid="backoff-strategy"]', 'exponential');
    await adminPage.selectOption('[data-testid="on-failure"]', 'continue');

    await adminPage.click('[data-testid="save-workflow"]');

    // Mock failing API endpoint
    let callCount = 0;
    await adminPage.route('/api/external/unreliable-service', async (route) => {
      callCount++;
      if (callCount < 3) {
        // Fail first 2 attempts
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Temporary service unavailable',
            code: 'SERVICE_ERROR',
            timestamp: new Date().toISOString(),
          }),
        });
      } else {
        // Succeed on 3rd attempt
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { processed: true },
            timestamp: new Date().toISOString(),
          }),
        });
      }
    });

    // Execute workflow
    await adminPage.click('[data-testid="test-workflow"]');
    await adminPage.click('[data-testid="start-execution"]');

    // Monitor retry attempts
    await expect(adminPage.locator('[data-testid="step-executing"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="retry-attempt-1"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(adminPage.locator('[data-testid="retry-attempt-2"]')).toBeVisible({
      timeout: 15000,
    });
    await expect(adminPage.locator('[data-testid="step-completed"]')).toBeVisible({
      timeout: 25000,
    });

    // Verify retry log
    await adminPage.click('[data-testid="view-execution-log"]');
    const retryLog = adminPage.locator('[data-testid="execution-log"]');
    await expect(retryLog).toContainText('Attempt 1: Failed');
    await expect(retryLog).toContainText('Attempt 2: Failed');
    await expect(retryLog).toContainText('Attempt 3: Success');

    expect(callCount).toBe(3);
  });

  test('workflow failure with manual intervention', async () => {
    // Test workflow that requires manual intervention when automated retry fails

    await adminPage.goto('/admin/workflows/designer');

    // Create workflow with critical step
    await adminPage.click('[data-testid="new-workflow-btn"]');
    await adminPage.fill('[data-testid="workflow-name"]', 'Manual Intervention Test');

    // Add critical API step
    await adminPage.click('[data-testid="add-step-action"]');
    await adminPage.fill('[data-testid="step-title"]', 'Critical Payment Processing');
    await adminPage.selectOption('[data-testid="action-type"]', 'api_call');
    await adminPage.fill('[data-testid="api-endpoint"]', '/api/payments/process');

    // Configure for manual intervention on failure
    await adminPage.fill('[data-testid="max-retries"]', '2');
    await adminPage.selectOption('[data-testid="on-failure"]', 'pause_for_intervention');
    await adminPage.selectOption('[data-testid="intervention-role"]', 'finance_manager');

    await adminPage.click('[data-testid="save-workflow"]');

    // Mock consistently failing API
    await adminPage.route('/api/payments/process', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Payment gateway connection timeout',
          code: 'GATEWAY_TIMEOUT',
        }),
      });
    });

    // Start workflow execution
    await adminPage.click('[data-testid="test-workflow"]');
    await adminPage.click('[data-testid="start-execution"]');

    // Wait for retries to exhaust
    await expect(adminPage.locator('[data-testid="step-failed"]')).toBeVisible({ timeout: 30000 });
    await expect(adminPage.locator('[data-testid="intervention-required"]')).toBeVisible();

    // Verify intervention notification
    await expect(adminPage.locator('[data-testid="intervention-alert"]')).toContainText(
      'finance_manager'
    );
    await expect(adminPage.locator('[data-testid="failure-reason"]')).toContainText(
      'Payment gateway connection timeout'
    );

    // Simulate manual intervention
    await adminPage.click('[data-testid="manual-intervention"]');
    await adminPage.selectOption('[data-testid="intervention-action"]', 'retry_with_alternate');
    await adminPage.fill('[data-testid="alternate-endpoint"]', '/api/payments/backup-processor');
    await adminPage.fill(
      '[data-testid="intervention-notes"]',
      'Using backup payment processor due to primary gateway timeout'
    );

    // Mock successful backup endpoint
    await adminPage.route('/api/payments/backup-processor', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          transactionId: 'TXN-BACKUP-001',
          processor: 'backup',
        }),
      });
    });

    await adminPage.click('[data-testid="apply-intervention"]');

    // Verify workflow resumes and completes
    await expect(adminPage.locator('[data-testid="workflow-resumed"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="workflow-completed"]')).toBeVisible({
      timeout: 15000,
    });

    // Check intervention log
    await adminPage.click('[data-testid="view-intervention-log"]');
    await expect(adminPage.locator('[data-testid="intervention-log"]')).toContainText(
      'backup payment processor'
    );
    await expect(adminPage.locator('[data-testid="intervention-user"]')).toContainText('admin');
  });

  test('network connectivity failure recovery', async () => {
    // Test workflow behavior during network connectivity issues

    await customerPage.goto('/customer/support/tickets/new');

    // Start ticket creation workflow
    await customerPage.fill('[data-testid="ticket-subject"]', 'Network Recovery Test');
    await customerPage.selectOption('[data-testid="category"]', 'technical_support');
    await customerPage.fill('[data-testid="description"]', 'Testing network failure recovery');

    // Mock network failure during submission
    let networkFailureSimulated = false;
    await customerPage.route('/api/tickets/create', async (route) => {
      if (!networkFailureSimulated) {
        networkFailureSimulated = true;
        await route.abort('failed');
      } else {
        // Second attempt succeeds
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'TICKET-RECOVERY-001',
            status: 'created',
            subject: 'Network Recovery Test',
          }),
        });
      }
    });

    await customerPage.click('[data-testid="submit-ticket"]');

    // Verify failure handling
    await expect(customerPage.locator('[data-testid="submission-failed"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(customerPage.locator('[data-testid="retry-notification"]')).toContainText(
      'connection failed'
    );

    // Verify automatic retry
    await expect(customerPage.locator('[data-testid="auto-retry-indicator"]')).toBeVisible();
    await expect(customerPage.locator('[data-testid="ticket-created-success"]')).toBeVisible({
      timeout: 15000,
    });

    const ticketId = await customerPage.locator('[data-testid="created-ticket-id"]').textContent();
    expect(ticketId).toBe('TICKET-RECOVERY-001');

    // Verify data integrity after recovery
    await customerPage.goto('/customer/support/tickets');
    const ticketRow = customerPage.locator('[data-testid="ticket-TICKET-RECOVERY-001"]');
    await expect(ticketRow).toBeVisible();
    await expect(ticketRow).toContainText('Network Recovery Test');
  });

  test('database transaction rollback on workflow failure', async () => {
    // Test database consistency during workflow failures

    await adminPage.goto('/admin/customers/bulk-operations');

    // Setup bulk customer import that will partially fail
    await adminPage.click('[data-testid="bulk-import-customers"]');

    const customerData = [
      { email: 'success1@test.com', name: 'Success Customer 1', plan: 'basic' },
      { email: 'success2@test.com', name: 'Success Customer 2', plan: 'premium' },
      { email: 'invalid@', name: 'Invalid Customer', plan: 'basic' }, // Invalid email
      { email: 'success3@test.com', name: 'Success Customer 3', plan: 'business' },
    ];

    const csvContent = [
      'email,name,plan',
      ...customerData.map((c) => `${c.email},${c.name},${c.plan}`),
    ].join('\n');

    await adminPage.setInputFiles('[data-testid="csv-upload"]', {
      name: 'bulk-customers.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csvContent),
    });

    // Configure transaction handling
    await adminPage.check('[data-testid="use-transactions"]');
    await adminPage.selectOption('[data-testid="on-error"]', 'rollback_all');

    await adminPage.click('[data-testid="start-import"]');

    // Monitor import progress and failure
    await expect(adminPage.locator('[data-testid="import-progress"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="processing-row-3"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(adminPage.locator('[data-testid="validation-error"]')).toBeVisible({
      timeout: 5000,
    });

    // Verify rollback occurred
    await expect(adminPage.locator('[data-testid="transaction-rolled-back"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="import-failed"]')).toContainText(
      'All changes rolled back'
    );

    // Verify no customers were created
    await adminPage.goto('/admin/customers/list');
    await adminPage.fill('[data-testid="search-customers"]', 'success1@test.com');
    await adminPage.click('[data-testid="search-btn"]');
    await expect(adminPage.locator('[data-testid="no-customers-found"]')).toBeVisible();

    // Test with continue-on-error strategy
    await adminPage.goto('/admin/customers/bulk-operations');
    await adminPage.click('[data-testid="bulk-import-customers"]');

    await adminPage.setInputFiles('[data-testid="csv-upload"]', {
      name: 'bulk-customers-retry.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csvContent),
    });

    await adminPage.selectOption('[data-testid="on-error"]', 'continue_with_valid');
    await adminPage.click('[data-testid="start-import"]');

    // Verify partial success
    await expect(adminPage.locator('[data-testid="import-completed"]')).toBeVisible({
      timeout: 15000,
    });
    await expect(adminPage.locator('[data-testid="successful-imports"]')).toContainText('3');
    await expect(adminPage.locator('[data-testid="failed-imports"]')).toContainText('1');

    // Verify valid customers were created
    await adminPage.goto('/admin/customers/list');
    await adminPage.fill('[data-testid="search-customers"]', 'success1@test.com');
    await adminPage.click('[data-testid="search-btn"]');
    await expect(adminPage.locator('[data-testid="customer-row-0"]')).toBeVisible();
  });

  test('workflow timeout and recovery', async () => {
    // Test workflow timeout handling and recovery mechanisms

    await adminPage.goto('/admin/workflows/designer');

    // Create workflow with timeout-sensitive step
    await adminPage.click('[data-testid="new-workflow-btn"]');
    await adminPage.fill('[data-testid="workflow-name"]', 'Timeout Recovery Test');

    // Add long-running step
    await adminPage.click('[data-testid="add-step-action"]');
    await adminPage.fill('[data-testid="step-title"]', 'Long Running Process');
    await adminPage.selectOption('[data-testid="action-type"]', 'api_call');
    await adminPage.fill('[data-testid="api-endpoint"]', '/api/long-process');

    // Configure timeout
    await adminPage.fill('[data-testid="step-timeout"]', '10000'); // 10 seconds
    await adminPage.selectOption('[data-testid="on-timeout"]', 'retry_with_longer_timeout');
    await adminPage.fill('[data-testid="extended-timeout"]', '30000'); // 30 seconds

    await adminPage.click('[data-testid="save-workflow"]');

    // Mock slow API that times out first, succeeds on retry
    let firstCall = true;
    await adminPage.route('/api/long-process', async (route) => {
      if (firstCall) {
        firstCall = false;
        // Don't respond - simulate timeout
        await new Promise(() => {}); // Never resolves
      } else {
        // Respond quickly on retry
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            processingTime: '25000ms',
            result: 'completed',
          }),
        });
      }
    });

    await adminPage.click('[data-testid="test-workflow"]');
    await adminPage.click('[data-testid="start-execution"]');

    // Monitor timeout and recovery
    await expect(adminPage.locator('[data-testid="step-executing"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="timeout-warning"]')).toBeVisible({
      timeout: 12000,
    });
    await expect(adminPage.locator('[data-testid="timeout-occurred"]')).toBeVisible({
      timeout: 15000,
    });
    await expect(adminPage.locator('[data-testid="extending-timeout"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="step-completed"]')).toBeVisible({
      timeout: 35000,
    });

    // Verify timeout handling log
    await adminPage.click('[data-testid="view-execution-log"]');
    const timeoutLog = adminPage.locator('[data-testid="execution-log"]');
    await expect(timeoutLog).toContainText('Step timed out after 10000ms');
    await expect(timeoutLog).toContainText('Retrying with extended timeout: 30000ms');
    await expect(timeoutLog).toContainText('Step completed successfully');
  });

  test('workflow state recovery after system restart', async () => {
    // Test workflow state persistence and recovery

    await adminPage.goto('/admin/workflows/monitoring');

    // Start a long-running workflow
    await adminPage.click('[data-testid="start-system-maintenance-workflow"]');
    await adminPage.selectOption('[data-testid="maintenance-type"]', 'database_optimization');
    await adminPage.fill('[data-testid="estimated-duration"]', '45');
    await adminPage.click('[data-testid="begin-maintenance"]');

    const workflowId = await adminPage.locator('[data-testid="workflow-id"]').textContent();

    // Wait for workflow to start processing
    await expect(adminPage.locator('[data-testid="workflow-running"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="step-1-completed"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(adminPage.locator('[data-testid="step-2-in-progress"]')).toBeVisible();

    // Simulate system restart by refreshing page (simulates browser/system restart)
    await adminPage.reload();
    await expect(adminPage.locator('[data-testid="workflow-monitoring"]')).toBeVisible();

    // Verify workflow state recovery
    const recoveredWorkflow = adminPage.locator(`[data-testid="workflow-${workflowId}"]`);
    await expect(recoveredWorkflow).toBeVisible({ timeout: 10000 });
    await expect(recoveredWorkflow).toContainText('In Progress');

    // Check workflow details
    await recoveredWorkflow.click();
    await expect(adminPage.locator('[data-testid="workflow-details"]')).toBeVisible();

    // Verify recovered state matches pre-restart state
    await expect(adminPage.locator('[data-testid="step-1-status"]')).toContainText('Completed');
    await expect(adminPage.locator('[data-testid="step-2-status"]')).toContainText('In Progress');

    // Verify workflow can continue from recovered state
    await expect(adminPage.locator('[data-testid="step-2-completed"]')).toBeVisible({
      timeout: 20000,
    });
    await expect(adminPage.locator('[data-testid="step-3-in-progress"]')).toBeVisible();

    // Verify recovery log
    await adminPage.click('[data-testid="view-recovery-log"]');
    const recoveryLog = adminPage.locator('[data-testid="recovery-log"]');
    await expect(recoveryLog).toContainText('Workflow state recovered');
    await expect(recoveryLog).toContainText('Resuming from step 2');
  });

  test('cascading failure handling', async () => {
    // Test handling of cascading failures across dependent workflows

    await adminPage.goto('/admin/workflows/orchestration');

    // Setup dependent workflow chain
    await adminPage.click('[data-testid="create-workflow-chain"]');

    const workflows = [
      { name: 'Customer Data Validation', endpoint: '/api/customer/validate' },
      { name: 'Service Eligibility Check', endpoint: '/api/services/eligibility' },
      { name: 'Service Provisioning', endpoint: '/api/services/provision' },
    ];

    for (let i = 0; i < workflows.length; i++) {
      await adminPage.click('[data-testid="add-workflow-step"]');
      await adminPage.fill(`[data-testid="workflow-${i}-name"]`, workflows[i].name);
      await adminPage.fill(`[data-testid="workflow-${i}-endpoint"]`, workflows[i].endpoint);

      if (i > 0) {
        await adminPage.check(`[data-testid="workflow-${i}-depends-on-${i - 1}"]`);
      }
    }

    await adminPage.click('[data-testid="save-workflow-chain"]');

    // Mock first workflow success, second workflow failure
    await adminPage.route('/api/customer/validate', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ valid: true, customerId: 'CUST-001' }),
      });
    });

    await adminPage.route('/api/services/eligibility', async (route) => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Service database unavailable' }),
      });
    });

    // Start workflow chain execution
    await adminPage.fill('[data-testid="customer-email"]', 'cascading-test@example.com');
    await adminPage.click('[data-testid="execute-workflow-chain"]');

    // Monitor cascading failure
    await expect(adminPage.locator('[data-testid="workflow-0-completed"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(adminPage.locator('[data-testid="workflow-1-failed"]')).toBeVisible({
      timeout: 10000,
    });
    await expect(adminPage.locator('[data-testid="workflow-2-cancelled"]')).toBeVisible({
      timeout: 5000,
    });

    // Verify cascade handling
    await expect(adminPage.locator('[data-testid="cascade-failure-detected"]')).toBeVisible();
    await expect(adminPage.locator('[data-testid="dependent-workflows-cancelled"]')).toContainText(
      '1 workflow cancelled'
    );

    // Test cascade recovery
    await adminPage.click('[data-testid="fix-cascade-failure"]');
    await adminPage.selectOption('[data-testid="recovery-strategy"]', 'retry_failed_step');

    // Mock fixed service
    await adminPage.route('/api/services/eligibility', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ eligible: true, availableServices: ['fiber_100'] }),
      });
    });

    await adminPage.route('/api/services/provision', async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify({ provisioned: true, serviceId: 'SVC-001' }),
      });
    });

    await adminPage.click('[data-testid="resume-workflow-chain"]');

    // Verify recovery and completion
    await expect(adminPage.locator('[data-testid="workflow-1-completed"]')).toBeVisible({
      timeout: 15000,
    });
    await expect(adminPage.locator('[data-testid="workflow-2-completed"]')).toBeVisible({
      timeout: 15000,
    });
    await expect(adminPage.locator('[data-testid="workflow-chain-completed"]')).toBeVisible();
  });

  test.afterAll(async () => {
    await adminPage.context().close();
    await customerPage.context().close();
  });
});
