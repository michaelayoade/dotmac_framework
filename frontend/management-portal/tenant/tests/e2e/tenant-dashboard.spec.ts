/**
 * Tenant Admin Dashboard E2E Tests
 * Testing dashboard overview, user management, permissions, and organization settings
 */

import { test, expect, Page } from '@playwright/test';
import {
  TestDataFactory,
  DEFAULT_TEST_TENANT,
  TestTenant,
  TestUser,
} from './utils/test-data-factory';
import { AuthHelper, APIHelper, TestUtils, PerformanceHelper } from './utils/test-helpers';
import { DashboardPage, SettingsPage, BillingPage } from './utils/page-objects';

test.describe('Tenant Admin Dashboard', () => {
  let testTenant: TestTenant;
  let dashboardPage: DashboardPage;
  let settingsPage: SettingsPage;
  let billingPage: BillingPage;

  test.beforeEach(async ({ page }) => {
    // Create comprehensive test tenant with various scenarios
    testTenant = TestDataFactory.createTenant({
      name: 'Dashboard Test Organization',
      email: 'admin@dashboard-test.com',
      domain: 'dashboard-test.com',
      plan: 'enterprise',
      subscriptions: [
        TestDataFactory.createSubscription({
          appName: 'ISP Core Management',
          appCategory: 'ISP',
          tier: 'enterprise',
          status: 'active',
          licenses: 100,
          usedLicenses: 75,
          monthlyPrice: 599,
        }),
        TestDataFactory.createSubscription({
          appName: 'CRM Professional',
          appCategory: 'CRM',
          tier: 'premium',
          status: 'active',
          licenses: 50,
          usedLicenses: 42,
          monthlyPrice: 299,
        }),
        TestDataFactory.createSubscription({
          appName: 'Project Manager',
          appCategory: 'Project Management',
          tier: 'standard',
          status: 'pending',
          licenses: 25,
          usedLicenses: 0,
          monthlyPrice: 199,
        }),
      ],
      users: [
        TestDataFactory.createUser({
          email: 'admin@dashboard-test.com',
          name: 'John Admin',
          role: 'admin',
          status: 'active',
          lastLogin: new Date().toISOString(),
        }),
        TestDataFactory.createUser({
          email: 'manager1@dashboard-test.com',
          name: 'Sarah Manager',
          role: 'manager',
          status: 'active',
          lastLogin: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
        }),
        TestDataFactory.createUser({
          email: 'manager2@dashboard-test.com',
          name: 'Mike Manager',
          role: 'manager',
          status: 'inactive',
          lastLogin: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
        }),
        ...Array.from({ length: 15 }, (_, i) =>
          TestDataFactory.createUser({
            email: `user${i + 1}@dashboard-test.com`,
            name: `User ${i + 1}`,
            role: 'user',
            status: i % 5 === 0 ? 'pending' : 'active', // Every 5th user is pending
          })
        ),
      ],
    });

    // Set up page objects
    dashboardPage = new DashboardPage(page);
    settingsPage = new SettingsPage(page);
    billingPage = new BillingPage(page);

    // Mock all necessary APIs
    await AuthHelper.mockAuthAPI(page, testTenant);
    await APIHelper.mockSubscriptionAPI(page, testTenant);
    await APIHelper.mockLicenseAPI(page, testTenant);
    await APIHelper.mockBillingAPI(page, testTenant);

    // Mock dashboard-specific APIs
    await mockDashboardAPI(page, testTenant);
    await mockUserManagementAPI(page, testTenant);

    // Authenticate as admin
    await AuthHelper.loginAsTenant(page, testTenant);
  });

  // Helper function to mock dashboard APIs
  async function mockDashboardAPI(page: Page, tenant: TestTenant) {
    await page.route('**/api/dashboard/**', async (route) => {
      const url = route.request().url();

      if (url.includes('/stats')) {
        const totalUsers = tenant.users.length;
        const activeUsers = tenant.users.filter((u) => u.status === 'active').length;
        const totalSubscriptions = tenant.subscriptions.length;
        const activeSubscriptions = tenant.subscriptions.filter(
          (s) => s.status === 'active'
        ).length;
        const totalLicenses = tenant.subscriptions.reduce((sum, s) => sum + s.licenses, 0);
        const usedLicenses = tenant.subscriptions.reduce((sum, s) => sum + s.usedLicenses, 0);
        const monthlySpend = tenant.subscriptions.reduce((sum, s) => sum + s.monthlyPrice, 0);

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            stats: {
              users: { total: totalUsers, active: activeUsers, pending: totalUsers - activeUsers },
              subscriptions: { total: totalSubscriptions, active: activeSubscriptions },
              licenses: {
                total: totalLicenses,
                used: usedLicenses,
                available: totalLicenses - usedLicenses,
              },
              billing: { monthlySpend, currency: 'USD' },
              lastUpdated: new Date().toISOString(),
            },
          }),
        });
      } else if (url.includes('/activity')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            activities: [
              {
                id: '1',
                type: 'user_login',
                user: 'Sarah Manager',
                timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
                details: 'Successful login from 192.168.1.100',
              },
              {
                id: '2',
                type: 'subscription_upgrade',
                user: 'John Admin',
                timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
                details: 'Upgraded CRM Professional to premium tier',
              },
              {
                id: '3',
                type: 'license_assigned',
                user: 'John Admin',
                timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
                details: 'Assigned 5 ISP Core licenses to new users',
              },
            ],
          }),
        });
      } else {
        await route.continue();
      }
    });
  }

  async function mockUserManagementAPI(page: Page, tenant: TestTenant) {
    await page.route('**/api/users/**', async (route) => {
      const url = route.request().url();
      const method = route.request().method();

      if (url.includes('/users') && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            users: tenant.users,
            total: tenant.users.length,
          }),
        });
      } else if (url.includes('/users') && method === 'POST') {
        const requestBody = JSON.parse(route.request().postData() || '{}');
        const newUser = TestDataFactory.createUser({
          ...requestBody,
          status: 'pending',
        });

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            user: newUser,
          }),
        });
      } else if (method === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'User updated successfully',
          }),
        });
      } else if (method === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'User deactivated successfully',
          }),
        });
      } else {
        await route.continue();
      }
    });
  }

  test.describe('Dashboard Overview', () => {
    test('should display comprehensive subscription status overview', async ({ page }) => {
      await dashboardPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="dashboard"]');

      // Verify subscription summary card
      const subscriptionsCard = page.locator('[data-testid="subscriptions-card"]');
      await expect(subscriptionsCard).toBeVisible();

      // Check subscription counts
      const totalSubscriptions = testTenant.subscriptions.length;
      const activeSubscriptions = testTenant.subscriptions.filter(
        (s) => s.status === 'active'
      ).length;

      await expect(subscriptionsCard.locator('[data-testid="total-subscriptions"]')).toContainText(
        totalSubscriptions.toString()
      );
      await expect(subscriptionsCard.locator('[data-testid="active-subscriptions"]')).toContainText(
        activeSubscriptions.toString()
      );

      // Verify subscription breakdown by category
      await TestUtils.assertElementVisible(page, '[data-testid="subscription-breakdown"]');

      const categories = ['ISP', 'CRM', 'Project Management'];
      for (const category of categories) {
        await expect(
          page.locator(`[data-testid="category-${category.toLowerCase().replace(' ', '-')}"]`)
        ).toBeVisible();
      }

      // Check subscription status indicators
      await TestUtils.assertElementVisible(page, '[data-testid="pending-subscriptions"]');
      const pendingCount = testTenant.subscriptions.filter((s) => s.status === 'pending').length;
      await expect(page.locator('[data-testid="pending-subscriptions"]')).toContainText(
        pendingCount.toString()
      );
    });

    test('should show accurate license usage metrics with visual indicators', async ({ page }) => {
      await dashboardPage.goto();

      const licenseCard = page.locator('[data-testid="license-usage-card"]');
      await expect(licenseCard).toBeVisible();

      // Calculate expected values
      const totalLicenses = testTenant.subscriptions.reduce((sum, s) => sum + s.licenses, 0);
      const usedLicenses = testTenant.subscriptions.reduce((sum, s) => sum + s.usedLicenses, 0);
      const usagePercentage = Math.round((usedLicenses / totalLicenses) * 100);

      // Verify license counts
      await expect(licenseCard.locator('[data-testid="total-licenses"]')).toContainText(
        totalLicenses.toString()
      );
      await expect(licenseCard.locator('[data-testid="used-licenses"]')).toContainText(
        usedLicenses.toString()
      );
      await expect(licenseCard.locator('[data-testid="available-licenses"]')).toContainText(
        (totalLicenses - usedLicenses).toString()
      );

      // Verify usage percentage
      const actualUsagePercentage = await dashboardPage.getLicenseUsagePercentage();
      expect(actualUsagePercentage).toBe(usagePercentage);

      // Verify visual indicators
      await TestUtils.assertElementVisible(page, '[data-testid="license-usage-chart"]');
      await TestUtils.assertElementVisible(page, '[data-testid="usage-progress-bar"]');

      // Check color coding based on usage
      const progressBar = licenseCard.locator('[data-testid="usage-progress-bar"]');
      if (usagePercentage > 90) {
        await expect(progressBar).toHaveClass(/usage-critical/);
      } else if (usagePercentage > 80) {
        await expect(progressBar).toHaveClass(/usage-high/);
      } else {
        await expect(progressBar).toHaveClass(/usage-normal/);
      }
    });

    test('should display user management summary with role breakdown', async ({ page }) => {
      await dashboardPage.goto();

      const userCard = page.locator('[data-testid="user-management-card"]');
      await expect(userCard).toBeVisible();

      // Verify total user counts
      const totalUsers = testTenant.users.length;
      const activeUsers = testTenant.users.filter((u) => u.status === 'active').length;
      const pendingUsers = testTenant.users.filter((u) => u.status === 'pending').length;

      await expect(userCard.locator('[data-testid="total-users"]')).toContainText(
        totalUsers.toString()
      );
      await expect(userCard.locator('[data-testid="active-users"]')).toContainText(
        activeUsers.toString()
      );
      await expect(userCard.locator('[data-testid="pending-users"]')).toContainText(
        pendingUsers.toString()
      );

      // Verify role breakdown
      const adminCount = testTenant.users.filter((u) => u.role === 'admin').length;
      const managerCount = testTenant.users.filter((u) => u.role === 'manager').length;
      const userCount = testTenant.users.filter((u) => u.role === 'user').length;

      await expect(userCard.locator('[data-testid="admin-count"]')).toContainText(
        adminCount.toString()
      );
      await expect(userCard.locator('[data-testid="manager-count"]')).toContainText(
        managerCount.toString()
      );
      await expect(userCard.locator('[data-testid="user-count"]')).toContainText(
        userCount.toString()
      );

      // Verify user management quick actions
      await TestUtils.assertElementVisible(page, '[data-testid="invite-user-quick"]');
      await TestUtils.assertElementVisible(page, '[data-testid="manage-users-quick"]');
    });

    test('should show billing overview with current spend and trends', async ({ page }) => {
      await dashboardPage.goto();

      const billingCard = page.locator('[data-testid="billing-card"]');
      await expect(billingCard).toBeVisible();

      // Calculate expected billing amounts
      const monthlySpend = testTenant.subscriptions
        .filter((s) => s.status === 'active')
        .reduce((sum, s) => sum + s.monthlyPrice, 0);

      // Verify current billing amount
      await expect(billingCard.locator('[data-testid="monthly-spend"]')).toContainText(
        `$${monthlySpend}`
      );

      // Verify billing breakdown by app
      await TestUtils.assertElementVisible(page, '[data-testid="billing-breakdown"]');

      for (const subscription of testTenant.subscriptions.filter((s) => s.status === 'active')) {
        const appBilling = billingCard.locator(`[data-testid="billing-${subscription.appId}"]`);
        await expect(appBilling).toContainText(subscription.appName);
        await expect(appBilling).toContainText(`$${subscription.monthlyPrice}`);
      }

      // Verify billing actions
      await TestUtils.assertElementVisible(page, '[data-testid="view-billing-quick"]');
      await TestUtils.assertElementVisible(page, '[data-testid="payment-methods-quick"]');

      // Verify next billing date
      await TestUtils.assertElementVisible(page, '[data-testid="next-billing-date"]');
    });

    test('should display recent activity feed with proper formatting', async ({ page }) => {
      await dashboardPage.goto();

      const activitySection = page.locator('[data-testid="recent-activity"]');
      await expect(activitySection).toBeVisible();

      // Wait for activity data to load
      await TestUtils.waitForStableElement(page, '[data-testid="activity-list"]');

      // Verify activity entries
      const activityItems = page.locator('[data-testid="activity-item"]');
      const activityCount = await activityItems.count();

      expect(activityCount, 'Should show recent activities').toBeGreaterThan(0);

      // Verify each activity has required elements
      for (let i = 0; i < Math.min(activityCount, 5); i++) {
        const activity = activityItems.nth(i);

        await expect(activity.locator('[data-testid="activity-type"]')).toBeVisible();
        await expect(activity.locator('[data-testid="activity-user"]')).toBeVisible();
        await expect(activity.locator('[data-testid="activity-timestamp"]')).toBeVisible();
        await expect(activity.locator('[data-testid="activity-details"]')).toBeVisible();
      }

      // Test activity filtering
      await page.click('[data-testid="activity-filter"]');
      await TestUtils.waitForStableElement(page, '[data-testid="activity-filter-menu"]');

      const filterOptions = ['All', 'User Login', 'Subscription Changes', 'License Updates'];
      for (const option of filterOptions) {
        await TestUtils.assertElementVisible(
          page,
          `[data-testid="filter-${option.toLowerCase().replace(' ', '-')}"]`
        );
      }

      // Test filtering by type
      await page.click('[data-testid="filter-user-login"]');
      await TestUtils.waitForStableElement(page, '[data-testid="filtered-activities"]');

      const filteredItems = page.locator('[data-testid="activity-item"]');
      const filteredCount = await filteredItems.count();

      // Verify all visible activities match the filter
      for (let i = 0; i < filteredCount; i++) {
        const activity = filteredItems.nth(i);
        const activityType = await activity.locator('[data-testid="activity-type"]').textContent();
        expect(activityType).toContain('login');
      }
    });
  });

  test.describe('Navigation and Quick Actions', () => {
    test('should provide working navigation to all major sections', async ({ page }) => {
      await dashboardPage.goto();

      // Test navigation to subscriptions
      await dashboardPage.navigateToSubscriptions();
      await expect(page).toHaveURL(/\/subscriptions/);
      await TestUtils.assertElementVisible(page, '[data-testid="subscription-management"]');

      // Navigate back to dashboard
      await dashboardPage.goto();

      // Test navigation to licenses
      await dashboardPage.navigateToLicenses();
      await expect(page).toHaveURL(/\/licenses/);
      await TestUtils.assertElementVisible(page, '[data-testid="license-management"]');

      // Navigate back to dashboard
      await dashboardPage.goto();

      // Test navigation to billing
      await dashboardPage.navigateToBilling();
      await expect(page).toHaveURL(/\/billing/);
      await TestUtils.assertElementVisible(page, '[data-testid="billing-management"]');

      // Navigate back to dashboard
      await dashboardPage.goto();

      // Test navigation to settings
      await dashboardPage.navigateToSettings();
      await expect(page).toHaveURL(/\/settings/);
      await TestUtils.assertElementVisible(page, '[data-testid="tenant-settings"]');
    });

    test('should provide functional quick action buttons', async ({ page }) => {
      await dashboardPage.goto();

      // Test quick invite user action
      await page.click('[data-testid="invite-user-quick"]');
      await TestUtils.waitForStableElement(page, '[data-testid="invite-user-modal"]');
      await TestUtils.assertElementVisible(page, '[data-testid="user-email-input"]');
      await page.click('[data-testid="close-modal"]');

      // Test quick subscription browse
      await page.click('[data-testid="browse-apps-quick"]');
      await TestUtils.waitForStableElement(page, '[data-testid="app-catalog"]');
      await expect(page).toHaveURL(/\/app-catalog/);

      // Go back to dashboard
      await dashboardPage.goto();

      // Test quick billing view
      await page.click('[data-testid="view-billing-quick"]');
      await expect(page).toHaveURL(/\/billing/);

      // Go back to dashboard
      await dashboardPage.goto();

      // Test license management quick action
      await page.click('[data-testid="manage-licenses-quick"]');
      await expect(page).toHaveURL(/\/licenses/);
    });

    test('should show contextual alerts and notifications', async ({ page }) => {
      // Mock high-priority alerts
      await page.route('**/api/alerts/**', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            alerts: [
              {
                id: 'alert-1',
                type: 'license_limit_warning',
                severity: 'warning',
                title: 'License usage approaching limit',
                message: 'CRM Professional is at 92% license capacity',
                actionRequired: true,
                actionUrl: '/licenses',
                actionText: 'Manage Licenses',
              },
              {
                id: 'alert-2',
                type: 'subscription_expiry',
                severity: 'info',
                title: 'Subscription renewal reminder',
                message: 'ISP Core Management renews in 30 days',
                actionRequired: false,
              },
              {
                id: 'alert-3',
                type: 'payment_failed',
                severity: 'error',
                title: 'Payment failed',
                message: 'Unable to process payment for Project Manager subscription',
                actionRequired: true,
                actionUrl: '/billing',
                actionText: 'Update Payment Method',
              },
            ],
          }),
        });
      });

      await dashboardPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="dashboard-alerts"]');

      // Verify alert display
      await TestUtils.assertElementVisible(page, '[data-testid="alert-alert-1"]');
      await TestUtils.assertElementVisible(page, '[data-testid="alert-alert-2"]');
      await TestUtils.assertElementVisible(page, '[data-testid="alert-alert-3"]');

      // Verify alert severity indicators
      const warningAlert = page.locator('[data-testid="alert-alert-1"]');
      await expect(warningAlert).toHaveClass(/alert-warning/);

      const errorAlert = page.locator('[data-testid="alert-alert-3"]');
      await expect(errorAlert).toHaveClass(/alert-error/);

      // Test alert actions
      await page.click('[data-testid="alert-alert-1"] [data-testid="alert-action"]');
      await expect(page).toHaveURL(/\/licenses/);

      // Go back and test error alert action
      await dashboardPage.goto();
      await page.click('[data-testid="alert-alert-3"] [data-testid="alert-action"]');
      await expect(page).toHaveURL(/\/billing/);
    });
  });

  test.describe('User Management from Dashboard', () => {
    test('should display comprehensive user statistics', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToUsersTab();

      // Wait for users list to load
      await TestUtils.waitForStableElement(page, '[data-testid="users-list"]');

      const usersList = await settingsPage.getUsersList();

      // Verify user count matches test data
      expect(usersList.length).toBe(testTenant.users.length);

      // Verify user information display
      for (const user of usersList.slice(0, 5)) {
        // Test first 5 users
        const userRow = page.locator(`[data-testid="user-${user.id}"]`);

        await expect(userRow.locator('[data-testid="user-email"]')).toContainText(user.email);
        await expect(userRow.locator('[data-testid="user-role"]')).toContainText(user.role);
        await expect(userRow.locator('[data-testid="user-status"]')).toContainText(user.status);

        // Verify role-specific styling
        const roleElement = userRow.locator('[data-testid="user-role"]');
        if (user.role === 'admin') {
          await expect(roleElement).toHaveClass(/role-admin/);
        } else if (user.role === 'manager') {
          await expect(roleElement).toHaveClass(/role-manager/);
        }
      }
    });

    test('should successfully add new users with validation', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToUsersTab();

      // Test adding a new user
      const newUserEmail = 'newuser@dashboard-test.com';
      const newUserName = 'New Test User';

      await settingsPage.addUser(newUserEmail, newUserName, 'user');

      // Verify success message
      await TestUtils.waitForStableElement(page, '[data-testid="user-added-success"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="user-added-success"]',
        'User added successfully'
      );

      // Verify user appears in the list
      await page.reload();
      await TestUtils.waitForStableElement(page, '[data-testid="users-list"]');

      const newUserRow = page.locator(`[data-testid*="${newUserEmail}"]`);
      await expect(newUserRow).toBeVisible();
      await expect(newUserRow.locator('[data-testid="user-status"]')).toContainText('pending');
    });

    test('should validate user input with appropriate error messages', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToUsersTab();

      // Click add user button
      await page.click('[data-testid="add-user-button"]');
      await TestUtils.waitForStableElement(page, '[data-testid="add-user-modal"]');

      // Try to submit without email
      await page.click('[data-testid="save-user"]');
      await TestUtils.assertElementVisible(page, '[data-testid="email-required-error"]');

      // Test invalid email format
      await page.fill('[data-testid="user-email"]', 'invalid-email');
      await page.click('[data-testid="save-user"]');
      await TestUtils.assertElementVisible(page, '[data-testid="email-format-error"]');

      // Test duplicate email
      const existingEmail = testTenant.users[0].email;
      await page.fill('[data-testid="user-email"]', existingEmail);
      await page.fill('[data-testid="user-name"]', 'Test User');
      await page.click('[data-testid="save-user"]');
      await TestUtils.assertElementVisible(page, '[data-testid="email-duplicate-error"]');

      // Test valid submission
      await page.fill('[data-testid="user-email"]', 'valid@dashboard-test.com');
      await page.fill('[data-testid="user-name"]', 'Valid User');
      await page.click('[data-testid="role-user"]');
      await page.click('[data-testid="save-user"]');
      await TestUtils.waitForStableElement(page, '[data-testid="user-added-success"]');
    });

    test('should support bulk user operations', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToUsersTab();
      await TestUtils.waitForStableElement(page, '[data-testid="users-list"]');

      // Enable bulk selection mode
      await page.click('[data-testid="bulk-operations"]');
      await TestUtils.waitForStableElement(page, '[data-testid="bulk-selection-mode"]');

      // Select multiple users (first 3 regular users)
      const userRows = page.locator('[data-testid^="user-"]');
      const userCount = Math.min(await userRows.count(), 3);

      for (let i = 0; i < userCount; i++) {
        const userCheckbox = userRows.nth(i).locator('[data-testid="user-select-checkbox"]');
        if ((await userCheckbox.count()) > 0) {
          await userCheckbox.check();
        }
      }

      // Verify bulk actions are enabled
      await TestUtils.assertElementVisible(page, '[data-testid="bulk-actions-toolbar"]');

      // Test bulk role change
      await page.click('[data-testid="bulk-change-role"]');
      await TestUtils.waitForStableElement(page, '[data-testid="bulk-role-change-modal"]');

      await page.click('[data-testid="role-manager"]');
      await page.click('[data-testid="confirm-bulk-role-change"]');

      await TestUtils.waitForStableElement(page, '[data-testid="bulk-operation-success"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="bulk-operation-success"]',
        'User roles updated successfully'
      );

      // Test bulk status change
      await page.click('[data-testid="bulk-change-status"]');
      await TestUtils.waitForStableElement(page, '[data-testid="bulk-status-change-modal"]');

      await page.click('[data-testid="status-inactive"]');
      await page.click('[data-testid="confirm-bulk-status-change"]');

      await TestUtils.waitForStableElement(page, '[data-testid="bulk-operation-success"]');
    });
  });

  test.describe('Cross-App Permissions Configuration', () => {
    test('should display permissions matrix for all subscribed apps', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToPermissionsTab();

      // Wait for permissions matrix to load
      await TestUtils.waitForStableElement(page, '[data-testid="permissions-matrix"]');

      // Verify matrix structure
      await TestUtils.assertElementVisible(page, '[data-testid="permissions-table"]');
      await TestUtils.assertElementVisible(page, '[data-testid="users-column"]');
      await TestUtils.assertElementVisible(page, '[data-testid="apps-columns"]');

      // Verify app columns for each active subscription
      const activeApps = testTenant.subscriptions.filter((s) => s.status === 'active');
      for (const app of activeApps) {
        await TestUtils.assertElementVisible(page, `[data-testid="app-column-${app.appId}"]`);
        await TestUtils.assertElementText(
          page,
          `[data-testid="app-column-${app.appId}"] [data-testid="app-name"]`,
          app.appName
        );
      }

      // Verify user rows
      for (const user of testTenant.users.slice(0, 10)) {
        // Test first 10 users
        const userRow = page.locator(`[data-testid="permissions-user-${user.id}"]`);
        await expect(userRow).toBeVisible();
        await expect(userRow.locator('[data-testid="user-name"]')).toContainText(user.name);
        await expect(userRow.locator('[data-testid="user-role"]')).toContainText(user.role);
      }
    });

    test('should allow configuring user permissions for individual apps', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToPermissionsTab();
      await TestUtils.waitForStableElement(page, '[data-testid="permissions-matrix"]');

      // Select a specific user to configure
      const testUser = testTenant.users.find((u) => u.role === 'manager');
      if (testUser) {
        const userRow = page.locator(`[data-testid="permissions-user-${testUser.id}"]`);

        // Test ISP Core permissions
        const ispPermissionCell = userRow.locator('[data-testid="permission-isp-core"]');
        await page.click(`${ispPermissionCell.locator('[data-testid="edit-permissions"]')}`);

        await TestUtils.waitForStableElement(page, '[data-testid="permission-editor-modal"]');

        // Verify available permissions for ISP app
        const ispPermissions = [
          'dashboard',
          'customer_management',
          'billing',
          'reports',
          'network_management',
        ];
        for (const permission of ispPermissions) {
          await TestUtils.assertElementVisible(page, `[data-testid="permission-${permission}"]`);
        }

        // Configure permissions
        await page.check('[data-testid="permission-dashboard"]');
        await page.check('[data-testid="permission-customer_management"]');
        await page.uncheck('[data-testid="permission-billing"]'); // Remove billing access

        await page.click('[data-testid="save-permissions"]');
        await TestUtils.waitForStableElement(page, '[data-testid="permissions-saved-success"]');

        // Verify permissions are reflected in the matrix
        await page.reload();
        await TestUtils.waitForStableElement(page, '[data-testid="permissions-matrix"]');

        const updatedPermissionCell = userRow.locator('[data-testid="permission-isp-core"]');
        await expect(
          updatedPermissionCell.locator('[data-testid="permission-indicator"]')
        ).toHaveClass(/partial-access/);
      }
    });

    test('should support role-based permission templates', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToPermissionsTab();

      // Navigate to role templates
      await page.click('[data-testid="role-templates-tab"]');
      await TestUtils.waitForStableElement(page, '[data-testid="role-templates"]');

      // Verify default role templates
      const roleTemplates = ['Admin Template', 'Manager Template', 'User Template'];
      for (const template of roleTemplates) {
        await TestUtils.assertElementVisible(
          page,
          `[data-testid="template-${template.toLowerCase().replace(' ', '-')}"]`
        );
      }

      // Test creating a custom role template
      await page.click('[data-testid="create-custom-template"]');
      await TestUtils.waitForStableElement(page, '[data-testid="custom-template-modal"]');

      await page.fill('[data-testid="template-name"]', 'Support Manager');
      await page.fill(
        '[data-testid="template-description"]',
        'Template for customer support managers'
      );

      // Configure template permissions
      await page.check('[data-testid="template-permission-customer_management"]');
      await page.check('[data-testid="template-permission-support_tickets"]');
      await page.uncheck('[data-testid="template-permission-billing"]');

      await page.click('[data-testid="save-template"]');
      await TestUtils.waitForStableElement(page, '[data-testid="template-created-success"]');

      // Verify template appears in the list
      await TestUtils.assertElementVisible(page, '[data-testid="template-support-manager"]');

      // Test applying template to users
      await page.click('[data-testid="template-support-manager"] [data-testid="apply-template"]');
      await TestUtils.waitForStableElement(page, '[data-testid="apply-template-modal"]');

      // Select users to apply template to
      const managerUsers = testTenant.users.filter((u) => u.role === 'manager');
      for (const user of managerUsers.slice(0, 2)) {
        await page.check(`[data-testid="user-${user.id}"]`);
      }

      await page.click('[data-testid="confirm-apply-template"]');
      await TestUtils.waitForStableElement(page, '[data-testid="template-applied-success"]');
    });

    test('should validate permission conflicts and dependencies', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.navigateToPermissionsTab();

      const testUser = testTenant.users.find((u) => u.role === 'user');
      if (testUser) {
        const userRow = page.locator(`[data-testid="permissions-user-${testUser.id}"]`);
        const crmPermissionCell = userRow.locator('[data-testid="permission-crm-pro"]');

        await page.click(crmPermissionCell.locator('[data-testid="edit-permissions"]'));
        await TestUtils.waitForStableElement(page, '[data-testid="permission-editor-modal"]');

        // Try to enable advanced analytics without basic permissions
        await page.uncheck('[data-testid="permission-contact_management"]'); // Disable basic permission
        await page.check('[data-testid="permission-advanced_analytics"]'); // Enable advanced permission

        await page.click('[data-testid="save-permissions"]');

        // Verify validation error
        await TestUtils.assertElementVisible(page, '[data-testid="permission-dependency-error"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="permission-dependency-error"]',
          'Advanced Analytics requires Contact Management permission'
        );

        // Test role-based restrictions
        await page.check('[data-testid="permission-admin_panel"]'); // Try to give admin permission to user role
        await page.click('[data-testid="save-permissions"]');

        await TestUtils.assertElementVisible(page, '[data-testid="role-restriction-error"]');
        await TestUtils.assertElementText(
          page,
          '[data-testid="role-restriction-error"]',
          'Admin Panel access requires Admin or Manager role'
        );
      }
    });
  });

  test.describe('Organization Settings Management', () => {
    test('should display and allow editing organization information', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.goto();

      // Verify organization information display
      await TestUtils.assertElementVisible(page, '[data-testid="organization-info"]');

      const orgInfo = page.locator('[data-testid="organization-info"]');
      await expect(orgInfo.locator('[data-testid="org-name"]')).toContainText(testTenant.name);
      await expect(orgInfo.locator('[data-testid="org-email"]')).toContainText(testTenant.email);
      await expect(orgInfo.locator('[data-testid="org-domain"]')).toContainText(testTenant.domain);
      await expect(orgInfo.locator('[data-testid="org-plan"]')).toContainText(testTenant.plan);

      // Test editing organization information
      await page.click('[data-testid="edit-org-info"]');
      await TestUtils.waitForStableElement(page, '[data-testid="edit-org-modal"]');

      const newOrgName = 'Updated Organization Name';
      await page.fill('[data-testid="org-name-input"]', newOrgName);
      await page.fill(
        '[data-testid="org-description"]',
        'Updated organization description for testing'
      );

      await page.click('[data-testid="save-org-changes"]');
      await TestUtils.waitForStableElement(page, '[data-testid="org-updated-success"]');

      // Verify changes are reflected
      await page.reload();
      await expect(page.locator('[data-testid="org-name"]')).toContainText(newOrgName);
    });

    test('should manage security settings and preferences', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.goto();

      // Navigate to security settings
      await page.click('[data-testid="security-settings-tab"]');
      await TestUtils.waitForStableElement(page, '[data-testid="security-settings"]');

      // Test password policy configuration
      await TestUtils.assertElementVisible(page, '[data-testid="password-policy"]');

      await page.check('[data-testid="require-uppercase"]');
      await page.check('[data-testid="require-numbers"]');
      await page.check('[data-testid="require-special-chars"]');
      await page.fill('[data-testid="min-password-length"]', '12');

      // Test session management settings
      await TestUtils.assertElementVisible(page, '[data-testid="session-settings"]');

      await page.fill('[data-testid="session-timeout"]', '480'); // 8 hours
      await page.check('[data-testid="require-mfa"]');

      // Test IP restrictions
      await TestUtils.assertElementVisible(page, '[data-testid="ip-restrictions"]');

      await page.click('[data-testid="enable-ip-whitelist"]');
      await TestUtils.waitForStableElement(page, '[data-testid="ip-whitelist-config"]');

      await page.fill('[data-testid="allowed-ips"]', '192.168.1.0/24\n10.0.0.0/8');

      // Save security settings
      await page.click('[data-testid="save-security-settings"]');
      await TestUtils.waitForStableElement(page, '[data-testid="security-settings-saved"]');

      // Verify settings are applied
      await page.reload();
      await page.click('[data-testid="security-settings-tab"]');
      await expect(page.locator('[data-testid="require-mfa"]')).toBeChecked();
      await expect(page.locator('[data-testid="session-timeout"]')).toHaveValue('480');
    });

    test('should configure notification preferences', async ({ page }) => {
      await dashboardPage.goto();
      await settingsPage.goto();

      // Navigate to notifications
      await page.click('[data-testid="notifications-tab"]');
      await TestUtils.waitForStableElement(page, '[data-testid="notification-settings"]');

      // Test email notification preferences
      const emailSettings = page.locator('[data-testid="email-notifications"]');

      await emailSettings.locator('[data-testid="license-alerts"]').check();
      await emailSettings.locator('[data-testid="billing-notifications"]').check();
      await emailSettings.locator('[data-testid="user-activity"]').uncheck();
      await emailSettings.locator('[data-testid="system-maintenance"]').check();

      // Configure notification frequency
      await page.selectOption('[data-testid="digest-frequency"]', 'weekly');

      // Test webhook configuration
      await page.click('[data-testid="webhook-settings"]');
      await TestUtils.waitForStableElement(page, '[data-testid="webhook-config"]');

      await page.fill('[data-testid="webhook-url"]', 'https://api.example.com/webhooks/tenant');
      await page.check('[data-testid="webhook-user-events"]');
      await page.check('[data-testid="webhook-subscription-events"]');

      // Test webhook verification
      await page.click('[data-testid="test-webhook"]');
      await TestUtils.waitForStableElement(page, '[data-testid="webhook-test-result"]');

      // Save notification settings
      await page.click('[data-testid="save-notification-settings"]');
      await TestUtils.waitForStableElement(page, '[data-testid="notifications-saved-success"]');
    });

    test('should manage billing and usage analytics preferences', async ({ page }) => {
      await dashboardPage.goto();
      await billingPage.goto();

      // Navigate to usage analytics
      await page.click('[data-testid="usage-analytics-tab"]');
      await TestUtils.waitForStableElement(page, '[data-testid="usage-analytics"]');

      // Verify current billing information
      const currentBill = await billingPage.getCurrentBillAmount();
      expect(currentBill).toBeGreaterThan(0);

      // Test billing history
      const billingHistory = await billingPage.getBillingHistory();
      expect(billingHistory.length).toBeGreaterThan(0);

      // Verify payment methods
      const paymentMethods = await billingPage.getPaymentMethods();
      expect(paymentMethods.length).toBeGreaterThan(0);

      // Test downloading invoices
      if (billingHistory.length > 0) {
        // Find a paid invoice to download
        const paidInvoice = billingHistory.find((invoice) => invoice.status.includes('paid'));
        if (paidInvoice) {
          await billingPage.downloadInvoice('1'); // Use first invoice ID
        }
      }

      // Test usage analytics configuration
      await page.click('[data-testid="analytics-preferences"]');
      await TestUtils.waitForStableElement(page, '[data-testid="analytics-config"]');

      await page.check('[data-testid="detailed-usage-tracking"]');
      await page.check('[data-testid="cost-optimization-insights"]');
      await page.selectOption('[data-testid="reporting-frequency"]', 'monthly');

      await page.click('[data-testid="save-analytics-preferences"]');
      await TestUtils.waitForStableElement(page, '[data-testid="analytics-preferences-saved"]');
    });
  });

  test.describe('Performance and Accessibility', () => {
    test('should meet dashboard performance benchmarks', async ({ page }) => {
      const metrics = await PerformanceHelper.measurePageLoad(page);

      await dashboardPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="dashboard"]');

      // Dashboard should load quickly
      expect(metrics.loadTime, 'Dashboard should load within 3 seconds').toBeLessThan(3000);
      expect(metrics.domContentLoaded, 'DOM should be ready within 1.5 seconds').toBeLessThan(1500);

      // Test navigation performance
      const startTime = Date.now();
      await settingsPage.goto();
      await TestUtils.waitForStableElement(page, '[data-testid="tenant-settings"]');
      const navigationTime = Date.now() - startTime;

      expect(navigationTime, 'Settings navigation should be fast').toBeLessThan(1000);
    });

    test('should be fully accessible with proper ARIA attributes', async ({ page }) => {
      await dashboardPage.goto();

      // Test main dashboard accessibility
      await TestUtils.assertElementAttribute(page, '[data-testid="dashboard"]', 'role', 'main');
      await TestUtils.assertElementVisible(page, 'h1');

      // Test card accessibility
      const cards = [
        'subscriptions-card',
        'license-usage-card',
        'user-management-card',
        'billing-card',
      ];
      for (const cardId of cards) {
        const card = page.locator(`[data-testid="${cardId}"]`);
        await expect(card).toHaveAttribute('role', 'region');
        await expect(card).toHaveAttribute('aria-labelledby');
      }

      // Test keyboard navigation
      await page.keyboard.press('Tab');
      const firstFocusable = await page.evaluate(() => document.activeElement?.tagName);
      expect(['A', 'BUTTON', 'INPUT']).toContain(firstFocusable);

      // Test screen reader announcements
      await TestUtils.assertElementAttribute(
        page,
        '[data-testid="recent-activity"]',
        'aria-live',
        'polite'
      );
    });

    test('should handle error states gracefully', async ({ page }) => {
      // Simulate various API failures
      await page.route('**/api/dashboard/stats', (route) => {
        route.abort('failed');
      });

      await dashboardPage.goto();

      // Verify error state handling
      await TestUtils.waitForStableElement(page, '[data-testid="dashboard-error"]');
      await TestUtils.assertElementText(
        page,
        '[data-testid="dashboard-error"]',
        'Unable to load dashboard data'
      );

      // Verify retry functionality
      await TestUtils.assertElementVisible(page, '[data-testid="retry-dashboard"]');

      // Test partial failures (some cards load, others don't)
      await page.unroute('**/api/dashboard/stats');
      await page.route('**/api/dashboard/activity', (route) => {
        route.abort('failed');
      });

      await page.click('[data-testid="retry-dashboard"]');

      // Verify partial loading state
      await TestUtils.assertElementVisible(page, '[data-testid="subscriptions-card"]');
      await TestUtils.assertElementVisible(page, '[data-testid="activity-error"]');
    });
  });

  test.afterEach(async ({ page }) => {
    // Take screenshot on failure
    if (test.info().status === 'failed') {
      await TestUtils.takeScreenshot(page, `tenant-dashboard-${test.info().title}`);
    }

    // Assert no console errors
    await TestUtils.assertNoConsoleErrors(page);
  });
});
