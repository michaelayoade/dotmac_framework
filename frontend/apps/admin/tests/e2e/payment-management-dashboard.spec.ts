/**
 * Admin Payment Management Dashboard E2E Tests
 * Tests payment monitoring, chargeback handling, refund processing, and dunning management
 */

import { test, expect } from '@playwright/test';
import { PaymentTestHelper } from '../../../testing/e2e/shared-scenarios/payment-test-helper';
import { performLogin, testCredentials, portalConfig } from '../../../testing/e2e/shared-scenarios/auth.scenarios';

class PaymentManagementJourney {
  constructor(
    public page: any,
    public paymentHelper: PaymentTestHelper
  ) {}

  async navigateToPaymentDashboard() {
    await this.page.goto('/admin/payments');
    await expect(this.page.getByTestId('payment-dashboard')).toBeVisible();
  }

  async testPaymentOverview() {
    console.log('Testing payment overview dashboard');
    
    await this.navigateToPaymentDashboard();
    
    // Verify key metrics are displayed
    await expect(this.page.getByTestId('total-payments-today')).toBeVisible();
    await expect(this.page.getByTestId('successful-payments-rate')).toBeVisible();
    await expect(this.page.getByTestId('failed-payments-count')).toBeVisible();
    await expect(this.page.getByTestId('total-volume-today')).toBeVisible();
    
    // Check payment status breakdown chart
    await expect(this.page.getByTestId('payment-status-chart')).toBeVisible();
    
    // Verify real-time payment feed
    await expect(this.page.getByTestId('recent-payments-feed')).toBeVisible();
    
    return true;
  }

  async testFailedPaymentsManagement() {
    console.log('Testing failed payments management');
    
    // Create some failed payments for testing
    await this.paymentHelper.createSuccessfulPayment({ amount: '50.00', cardNumber: '4000000000000002' });
    await this.paymentHelper.createSuccessfulPayment({ amount: '125.00', cardNumber: '4000000000009995' });
    
    await this.page.goto('/admin/payments/failed');
    
    // Verify failed payments list
    await expect(this.page.getByTestId('failed-payments-table')).toBeVisible();
    await expect(this.page.getByText('2 failed payments')).toBeVisible();
    
    // Test filtering by failure reason
    await this.page.selectOption('[data-testid="failure-reason-filter"]', 'insufficient_funds');
    await expect(this.page.getByText('1 failed payment')).toBeVisible();
    
    // Test bulk retry functionality
    await this.page.click('[data-testid="select-all-failed"]');
    await this.page.click('[data-testid="bulk-retry-payments"]');
    
    await expect(this.page.getByText(/retry initiated for \d+ payments/i)).toBeVisible();
    
    // Test individual payment details
    await this.page.click('[data-testid="view-payment-details"]:first-child');
    await expect(this.page.getByTestId('payment-details-modal')).toBeVisible();
    await expect(this.page.getByTestId('failure-reason')).toBeVisible();
    await expect(this.page.getByTestId('gateway-response')).toBeVisible();
    
    return true;
  }

  async testChargebackDashboard() {
    console.log('Testing chargeback management dashboard');
    
    // Create test chargeback data
    const paymentId = await this.paymentHelper.createSuccessfulPayment({ amount: '300.00', cardNumber: '4242424242424242' });
    await this.paymentHelper.simulateChargeback(paymentId, {
      reason: 'fraudulent',
      amount: '300.00',
      chargebackId: 'cb_test_123'
    });
    
    await this.page.goto('/admin/payments/chargebacks');
    
    // Verify chargeback dashboard elements
    await expect(this.page.getByTestId('chargebacks-overview')).toBeVisible();
    await expect(this.page.getByTestId('active-chargebacks-count')).toBeVisible();
    await expect(this.page.getByTestId('chargeback-win-rate')).toBeVisible();
    
    // Test chargeback list and filtering
    await expect(this.page.getByTestId('chargebacks-table')).toBeVisible();
    await this.page.selectOption('[data-testid="chargeback-status-filter"]', 'received');
    
    // Test dispute submission
    await this.page.click(`[data-testid="dispute-chargeback-${paymentId}"]`);
    
    await expect(this.page.getByTestId('dispute-form')).toBeVisible();
    await this.page.fill('[data-testid="dispute-evidence"]', 'Transaction was authorized with valid CVV and 3DS authentication');
    await this.page.fill('[data-testid="dispute-message"]', 'Customer signature on file, delivery confirmed');
    
    // Upload evidence documents (simulate)
    await this.page.click('[data-testid="upload-evidence-button"]');
    
    await this.page.click('[data-testid="submit-dispute"]');
    await expect(this.page.getByText(/dispute submitted successfully/i)).toBeVisible();
    
    // Verify chargeback status updated
    await expect(this.page.getByTestId('chargeback-status')).toContainText('Under Review');
    
    return true;
  }

