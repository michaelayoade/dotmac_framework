/**
 * Payment Test Helper - Utilities for E2E payment testing
 * Handles payment mocking, database interactions, and webhook simulation
 */

import { expect } from '@playwright/test';

export interface PaymentFormData {
  cardNumber: string;
  expiry: string;
  cvv: string;
  name: string;
  amount?: string;
  billingAddress?: {
    line1: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
  };
}

export interface TestPayment {
  amount: string;
  cardNumber: string;
  currency?: string;
  description?: string;
}

export interface ChargebackData {
  reason: string;
  amount: string;
  chargebackId: string;
  evidence?: string;
}

export interface TestCustomerData {
  email: string;
  failedAmount: string;
  failedDate: Date;
  name?: string;
}

export interface SubscriptionData {
  customerId: string;
  planId: string;
  paymentMethod: {
    cardNumber: string;
    expiry: string;
    cvv: string;
  };
}

export class PaymentTestHelper {
  constructor(private page: any) {}

  async setup() {
    // Set up payment testing environment

    // Mock payment processor endpoints
    await this.page.route('**/api/payments/**', async (route: any) => {
      const request = route.request();
      const url = request.url();
      const method = request.method();

      if (method === 'POST' && url.includes('/api/payments/process')) {
        const postData = request.postDataJSON();
        const response = await this.mockPaymentProcessing(postData);
        await route.fulfill({
          status: response.status,
          contentType: 'application/json',
          body: JSON.stringify(response.body),
        });
      } else if (method === 'POST' && url.includes('/api/payments/refund')) {
        const postData = request.postDataJSON();
        const response = await this.mockRefundProcessing(postData);
        await route.fulfill({
          status: response.status,
          contentType: 'application/json',
          body: JSON.stringify(response.body),
        });
      } else {
        await route.continue();
      }
    });

    // Mock 3DS authentication endpoints
    await this.page.route('**/api/3ds/**', async (route: any) => {
      const request = route.request();
      const postData = request.postDataJSON();
      const response = await this.mock3DSAuth(postData);
      await route.fulfill({
        status: response.status,
        contentType: 'application/json',
        body: JSON.stringify(response.body),
      });
    });

    // Mock chargeback webhook endpoint
    await this.page.route('**/webhooks/chargebacks', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ received: true }),
      });
    });

    // Set up test database state
    await this.initializeTestData();
  }

  async cleanup() {
    // Clean up test data and reset mocks
    await this.clearTestData();
  }

  async fillPaymentForm(data: PaymentFormData) {
    // Fill payment form with provided data
    await this.page.fill('[data-testid="card-number"]', data.cardNumber);
    await this.page.fill('[data-testid="expiry"]', data.expiry);
    await this.page.fill('[data-testid="cvv"]', data.cvv);
    await this.page.fill('[data-testid="cardholder-name"]', data.name);

    if (data.amount) {
      await this.page.fill('[data-testid="payment-amount"]', data.amount);
    }

    if (data.billingAddress) {
      await this.page.fill('[data-testid="address-line1"]', data.billingAddress.line1);
      await this.page.fill('[data-testid="city"]', data.billingAddress.city);
      await this.page.fill('[data-testid="state"]', data.billingAddress.state);
      await this.page.fill('[data-testid="postal-code"]', data.billingAddress.postal_code);
      await this.page.selectOption('[data-testid="country"]', data.billingAddress.country);
    }
  }

  private async mockPaymentProcessing(paymentData: any) {
    const { card_number, amount } = paymentData;

    // Simulate different responses based on test card numbers
    const responses = {
      // Successful payment
      '4242424242424242': {
        status: 200,
        body: {
          id: `pay_${Date.now()}`,
          status: 'COMPLETED',
          amount: amount,
          currency: 'USD',
          gateway_transaction_id: `txn_${Date.now()}`,
          authorization_code: 'AUTH123',
          processed_date: new Date().toISOString(),
        },
      },

      // Declined payment
      '4000000000000002': {
        status: 400,
        body: {
          error: 'payment_failed',
          message: 'Your card was declined',
          decline_reason: 'generic_decline',
          status: 'FAILED',
        },
      },

      // Insufficient funds
      '4000000000009995': {
        status: 400,
        body: {
          error: 'payment_failed',
          message: 'Your card has insufficient funds',
          decline_reason: 'insufficient_funds',
          status: 'FAILED',
        },
      },

      // Expired card
      '4000000000000069': {
        status: 400,
        body: {
          error: 'payment_failed',
          message: 'Your card has expired',
          decline_reason: 'expired_card',
          status: 'FAILED',
        },
      },

      // 3DS required
      '4000000000003220': {
        status: 200,
        body: {
          id: `pay_${Date.now()}`,
          status: 'PROCESSING',
          requires_3ds: true,
          three_ds_challenge_url: '/3ds/challenge',
          client_secret: `cs_${Date.now()}`,
        },
      },

      // 3DS authentication failed
      '4000000000003253': {
        status: 400,
        body: {
          error: 'authentication_failed',
          message: '3D Secure authentication failed',
          status: 'FAILED',
          three_ds_result: 'failed',
        },
      },

      // Fraudulent card
      '4100000000000019': {
        status: 400,
        body: {
          error: 'payment_failed',
          message: 'Your card was declined',
          decline_reason: 'fraudulent',
          status: 'FAILED',
        },
      },
    };

    return responses[card_number as keyof typeof responses] || responses['4000000000000002'];
  }

  private async mock3DSAuth(authData: any) {
    const { challenge_response } = authData;

    if (challenge_response === 'authenticate') {
      return {
        status: 200,
        body: {
          status: 'COMPLETED',
          authentication_result: 'success',
          payment_id: `pay_${Date.now()}`,
          redirect_url: '/payment/success',
        },
      };
    } else {
      return {
        status: 400,
        body: {
          status: 'FAILED',
          authentication_result: 'failed',
          error: '3D Secure authentication failed',
        },
      };
    }
  }

  private async mockRefundProcessing(refundData: any) {
    const { payment_id, amount, reason } = refundData;

    return {
      status: 200,
      body: {
        id: `ref_${Date.now()}`,
        payment_id: payment_id,
        amount: amount,
        status: 'REFUNDED',
        reason: reason,
        processed_date: new Date().toISOString(),
        gateway_refund_id: `rfnd_${Date.now()}`,
      },
    };
  }

  async createSuccessfulPayment(data: TestPayment): Promise<string> {
    // Create a successful payment record for testing
    const paymentId = `pay_test_${Date.now()}`;

    // Mock API call to create payment
    await this.page.evaluate(
      async (payment) => {
        // Store in session storage for testing
        const payments = JSON.parse(sessionStorage.getItem('test_payments') || '[]');
        payments.push({
          id: payment.id,
          amount: payment.amount,
          status: 'COMPLETED',
          card_number: payment.cardNumber.slice(-4),
          created_at: new Date().toISOString(),
        });
        sessionStorage.setItem('test_payments', JSON.stringify(payments));
      },
      { id: paymentId, ...data }
    );

    return paymentId;
  }

  async getLastPaymentStatus(): Promise<string> {
    // Get the status of the most recent payment
    const status = await this.page.evaluate(() => {
      const payments = JSON.parse(sessionStorage.getItem('test_payments') || '[]');
      return payments.length > 0 ? payments[payments.length - 1].status : 'UNKNOWN';
    });

    return status;
  }

  async getRefundStatus(paymentId: string): Promise<string> {
    // Get refund status for a specific payment
    const status = await this.page.evaluate((id) => {
      const refunds = JSON.parse(sessionStorage.getItem('test_refunds') || '[]');
      const refund = refunds.find((r: any) => r.payment_id === id);
      return refund ? refund.status : 'NOT_REFUNDED';
    }, paymentId);

    return status;
  }

  async getRefundAmount(paymentId: string): Promise<number> {
    const amount = await this.page.evaluate((id) => {
      const refunds = JSON.parse(sessionStorage.getItem('test_refunds') || '[]');
      const refund = refunds.find((r: any) => r.payment_id === id);
      return refund ? parseFloat(refund.amount) : 0;
    }, paymentId);

    return amount;
  }

  async getRemainingPaymentAmount(paymentId: string): Promise<number> {
    const remaining = await this.page.evaluate((id) => {
      const payments = JSON.parse(sessionStorage.getItem('test_payments') || '[]');
      const refunds = JSON.parse(sessionStorage.getItem('test_refunds') || '[]');

      const payment = payments.find((p: any) => p.id === id);
      const refund = refunds.find((r: any) => r.payment_id === id);

      if (!payment) return 0;

      const originalAmount = parseFloat(payment.amount);
      const refundedAmount = refund ? parseFloat(refund.amount) : 0;

      return originalAmount - refundedAmount;
    }, paymentId);

    return remaining;
  }

  async simulateChargeback(paymentId: string, chargebackData: ChargebackData) {
    // Simulate chargeback webhook
    await this.page.evaluate(
      async (data) => {
        const chargebacks = JSON.parse(sessionStorage.getItem('test_chargebacks') || '[]');
        chargebacks.push({
          id: data.chargebackId,
          payment_id: data.paymentId,
          reason: data.reason,
          amount: data.amount,
          status: 'received',
          created_at: new Date().toISOString(),
        });
        sessionStorage.setItem('test_chargebacks', JSON.stringify(chargebacks));
      },
      { ...chargebackData, paymentId }
    );
  }

  async createCustomerWithFailedPayment(customerData: TestCustomerData): Promise<string> {
    const customerId = `cust_${Date.now()}`;

    await this.page.evaluate(
      async (data) => {
        // Create customer with failed payment
        const customers = JSON.parse(sessionStorage.getItem('test_customers') || '[]');
        customers.push({
          id: data.customerId,
          email: data.email,
          name: data.name || 'Test Customer',
          failed_payment: {
            amount: data.failedAmount,
            failed_date: data.failedDate.toISOString(),
            retry_count: 1,
            next_retry: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days
          },
          dunning_stage: 'reminder_1',
          created_at: new Date().toISOString(),
        });
        sessionStorage.setItem('test_customers', JSON.stringify(customers));

        // Create dunning email record
        const emails = JSON.parse(sessionStorage.getItem('test_dunning_emails') || '[]');
        emails.push({
          customer_id: data.customerId,
          email_type: 'payment_failed_reminder',
          sent_at: new Date().toISOString(),
          subject: 'Payment Failed - Action Required',
          content: `Your payment of ${data.failedAmount} failed. Please update your payment method.`,
        });
        sessionStorage.setItem('test_dunning_emails', JSON.stringify(emails));
      },
      { customerId, ...customerData }
    );

    return customerId;
  }

  async getDunningEmails(customerId: string): Promise<string[]> {
    const emails = await this.page.evaluate((id) => {
      const dunningEmails = JSON.parse(sessionStorage.getItem('test_dunning_emails') || '[]');
      return dunningEmails
        .filter((email: any) => email.customer_id === id)
        .map((email: any) => email.content);
    }, customerId);

    return emails;
  }

  async createSubscription(data: SubscriptionData): Promise<string> {
    const subscriptionId = `sub_${Date.now()}`;

    await this.page.evaluate(
      async (subData) => {
        const subscriptions = JSON.parse(sessionStorage.getItem('test_subscriptions') || '[]');
        subscriptions.push({
          id: subData.subscriptionId,
          customer_id: subData.customerId,
          plan_id: subData.planId,
          status: 'active',
          current_period_start: new Date().toISOString(),
          current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
          payment_method: {
            card_last_four: subData.paymentMethod.cardNumber.slice(-4),
            brand: 'visa',
            exp_month: parseInt(subData.paymentMethod.expiry.split('/')[0]),
            exp_year: parseInt('20' + subData.paymentMethod.expiry.split('/')[1]),
          },
          created_at: new Date().toISOString(),
        });
        sessionStorage.setItem('test_subscriptions', JSON.stringify(subscriptions));
      },
      { subscriptionId, ...data }
    );

    return subscriptionId;
  }

  async triggerRecurringPayment(subscriptionId: string) {
    // Simulate recurring payment failure
    await this.page.evaluate(async (id) => {
      const subscriptions = JSON.parse(sessionStorage.getItem('test_subscriptions') || '[]');
      const subscription = subscriptions.find((s: any) => s.id === id);

      if (subscription) {
        // Mark as past due
        subscription.status = 'past_due';
        subscription.last_payment_error = {
          code: 'card_declined',
          message: 'Your card was declined',
          occurred_at: new Date().toISOString(),
        };
        subscription.retry_at = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString();

        sessionStorage.setItem('test_subscriptions', JSON.stringify(subscriptions));
      }
    }, subscriptionId);
  }

  private async initializeTestData() {
    // Initialize test data in browser storage
    await this.page.evaluate(() => {
      sessionStorage.setItem('test_payments', '[]');
      sessionStorage.setItem('test_refunds', '[]');
      sessionStorage.setItem('test_chargebacks', '[]');
      sessionStorage.setItem('test_customers', '[]');
      sessionStorage.setItem('test_dunning_emails', '[]');
      sessionStorage.setItem('test_subscriptions', '[]');
    });
  }

  private async clearTestData() {
    // Clear test data
    await this.page.evaluate(() => {
      sessionStorage.removeItem('test_payments');
      sessionStorage.removeItem('test_refunds');
      sessionStorage.removeItem('test_chargebacks');
      sessionStorage.removeItem('test_customers');
      sessionStorage.removeItem('test_dunning_emails');
      sessionStorage.removeItem('test_subscriptions');
    });
  }

  // Utility methods for common payment scenarios
  async waitForPaymentProcessing(timeout: number = 10000) {
    await this.page.waitForSelector('[data-testid="payment-processing"]', { timeout });
  }

  async waitForPaymentSuccess(timeout: number = 15000) {
    await this.page.waitForSelector('[data-testid="payment-success"]', { timeout });
  }

  async waitForPaymentError(timeout: number = 10000) {
    await this.page.waitForSelector('[data-testid="payment-error"]', { timeout });
  }

  async verifyPaymentSuccessMessage() {
    await expect(this.page.getByTestId('payment-success')).toBeVisible();
    await expect(this.page.getByText(/payment.*successful|transaction.*completed/i)).toBeVisible();
  }

  async verifyPaymentErrorMessage(expectedError?: string) {
    await expect(this.page.getByTestId('payment-error')).toBeVisible();
    if (expectedError) {
      await expect(this.page.getByText(new RegExp(expectedError, 'i'))).toBeVisible();
    }
  }

  // Helper for generating test card data
  static getTestCardData(
    scenario: 'success' | 'decline' | '3ds' | 'insufficient' | 'expired' | 'fraud'
  ) {
    const cards = {
      success: '4242424242424242',
      decline: '4000000000000002',
      '3ds': '4000000000003220',
      insufficient: '4000000000009995',
      expired: '4000000000000069',
      fraud: '4100000000000019',
    };

    return {
      cardNumber: cards[scenario],
      expiry: scenario === 'expired' ? '01/20' : '12/25',
      cvv: '123',
      name: 'Test Customer',
    };
  }
}
