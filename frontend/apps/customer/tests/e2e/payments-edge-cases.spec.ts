/**
 * Comprehensive payment edge cases E2E testing
 * Tests declined payments, 3DS authentication, refunds, chargebacks, and dunning
 */

import { test, expect } from '@playwright/test';
import { PaymentTestHelper } from '../../../testing/e2e/shared-scenarios/payment-test-helper';

// Payment edge case scenarios
class PaymentEdgeCasesJourney {
  constructor(
    public page: any,
    public paymentHelper: PaymentTestHelper
  ) {}

  async testDeclinedPayment() {
    console.log('Testing declined payment scenario');
    
    await this.page.goto('/billing/payment');
    
    // Use test card number that will be declined
    await this.paymentHelper.fillPaymentForm({
      cardNumber: '4000000000000002', // Declined card
      expiry: '12/25',
      cvv: '123',
      name: 'Test Customer',
      amount: '99.99'
    });
    
    await this.page.click('[data-testid="submit-payment"]');
    
    // Verify declined payment handling
    await expect(this.page.getByTestId('payment-error')).toBeVisible();
    await expect(this.page.getByText(/payment.*declined|card.*declined/i)).toBeVisible();
    await expect(this.page.getByTestId('retry-payment-button')).toBeVisible();
    
    // Verify payment status in database
    const paymentStatus = await this.paymentHelper.getLastPaymentStatus();
    expect(paymentStatus).toBe('FAILED');
    
    return true;
  }

  async test3DSAuthentication() {
    console.log('Testing 3DS authentication flow');
    
    await this.page.goto('/billing/payment');
    
    // Use 3DS test card
    await this.paymentHelper.fillPaymentForm({
      cardNumber: '4000000000003220', // 3DS required card
      expiry: '12/25', 
      cvv: '123',
      name: 'Test Customer',
      amount: '50.00'
    });
    
    await this.page.click('[data-testid="submit-payment"]');
    
    // Wait for 3DS challenge iframe
    await this.page.waitForSelector('[data-testid="3ds-challenge-frame"]', { timeout: 10000 });
    
    // Interact with 3DS challenge
    const challengeFrame = this.page.frameLocator('[data-testid="3ds-challenge-frame"]');
    await challengeFrame.click('[data-testid="authenticate-button"]');
    
    // Wait for authentication completion
    await this.page.waitForSelector('[data-testid="payment-processing"]', { timeout: 5000 });
    await this.page.waitForSelector('[data-testid="payment-success"]', { timeout: 15000 });
    
    // Verify successful 3DS payment
    await expect(this.page.getByTestId('payment-success')).toBeVisible();
    await expect(this.page.getByText(/payment.*successful|authenticated/i)).toBeVisible();
    
    const paymentStatus = await this.paymentHelper.getLastPaymentStatus();
    expect(paymentStatus).toBe('COMPLETED');
    
    return true;
  }

  async test3DSFailure() {
    console.log('Testing failed 3DS authentication');
    
    await this.page.goto('/billing/payment');
    
    await this.paymentHelper.fillPaymentForm({
      cardNumber: '4000000000003253', // 3DS authentication failure
      expiry: '12/25',
      cvv: '123', 
      name: 'Test Customer',
      amount: '75.50'
    });
    
    await this.page.click('[data-testid="submit-payment"]');
    
    // Wait for 3DS challenge
    await this.page.waitForSelector('[data-testid="3ds-challenge-frame"]', { timeout: 10000 });
    
    // Simulate authentication failure
    const challengeFrame = this.page.frameLocator('[data-testid="3ds-challenge-frame"]');
    await challengeFrame.click('[data-testid="decline-authentication"]');
    
    // Verify failed authentication handling
    await expect(this.page.getByTestId('payment-error')).toBeVisible();
    await expect(this.page.getByText(/authentication.*failed|3ds.*failed/i)).toBeVisible();
    
    const paymentStatus = await this.paymentHelper.getLastPaymentStatus();
    expect(paymentStatus).toBe('FAILED');
    
    return true;
  }

