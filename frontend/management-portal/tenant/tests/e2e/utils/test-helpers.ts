/**
 * Test Helper Functions for Tenant Portal E2E Tests
 * Common utilities and authentication helpers
 */

import { Page, expect, BrowserContext } from '@playwright/test';
import { TestDataFactory, TestTenant, DEFAULT_TEST_TENANT } from './test-data-factory';
import { LoginPage } from './page-objects';

export interface TestSession {
  tenant: TestTenant;
  authToken?: string;
  cookies?: any[];
}

export class AuthHelper {
  /**
   * Authenticate as a test tenant admin
   */
  static async loginAsTenant(page: Page, tenant: TestTenant = DEFAULT_TEST_TENANT): Promise<void> {
    const loginPage = new LoginPage(page);
    await loginPage.goto();

    // Use the tenant admin credentials
    const adminUser = tenant.users.find((user) => user.role === 'admin') || tenant.users[0];
    await loginPage.login(adminUser.email, 'TestPassword123!');

    // Wait for successful authentication
    await expect(page).toHaveURL(/\/dashboard/);
    await page.waitForSelector('[data-testid="dashboard"]');
  }

  /**
   * Set up authentication context for multiple tests
   */
  static async setupAuthContext(context: BrowserContext): Promise<void> {
    const page = await context.newPage();
    await this.loginAsTenant(page);

    // Store authentication state
    await context.storageState({ path: '.auth/tenant-state.json' });
    await page.close();
  }

  /**
   * Mock API authentication responses
   */
  static async mockAuthAPI(page: Page, tenant: TestTenant): Promise<void> {
    // Mock authentication endpoints
    await page.route('**/api/auth/**', async (route) => {
      const url = route.request().url();

      if (url.includes('/login')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            user: tenant.users.find((u) => u.role === 'admin'),
            token: 'mock-jwt-token',
          }),
        });
      } else if (url.includes('/me')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            user: tenant.users.find((u) => u.role === 'admin'),
            tenant: tenant,
          }),
        });
      } else {
        await route.continue();
      }
    });
  }
}

export class APIHelper {
  /**
   * Mock subscription management API responses
   */
  static async mockSubscriptionAPI(page: Page, tenant: TestTenant): Promise<void> {
    // Mock subscription endpoints
    await page.route('**/api/subscriptions/**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();

      if (url.includes('/subscriptions') && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            subscriptions: tenant.subscriptions,
            total: tenant.subscriptions.length,
          }),
        });
      } else if (url.includes('/subscribe') && method === 'POST') {
        const requestBody = JSON.parse(route.request().postData() || '{}');
        const newSubscription = TestDataFactory.createSubscription({
          appId: requestBody.appId,
          appName: requestBody.appName,
          appCategory: requestBody.appCategory,
          tier: requestBody.tier,
          licenses: requestBody.licenses,
          status: 'active',
        });

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            subscription: newSubscription,
          }),
        });
      } else if (url.includes('/upgrade') && method === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Subscription upgraded successfully',
          }),
        });
      } else if (url.includes('/cancel') && method === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Subscription cancelled successfully',
          }),
        });
      } else {
        await route.continue();
      }
    });
  }

  /**
   * Mock app catalog API responses
   */
  static async mockAppCatalogAPI(page: Page): Promise<void> {
    const catalogData = TestDataFactory.createAppCatalog();

    await page.route('**/api/apps/**', async (route) => {
      const url = route.request().url();

      if (url.includes('/catalog')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(catalogData),
        });
      } else {
        await route.continue();
      }
    });
  }

  /**
   * Mock license management API responses
   */
  static async mockLicenseAPI(page: Page, tenant: TestTenant): Promise<void> {
    await page.route('**/api/licenses/**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();

      if (url.includes('/licenses') && method === 'GET') {
        const licenses = tenant.subscriptions.map((sub) =>
          TestDataFactory.createLicense({
            appId: sub.appId,
            limit: sub.licenses,
            used: sub.usedLicenses,
          })
        );

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ licenses }),
        });
      } else if (url.includes('/upgrade') && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'License upgrade request submitted',
          }),
        });
      } else {
        await route.continue();
      }
    });
  }

  /**
   * Mock billing API responses
   */
  static async mockBillingAPI(page: Page, tenant: TestTenant): Promise<void> {
    await page.route('**/api/billing/**', async (route) => {
      const url = route.request().url();

      if (url.includes('/current')) {
        const totalAmount = tenant.subscriptions.reduce((sum, sub) => sum + sub.monthlyPrice, 0);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            amount: totalAmount,
            dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
            status: 'pending',
          }),
        });
      } else if (url.includes('/history')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            invoices: [
              { id: '1', date: '2024-01-01', amount: 299, status: 'paid' },
              { id: '2', date: '2024-02-01', amount: 299, status: 'paid' },
              { id: '3', date: '2024-03-01', amount: 399, status: 'pending' },
            ],
          }),
        });
      } else {
        await route.continue();
      }
    });
  }
}