  async testRefundManagement() {
    console.log('Testing refund management interface');
    
    await this.page.goto('/admin/payments/refunds');
    
    // Verify refunds dashboard
    await expect(this.page.getByTestId('refunds-dashboard')).toBeVisible();
    await expect(this.page.getByTestId('pending-refunds-count')).toBeVisible();
    await expect(this.page.getByTestId('refunds-processed-today')).toBeVisible();
    
    // Test refund processing workflow
    const paymentId = await this.paymentHelper.createSuccessfulPayment({ amount: '150.00', cardNumber: '4242424242424242' });
    
    await this.page.goto(`/admin/payments/${paymentId}`);
    await this.page.click('[data-testid="process-refund"]');
    
    // Test partial refund
    await this.page.fill('[data-testid="refund-amount"]', '75.00');
    await this.page.selectOption('[data-testid="refund-reason"]', 'customer_request');
    await this.page.fill('[data-testid="refund-notes"]', 'Customer requested partial refund for service issue');
    
    await this.page.click('[data-testid="confirm-refund"]');
    
    await expect(this.page.getByTestId('refund-processing')).toBeVisible();
    await expect(this.page.getByText(/refund of \$75\.00 initiated/i)).toBeVisible();
    
    // Test refund approval workflow (for higher amounts)
    await this.page.goto(`/admin/payments/${paymentId}`);
    await this.page.click('[data-testid="process-refund"]');
    
    await this.page.fill('[data-testid="refund-amount"]', '75.00'); // Remaining amount
    await this.page.selectOption('[data-testid="refund-reason"]', 'merchant_error');
    
    await this.page.click('[data-testid="confirm-refund"]');
    
    // Should complete full refund
    await expect(this.page.getByText(/full refund completed/i)).toBeVisible();
    
    return true;
  }

  async testDunningManagement() {
    console.log('Testing dunning management dashboard');
    
    // Create customers in dunning process
    const customer1 = await this.paymentHelper.createCustomerWithFailedPayment({
      email: 'customer1@example.com',
      failedAmount: '99.99',
      failedDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) // 7 days ago
    });
    
    const customer2 = await this.paymentHelper.createCustomerWithFailedPayment({
      email: 'customer2@example.com', 
      failedAmount: '149.99',
      failedDate: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000) // 14 days ago
    });
    
    await this.page.goto('/admin/payments/dunning');
    
    // Verify dunning dashboard
    await expect(this.page.getByTestId('dunning-dashboard')).toBeVisible();
    await expect(this.page.getByTestId('customers-in-dunning')).toContainText('2');
    await expect(this.page.getByTestId('total-overdue-amount')).toContainText('$249.98');
    
    // Test dunning stages visualization
    await expect(this.page.getByTestId('dunning-funnel-chart')).toBeVisible();
    
    // Test customer list filtering
    await this.page.selectOption('[data-testid="dunning-stage-filter"]', 'reminder_1');
    await expect(this.page.getByTestId('dunning-customers-table')).toBeVisible();
    
    // Test individual customer dunning management
    await this.page.click(`[data-testid="manage-dunning-${customer1}"]`);
    
    await expect(this.page.getByTestId('customer-dunning-timeline')).toBeVisible();
    await expect(this.page.getByTestId('dunning-emails-sent')).toBeVisible();
    
    // Test manual retry payment
    await this.page.click('[data-testid="retry-customer-payment"]');
    await expect(this.page.getByText(/retry payment initiated/i)).toBeVisible();
    
    // Test escalation to collections
    await this.page.click(`[data-testid="escalate-to-collections-${customer2}"]`);
    await this.page.fill('[data-testid="escalation-notes"]', 'Customer unresponsive to payment reminders');
    await this.page.click('[data-testid="confirm-escalation"]');
    
    await expect(this.page.getByText(/escalated to collections/i)).toBeVisible();
    
    // Test dunning email configuration
    await this.page.goto('/admin/payments/dunning/settings');
    
    await expect(this.page.getByTestId('dunning-email-templates')).toBeVisible();
    await expect(this.page.getByTestId('retry-schedule-config')).toBeVisible();
    
    return true;
  }

  async testPaymentAnalytics() {
    console.log('Testing payment analytics and reporting');
    
    await this.page.goto('/admin/payments/analytics');
    
    // Verify analytics dashboard
    await expect(this.page.getByTestId('payment-analytics-dashboard')).toBeVisible();
    
    // Test date range selector
    await this.page.click('[data-testid="date-range-selector"]');
    await this.page.click('[data-testid="last-30-days"]');
    
    // Verify key metrics
    await expect(this.page.getByTestId('success-rate-metric')).toBeVisible();
    await expect(this.page.getByTestId('average-transaction-value')).toBeVisible();
    await expect(this.page.getByTestId('chargeback-rate')).toBeVisible();
    await expect(this.page.getByTestId('refund-rate')).toBeVisible();
    
    // Test payment method breakdown
    await expect(this.page.getByTestId('payment-methods-chart')).toBeVisible();
    
    // Test decline reason analysis
    await expect(this.page.getByTestId('decline-reasons-chart')).toBeVisible();
    
    // Test geographic payment distribution
    await expect(this.page.getByTestId('payment-geography-map')).toBeVisible();
    
    // Test export functionality
    await this.page.click('[data-testid="export-analytics"]');
    await this.page.selectOption('[data-testid="export-format"]', 'csv');
    await this.page.click('[data-testid="generate-export"]');
    
    await expect(this.page.getByText(/export generated successfully/i)).toBeVisible();
    
    return true;
  }

  async testRiskManagement() {
    console.log('Testing risk management and fraud detection');
    
    await this.page.goto('/admin/payments/risk');
    
    // Verify risk dashboard
    await expect(this.page.getByTestId('risk-management-dashboard')).toBeVisible();
    
    // Test fraud detection alerts
    await expect(this.page.getByTestId('fraud-alerts-count')).toBeVisible();
    await expect(this.page.getByTestId('high-risk-transactions')).toBeVisible();
    
    // Test risk rules configuration
    await this.page.click('[data-testid="configure-risk-rules"]');
    
    await expect(this.page.getByTestId('risk-rules-editor')).toBeVisible();
    
    // Add new risk rule
    await this.page.click('[data-testid="add-risk-rule"]');
    await this.page.fill('[data-testid="rule-name"]', 'High Value Transaction Alert');
    await this.page.selectOption('[data-testid="rule-condition"]', 'amount_greater_than');
    await this.page.fill('[data-testid="rule-value"]', '500');
    await this.page.selectOption('[data-testid="rule-action"]', 'require_manual_review');
    
    await this.page.click('[data-testid="save-risk-rule"]');
    await expect(this.page.getByText(/risk rule saved successfully/i)).toBeVisible();
    
    // Test blocked transactions review
    await this.page.goto('/admin/payments/risk/blocked');
    
    await expect(this.page.getByTestId('blocked-transactions-table')).toBeVisible();
    
    return true;
  }
}

