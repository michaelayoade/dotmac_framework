/**
 * Smoke Tests for Critical Path Validation
 * Quick tests to verify essential functionality is working
 */

import { test, expect } from '@playwright/test';
import { TestDataFactory, DEFAULT_TEST_TENANT } from './utils/test-data-factory';
import { AuthHelper, APIHelper, TestUtils, PerformanceHelper } from './utils/test-helpers';
import {
  DashboardPage,
  SubscriptionManagementPage,
  LicenseManagementPage,
} from './utils/page-objects';
import { TEST_CONFIG } from './test.config';

test.describe('Smoke Tests @smoke @critical', () => {
  let testTenant = DEFAULT_TEST_TENANT;

  test.beforeEach(async ({ page }) => {
    // Set up minimal mocking for smoke tests
    await AuthHelper.mockAuthAPI(page, testTenant);
    await APIHelper.mockSubscriptionAPI(page, testTenant);
    await APIHelper.mockLicenseAPI(page, testTenant);

    // Quick authentication
    await AuthHelper.loginAsTenant(page, testTenant);
  });

  test('should successfully login and access dashboard @smoke', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Navigate to dashboard
    await dashboardPage.goto();

    // Verify dashboard loads within performance threshold
    await PerformanceHelper.assertPagePerformance(
      page,
      TEST_CONFIG.performance.pageLoad,
      TEST_CONFIG.performance.domReady
    );

    // Verify essential dashboard elements are present
    await TestUtils.assertElementVisible(page, '[data-testid="dashboard"]');
    await TestUtils.assertElementVisible(page, '[data-testid="navigation-menu"]');
    await TestUtils.assertElementVisible(page, '[data-testid="subscriptions-card"]');
    await TestUtils.assertElementVisible(page, '[data-testid="license-usage-card"]');

    // Verify user context is displayed
    await TestUtils.assertElementVisible(page, '[data-testid="user-profile"]');
    await TestUtils.assertElementText(page, '[data-testid="tenant-name"]', testTenant.name);
  });

  test('should display subscription overview correctly @smoke', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();

    // Verify subscription count is accurate
    const subscriptionCount = await dashboardPage.getSubscriptionCount();
    expect(subscriptionCount).toBe(testTenant.subscriptions.length);

    // Verify subscription card shows key metrics
    const subscriptionsCard = page.locator('[data-testid="subscriptions-card"]');
    await expect(subscriptionsCard.locator('[data-testid="active-subscriptions"]')).toBeVisible();
    await expect(subscriptionsCard.locator('[data-testid="subscription-breakdown"]')).toBeVisible();

    // Quick navigation test to subscription management
    await dashboardPage.navigateToSubscriptions();
    await expect(page).toHaveURL(/\/subscriptions/);
    await TestUtils.assertElementVisible(page, '[data-testid="subscription-management"]');
  });

  test('should show license usage with correct calculations @smoke', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();

    // Verify license usage percentage
    const usagePercentage = await dashboardPage.getLicenseUsagePercentage();

    // Calculate expected usage
    const totalLicenses = testTenant.subscriptions.reduce((sum, s) => sum + s.licenses, 0);
    const usedLicenses = testTenant.subscriptions.reduce((sum, s) => sum + s.usedLicenses, 0);
    const expectedPercentage = Math.round((usedLicenses / totalLicenses) * 100);

    expect(usagePercentage).toBe(expectedPercentage);

    // Verify license card displays key information
    const licenseCard = page.locator('[data-testid="license-usage-card"]');
    await expect(licenseCard.locator('[data-testid="usage-progress-bar"]')).toBeVisible();
    await expect(licenseCard.locator('[data-testid="license-breakdown"]')).toBeVisible();
  });

  test('should provide working navigation between main sections @smoke', async ({ page }) => {
    const dashboardPage = new DashboardPage(page);

    // Start from dashboard
    await dashboardPage.goto();
    await TestUtils.assertElementVisible(page, '[data-testid="dashboard"]');

    // Test navigation to each main section
    const navigationTests = [
      {
        method: () => dashboardPage.navigateToSubscriptions(),
        url: /\/subscriptions/,
        element: '[data-testid="subscription-management"]',
      },
      {
        method: () => dashboardPage.navigateToLicenses(),
        url: /\/licenses/,
        element: '[data-testid="license-management"]',
      },
      {
        method: () => dashboardPage.navigateToBilling(),
        url: /\/billing/,
        element: '[data-testid="billing-management"]',
      },
      {
        method: () => dashboardPage.navigateToSettings(),
        url: /\/settings/,
        element: '[data-testid="tenant-settings"]',
      },
    ];

    for (const navTest of navigationTests) {
      await navTest.method();
      await expect(page).toHaveURL(navTest.url);
      await TestUtils.assertElementVisible(page, navTest.element);

      // Return to dashboard
      await dashboardPage.goto();
      await TestUtils.assertElementVisible(page, '[data-testid="dashboard"]');
    }
  });

  test('should handle basic app catalog browsing @smoke', async ({ page }) => {
    const catalogPage = page.locator('[data-testid="app-catalog"]');

    // Navigate to app catalog
    await page.goto('/app-catalog');
    await TestUtils.waitForStableElement(page, '[data-testid="app-catalog"]');

    // Verify catalog structure
    await TestUtils.assertElementVisible(page, '[data-testid="app-categories"]');
    await TestUtils.assertElementVisible(page, '[data-testid="app-list"]');

    // Test category filtering
    const categories = ['ISP', 'CRM', 'E-commerce'];
    for (const category of categories) {
      const filterButton = page.locator(`[data-testid="filter-${category.toLowerCase()}"]`);
      if ((await filterButton.count()) > 0) {
        await filterButton.click();
        await TestUtils.waitForStableElement(page, '[data-testid="filtered-apps"]');

        // Verify apps are displayed
        const appCards = page.locator('[data-testid^="app-"]');
        const appCount = await appCards.count();
        expect(appCount, `Should show apps for ${category} category`).toBeGreaterThan(0);
      }
    }
  });

  test('should display user management section @smoke', async ({ page }) => {
    const settingsPage = page.locator('[data-testid="tenant-settings"]');

    // Navigate to settings/users
    await page.goto('/settings');
    await TestUtils.waitForStableElement(page, '[data-testid="tenant-settings"]');

    // Navigate to users tab
    await page.click('[data-testid="users-tab"]');
    await TestUtils.waitForStableElement(page, '[data-testid="users-list"]');

    // Verify user list displays
    await TestUtils.assertElementVisible(page, '[data-testid="users-table"]');
    await TestUtils.assertElementVisible(page, '[data-testid="add-user-button"]');

    // Verify user count matches test data
    const userRows = page.locator('[data-testid^="user-"]');
    const userCount = await userRows.count();
    expect(userCount).toBe(testTenant.users.length);
  });

  test('should show billing overview with correct totals @smoke', async ({ page }) => {
    // Navigate to billing
    await page.goto('/billing');
    await TestUtils.waitForStableElement(page, '[data-testid="billing-management"]');

    // Verify billing overview
    await TestUtils.assertElementVisible(page, '[data-testid="current-bill"]');
    await TestUtils.assertElementVisible(page, '[data-testid="billing-breakdown"]');

    // Calculate expected monthly total
    const expectedTotal = testTenant.subscriptions
      .filter((s) => s.status === 'active')
      .reduce((sum, s) => sum + s.monthlyPrice, 0);

    // Verify total is displayed
    const billingCard = page.locator('[data-testid="current-bill"]');
    const totalElement = billingCard.locator('[data-testid="monthly-total"]');

    if ((await totalElement.count()) > 0) {
      const displayedTotal = await totalElement.textContent();
      expect(displayedTotal).toContain(expectedTotal.toString());
    }
  });

  test('should handle error states gracefully @smoke', async ({ page }) => {
    // Simulate network failure
    await page.route('**/api/dashboard/**', (route) => {
      route.abort('failed');
    });

    // Navigate to dashboard
    await page.goto('/dashboard');

    // Verify error state is displayed
    await TestUtils.waitForStableElement(page, '[data-testid="dashboard-error"]');
    await TestUtils.assertElementVisible(page, '[data-testid="retry-button"]');

    // Verify error message is user-friendly
    const errorMessage = await page.textContent('[data-testid="error-message"]');
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).not.toContain('undefined');
    expect(errorMessage).not.toContain('null');
    expect(errorMessage).not.toContain('500');
  });

  test('should maintain accessibility standards @smoke @accessibility', async ({ page }) => {
    await page.goto('/dashboard');
    await TestUtils.waitForStableElement(page, '[data-testid="dashboard"]');

    // Check for basic accessibility requirements
    await TestUtils.assertElementVisible(page, 'h1');
    await TestUtils.assertElementAttribute(page, '[data-testid="dashboard"]', 'role', 'main');

    // Verify navigation is accessible
    await TestUtils.assertElementAttribute(
      page,
      '[data-testid="navigation-menu"]',
      'role',
      'navigation'
    );

    // Test keyboard navigation
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(['A', 'BUTTON', 'INPUT']).toContain(focusedElement);

    // Verify skip links exist for screen readers
    const skipLink = page.locator('[data-testid="skip-to-content"]');
    if ((await skipLink.count()) > 0) {
      await expect(skipLink).toHaveAttribute('href', '#main-content');
    }
  });

  test('should perform within acceptable time limits @smoke @performance', async ({ page }) => {
    const startTime = Date.now();

    // Navigate to dashboard
    await page.goto('/dashboard');
    await TestUtils.waitForStableElement(page, '[data-testid="dashboard"]');

    const loadTime = Date.now() - startTime;
    expect(loadTime, 'Dashboard should load within 3 seconds').toBeLessThan(3000);

    // Test navigation performance
    const navStartTime = Date.now();
    await page.click('[data-testid="nav-subscriptions"]');
    await TestUtils.waitForStableElement(page, '[data-testid="subscription-management"]');
    const navTime = Date.now() - navStartTime;

    expect(navTime, 'Navigation should be fast').toBeLessThan(2000);

    // Test API response times (mocked)
    const apiStartTime = Date.now();
    await page.reload();
    await TestUtils.waitForStableElement(page, '[data-testid="dashboard"]');
    const apiTime = Date.now() - apiStartTime;

    expect(apiTime, 'API responses should be timely').toBeLessThan(2500);
  });

  test.afterEach(async ({ page }, testInfo) => {
    // Take screenshot on failure for smoke tests
    if (testInfo.status === 'failed') {
      await TestUtils.takeScreenshot(page, `smoke-${testInfo.title.replace(/\s+/g, '-')}`);
    }

    // Log performance metrics for smoke tests
    const metrics = await page.evaluate(() => ({
      loadTime: performance.timing?.loadEventEnd - performance.timing?.navigationStart,
      domReady: performance.timing?.domContentLoadedEventEnd - performance.timing?.navigationStart,
    }));

    console.log(`Test: ${testInfo.title}`);
    console.log(`Load Time: ${metrics.loadTime}ms`);
    console.log(`DOM Ready: ${metrics.domReady}ms`);
    console.log(`Status: ${testInfo.status}`);
    console.log('---');
  });
});