export class TestUtils {
  /**
   * Wait for element to be visible and stable
   */
  static async waitForStableElement(
    page: Page,
    selector: string,
    timeout: number = 10000
  ): Promise<void> {
    await page.waitForSelector(selector, { state: 'visible', timeout });
    await page.waitForLoadState('networkidle');
  }

  /**
   * Take screenshot with timestamp
   */
  static async takeScreenshot(page: Page, name: string): Promise<void> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    await page.screenshot({
      path: `test-results/screenshots/${name}-${timestamp}.png`,
      fullPage: true,
    });
  }

  /**
   * Assert element exists and is visible
   */
  static async assertElementVisible(page: Page, selector: string, message?: string): Promise<void> {
    const element = page.locator(selector);
    await expect(element, message || `Element ${selector} should be visible`).toBeVisible();
  }

  /**
   * Assert element contains text
   */
  static async assertElementText(
    page: Page,
    selector: string,
    expectedText: string
  ): Promise<void> {
    const element = page.locator(selector);
    await expect(element).toContainText(expectedText);
  }

  /**
   * Assert element has attribute
   */
  static async assertElementAttribute(
    page: Page,
    selector: string,
    attribute: string,
    expectedValue: string
  ): Promise<void> {
    const element = page.locator(selector);
    await expect(element).toHaveAttribute(attribute, expectedValue);
  }

  /**
   * Wait for API call to complete
   */
  static async waitForAPICall(page: Page, urlPattern: string): Promise<void> {
    await page.waitForResponse(
      (response) => response.url().includes(urlPattern) && response.status() === 200
    );
  }

  /**
   * Clear all cookies and storage
   */
  static async clearBrowserData(page: Page): Promise<void> {
    await page.context().clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  }

  /**
   * Generate unique test ID
   */
  static generateTestId(prefix: string = 'test'): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2, 5);
    return `${prefix}-${timestamp}-${random}`;
  }

  /**
   * Retry operation with exponential backoff
   */
  static async retry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    baseDelay: number = 1000
  ): Promise<T> {
    let lastError: Error;

    for (let i = 0; i < maxRetries; i++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        if (i < maxRetries - 1) {
          const delay = baseDelay * Math.pow(2, i);
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError!;
  }

  /**
   * Assert no console errors occurred during test
   */
  static async assertNoConsoleErrors(page: Page): Promise<void> {
    const errors: string[] = [];

    page.on('console', (message) => {
      if (message.type() === 'error') {
        errors.push(message.text());
      }
    });

    // Check at the end of test
    expect(errors, `Console errors found: ${errors.join(', ')}`).toHaveLength(0);
  }
}

export class PerformanceHelper {
  /**
   * Measure page load performance
   */
  static async measurePageLoad(
    page: Page
  ): Promise<{ loadTime: number; domContentLoaded: number }> {
    const startTime = Date.now();

    await page.waitForLoadState('domcontentloaded');
    const domContentLoaded = Date.now() - startTime;

    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    return { loadTime, domContentLoaded };
  }

  /**
   * Assert page loads within acceptable time
   */
  static async assertPagePerformance(
    page: Page,
    maxLoadTime: number = 3000,
    maxDOMTime: number = 1500
  ): Promise<void> {
    const metrics = await this.measurePageLoad(page);

    expect(metrics.domContentLoaded, 'DOM Content Loaded should be under threshold').toBeLessThan(
      maxDOMTime
    );
    expect(metrics.loadTime, 'Page Load should be under threshold').toBeLessThan(maxLoadTime);
  }
}