  async testRefundFlow() {
    console.log('Testing refund processing');
    
    // First, create a successful payment
    const paymentId = await this.paymentHelper.createSuccessfulPayment({
      amount: '125.00',
      cardNumber: '4242424242424242'
    });
    
    // Navigate to payment management
    await this.page.goto(`/billing/payments/${paymentId}`);
    
    // Initiate refund
    await this.page.click('[data-testid="refund-payment-button"]');
    
    // Fill refund form
    await this.page.fill('[data-testid="refund-amount"]', '125.00');
    await this.page.fill('[data-testid="refund-reason"]', 'Customer requested refund');
    await this.page.click('[data-testid="confirm-refund"]');
    
    // Verify refund processing
    await expect(this.page.getByTestId('refund-processing')).toBeVisible();
    await this.page.waitForSelector('[data-testid="refund-success"]', { timeout: 10000 });
    
    await expect(this.page.getByText(/refund.*successful|refund.*processed/i)).toBeVisible();
    
    // Verify refund status in database
    const refundStatus = await this.paymentHelper.getRefundStatus(paymentId);
    expect(refundStatus).toBe('REFUNDED');
    
    return true;
  }

  async testPartialRefund() {
    console.log('Testing partial refund');
    
    const paymentId = await this.paymentHelper.createSuccessfulPayment({
      amount: '200.00',
      cardNumber: '4242424242424242'
    });
    
    await this.page.goto(`/billing/payments/${paymentId}`);
    
    // Process partial refund
    await this.page.click('[data-testid="refund-payment-button"]');
    await this.page.fill('[data-testid="refund-amount"]', '75.00'); // Partial amount
    await this.page.fill('[data-testid="refund-reason"]', 'Partial refund - service issue');
    await this.page.click('[data-testid="confirm-refund"]');
    
    await this.page.waitForSelector('[data-testid="refund-success"]', { timeout: 10000 });
    
    // Verify partial refund details
    const refundAmount = await this.paymentHelper.getRefundAmount(paymentId);
    expect(refundAmount).toBe(75.00);
    
    const remainingAmount = await this.paymentHelper.getRemainingPaymentAmount(paymentId);
    expect(remainingAmount).toBe(125.00);
    
    return true;
  }

  async testChargebackHandling() {
    console.log('Testing chargeback processing');
    
    // Simulate chargeback webhook from payment processor
    const paymentId = await this.paymentHelper.createSuccessfulPayment({
      amount: '300.00',
      cardNumber: '4242424242424242'
    });
    
    // Simulate chargeback webhook
    await this.paymentHelper.simulateChargeback(paymentId, {
      reason: 'fraudulent',
      amount: '300.00',
      chargebackId: 'cb_test_123456'
    });
    
    // Check chargeback notification in admin portal
    await this.page.goto('/billing/chargebacks');
    
    await expect(this.page.getByTestId('chargeback-alert')).toBeVisible();
    await expect(this.page.getByText(/chargeback.*received/i)).toBeVisible();
    
    // Verify chargeback details
    await this.page.click(`[data-testid="chargeback-${paymentId}"]`);
    
    await expect(this.page.getByText('fraudulent')).toBeVisible();
    await expect(this.page.getByText('$300.00')).toBeVisible();
    
    // Test dispute submission
    await this.page.click('[data-testid="dispute-chargeback"]');
    await this.page.fill('[data-testid="dispute-evidence"]', 'Valid transaction with customer signature');
    await this.page.click('[data-testid="submit-dispute"]');
    
    await expect(this.page.getByText(/dispute.*submitted/i)).toBeVisible();
    
    return true;
  }

  async testDunningProcess() {
    console.log('Testing dunning process for failed payments');
    
    // Create customer with failed payment
    const customerId = await this.paymentHelper.createCustomerWithFailedPayment({
      email: 'dunning-test@example.com',
      failedAmount: '99.99',
      failedDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) // 7 days ago
    });
    
    // Verify dunning email sent
    const dunningEmails = await this.paymentHelper.getDunningEmails(customerId);
    expect(dunningEmails.length).toBeGreaterThan(0);
    expect(dunningEmails[0]).toContain('payment.*failed|overdue.*payment');
    
