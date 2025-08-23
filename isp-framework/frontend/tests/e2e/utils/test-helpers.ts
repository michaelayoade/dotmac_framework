/**
 * E2E Test Helper Utilities
 * Following backend testing patterns for comprehensive E2E support
 */

import { expect, type Page } from '@playwright/test';

export class E2ETestHelpers {
  constructor(private page: Page) {}

  // Authentication helpers
  async loginAs(role: 'admin' | 'customer' | 'reseller') {
    await this.page.goto('/login');

    const credentials = {
      admin: { email: 'admin@test.com', password: 'admin-password' },
      customer: { email: 'customer@test.com', password: 'customer-password' },
      reseller: { email: 'reseller@test.com', password: 'reseller-password' },
    };

    const { email, password } = credentials[role];

    await this.page.fill('[data-testid="email-input"]', email);
    await this.page.fill('[data-testid="password-input"]', password);
    await this.page.click('[data-testid="login-button"]');

    // Wait for redirect to dashboard
    await this.page.waitForURL(/\/(admin|customer|reseller)\/dashboard/);

    // Verify login success
    await expect(this.page.locator('[data-testid="user-menu"]')).toBeVisible();
  }

  async logout() {
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout-button"]');
    await this.page.waitForURL('/login');
  }

  // Navigation helpers
  async navigateTo(portal: 'admin' | 'customer' | 'reseller', path: string) {
    const url = `/${portal}${path}`;
    await this.page.goto(url);
    await this.page.waitForLoadState('networkidle');
  }

  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForSelector('[data-testid="page-loaded"]', { timeout: 10000 });
  }

  // Form helpers
  async fillForm(formData: Record<string, string>) {
    for (const [field, value] of Object.entries(formData)) {
      const input = this.page.locator(`[data-testid="${field}-input"]`);
      await input.fill(value);
    }
  }

  async submitForm(formTestId = 'form-submit') {
    await this.page.click(`[data-testid="${formTestId}"]`);
  }

  // Table helpers
  async getTableRowCount(tableTestId = 'data-table') {
    const rows = this.page.locator(`[data-testid="${tableTestId}"] tbody tr`);
    return await rows.count();
  }

  async searchTable(searchTerm: string, searchTestId = 'search-input') {
    await this.page.fill(`[data-testid="${searchTestId}"]`, searchTerm);
    await this.page.waitForTimeout(500); // Debounce
  }

  async selectTableRow(index: number, tableTestId = 'data-table') {
    await this.page.click(
      `[data-testid="${tableTestId}"] tbody tr:nth-child(${index + 1}) input[type="checkbox"]`
    );
  }

  // Modal helpers
  async waitForModal(modalTestId = 'modal') {
    await expect(this.page.locator(`[data-testid="${modalTestId}"]`)).toBeVisible();
  }

  async closeModal(closeTestId = 'modal-close') {
    await this.page.click(`[data-testid="${closeTestId}"]`);
    await expect(this.page.locator('[data-testid="modal"]')).not.toBeVisible();
  }

  // Error handling
  async expectErrorMessage(message: string) {
    await expect(this.page.locator('[data-testid="error-message"]')).toContainText(message);
  }

  async expectSuccessMessage(message: string) {
    await expect(this.page.locator('[data-testid="success-message"]')).toContainText(message);
  }

  // Loading states
  async waitForLoading() {
    await expect(this.page.locator('[data-testid="loading"]')).toBeVisible();
  }

  async waitForLoadingToComplete() {
    await expect(this.page.locator('[data-testid="loading"]')).not.toBeVisible();
  }

  // API mocking helpers
  async mockApiCall(endpoint: string, response: unknown, status = 200) {
    await this.page.route(endpoint, (route) => {
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(response),
      });
    });
  }

  async mockApiError(endpoint: string, status = 500, message = 'Internal Server Error') {
    await this.page.route(endpoint, (route) => {
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({ error: { message, status } }),
      });
    });
  }

  // Screenshot helpers
  async takeScreenshot(name: string) {
    await this.page.screenshot({
      path: `test-results/screenshots/${name}.png`,
      fullPage: true,
    });
  }

  async takeElementScreenshot(selector: string, name: string) {
    await this.page.locator(selector).screenshot({
      path: `test-results/screenshots/${name}.png`,
    });
  }

  // Performance helpers
  async measurePageLoadTime() {
    const startTime = Date.now();
    await this.page.waitForLoadState('networkidle');
    return Date.now() - startTime;
  }

  async getCoreWebVitals() {
    return await this.page.evaluate(() => {
      return new Promise((resolve) => {
        const vitals: any = {
          fcp: 0,
          lcp: 0,
          cls: 0,
        };

        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries();

          entries.forEach((entry) => {
            if (entry.entryType === 'paint' && entry.name === 'first-contentful-paint') {
              vitals.fcp = entry.startTime;
            }
            if (entry.entryType === 'largest-contentful-paint') {
              vitals.lcp = entry.startTime;
            }
            if (entry.entryType === 'layout-shift' && !(entry as any).hadRecentInput) {
              vitals.cls = (vitals.cls || 0) + (entry as any).value;
            }
          });

          resolve(vitals);
        });

        observer.observe({
          entryTypes: ['paint', 'largest-contentful-paint', 'layout-shift'],
        });

        // Fallback timeout
        setTimeout(() => resolve(vitals), 5000);
      });
    });
  }

  // Accessibility helpers
  async checkA11y() {
    const results = await this.page.evaluate(async () => {
      // @ts-expect-error - axe may not be available in all environments
      if (typeof axe !== 'undefined') {
        // @ts-expect-error - axe may not be available in all environments
        return await axe.run();
      }
      return null;
    });

    if (results && results.violations.length > 0) {
      return results.violations;
    }

    return [];
  }

  // Mobile helpers
  async setMobileViewport() {
    await this.page.setViewportSize({ width: 375, height: 667 });
  }

  async setDesktopViewport() {
    await this.page.setViewportSize({ width: 1280, height: 720 });
  }

  // Wait helpers
  async waitForText(text: string, timeout = 10000) {
    await expect(this.page.locator(`text=${text}`)).toBeVisible({ timeout });
  }

  async waitForElement(selector: string, timeout = 10000) {
    await expect(this.page.locator(selector)).toBeVisible({ timeout });
  }

  // Data helpers
  createTestCustomer(
    overrides = {
      // Implementation pending
    }
  ) {
    return {
      name: 'E2E Test Customer',
      email: 'e2e-customer@test.com',
      phone: '+1 (555) 123-4567',
      address: '123 E2E Test St',
      plan: 'business_pro',
      ...overrides,
    };
  }

  createTestService(
    overrides = {
      // Implementation pending
    }
  ) {
    return {
      name: 'E2E Test Service',
      type: 'internet',
      speedDown: 100,
      speedUp: 20,
      monthlyPrice: 79.99,
      ...overrides,
    };
  }
}

// Export helper function to create test helpers
export function createTestHelpers(page: Page) {
  return new E2ETestHelpers(page);
}
