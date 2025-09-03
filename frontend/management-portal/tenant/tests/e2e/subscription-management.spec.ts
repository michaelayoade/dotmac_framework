/**
 * Subscription Management E2E Tests
 * Testing complete subscription lifecycle workflows
 */

import { test, expect, Page } from '@playwright/test';
import {
  TestDataFactory,
  DEFAULT_TEST_TENANT,
  TestTenant,
  TestSubscription,
} from './utils/test-data-factory';
import { AuthHelper, APIHelper, TestUtils, PerformanceHelper } from './utils/test-helpers';
import { DashboardPage, SubscriptionManagementPage, AppCatalogPage } from './utils/page-objects';

test.describe('Subscription Management', () => {
  let testTenant: TestTenant;
  let subscriptionPage: SubscriptionManagementPage;
  let catalogPage: AppCatalogPage;
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    // Set up test data
    testTenant = TestDataFactory.createTenant({
      name: 'E2E Test Tenant',
      email: 'e2e-test@example.com',
      subscriptions: [
        TestDataFactory.createSubscription({
          appName: 'ISP Core Management',
          appCategory: 'ISP',
          tier: 'standard',
          status: 'active',
        }),
        TestDataFactory.createSubscription({
          appName: 'CRM Professional',
          appCategory: 'CRM',
          tier: 'basic',
          status: 'pending',
        }),
      ],
    });

    // Set up page objects
    subscriptionPage = new SubscriptionManagementPage(page);
    catalogPage = new AppCatalogPage(page);
    dashboardPage = new DashboardPage(page);

    // Mock API responses
    await AuthHelper.mockAuthAPI(page, testTenant);
    await APIHelper.mockSubscriptionAPI(page, testTenant);
    await APIHelper.mockAppCatalogAPI(page);

    // Authenticate
    await AuthHelper.loginAsTenant(page, testTenant);
  });

  test.describe('App Catalog Browsing', () => {
    test('should display all available app categories', async ({ page }) => {
      await subscriptionPage.goto();
      await subscriptionPage.browseAppCatalog();

      // Verify all categories are displayed
      const categories = ['ISP', 'CRM', 'E-commerce', 'Project Management'];

      for (const category of categories) {
        await TestUtils.assertElementVisible(
          page,
          `[data-testid="filter-${category.toLowerCase()}"]`,
          `${category} filter should be visible`
        );
      }

      // Test performance
      await PerformanceHelper.assertPagePerformance(page, 2000, 1000);
    });

    test('should filter apps by category', async ({ page }) => {
      await catalogPage.goto();

      // Test each category filter
      const categories = ['ISP', 'CRM', 'E-commerce', 'Project Management'];

      for (const category of categories) {
        await catalogPage.filterByCategory(category as any);

        // Verify filtered results
        await TestUtils.waitForStableElement(page, '[data-testid="filtered-apps"]');

        const visibleApps = await page.locator('[data-testid^="app-"]').count();
        expect(visibleApps, `Should show apps for ${category} category`).toBeGreaterThan(0);

        // Verify all visible apps belong to the selected category
        const appCategories = await page.locator('[data-testid="app-category"]').allTextContents();
        appCategories.forEach((appCategory) => {
          expect(appCategory.trim()).toContain(category);
        });
      }
    });

    test('should display app details correctly', async ({ page }) => {
      await catalogPage.goto();

      // Get details for the first ISP app
      await catalogPage.filterByCategory('ISP');
      const firstApp = page.locator('[data-testid^="app-"]').first();
      const appId = await firstApp.getAttribute('data-testid');

      if (appId) {
        const extractedId = appId.replace('app-', '');
        const appDetails = await catalogPage.getAppDetails(extractedId);

        // Verify app details structure
        expect(appDetails.name).toBeTruthy();
        expect(appDetails.category).toBeTruthy();
        expect(appDetails.price).toMatch(/\$\d+/); // Should contain price format

        // Verify app card contains all necessary information
        await TestUtils.assertElementVisible(page, `${appId} [data-testid="app-description"]`);
        await TestUtils.assertElementVisible(page, `${appId} [data-testid="app-features"]`);
        await TestUtils.assertElementVisible(page, `${appId} [data-testid="tier-options"]`);
      }
    });
  });

  test.describe('New Subscription Creation', () => {
    test('should successfully subscribe to new application with different tiers', async ({
      page,
    }) => {
      await catalogPage.goto();
      await catalogPage.filterByCategory('E-commerce');

      const tiers = ['basic', 'standard', 'premium'];

      for (const tier of tiers) {
        const appId = 'store-builder';
        const licenses = tier === 'basic' ? 5 : tier === 'standard' ? 10 : 25;

        await catalogPage.subscribeToApp(appId, tier, licenses);

        // Verify subscription success message
        await TestUtils.waitForStableElement(page, '[data-testid="subscription-success"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="subscription-success"]',
          'Successfully subscribed'
        );

        // Close success modal to continue with next tier
        await page.click('[data-testid="close-success-modal"]');
        await page.waitForTimeout(500);
      }
    });

    test('should handle subscription validation errors', async ({ page }) => {
      await catalogPage.goto();

      // Mock API to return validation error
      await page.route('**/api/subscriptions/subscribe', (route) => {
        route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            error: 'Insufficient licenses available',
            details: 'Maximum 50 licenses allowed for this tier',
          }),
        });
      });

      await catalogPage.filterByCategory('ISP');
      await catalogPage.subscribeToApp('isp-core', 'premium', 100); // Invalid quantity

      // Verify error handling
      await TestUtils.waitForStableElement(page, '[data-testid="subscription-error"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="subscription-error"]',
        'Insufficient licenses available'
      );
    });

    test('should validate required fields before subscription', async ({ page }) => {
      await catalogPage.goto();
      await catalogPage.filterByCategory('CRM');

      const appId = 'crm-pro';
      await page.click(`[data-testid="subscribe-${appId}"]`);
      await TestUtils.waitForStableElement(page, '[data-testid="subscription-modal"]');

      // Try to submit without selecting tier
      await page.click('[data-testid="confirm-subscription"]');

      // Verify validation messages
      await TestUtils.assertElementVisible(page, '[data-testid="tier-required-error"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="tier-required-error"]',
        'Please select a subscription tier'
      );

      // Clear license quantity and try again
      await page.fill('[data-testid="license-quantity"]', '');
      await page.click('[data-testid="confirm-subscription"]');

      await TestUtils.assertElementVisible(page, '[data-testid="license-quantity-error"]');
    });
  });

  test.describe('Subscription Management', () => {
    test('should display current active subscriptions', async ({ page }) => {
      await subscriptionPage.goto();

      // Wait for subscriptions to load
      await TestUtils.waitForStableElement(page, '[data-testid="subscriptions-list"]');

      const activeSubscriptions = await subscriptionPage.getActiveSubscriptions();
      expect(activeSubscriptions.length).toBeGreaterThan(0);

      // Verify subscription details are displayed
      for (const subscriptionId of activeSubscriptions) {
        const card = page.locator(`[data-testid="${subscriptionId}"]`);

        // Check for essential subscription information
        await expect(card.locator('[data-testid="app-name"]')).toBeVisible();
        await expect(card.locator('[data-testid="subscription-tier"]')).toBeVisible();
        await expect(card.locator('[data-testid="license-usage"]')).toBeVisible();
        await expect(card.locator('[data-testid="monthly-cost"]')).toBeVisible();
        await expect(card.locator('[data-testid="subscription-status"]')).toBeVisible();
      }
    });

    test('should show subscription status indicators correctly', async ({ page }) => {
      await subscriptionPage.goto();

      // Check active subscription indicators
      const activeCards = page.locator('[data-testid^="subscription-"][data-status="active"]');
      const activeCount = await activeCards.count();

      for (let i = 0; i < activeCount; i++) {
        const card = activeCards.nth(i);
        await expect(card.locator('[data-testid="status-indicator"]')).toHaveClass(/status-active/);
        await expect(card.locator('[data-testid="subscription-actions"]')).toBeVisible();
      }

      // Check pending subscription indicators
      const pendingCards = page.locator('[data-testid^="subscription-"][data-status="pending"]');
      const pendingCount = await pendingCards.count();

      for (let i = 0; i < pendingCount; i++) {
        const card = pendingCards.nth(i);
        await expect(card.locator('[data-testid="status-indicator"]')).toHaveClass(
          /status-pending/
        );
        await TestUtils.assertElementText(
          card,
          '[data-testid="pending-message"]',
          'Activation pending'
        );
      }
    });

    test('should display license usage with visual indicators', async ({ page }) => {
      await subscriptionPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="subscriptions-list"]');

      const subscriptionCards = page.locator(
        '[data-testid^="subscription-"][data-status="active"]'
      );
      const cardCount = await subscriptionCards.count();

      for (let i = 0; i < cardCount; i++) {
        const card = subscriptionCards.nth(i);

        // Verify license usage display
        await expect(card.locator('[data-testid="license-usage"]')).toBeVisible();
        await expect(card.locator('[data-testid="license-progress-bar"]')).toBeVisible();

        // Check usage percentage calculation
        const usageText = await card.locator('[data-testid="license-usage"]').textContent();
        const usageMatch = usageText?.match(/(\d+)\s*\/\s*(\d+)/);

        if (usageMatch) {
          const used = parseInt(usageMatch[1]);
          const total = parseInt(usageMatch[2]);
          const percentage = Math.round((used / total) * 100);

          const progressBar = card.locator('[data-testid="license-progress-bar"]');
          await expect(progressBar).toHaveAttribute('aria-valuenow', percentage.toString());
        }
      }
    });
  });

  test.describe('Subscription Upgrades', () => {
    test('should successfully upgrade subscription tier', async ({ page }) => {
      await subscriptionPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="subscriptions-list"]');

      // Find a subscription to upgrade
      const activeSubscriptions = await subscriptionPage.getActiveSubscriptions();
      const subscriptionToUpgrade = activeSubscriptions[0];

      if (subscriptionToUpgrade) {
        const subscriptionId = subscriptionToUpgrade.replace('subscription-', '');

        // Perform upgrade
        await subscriptionPage.upgradeSubscription(subscriptionId, 'premium');

        // Verify upgrade success
        await TestUtils.waitForStableElement(page, '[data-testid="upgrade-success"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="upgrade-success"]',
          'Subscription upgraded successfully'
        );

        // Verify the subscription reflects the new tier
        await page.reload();
        await TestUtils.waitForStableElement(page, '[data-testid="subscriptions-list"]');

        const upgradedCard = page.locator(`[data-testid="subscription-${subscriptionId}"]`);
        await TestUtils.assertElementText(
          upgradedCard,
          '[data-testid="subscription-tier"]',
          'premium'
        );
      }
    });

    test('should show upgrade cost preview', async ({ page }) => {
      await subscriptionPage.goto();

      const activeSubscriptions = await subscriptionPage.getActiveSubscriptions();
      const subscriptionToUpgrade = activeSubscriptions[0];

      if (subscriptionToUpgrade) {
        const subscriptionId = subscriptionToUpgrade.replace('subscription-', '');

        // Click upgrade button
        await page.click(`[data-testid="upgrade-subscription-${subscriptionId}"]`);
        await TestUtils.waitForStableElement(page, '[data-testid="upgrade-modal"]');

        // Select a higher tier
        await page.click('[data-testid="tier-premium"]');

        // Verify cost preview is shown
        await TestUtils.assertElementVisible(page, '[data-testid="upgrade-cost-preview"]');
        await TestUtils.assertElementVisible(page, '[data-testid="current-cost"]');
        await TestUtils.assertElementVisible(page, '[data-testid="new-cost"]');
        await TestUtils.assertElementVisible(page, '[data-testid="cost-difference"]');

        // Verify cost calculation
        const costDifference = await page.textContent('[data-testid="cost-difference"]');
        expect(costDifference).toMatch(/\+\$\d+/);
      }
    });

    test('should handle downgrade scenarios', async ({ page }) => {
      await subscriptionPage.goto();

      const activeSubscriptions = await subscriptionPage.getActiveSubscriptions();
      const subscriptionToDowngrade = activeSubscriptions[0];

      if (subscriptionToDowngrade) {
        const subscriptionId = subscriptionToDowngrade.replace('subscription-', '');

        await page.click(`[data-testid="upgrade-subscription-${subscriptionId}"]`);
        await TestUtils.waitForStableElement(page, '[data-testid="upgrade-modal"]');

        // Select a lower tier (downgrade)
        await page.click('[data-testid="tier-basic"]');

        // Verify downgrade warning
        await TestUtils.assertElementVisible(page, '[data-testid="downgrade-warning"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="downgrade-warning"]',
          'Downgrading may result in loss of features'
        );

        // Verify confirmation is required
        await page.click('[data-testid="confirm-upgrade"]');
        await TestUtils.assertElementVisible(page, '[data-testid="downgrade-confirmation"]');
      }
    });
  });

  test.describe('Subscription Cancellation', () => {
    test('should successfully cancel subscription with reason', async ({ page }) => {
      await subscriptionPage.goto();

      const activeSubscriptions = await subscriptionPage.getActiveSubscriptions();
      const subscriptionToCancel = activeSubscriptions[0];

      if (subscriptionToCancel) {
        const subscriptionId = subscriptionToCancel.replace('subscription-', '');
        const cancellationReason = 'No longer needed for our business';

        await subscriptionPage.cancelSubscription(subscriptionId, cancellationReason);

        // Verify cancellation success
        await TestUtils.waitForStableElement(page, '[data-testid="cancellation-success"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="cancellation-success"]',
          'Subscription cancelled successfully'
        );

        // Verify subscription status updated
        await page.reload();
        await TestUtils.waitForStableElement(page, '[data-testid="subscriptions-list"]');

        const cancelledCard = page.locator(`[data-testid="subscription-${subscriptionId}"]`);
        await expect(cancelledCard).toHaveAttribute('data-status', 'cancelled');
      }
    });

    test('should require cancellation reason', async ({ page }) => {
      await subscriptionPage.goto();

      const activeSubscriptions = await subscriptionPage.getActiveSubscriptions();
      const subscriptionToCancel = activeSubscriptions[0];

      if (subscriptionToCancel) {
        const subscriptionId = subscriptionToCancel.replace('subscription-', '');

        await page.click(`[data-testid="cancel-subscription-${subscriptionId}"]`);
        await TestUtils.waitForStableElement(page, '[data-testid="cancel-modal"]');

        // Try to confirm without providing reason
        await page.click('[data-testid="confirm-cancellation"]');

        // Verify validation error
        await TestUtils.assertElementVisible(page, '[data-testid="reason-required-error"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="reason-required-error"]',
          'Please provide a cancellation reason'
        );
      }
    });

    test('should show cancellation impact warning', async ({ page }) => {
      await subscriptionPage.goto();

      const activeSubscriptions = await subscriptionPage.getActiveSubscriptions();
      const subscriptionToCancel = activeSubscriptions[0];

      if (subscriptionToCancel) {
        const subscriptionId = subscriptionToCancel.replace('subscription-', '');

        await page.click(`[data-testid="cancel-subscription-${subscriptionId}"]`);
        await TestUtils.waitForStableElement(page, '[data-testid="cancel-modal"]');

        // Verify impact warning is shown
        await TestUtils.assertElementVisible(page, '[data-testid="cancellation-impact"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="cancellation-impact"]',
          'data will be retained for 30 days'
        );

        // Verify effective date is shown
        await TestUtils.assertElementVisible(page, '[data-testid="cancellation-effective-date"]');
      }
    });
  });

  test.describe('Subscription History', () => {
    test('should display complete subscription history', async ({ page }) => {
      await subscriptionPage.goto();
      await subscriptionPage.viewSubscriptionHistory();

      // Wait for history to load
      await TestUtils.waitForStableElement(page, '[data-testid="subscription-history-list"]');

      // Verify history table structure
      await TestUtils.assertElementVisible(page, '[data-testid="history-table-headers"]');

      const expectedHeaders = ['App Name', 'Action', 'Date', 'Previous Tier', 'New Tier', 'Status'];
      for (const header of expectedHeaders) {
        await TestUtils.assertElementText(page, '[data-testid="history-table-headers"]', header);
      }

      // Verify history entries
      const historyRows = page.locator('[data-testid="history-row"]');
      const rowCount = await historyRows.count();

      expect(rowCount, 'Should show subscription history entries').toBeGreaterThan(0);

      // Verify each row has required data
      for (let i = 0; i < Math.min(rowCount, 5); i++) {
        const row = historyRows.nth(i);
        await expect(row.locator('[data-testid="history-app-name"]')).toBeVisible();
        await expect(row.locator('[data-testid="history-action"]')).toBeVisible();
        await expect(row.locator('[data-testid="history-date"]')).toBeVisible();
        await expect(row.locator('[data-testid="history-status"]')).toBeVisible();
      }
    });

    test('should filter subscription history by app and action', async ({ page }) => {
      await subscriptionPage.goto();
      await subscriptionPage.viewSubscriptionHistory();
      await TestUtils.waitForStableElement(page, '[data-testid="subscription-history-list"]');

      // Test app filter
      const appFilter = page.locator('[data-testid="history-app-filter"]');
      await appFilter.selectOption('ISP Core Management');

      await TestUtils.waitForStableElement(page, '[data-testid="filtered-history"]');

      const filteredRows = page.locator('[data-testid="history-row"]');
      const filteredCount = await filteredRows.count();

      // Verify all visible rows match the filter
      for (let i = 0; i < filteredCount; i++) {
        const row = filteredRows.nth(i);
        await TestUtils.assertElementText(
          row,
          '[data-testid="history-app-name"]',
          'ISP Core Management'
        );
      }

      // Test action filter
      const actionFilter = page.locator('[data-testid="history-action-filter"]');
      await actionFilter.selectOption('Upgrade');

      await TestUtils.waitForStableElement(page, '[data-testid="filtered-history"]');

      // Verify action filter
      const actionFilteredRows = page.locator('[data-testid="history-row"]');
      const actionFilteredCount = await actionFilteredRows.count();

      for (let i = 0; i < actionFilteredCount; i++) {
        const row = actionFilteredRows.nth(i);
        await TestUtils.assertElementText(row, '[data-testid="history-action"]', 'Upgrade');
      }
    });

    test('should allow exporting subscription history', async ({ page }) => {
      await subscriptionPage.goto();
      await subscriptionPage.viewSubscriptionHistory();
      await TestUtils.waitForStableElement(page, '[data-testid="subscription-history-list"]');

      // Test CSV export
      const downloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-history-csv"]');
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toContain('subscription-history');
      expect(download.suggestedFilename()).toContain('.csv');

      // Test PDF export
      const pdfDownloadPromise = page.waitForEvent('download');
      await page.click('[data-testid="export-history-pdf"]');
      const pdfDownload = await pdfDownloadPromise;

      expect(pdfDownload.suggestedFilename()).toContain('subscription-history');
      expect(pdfDownload.suggestedFilename()).toContain('.pdf');
    });
  });

  test.describe('Performance and Accessibility', () => {
    test('should meet performance benchmarks', async ({ page }) => {
      // Test subscription page load performance
      const startTime = Date.now();
      await subscriptionPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="subscriptions-list"]');
      const loadTime = Date.now() - startTime;

      expect(loadTime, 'Subscription page should load quickly').toBeLessThan(2000);

      // Test app catalog performance
      const catalogStartTime = Date.now();
      await catalogPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="app-catalog"]');
      const catalogLoadTime = Date.now() - catalogStartTime;

      expect(catalogLoadTime, 'App catalog should load quickly').toBeLessThan(2500);
    });

    test('should be accessible to screen readers', async ({ page }) => {
      await subscriptionPage.goto();

      // Check for proper ARIA labels and roles
      await TestUtils.assertElementAttribute(
        page,
        '[data-testid="subscriptions-list"]',
        'role',
        'list'
      );

      await TestUtils.assertElementAttribute(
        page,
        '[data-testid^="subscription-"]',
        'role',
        'listitem'
      );

      // Check for proper heading structure
      await TestUtils.assertElementVisible(page, 'h1');
      await TestUtils.assertElementVisible(page, 'h2');

      // Verify focus management
      await page.keyboard.press('Tab');
      const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
      expect(['BUTTON', 'A', 'INPUT']).toContain(focusedElement);
    });

    test('should handle network errors gracefully', async ({ page }) => {
      // Simulate network failure
      await page.route('**/api/subscriptions/**', (route) => {
        route.abort('failed');
      });

      await subscriptionPage.goto();

      // Verify error handling
      await TestUtils.waitForStableElement(page, '[data-testid="network-error"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="network-error"]',
        'Unable to load subscriptions'
      );

      // Verify retry functionality
      await TestUtils.assertElementVisible(page, '[data-testid="retry-button"]');
    });
  });

  test.afterEach(async ({ page }) => {
    // Take screenshot on failure
    if (test.info().status === 'failed') {
      await TestUtils.takeScreenshot(page, `subscription-management-${test.info().title}`);
    }

    // Assert no console errors
    await TestUtils.assertNoConsoleErrors(page);
  });
});