    // Check dunning dashboard
    await this.page.goto('/billing/dunning');
    
    await expect(this.page.getByTestId('dunning-dashboard')).toBeVisible();
    await expect(this.page.getByText('1 customer')).toBeVisible(); // 1 in dunning
    
    // Test retry payment from dunning
    await this.page.click(`[data-testid="retry-payment-${customerId}"]`);
    
    // Use successful card for retry
    await this.paymentHelper.fillPaymentForm({
      cardNumber: '4242424242424242',
      expiry: '12/25',
      cvv: '123',
      name: 'Test Customer',
      amount: '99.99'
    });
    
    await this.page.click('[data-testid="submit-payment"]');
    
    await expect(this.page.getByTestId('payment-success')).toBeVisible();
    
    // Verify customer removed from dunning
    await this.page.goto('/billing/dunning');
    await expect(this.page.getByText('0 customers')).toBeVisible();
    
    return true;
  }

  async testInsufficientFunds() {
    console.log('Testing insufficient funds scenario');
    
    await this.page.goto('/billing/payment');
    
    await this.paymentHelper.fillPaymentForm({
      cardNumber: '4000000000009995', // Insufficient funds card
      expiry: '12/25',
      cvv: '123',
      name: 'Test Customer',
      amount: '150.00'
    });
    
    await this.page.click('[data-testid="submit-payment"]');
    
    await expect(this.page.getByTestId('payment-error')).toBeVisible();
    await expect(this.page.getByText(/insufficient.*funds|card.*declined/i)).toBeVisible();
    
    // Verify specific error handling for insufficient funds
    await expect(this.page.getByTestId('insufficient-funds-message')).toBeVisible();
    await expect(this.page.getByTestId('alternative-payment-methods')).toBeVisible();
    
    return true;
  }

  async testExpiredCard() {
    console.log('Testing expired card scenario');
    
    await this.page.goto('/billing/payment');
    
    await this.paymentHelper.fillPaymentForm({
      cardNumber: '4000000000000069', // Expired card
      expiry: '01/20', // Expired date
      cvv: '123',
      name: 'Test Customer',
      amount: '85.00'
    });
    
    await this.page.click('[data-testid="submit-payment"]');
    
    await expect(this.page.getByTestId('payment-error')).toBeVisible();
    await expect(this.page.getByText(/card.*expired|expired.*card/i)).toBeVisible();
    await expect(this.page.getByTestId('update-payment-method')).toBeVisible();
    
    return true;
  }

  async testRecurringPaymentFailure() {
    console.log('Testing recurring payment failure handling');
    
    // Set up subscription with failing card
    const subscriptionId = await this.paymentHelper.createSubscription({
      customerId: 'test-customer-123',
      planId: 'monthly-plan',
      paymentMethod: {
        cardNumber: '4000000000000341', // Attaching to customer will succeed, charging will fail
        expiry: '12/25',
        cvv: '123'
      }
    });
    
    // Simulate recurring payment attempt
    await this.paymentHelper.triggerRecurringPayment(subscriptionId);
    
    // Check subscription status
    await this.page.goto(`/billing/subscriptions/${subscriptionId}`);
    
    await expect(this.page.getByTestId('subscription-status')).toContainText('Past Due');
    await expect(this.page.getByTestId('payment-retry-date')).toBeVisible();
    
    // Test manual retry
    await this.page.click('[data-testid="retry-subscription-payment"]');
    
    // Update with working payment method
    await this.page.click('[data-testid="update-payment-method"]');
    await this.paymentHelper.fillPaymentForm({
      cardNumber: '4242424242424242',
      expiry: '12/25', 
      cvv: '123',
      name: 'Test Customer'
    });
    
    await this.page.click('[data-testid="save-payment-method"]');
    await this.page.click('[data-testid="retry-payment-now"]');
    
    await expect(this.page.getByTestId('subscription-status')).toContainText('Active');
    
    return true;
  }
}