test.describe('Payment Management Dashboard', () => {
  let paymentHelper: PaymentTestHelper;

  test.beforeEach(async ({ page }) => {
    paymentHelper = new PaymentTestHelper(page);
    await paymentHelper.setup();
    
    // Login as admin
    await performLogin(page, testCredentials.admin, {
      portal: 'admin',
      loginUrl: portalConfig.admin.loginUrl,
      expectedRedirect: portalConfig.admin.dashboardUrl
    });
  });

  test.afterEach(async ({ page }) => {
    await paymentHelper.cleanup();
  });

  test('displays payment overview correctly @admin @payments @dashboard', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await test.step('test payment overview', async () => {
      const result = await journey.testPaymentOverview();
      expect(result).toBe(true);
    });
  });

  test('manages failed payments effectively @admin @payments @failed', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await test.step('test failed payments management', async () => {
      const result = await journey.testFailedPaymentsManagement();
      expect(result).toBe(true);
    });
  });

  test('handles chargebacks properly @admin @payments @chargebacks', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await test.step('test chargeback management', async () => {
      const result = await journey.testChargebackDashboard();
      expect(result).toBe(true);
    });
  });

  test('processes refunds correctly @admin @payments @refunds', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await test.step('test refund management', async () => {
      const result = await journey.testRefundManagement();
      expect(result).toBe(true);
    });
  });

  test('manages dunning process @admin @payments @dunning', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await test.step('test dunning management', async () => {
      const result = await journey.testDunningManagement();
      expect(result).toBe(true);
    });
  });

  test('provides payment analytics @admin @payments @analytics', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await test.step('test payment analytics', async () => {
      const result = await journey.testPaymentAnalytics();
      expect(result).toBe(true);
    });
  });

  test('manages payment risk @admin @payments @risk', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await test.step('test risk management', async () => {
      const result = await journey.testRiskManagement();
      expect(result).toBe(true);
    });
  });

  test('payment dashboard performance @admin @payments @performance', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    const startTime = Date.now();
    
    await journey.testPaymentOverview();
    await journey.testFailedPaymentsManagement();
    await journey.testPaymentAnalytics();
    
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(45000); // 45 seconds max
  });

  test('payment dashboard accessibility @admin @payments @a11y', async ({ page }) => {
    const journey = new PaymentManagementJourney(page, paymentHelper);
    
    await journey.navigateToPaymentDashboard();
    
    // Check keyboard navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
    
    // Check ARIA labels on interactive elements
    const chartElements = page.getByTestId('payment-status-chart');
    await expect(chartElements).toHaveAttribute('role', 'img');
    await expect(chartElements).toHaveAttribute('aria-label');
    
    // Check color contrast and accessibility
    const accessibilityResults = await page.accessibility.snapshot();
    expect(accessibilityResults).toBeTruthy();
    
    // Test screen reader compatibility
    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('navigation')).toBeVisible();
  });
});