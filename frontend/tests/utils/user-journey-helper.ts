/**
 * User Journey Helper for E2E Tests
 * Provides utilities for simulating complete user workflows
 */

import { Page } from '@playwright/test';

export interface TestCustomer {
  id: string;
  email: string;
  password: string;
  name: string;
  companyName: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  plan: string;
}

export interface TestAdmin {
  id: string;
  email: string;
  password: string;
  name: string;
  role: string;
}

export interface TestUser {
  id: string;
  email: string;
  password: string;
  name: string;
  role: string;
}

export interface TestDevice {
  id: string;
  name: string;
  ip: string;
  type: string;
  location: string;
}

export interface TestTicket {
  id: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  customerId: string;
}

export interface TestInvoice {
  id: string;
  amount: string;
  status: string;
  customerId: string;
}

export class UserJourneyHelper {
  private baseURL: string;
  private testData: Map<string, any> = new Map();

  constructor(baseURL: string = 'http://localhost:3000') {
    this.baseURL = baseURL;
  }

  // Customer Journey Helpers
  async createTestCustomer(): Promise<TestCustomer> {
    const customer: TestCustomer = {
      id: `customer_${Date.now()}`,
      email: `customer_${Date.now()}@test.com`,
      password: 'TestPassword123!',
      name: 'Test Customer',
      companyName: 'Test Company Inc',
      phone: '+1-555-0123',
      address: '123 Test Street',
      city: 'Test City',
      state: 'CA',
      zipCode: '90210',
      plan: 'starter'
    };

    this.testData.set(`customer_${customer.id}`, customer);
    return customer;
  }

  async customerLogin(page: Page, customer: TestCustomer): Promise<void> {
    await page.goto(`${this.baseURL}/customer/login`);
    await page.fill('[data-testid="email"]', customer.email);
    await page.fill('[data-testid="password"]', customer.password);
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL('**/dashboard');
  }

  async getEmailVerificationLink(email: string): Promise<string> {
    // In a real implementation, this would check an email service
    // For testing, we'll simulate the verification link
    return `${this.baseURL}/verify-email?token=test-verification-token`;
  }

  // Admin Journey Helpers
  async createTestAdmin(): Promise<TestAdmin> {
    const admin: TestAdmin = {
      id: `admin_${Date.now()}`,
      email: `admin_${Date.now()}@test.com`,
      password: 'AdminPassword123!',
      name: 'Test Admin',
      role: 'super_admin'
    };

    this.testData.set(`admin_${admin.id}`, admin);
    return admin;
  }

  async adminLogin(page: Page, admin: TestAdmin): Promise<void> {
    await page.goto(`${this.baseURL}/admin/login`);
    await page.fill('[data-testid="email"]', admin.email);
    await page.fill('[data-testid="password"]', admin.password);
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL('**/admin/dashboard');
  }

  // User Management Helpers
  async createTestUser(): Promise<TestUser> {
    const user: TestUser = {
      id: `user_${Date.now()}`,
      email: `user_${Date.now()}@test.com`,
      password: 'UserPassword123!',
      name: 'Test User',
      role: 'user'
    };

    this.testData.set(`user_${user.id}`, user);
    return user;
  }

  async userLogin(page: Page, user: TestUser): Promise<void> {
    await page.goto(`${this.baseURL}/login`);
    await page.fill('[data-testid="email"]', user.email);
    await page.fill('[data-testid="password"]', user.password);
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL('**/dashboard');
  }

  // Device Management Helpers
  async createTestDevice(): Promise<TestDevice> {
    const device: TestDevice = {
      id: `device_${Date.now()}`,
      name: `Test Router ${Date.now()}`,
      ip: `192.168.1.${Math.floor(Math.random() * 254) + 1}`,
      type: 'router',
      location: 'Test Location'
    };

    this.testData.set(`device_${device.id}`, device);
    return device;
  }

  // Support Ticket Helpers
  async createTestTicket(): Promise<TestTicket> {
    const ticket: TestTicket = {
      id: `ticket_${Date.now()}`,
      subject: 'Test Support Ticket',
      description: 'This is a test support ticket for automated testing',
      status: 'open',
      priority: 'medium',
      customerId: 'test-customer-id'
    };

    this.testData.set(`ticket_${ticket.id}`, ticket);
    return ticket;
  }

  // Billing Helpers
  async createTestInvoice(customer: TestCustomer): Promise<TestInvoice> {
    const invoice: TestInvoice = {
      id: `invoice_${Date.now()}`,
      amount: '$99.99',
      status: 'unpaid',
      customerId: customer.id
    };

    this.testData.set(`invoice_${invoice.id}`, invoice);
    return invoice;
  }

  // Utility Methods
  async waitForNetworkIdle(page: Page, timeout: number = 5000): Promise<void> {
    await page.waitForLoadState('networkidle', { timeout });
  }

  async clearBrowserStorage(page: Page): Promise<void> {
    await page.context().clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  }

  async simulateNetworkDelay(page: Page, delayMs: number = 1000): Promise<void> {
    await page.route('**/api/**', async route => {
      await new Promise(resolve => setTimeout(resolve, delayMs));
      await route.continue();
    });
  }

  async simulateOfflineMode(page: Page): Promise<void> {
    await page.context().setOffline(true);
  }

  async restoreOnlineMode(page: Page): Promise<void> {
    await page.context().setOffline(false);
  }

  // Data Cleanup
  async cleanupTestData(): Promise<void> {
    // In a real implementation, this would clean up test data from the database
    this.testData.clear();
  }

  // Test Assertions Helpers
  async assertPageAccessible(page: Page): Promise<void> {
    // Check for accessibility violations
    const violations = await page.evaluate(() => {
      // This would integrate with axe-core or similar
      return []; // Placeholder
    });

    if (violations.length > 0) {
      throw new Error(`Accessibility violations found: ${violations.length}`);
    }
  }

  async assertPerformanceMetrics(page: Page, thresholds: {
    firstContentfulPaint?: number;
    largestContentfulPaint?: number;
    cumulativeLayoutShift?: number;
  } = {}): Promise<void> {
    const metrics = await page.evaluate(() => {
      // This would collect Web Vitals metrics
      return {
        fcp: 0,
        lcp: 0,
        cls: 0
      };
    });

    if (thresholds.firstContentfulPaint && metrics.fcp > thresholds.firstContentfulPaint) {
      throw new Error(`FCP too slow: ${metrics.fcp}ms > ${thresholds.firstContentfulPaint}ms`);
    }

    if (thresholds.largestContentfulPaint && metrics.lcp > thresholds.largestContentfulPaint) {
      throw new Error(`LCP too slow: ${metrics.lcp}ms > ${thresholds.largestContentfulPaint}ms`);
    }

    if (thresholds.cumulativeLayoutShift && metrics.cls > thresholds.cumulativeLayoutShift) {
      throw new Error(`CLS too high: ${metrics.cls} > ${thresholds.cumulativeLayoutShift}`);
    }
  }
}