test.describe('Payment Edge Cases', () => {
  let paymentHelper: PaymentTestHelper;

  test.beforeEach(async ({ page }) => {
    paymentHelper = new PaymentTestHelper(page);
    await paymentHelper.setup();
  });

  test.afterEach(async ({ page }) => {
    await paymentHelper.cleanup();
  });

  test('handles declined payments correctly @payments @edge-case', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    await test.step('test declined payment', async () => {
      const result = await journey.testDeclinedPayment();
      expect(result).toBe(true);
    });
  });

  test('processes 3DS authentication successfully @payments @3ds @edge-case', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    await test.step('test successful 3DS', async () => {
      const result = await journey.test3DSAuthentication();
      expect(result).toBe(true);
    });
    
    await test.step('test failed 3DS', async () => {
      const result = await journey.test3DSFailure(); 
      expect(result).toBe(true);
    });
  });

  test('handles refunds properly @payments @refunds @edge-case', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    await test.step('test full refund', async () => {
      const result = await journey.testRefundFlow();
      expect(result).toBe(true);
    });
    
    await test.step('test partial refund', async () => {
      const result = await journey.testPartialRefund();
      expect(result).toBe(true);
    });
  });

  test('processes chargebacks correctly @payments @chargebacks @edge-case', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    await test.step('test chargeback handling', async () => {
      const result = await journey.testChargebackHandling();
      expect(result).toBe(true);
    });
  });

  test('executes dunning process effectively @payments @dunning @edge-case', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    await test.step('test dunning process', async () => {
      const result = await journey.testDunningProcess();
      expect(result).toBe(true);
    });
  });

  test('handles various card errors @payments @card-errors @edge-case', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    await test.step('test insufficient funds', async () => {
      const result = await journey.testInsufficientFunds();
      expect(result).toBe(true);
    });
    
    await test.step('test expired card', async () => {
      const result = await journey.testExpiredCard();
      expect(result).toBe(true);
    });
  });

  test('manages recurring payment failures @payments @subscriptions @edge-case', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    await test.step('test recurring payment failure', async () => {
      const result = await journey.testRecurringPaymentFailure();
      expect(result).toBe(true);
    });
  });

  test('payment edge cases performance @payments @performance', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    const startTime = Date.now();
    
    // Run multiple edge cases in sequence
    await journey.testDeclinedPayment();
    await journey.testRefundFlow();
    await journey.testInsufficientFunds();
    
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(60000); // 1 minute max for edge cases
  });

  test('payment accessibility in error states @payments @a11y', async ({ page }) => {
    const journey = new PaymentEdgeCasesJourney(page, paymentHelper);
    
    // Test declined payment accessibility
    await journey.testDeclinedPayment();
    
    // Check error message accessibility
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByTestId('payment-error')).toHaveAttribute('aria-live', 'assertive');
    
    // Check retry button accessibility
    const retryButton = page.getByTestId('retry-payment-button');
    await expect(retryButton).toBeVisible();
    await expect(retryButton).toHaveAttribute('aria-label');
    
    // Test keyboard navigation
    await retryButton.focus();
    await expect(retryButton).toBeFocused();
  });
});

// Test utilities for payment edge cases
export const paymentEdgeCaseUtils = {
  // Test card numbers for different scenarios
  testCards: {
    declined: '4000000000000002',
    insufficientFunds: '4000000000009995',
    expired: '4000000000000069',
    fraudulent: '4100000000000019',
    3dsRequired: '4000000000003220',
    3dsFailed: '4000000000003253',
    processingError: '4000000000000119'
  },

  // Verify payment states
  async verifyPaymentState(page: any, expectedState: string) {
    const statusElement = page.getByTestId('payment-status');
    await expect(statusElement).toContainText(expectedState);
  },

  // Generate test data for edge cases
  generateTestPayment(scenario: string) {
    const basePayment = {
      amount: '99.99',
      currency: 'USD',
      description: `Test payment for ${scenario}`,
      expiry: '12/25',
      cvv: '123',
      name: 'Test Customer'
    };

    const cardNumbers: Record<string, string> = this.testCards;
    return {
      ...basePayment,
      cardNumber: cardNumbers[scenario] || cardNumbers.declined
    };
  }
};