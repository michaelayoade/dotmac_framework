/**
 * License Management E2E Tests
 * Testing multi-app license management and feature access validation
 */

import { test, expect, Page } from '@playwright/test';
import {
  TestDataFactory,
  DEFAULT_TEST_TENANT,
  TestTenant,
  TestSubscription,
  TestLicense,
} from './utils/test-data-factory';
import { AuthHelper, APIHelper, TestUtils, PerformanceHelper } from './utils/test-helpers';
import { DashboardPage, LicenseManagementPage } from './utils/page-objects';

test.describe('License Management', () => {
  let testTenant: TestTenant;
  let licenseManager: LicenseManagementPage;
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    // Set up comprehensive test data with various license scenarios
    testTenant = TestDataFactory.createTenant({
      name: 'License Test Tenant',
      email: 'license-test@example.com',
      subscriptions: [
        TestDataFactory.createSubscription({
          id: 'sub-isp-core',
          appId: 'isp-core',
          appName: 'ISP Core Management',
          appCategory: 'ISP',
          tier: 'standard',
          status: 'active',
          licenses: 50,
          usedLicenses: 35, // 70% usage
          features: ['Dashboard', 'Customer Management', 'Billing', 'Reports'],
        }),
        TestDataFactory.createSubscription({
          id: 'sub-crm-pro',
          appId: 'crm-pro',
          appName: 'CRM Professional',
          appCategory: 'CRM',
          tier: 'premium',
          status: 'active',
          licenses: 25,
          usedLicenses: 23, // 92% usage - near limit
          features: [
            'Contact Management',
            'Sales Pipeline',
            'Email Integration',
            'Advanced Analytics',
            'API Access',
          ],
        }),
        TestDataFactory.createSubscription({
          id: 'sub-project-mgr',
          appId: 'project-manager',
          appName: 'Project Manager Enterprise',
          appCategory: 'Project Management',
          tier: 'enterprise',
          status: 'active',
          licenses: 100,
          usedLicenses: 15, // 15% usage - low usage
          features: [
            'Task Management',
            'Team Collaboration',
            'Time Tracking',
            'Resource Planning',
            'Custom Integrations',
          ],
        }),
        TestDataFactory.createSubscription({
          id: 'sub-limited',
          appId: 'limited-app',
          appName: 'Limited Feature App',
          appCategory: 'E-commerce',
          tier: 'basic',
          status: 'active',
          licenses: 5,
          usedLicenses: 5, // 100% usage - at limit
          features: ['Basic Store', 'Payment Processing'],
        }),
      ],
    });

    // Set up page objects
    licenseManager = new LicenseManagementPage(page);
    dashboardPage = new DashboardPage(page);

    // Mock API responses
    await AuthHelper.mockAuthAPI(page, testTenant);
    await APIHelper.mockLicenseAPI(page, testTenant);
    await APIHelper.mockSubscriptionAPI(page, testTenant);

    // Authenticate
    await AuthHelper.loginAsTenant(page, testTenant);
  });

  test.describe('License Overview Display', () => {
    test('should display current licenses and usage limits', async ({ page }) => {
      await licenseManager.goto();

      // Wait for license data to load
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      // Verify each subscription's license information is displayed
      for (const subscription of testTenant.subscriptions) {
        const licenseCard = page.locator(`[data-testid="license-${subscription.appId}"]`);

        // Verify license counts
        await expect(licenseCard.locator('[data-testid="licenses-used"]')).toContainText(
          subscription.usedLicenses.toString()
        );
        await expect(licenseCard.locator('[data-testid="licenses-total"]')).toContainText(
          subscription.licenses.toString()
        );

        // Verify usage percentage
        const expectedPercentage = Math.round(
          (subscription.usedLicenses / subscription.licenses) * 100
        );
        await expect(licenseCard.locator('[data-testid="usage-percentage"]')).toContainText(
          `${expectedPercentage}%`
        );

        // Verify app name and tier
        await expect(licenseCard.locator('[data-testid="app-name"]')).toContainText(
          subscription.appName
        );
        await expect(licenseCard.locator('[data-testid="subscription-tier"]')).toContainText(
          subscription.tier
        );
      }
    });

    test('should display visual usage indicators with correct colors', async ({ page }) => {
      await licenseManager.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      // Check usage indicators for different usage levels
      const testCases = [
        { appId: 'isp-core', expectedClass: 'usage-medium', usage: 70 }, // 70% usage
        { appId: 'crm-pro', expectedClass: 'usage-high', usage: 92 }, // 92% usage
        { appId: 'project-manager', expectedClass: 'usage-low', usage: 15 }, // 15% usage
        { appId: 'limited-app', expectedClass: 'usage-critical', usage: 100 }, // 100% usage
      ];

      for (const testCase of testCases) {
        const licenseCard = page.locator(`[data-testid="license-${testCase.appId}"]`);
        const progressBar = licenseCard.locator('[data-testid="usage-progress-bar"]');

        // Verify progress bar color class
        await expect(progressBar).toHaveClass(new RegExp(testCase.expectedClass));

        // Verify aria attributes for accessibility
        await expect(progressBar).toHaveAttribute('aria-valuenow', testCase.usage.toString());
        await expect(progressBar).toHaveAttribute('role', 'progressbar');
      }
    });

    test('should show license expiry dates and renewal warnings', async ({ page }) => {
      await licenseManager.goto();

      // Mock some licenses with different expiry scenarios
      await page.route('**/api/licenses/**', (route) => {
        const licenses = [
          TestDataFactory.createLicense({
            appId: 'isp-core',
            expiryDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days
          }),
          TestDataFactory.createLicense({
            appId: 'crm-pro',
            expiryDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days
          }),
        ];

        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ licenses }),
        });
      });

      await page.reload();
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      // Check for expiry warnings
      const nearExpiryCard = page.locator('[data-testid="license-isp-core"]');
      await expect(nearExpiryCard.locator('[data-testid="expiry-warning"]')).toBeVisible();
      await expect(nearExpiryCard.locator('[data-testid="expiry-warning"]')).toContainText(
        'expires in 7 days'
      );

      // Verify renewal button is present
      await expect(nearExpiryCard.locator('[data-testid="renew-license"]')).toBeVisible();
    });
  });

  test.describe('Feature Access Validation', () => {
    test('should correctly validate feature access based on license tier', async ({ page }) => {
      await licenseManager.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      // Test premium tier features (CRM Pro)
      const crmCard = page.locator('[data-testid="license-crm-pro"]');

      // Premium features should be available
      const premiumFeatures = ['Advanced Analytics', 'API Access'];
      for (const feature of premiumFeatures) {
        const hasAccess = await licenseManager.validateFeatureAccess('crm-pro', feature);
        expect(hasAccess, `Premium tier should have access to ${feature}`).toBe(true);

        // Verify UI shows feature as enabled
        await expect(
          crmCard.locator(`[data-testid="feature-${feature.toLowerCase().replace(' ', '-')}"]`)
        ).toHaveClass(/feature-enabled/);
      }

      // Test basic tier limitations (Limited App)
      const limitedCard = page.locator('[data-testid="license-limited-app"]');

      // Advanced features should be disabled for basic tier
      const restrictedFeatures = ['Advanced Analytics', 'API Access', 'Custom Integrations'];
      for (const feature of restrictedFeatures) {
        const featureElement = limitedCard.locator(
          `[data-testid="feature-${feature.toLowerCase().replace(' ', '-')}"]`
        );
        if ((await featureElement.count()) > 0) {
          await expect(featureElement).toHaveClass(/feature-disabled/);
        }
      }
    });

    test('should prevent access when at license limit', async ({ page }) => {
      await licenseManager.goto();

      // Test app at 100% license usage
      const limitedCard = page.locator('[data-testid="license-limited-app"]');

      // Verify at-limit warning is displayed
      await expect(limitedCard.locator('[data-testid="at-limit-warning"]')).toBeVisible();
      await expect(limitedCard.locator('[data-testid="at-limit-warning"]')).toContainText(
        'License limit reached'
      );

      // Verify upgrade prompt is shown
      await expect(limitedCard.locator('[data-testid="upgrade-prompt"]')).toBeVisible();
      await expect(limitedCard.locator('[data-testid="request-upgrade"]')).toBeEnabled();

      // Test trying to assign new license (should be blocked)
      const assignButton = limitedCard.locator('[data-testid="assign-license"]');
      if ((await assignButton.count()) > 0) {
        await expect(assignButton).toBeDisabled();
      }
    });

    test('should show feature comparison between tiers', async ({ page }) => {
      await licenseManager.goto();

      // Open feature comparison modal
      await page.click('[data-testid="compare-features"]');
      await TestUtils.waitForStableElement(page, '[data-testid="feature-comparison-modal"]');

      // Verify comparison table structure
      await TestUtils.assertElementVisible(page, '[data-testid="comparison-table"]');
      await TestUtils.assertElementVisible(page, '[data-testid="tier-columns"]');
      await TestUtils.assertElementVisible(page, '[data-testid="feature-rows"]');

      // Verify feature availability indicators
      const tiers = ['basic', 'standard', 'premium', 'enterprise'];
      const features = [
        'Dashboard',
        'Reports',
        'API Access',
        'Advanced Analytics',
        'Custom Integrations',
      ];

      for (const tier of tiers) {
        for (const feature of features) {
          const cell = page.locator(
            `[data-testid="feature-${feature.toLowerCase().replace(' ', '-')}-${tier}"]`
          );
          await expect(cell).toBeVisible();

          // Check if cell contains checkmark (✓) or X (✗) or upgrade arrow (↑)
          const cellContent = await cell.textContent();
          expect(['✓', '✗', '↑']).toContain(cellContent?.trim());
        }
      }
    });
  });

  test.describe('License Upgrade Requests', () => {
    test('should successfully submit license upgrade request', async ({ page }) => {
      await licenseManager.goto();

      // Find an app that can be upgraded (high usage but not at enterprise tier)
      const crmCard = page.locator('[data-testid="license-crm-pro"]');

      // Request upgrade
      const newQuantity = 50; // Upgrade from 25 to 50
      await licenseManager.requestLicenseUpgrade('crm-pro', newQuantity);

      // Verify success message
      await TestUtils.waitForStableElement(page, '[data-testid="upgrade-request-success"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="upgrade-request-success"]',
        'License upgrade request submitted successfully'
      );

      // Verify request details are shown
      await expect(page.locator('[data-testid="upgrade-details"]')).toContainText(
        `${newQuantity} licenses`
      );
      await expect(page.locator('[data-testid="upgrade-app"]')).toContainText('CRM Professional');
    });

    test('should validate upgrade request with cost estimate', async ({ page }) => {
      await licenseManager.goto();

      const ispCard = page.locator('[data-testid="license-isp-core"]');

      // Click upgrade button
      await page.click('[data-testid="upgrade-license-isp-core"]');
      await TestUtils.waitForStableElement(page, '[data-testid="upgrade-license-modal"]');

      // Enter new quantity
      const newQuantity = 75; // Upgrade from 50 to 75
      await page.fill('[data-testid="license-quantity-input"]', newQuantity.toString());

      // Trigger cost calculation
      await page.click('[data-testid="calculate-cost"]');

      // Verify cost estimate is shown
      await TestUtils.assertElementVisible(page, '[data-testid="cost-estimate"]');
      await TestUtils.assertElementVisible(page, '[data-testid="current-monthly-cost"]');
      await TestUtils.assertElementVisible(page, '[data-testid="new-monthly-cost"]');
      await TestUtils.assertElementVisible(page, '[data-testid="additional-cost"]');

      // Verify cost calculation is reasonable
      const additionalCostText = await page.textContent('[data-testid="additional-cost"]');
      expect(additionalCostText).toMatch(/\+\$\d+/);

      // Verify prorated billing explanation
      await TestUtils.assertElementVisible(page, '[data-testid="proration-explanation"]');
    });

    test('should handle upgrade request validation errors', async ({ page }) => {
      await licenseManager.goto();

      await page.click('[data-testid="upgrade-license-isp-core"]');
      await TestUtils.waitForStableElement(page, '[data-testid="upgrade-license-modal"]');

      // Test invalid quantity (less than current)
      const currentQuantity = 50;
      await page.fill('[data-testid="license-quantity-input"]', (currentQuantity - 10).toString());
      await page.click('[data-testid="submit-upgrade-request"]');

      await TestUtils.assertElementVisible(page, '[data-testid="validation-error"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="validation-error"]',
        'New quantity must be greater than current'
      );

      // Test quantity too high (over reasonable limit)
      await page.fill('[data-testid="license-quantity-input"]', '10000');
      await page.click('[data-testid="submit-upgrade-request"]');

      await TestUtils.assertElementVisible(page, '[data-testid="validation-error"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="validation-error"]',
        'Please contact sales for quantities over 1000'
      );

      // Test empty quantity
      await page.fill('[data-testid="license-quantity-input"]', '');
      await page.click('[data-testid="submit-upgrade-request"]');

      await TestUtils.assertElementVisible(page, '[data-testid="validation-error"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="validation-error"]',
        'License quantity is required'
      );
    });

    test('should show upgrade request status and history', async ({ page }) => {
      // Mock pending upgrade requests
      await page.route('**/api/licenses/upgrade-requests', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            requests: [
              {
                id: 'req-1',
                appId: 'crm-pro',
                appName: 'CRM Professional',
                requestedQuantity: 50,
                currentQuantity: 25,
                status: 'pending',
                requestDate: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
                estimatedApprovalDate: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString(),
              },
              {
                id: 'req-2',
                appId: 'isp-core',
                appName: 'ISP Core Management',
                requestedQuantity: 100,
                currentQuantity: 50,
                status: 'approved',
                requestDate: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
                approvalDate: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
              },
            ],
          }),
        });
      });

      await licenseManager.goto();

      // Navigate to upgrade requests tab
      await page.click('[data-testid="upgrade-requests-tab"]');
      await TestUtils.waitForStableElement(page, '[data-testid="upgrade-requests-list"]');

      // Verify pending request
      const pendingRequest = page.locator('[data-testid="request-req-1"]');
      await expect(pendingRequest.locator('[data-testid="request-status"]')).toContainText(
        'Pending'
      );
      await expect(pendingRequest.locator('[data-testid="estimated-approval"]')).toBeVisible();

      // Verify approved request
      const approvedRequest = page.locator('[data-testid="request-req-2"]');
      await expect(approvedRequest.locator('[data-testid="request-status"]')).toContainText(
        'Approved'
      );
      await expect(approvedRequest.locator('[data-testid="approval-date"]')).toBeVisible();

      // Verify cancel option for pending requests
      await expect(pendingRequest.locator('[data-testid="cancel-request"]')).toBeVisible();
      await expect(approvedRequest.locator('[data-testid="cancel-request"]')).not.toBeVisible();
    });
  });

  test.describe('Usage Monitoring and Alerts', () => {
    test('should display usage alerts for high consumption', async ({ page }) => {
      await licenseManager.goto();

      // Check for usage alerts
      const alerts = await licenseManager.getUsageAlerts();

      // Verify high usage alert for CRM (92% usage)
      const highUsageAlert = alerts.find(
        (alert) => alert.includes('CRM Professional') && alert.includes('92%')
      );
      expect(highUsageAlert, 'Should show high usage alert for CRM').toBeTruthy();

      // Verify critical usage alert for Limited App (100% usage)
      const criticalAlert = alerts.find(
        (alert) => alert.includes('Limited Feature App') && alert.includes('limit reached')
      );
      expect(criticalAlert, 'Should show critical alert for app at limit').toBeTruthy();
    });

    test('should provide usage trend analytics', async ({ page }) => {
      await licenseManager.goto();

      // Navigate to usage analytics
      await page.click('[data-testid="usage-analytics-tab"]');
      await TestUtils.waitForStableElement(page, '[data-testid="usage-chart"]');

      // Verify chart components
      await TestUtils.assertElementVisible(page, '[data-testid="usage-over-time-chart"]');
      await TestUtils.assertElementVisible(page, '[data-testid="app-usage-breakdown"]');
      await TestUtils.assertElementVisible(page, '[data-testid="usage-predictions"]');

      // Verify time period selector
      await TestUtils.assertElementVisible(page, '[data-testid="time-period-selector"]');

      const timePeriods = ['7 days', '30 days', '90 days', '1 year'];
      for (const period of timePeriods) {
        await expect(page.locator(`[data-testid="period-${period}"]`)).toBeVisible();
      }

      // Test different time periods
      await page.click('[data-testid="period-30 days"]');
      await TestUtils.waitForStableElement(page, '[data-testid="chart-updated"]');

      // Verify chart shows 30-day data
      const chartDataPoints = page.locator('[data-testid="chart-data-point"]');
      const dataPointCount = await chartDataPoints.count();
      expect(dataPointCount, 'Should show approximately 30 data points').toBeGreaterThan(25);
    });

    test('should show license optimization recommendations', async ({ page }) => {
      await licenseManager.goto();

      // Navigate to optimization recommendations
      await page.click('[data-testid="optimization-tab"]');
      await TestUtils.waitForStableElement(page, '[data-testid="optimization-recommendations"]');

      // Verify different types of recommendations
      await TestUtils.assertElementVisible(page, '[data-testid="underutilized-licenses"]');
      await TestUtils.assertElementVisible(page, '[data-testid="overutilized-apps"]');
      await TestUtils.assertElementVisible(page, '[data-testid="cost-optimization"]');

      // Check underutilized licenses recommendation (Project Manager at 15% usage)
      const underutilizedCard = page.locator('[data-testid="underutilized-project-manager"]');
      await expect(underutilizedCard).toBeVisible();
      await expect(underutilizedCard).toContainText('15% utilized');
      await expect(underutilizedCard).toContainText('Consider reducing');

      // Check overutilized apps recommendation (CRM at 92% usage)
      const overutilizedCard = page.locator('[data-testid="overutilized-crm-pro"]');
      await expect(overutilizedCard).toBeVisible();
      await expect(overutilizedCard).toContainText('92% utilized');
      await expect(overutilizedCard).toContainText('Consider upgrading');

      // Verify cost savings estimates
      await TestUtils.assertElementVisible(page, '[data-testid="potential-savings"]');
      const savingsText = await page.textContent('[data-testid="potential-savings"]');
      expect(savingsText).toMatch(/\$\d+/);
    });
  });

  test.describe('License Assignment and Management', () => {
    test('should assign licenses to users within available limits', async ({ page }) => {
      await licenseManager.goto();

      // Select app with available licenses (ISP Core with 35/50 used)
      const ispCard = page.locator('[data-testid="license-isp-core"]');
      await page.click('[data-testid="manage-licenses-isp-core"]');
      await TestUtils.waitForStableElement(page, '[data-testid="license-assignment-modal"]');

      // Verify current assignments are shown
      await TestUtils.assertElementVisible(page, '[data-testid="current-assignments"]');
      await TestUtils.assertElementVisible(page, '[data-testid="available-users"]');

      // Assign license to an unassigned user
      const availableUser = page.locator('[data-testid="user-available"]').first();
      const userName = await availableUser.textContent();

      await page.click('[data-testid="assign-license"]', { timeout: 5000 });
      await TestUtils.waitForStableElement(page, '[data-testid="assignment-success"]');

      // Verify assignment success
      await TestUtils.assertElementText(
        page,
        '[data-testid="assignment-success"]',
        `License assigned to ${userName}`
      );

      // Verify usage count updated
      await page.reload();
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      const updatedCard = page.locator('[data-testid="license-isp-core"]');
      await expect(updatedCard.locator('[data-testid="licenses-used"]')).toContainText('36'); // 35 + 1
    });

    test('should prevent license assignment when at limit', async ({ page }) => {
      await licenseManager.goto();

      // Select app at license limit (Limited App with 5/5 used)
      const limitedCard = page.locator('[data-testid="license-limited-app"]');
      await page.click('[data-testid="manage-licenses-limited-app"]');
      await TestUtils.waitForStableElement(page, '[data-testid="license-assignment-modal"]');

      // Verify assignment is blocked
      await TestUtils.assertElementVisible(page, '[data-testid="at-limit-message"]');

      const assignButtons = page.locator('[data-testid="assign-license"]');
      const assignButtonCount = await assignButtons.count();

      for (let i = 0; i < assignButtonCount; i++) {
        await expect(assignButtons.nth(i)).toBeDisabled();
      }

      // Verify upgrade option is provided
      await TestUtils.assertElementVisible(page, '[data-testid="upgrade-to-assign"]');
    });

    test('should allow bulk license assignment and revocation', async ({ page }) => {
      await licenseManager.goto();

      const ispCard = page.locator('[data-testid="license-isp-core"]');
      await page.click('[data-testid="manage-licenses-isp-core"]');
      await TestUtils.waitForStableElement(page, '[data-testid="license-assignment-modal"]');

      // Test bulk assignment
      await page.click('[data-testid="bulk-operations"]');
      await TestUtils.waitForStableElement(page, '[data-testid="bulk-assign-section"]');

      // Select multiple users
      const availableUsers = page.locator('[data-testid="user-checkbox"]');
      const userCount = Math.min(await availableUsers.count(), 3);

      for (let i = 0; i < userCount; i++) {
        await availableUsers.nth(i).check();
      }

      // Bulk assign
      await page.click('[data-testid="bulk-assign-selected"]');
      await TestUtils.waitForStableElement(page, '[data-testid="bulk-assignment-success"]');

      // Verify success message
      await TestUtils.assertElementText(
        page,
        '[data-testid="bulk-assignment-success"]',
        `${userCount} licenses assigned successfully`
      );

      // Test bulk revocation
      const assignedUsers = page.locator('[data-testid="assigned-user-checkbox"]');
      const assignedCount = Math.min(await assignedUsers.count(), 2);

      for (let i = 0; i < assignedCount; i++) {
        await assignedUsers.nth(i).check();
      }

      await page.click('[data-testid="bulk-revoke-selected"]');

      // Confirm revocation
      await TestUtils.waitForStableElement(page, '[data-testid="revocation-confirmation"]');
      await page.click('[data-testid="confirm-revocation"]');

      await TestUtils.waitForStableElement(page, '[data-testid="bulk-revocation-success"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="bulk-revocation-success"]',
        `${assignedCount} licenses revoked successfully`
      );
    });
  });

  test.describe('Renewal Management', () => {
    test('should display renewal notices and options', async ({ page }) => {
      // Mock licenses with different expiry scenarios
      await page.route('**/api/licenses/**', (route) => {
        const licenses = testTenant.subscriptions.map((sub) => ({
          ...TestDataFactory.createLicense({
            appId: sub.appId,
            limit: sub.licenses,
            used: sub.usedLicenses,
          }),
          expiryDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days
        }));

        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ licenses }),
        });
      });

      await licenseManager.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      // Check renewal notices
      await TestUtils.assertElementVisible(page, '[data-testid="renewal-notices"]');

      const renewalCards = page.locator('[data-testid^="renewal-notice-"]');
      const renewalCount = await renewalCards.count();

      expect(renewalCount, 'Should show renewal notices').toBeGreaterThan(0);

      // Verify renewal options for each license
      for (let i = 0; i < renewalCount; i++) {
        const renewalCard = renewalCards.nth(i);

        await expect(renewalCard.locator('[data-testid="expiry-date"]')).toBeVisible();
        await expect(renewalCard.locator('[data-testid="renewal-options"]')).toBeVisible();
        await expect(renewalCard.locator('[data-testid="auto-renew-toggle"]')).toBeVisible();
      }
    });

    test('should handle auto-renewal configuration', async ({ page }) => {
      await licenseManager.goto();

      const ispCard = page.locator('[data-testid="license-isp-core"]');

      // Enable auto-renewal
      await page.click('[data-testid="auto-renew-toggle-isp-core"]');
      await TestUtils.waitForStableElement(page, '[data-testid="auto-renew-confirmation"]');

      // Configure auto-renewal settings
      await page.click('[data-testid="renewal-period-1-year"]');
      await page.click('[data-testid="same-quantity"]');
      await page.click('[data-testid="confirm-auto-renew"]');

      // Verify auto-renewal enabled
      await TestUtils.waitForStableElement(page, '[data-testid="auto-renew-success"]');
      await expect(ispCard.locator('[data-testid="auto-renew-indicator"]')).toBeVisible();
      await expect(ispCard.locator('[data-testid="auto-renew-indicator"]')).toContainText(
        'Auto-renew enabled'
      );

      // Test disabling auto-renewal
      await page.click('[data-testid="auto-renew-toggle-isp-core"]');
      await TestUtils.waitForStableElement(page, '[data-testid="disable-auto-renew-confirmation"]');
      await page.click('[data-testid="confirm-disable-auto-renew"]');

      // Verify auto-renewal disabled
      await expect(ispCard.locator('[data-testid="auto-renew-indicator"]')).not.toBeVisible();
    });
  });

  test.describe('Performance and Error Handling', () => {
    test('should load license data efficiently', async ({ page }) => {
      const startTime = Date.now();
      await licenseManager.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');
      const loadTime = Date.now() - startTime;

      expect(loadTime, 'License page should load within 2 seconds').toBeLessThan(2000);

      // Verify all license cards are loaded
      const licenseCards = page.locator('[data-testid^="license-"]');
      const cardCount = await licenseCards.count();
      expect(cardCount).toBe(testTenant.subscriptions.length);
    });

    test('should handle API failures gracefully', async ({ page }) => {
      // Simulate API failure
      await page.route('**/api/licenses/**', (route) => {
        route.abort('failed');
      });

      await licenseManager.goto();

      // Verify error state
      await TestUtils.waitForStableElement(page, '[data-testid="license-error-state"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="license-error-state"]',
        'Unable to load license information'
      );

      // Verify retry functionality
      await TestUtils.assertElementVisible(page, '[data-testid="retry-license-load"]');

      // Mock successful retry
      await page.unroute('**/api/licenses/**');
      await APIHelper.mockLicenseAPI(page, testTenant);

      await page.click('[data-testid="retry-license-load"]');
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      // Verify data loads successfully after retry
      const licenseCards = page.locator('[data-testid^="license-"]');
      const cardCount = await licenseCards.count();
      expect(cardCount).toBeGreaterThan(0);
    });

    test('should maintain accessibility standards', async ({ page }) => {
      await licenseManager.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="licenses-list"]');

      // Verify proper ARIA labels
      await TestUtils.assertElementAttribute(page, '[data-testid="licenses-list"]', 'role', 'list');

      // Verify progress bars have proper accessibility attributes
      const progressBars = page.locator('[data-testid="usage-progress-bar"]');
      const progressBarCount = await progressBars.count();

      for (let i = 0; i < progressBarCount; i++) {
        const progressBar = progressBars.nth(i);
        await expect(progressBar).toHaveAttribute('role', 'progressbar');
        await expect(progressBar).toHaveAttribute('aria-valuenow');
        await expect(progressBar).toHaveAttribute('aria-valuemin', '0');
        await expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      }

      // Test keyboard navigation
      await page.keyboard.press('Tab');
      const firstFocusable = await page.evaluate(() =>
        document.activeElement?.getAttribute('data-testid')
      );
      expect(firstFocusable).toBeTruthy();
    });
  });

  test.afterEach(async ({ page }) => {
    // Take screenshot on failure
    if (test.info().status === 'failed') {
      await TestUtils.takeScreenshot(page, `license-management-${test.info().title}`);
    }

    // Ensure no console errors
    await TestUtils.assertNoConsoleErrors(page);
  });
});
