/**
 * Visual Workflow Designer E2E Tests
 * Tests the complete workflow creation and management experience
 */

import { test, expect, Page } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';

test.describe('Visual Workflow Designer - Complete User Journeys', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    // Setup admin authentication for workflow management
    await setupAuth(page, 'admin');
    await page.goto('/admin/workflow-designer');
    
    // Wait for designer to load
    await expect(page.locator('[data-testid="workflow-designer"]')).toBeVisible();
  });

  test('should create complete ISP customer onboarding workflow', async ({ page }) => {
    // Create new workflow from scratch
    await page.click('[data-testid="new-workflow-btn"]');
    
    // Set workflow metadata
    await page.fill('[data-testid="workflow-name"]', 'Customer Onboarding Automation');
    await page.fill('[data-testid="workflow-description"]', 'Complete customer onboarding with service activation');
    
    // Add form step for customer details
    await page.click('[data-testid="add-step-form"]');
    await page.fill('[data-testid="step-title"]', 'Customer Information');
    await page.fill('[data-testid="step-description"]', 'Collect customer details and service preferences');
    
    // Configure form fields
    await page.click('[data-testid="add-field-btn"]');
    await page.fill('[data-testid="field-label"]', 'Customer Name');
    await page.selectOption('[data-testid="field-type"]', 'text');
    await page.check('[data-testid="field-required"]');
    
    await page.click('[data-testid="add-field-btn"]');
    await page.fill('[data-testid="field-label"]', 'Service Plan');
    await page.selectOption('[data-testid="field-type"]', 'select');
    await page.fill('[data-testid="field-options"]', 'Basic 100Mbps,Premium 500Mbps,Business 1Gbps');
    
    // Add approval step
    await page.click('[data-testid="add-step-approval"]');
    await page.fill('[data-testid="step-title"]', 'Credit Check Approval');
    await page.selectOption('[data-testid="approver-role"]', 'finance_manager');
    await page.selectOption('[data-testid="approval-policy"]', 'any');
    
    // Add action step for service provisioning
    await page.click('[data-testid="add-step-action"]');
    await page.fill('[data-testid="step-title"]', 'Service Provisioning');
    await page.selectOption('[data-testid="action-type"]', 'api_call');
    await page.fill('[data-testid="api-endpoint"]', '/api/v1/services/provision');
    await page.selectOption('[data-testid="api-method"]', 'POST');
    
    // Add conditional step for equipment
    await page.click('[data-testid="add-step-conditional"]');
    await page.fill('[data-testid="condition-field"]', 'service_plan');
    await page.selectOption('[data-testid="condition-operator"]', 'equals');
    await page.fill('[data-testid="condition-value"]', 'Business 1Gbps');
    
    // Configure equipment step for business customers
    await page.click('[data-testid="add-action-on-true"]');
    await page.selectOption('[data-testid="conditional-action-type"]', 'create_task');
    await page.fill('[data-testid="task-title"]', 'Schedule Equipment Installation');
    await page.selectOption('[data-testid="task-assign-role"]', 'field_technician');
    
    // Add notification step
    await page.click('[data-testid="add-step-action"]');
    await page.fill('[data-testid="step-title"]', 'Welcome Notification');
    await page.selectOption('[data-testid="action-type"]', 'send_notification');
    await page.fill('[data-testid="notification-template"]', 'customer_welcome');
    await page.fill('[data-testid="notification-recipients"]', 'customer');
    
    // Test workflow validation
    await page.click('[data-testid="validate-workflow"]');
    await expect(page.locator('[data-testid="validation-success"]')).toBeVisible();
    await expect(page.locator('[data-testid="validation-errors"]')).toHaveCount(0);
    
    // Save workflow
    await page.click('[data-testid="save-workflow"]');
    await expect(page.locator('[data-testid="save-success"]')).toContainText('Workflow saved successfully');
    
    // Verify workflow appears in workflow list
    await page.click('[data-testid="workflow-list-tab"]');
    await expect(page.locator('[data-testid="workflow-item"]')).toContainText('Customer Onboarding Automation');
  });

  test('should test workflow with real-time preview', async ({ page }) => {
    // Create simple workflow for preview testing
    await page.click('[data-testid="new-workflow-btn"]');
    await page.fill('[data-testid="workflow-name"]', 'Preview Test Workflow');
    
    // Add a form step
    await page.click('[data-testid="add-step-form"]');
    await page.fill('[data-testid="step-title"]', 'Test Form');
    
    await page.click('[data-testid="add-field-btn"]');
    await page.fill('[data-testid="field-label"]', 'Test Input');
    await page.selectOption('[data-testid="field-type"]', 'text');
    
    // Switch to preview mode
    await page.click('[data-testid="preview-mode-btn"]');
    
    // Verify preview interface loads
    await expect(page.locator('[data-testid="workflow-preview"]')).toBeVisible();
    await expect(page.locator('[data-testid="workflow-title"]')).toContainText('Preview Test Workflow');
    
    // Test form interaction in preview
    await expect(page.locator('[data-testid="step-0"]')).toBeVisible();
    await expect(page.locator('[data-testid="field-test-input"]')).toBeVisible();
    
    // Fill form in preview
    await page.fill('[data-testid="field-test-input"]', 'Test Value');
    await page.click('[data-testid="next-step-btn"]');
    
    // Verify form data is captured
    await expect(page.locator('[data-testid="preview-data"]')).toContainText('Test Value');
    
    // Return to designer
    await page.click('[data-testid="back-to-designer"]');
    await expect(page.locator('[data-testid="workflow-designer"]')).toBeVisible();
  });

  test('should handle drag-and-drop workflow step reordering', async ({ page }) => {
    // Create workflow with multiple steps
    await page.click('[data-testid="new-workflow-btn"]');
    await page.fill('[data-testid="workflow-name"]', 'Step Reorder Test');
    
    // Add multiple steps
    await page.click('[data-testid="add-step-form"]');
    await page.fill('[data-testid="step-title"]', 'First Step');
    
    await page.click('[data-testid="add-step-approval"]');
    await page.fill('[data-testid="step-title"]', 'Second Step');
    
    await page.click('[data-testid="add-step-action"]');
    await page.fill('[data-testid="step-title"]', 'Third Step');
    
    // Verify initial order
    const steps = page.locator('[data-testid^="step-card-"]');
    await expect(steps.nth(0)).toContainText('First Step');
    await expect(steps.nth(1)).toContainText('Second Step');
    await expect(steps.nth(2)).toContainText('Third Step');
    
    // Drag second step to first position
    const secondStep = page.locator('[data-testid="step-card-1"]');
    const firstStep = page.locator('[data-testid="step-card-0"]');
    
    await secondStep.dragTo(firstStep);
    
    // Verify reordered steps
    await expect(steps.nth(0)).toContainText('Second Step');
    await expect(steps.nth(1)).toContainText('First Step');
    await expect(steps.nth(2)).toContainText('Third Step');
    
    // Verify step order numbers updated
    await expect(page.locator('[data-testid="step-order-0"]')).toContainText('1');
    await expect(page.locator('[data-testid="step-order-1"]')).toContainText('2');
    await expect(page.locator('[data-testid="step-order-2"]')).toContainText('3');
  });

  test('should export and import workflow definitions', async ({ page }) => {
    // Create a workflow to export
    await page.click('[data-testid="new-workflow-btn"]');
    await page.fill('[data-testid="workflow-name"]', 'Export Test Workflow');
    await page.fill('[data-testid="workflow-description"]', 'Test workflow for export functionality');
    
    // Add a simple step
    await page.click('[data-testid="add-step-form"]');
    await page.fill('[data-testid="step-title"]', 'Test Step');
    
    // Save workflow
    await page.click('[data-testid="save-workflow"]');
    await expect(page.locator('[data-testid="save-success"]')).toBeVisible();
    
    // Export workflow
    await page.click('[data-testid="export-workflow"]');
    
    // Wait for download
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="confirm-export"]');
    const download = await downloadPromise;
    
    // Verify download filename
    expect(download.suggestedFilename()).toMatch(/export-test-workflow.*\.json$/);
    
    // Test import functionality
    await page.click('[data-testid="import-workflow-btn"]');
    
    // Mock file input for import
    const fileInput = page.locator('[data-testid="workflow-file-input"]');
    await fileInput.setInputFiles({
      name: 'test-workflow.json',
      mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({
        name: 'Imported Test Workflow',
        description: 'This workflow was imported from file',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            title: 'Imported Step',
            type: 'form',
            fields: [
              { key: 'test_field', label: 'Test Field', type: 'text', required: true }
            ]
          }
        ]
      }))
    });
    
    // Confirm import
    await page.click('[data-testid="confirm-import"]');
    
    // Verify imported workflow appears
    await expect(page.locator('[data-testid="import-success"]')).toContainText('Workflow imported successfully');
    await expect(page.locator('[data-testid="workflow-name"]')).toHaveValue('Imported Test Workflow');
    await expect(page.locator('[data-testid="step-card-0"]')).toContainText('Imported Step');
  });

  test('should validate workflow configuration errors', async ({ page }) => {
    // Create workflow with intentional errors
    await page.click('[data-testid="new-workflow-btn"]');
    
    // Don't set name (required field)
    await page.fill('[data-testid="workflow-description"]', 'Test validation');
    
    // Add step without required fields
    await page.click('[data-testid="add-step-form"]');
    // Don't set step title (required)
    
    // Add approval step with invalid configuration
    await page.click('[data-testid="add-step-approval"]');
    await page.fill('[data-testid="step-title"]', 'Test Approval');
    // Don't set approver (required)
    
    // Run validation
    await page.click('[data-testid="validate-workflow"]');
    
    // Verify validation errors are shown
    await expect(page.locator('[data-testid="validation-errors"]')).toBeVisible();
    
    const errors = page.locator('[data-testid="validation-error-item"]');
    await expect(errors).toHaveCount(3);
    
    // Check specific error messages
    await expect(errors.nth(0)).toContainText('Workflow name is required');
    await expect(errors.nth(1)).toContainText('Step title is required');
    await expect(errors.nth(2)).toContainText('Approver is required for approval steps');
    
    // Fix errors and revalidate
    await page.fill('[data-testid="workflow-name"]', 'Fixed Workflow');
    await page.fill('[data-testid="step-title-0"]', 'Fixed Step');
    await page.selectOption('[data-testid="approver-role-1"]', 'admin');
    
    await page.click('[data-testid="validate-workflow"]');
    
    // Verify validation passes
    await expect(page.locator('[data-testid="validation-success"]')).toBeVisible();
    await expect(page.locator('[data-testid="validation-errors"]')).not.toBeVisible();
  });

  test('should integrate with existing WorkflowTemplate system', async ({ page }) => {
    // Create workflow and test integration with WorkflowTemplate
    await page.click('[data-testid="new-workflow-btn"]');
    await page.fill('[data-testid="workflow-name"]', 'Template Integration Test');
    
    // Add form step with complex configuration
    await page.click('[data-testid="add-step-form"]');
    await page.fill('[data-testid="step-title"]', 'Customer Service Request');
    
    // Add multiple field types
    await page.click('[data-testid="add-field-btn"]');
    await page.fill('[data-testid="field-label"]', 'Request Type');
    await page.selectOption('[data-testid="field-type"]', 'select');
    await page.fill('[data-testid="field-options"]', 'Service Upgrade,Technical Support,Billing Inquiry');
    await page.check('[data-testid="field-required"]');
    
    await page.click('[data-testid="add-field-btn"]');
    await page.fill('[data-testid="field-label"]', 'Description');
    await page.selectOption('[data-testid="field-type"]', 'textarea');
    await page.fill('[data-testid="field-rows"]', '4');
    
    await page.click('[data-testid="add-field-btn"]');
    await page.fill('[data-testid="field-label"]', 'Priority');
    await page.selectOption('[data-testid="field-type"]', 'select');
    await page.fill('[data-testid="field-options"]', 'Low,Medium,High,Urgent');
    
    // Test preview integration with WorkflowTemplate
    await page.click('[data-testid="preview-mode-btn"]');
    
    // Verify WorkflowTemplate renders correctly
    await expect(page.locator('[data-testid="workflow-template"]')).toBeVisible();
    await expect(page.locator('[data-testid="workflow-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="step-navigation"]')).toBeVisible();
    
    // Test form interaction
    await page.selectOption('[data-testid="field-request-type"]', 'Service Upgrade');
    await page.fill('[data-testid="field-description"]', 'Customer wants to upgrade to 1Gbps service');
    await page.selectOption('[data-testid="field-priority"]', 'High');
    
    // Test form validation
    await page.click('[data-testid="next-step-btn"]');
    
    // Verify form data is properly handled by WorkflowTemplate
    const formData = await page.evaluate(() => {
      return (window as any).workflowFormData;
    });
    
    expect(formData).toEqual({
      'request-type': 'Service Upgrade',
      'description': 'Customer wants to upgrade to 1Gbps service',
      'priority': 'High'
    });
    
    // Test workflow completion
    await expect(page.locator('[data-testid="workflow-complete"]')).toBeVisible();
    await expect(page.locator('[data-testid="completion-message"]')).toContainText('successfully completed');
  });

  test('should handle workflow execution with error scenarios', async ({ page }) => {
    // Create workflow with API call that might fail
    await page.click('[data-testid="new-workflow-btn"]');
    await page.fill('[data-testid="workflow-name"]', 'Error Handling Test');
    
    // Add action step with API call
    await page.click('[data-testid="add-step-action"]');
    await page.fill('[data-testid="step-title"]', 'External API Call');
    await page.selectOption('[data-testid="action-type"]', 'api_call');
    await page.fill('[data-testid="api-endpoint"]', '/api/external/service');
    await page.selectOption('[data-testid="api-method"]', 'POST');
    await page.fill('[data-testid="max-retries"]', '3');
    await page.fill('[data-testid="timeout"]', '30000');
    
    // Configure error handling
    await page.selectOption('[data-testid="on-error"]', 'continue');
    await page.fill('[data-testid="error-message"]', 'External service temporarily unavailable');
    
    // Save and test execution
    await page.click('[data-testid="save-workflow"]');
    await page.click('[data-testid="test-workflow"]');
    
    // Mock API failure for testing
    await page.route('/api/external/service', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Service unavailable',
          code: 'SERVICE_ERROR'
        })
      });
    });
    
    // Execute workflow in test mode
    await page.click('[data-testid="start-test-execution"]');
    
    // Verify error handling
    await expect(page.locator('[data-testid="step-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('External service temporarily unavailable');
    
    // Verify retry attempts
    await expect(page.locator('[data-testid="retry-count"]')).toContainText('3');
    
    // Verify workflow continues despite error (based on configuration)
    await expect(page.locator('[data-testid="workflow-status"]')).toContainText('Completed with warnings');
  });
});