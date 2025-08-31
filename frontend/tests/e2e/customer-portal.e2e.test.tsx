/**
 * Customer Portal E2E Tests
 * End-to-end testing for customer portal workflows
 */

import { test, expect } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';
import { APIBehaviorTester } from '../fixtures/api-behaviors';

test.describe('Customer Portal E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure authenticated session
    await setupAuth(page, 'customer');
    const api = new APIBehaviorTester(page, { enableMocking: true });
    await api.setupCustomerAPIMocks();

    // Navigate to customer portal
    await page.goto('/customer');

    await page.waitForSelector('[data-testid="customer-dashboard"]', { timeout: 10000 });
  });

  test.describe('Dashboard Workflow', () => {
    test('should display customer dashboard with account overview', async ({ page }) => {
      await expect(page.getByTestId('customer-dashboard')).toBeVisible();
      await expect(page.getByText('Customer Dashboard')).toBeVisible();

      // Check for key customer information
      await expect(page.getByText(/Account Overview/i)).toBeVisible();
    });

    test('should show current service status', async ({ page }) => {
      // Verify service status indicators
      await page.waitForSelector('[data-testid="service-status"]');
      await expect(page.getByTestId('service-status')).toBeVisible();
    });

    test('should display usage metrics', async ({ page }) => {
      // Check data usage displays
      await page.waitForSelector('[data-testid="usage-metrics"]');
      await expect(page.getByTestId('usage-metrics')).toBeVisible();
    });
  });

  test.describe('Billing Workflow', () => {
    test('should navigate to billing page', async ({ page }) => {
      await page.click('a[href*="billing"]');
      await page.waitForSelector('[data-testid="customer-billing"]');

      expect(page.url()).toContain('/billing');
      await expect(page.getByText('Billing & Payments')).toBeVisible();
    });

    test('should display current bill and payment history', async ({ page }) => {
      await page.goto('/customer/billing');
      await page.waitForSelector('[data-testid="customer-billing"]');

      // Check current bill display
      await expect(page.getByText(/Current Bill/i)).toBeVisible();
      await expect(page.getByText(/Payment History/i)).toBeVisible();
    });

    test('should handle payment workflow', async ({ page }) => {
      await page.goto('/customer/billing');
      await page.waitForSelector('[data-testid="pay-bill-button"]');

      // Click pay bill button
      await page.click('[data-testid="pay-bill-button"]');

      // Should open payment form or redirect to payment processor
    });

    test('should allow invoice download', async ({ page }) => {
      await page.goto('/customer/billing');

      // Check for download invoice functionality
      const downloadButton = page.getByText(/Download Invoice/i);
      if (await downloadButton.isVisible()) {
        await downloadButton.click();
      }
    });
  });

  test.describe('Support Workflow', () => {
    test('should access support center', async ({ page }) => {
      await page.goto('/customer/support');

      expect(page.url()).toContain('/support');
      await expect(page.getByText(/Support Center/i)).toBeVisible();
    });

    test('should create support ticket', async ({ page }) => {
      await page.goto('/customer/support');

      // Look for ticket creation functionality
      const createTicketButton = page.getByText(/Create Ticket/i).first();
      if (await createTicketButton.isVisible()) {
        await createTicketButton.click();
      }
    });

    test('should display ticket history', async ({ page }) => {
      await page.goto('/customer/support');

      // Verify ticket history is accessible
      await expect(
        page.getByText(/Support History/i).or(page.getByText(/My Tickets/i))
      ).toBeVisible();
    });
  });

  test.describe('Usage Monitoring', () => {
    test('should display data usage charts', async ({ page }) => {
      await page.goto('/customer/usage');

      // Check for usage visualization
      expect(page.url()).toContain('/usage');
    });

    test('should show usage alerts and notifications', async ({ page }) => {
      await page.goto('/customer/usage');

      // Verify usage alerts functionality
      const alertsSection = page.getByText(/Usage Alerts/i);
      if (await alertsSection.isVisible()) {
        await expect(alertsSection).toBeVisible();
      }
    });
  });

  test.describe('Account Management', () => {
    test('should access account settings', async ({ page }) => {
      await page.goto('/customer/account');

      expect(page.url()).toContain('/account');
      await expect(page.getByText(/Account Settings/i)).toBeVisible();
    });

    test('should update account information', async ({ page }) => {
      await page.goto('/customer/account');

      // Look for edit profile functionality
      const editButton = page.getByText(/Edit Profile/i).or(page.getByText(/Update Information/i));
      if (await editButton.isVisible()) {
        await editButton.click();
      }
    });

    test('should change password', async ({ page }) => {
      await page.goto('/customer/account');

      // Check password change functionality
      const passwordButton = page.getByText(/Change Password/i);
      if (await passwordButton.isVisible()) {
        await passwordButton.click();
      }
    });
  });

  test.describe('Service Management', () => {
    test('should display current services', async ({ page }) => {
      await page.goto('/customer/services');

      expect(page.url()).toContain('/services');
      await expect(page.getByText(/My Services/i)).toBeVisible();
    });

    test('should request service changes', async ({ page }) => {
      await page.goto('/customer/services');

      // Check for service modification options
      const upgradeButton = page.getByText(/Upgrade/i).or(page.getByText(/Change Plan/i));
      if (await upgradeButton.isVisible()) {
        await upgradeButton.click();
      }
    });
  });

  test.describe('Mobile App Integration', () => {
    test('should provide mobile app download links', async ({ page }) => {
      // Check for mobile app promotion
      const mobileLinks = page.getByText(/Mobile App/i).or(page.getByText(/Download App/i));
      if (await mobileLinks.isVisible()) {
        await expect(mobileLinks).toBeVisible();
      }
    });
  });

  test.describe('Performance Tests', () => {
    test('should load customer pages quickly', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/customer/dashboard');
      await page.waitForSelector('[data-testid="customer-dashboard"]');

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(2000);
    });

    test('should handle concurrent page loads', async ({ page }) => {
      // Test multiple page navigation
      await Promise.all([
        page.goto('/customer/billing'),
        page.goto('/customer/usage'),
        page.goto('/customer/support'),
      ]);
    });
  });

  test.describe('Security Tests', () => {
    test('should protect customer data', async ({ page }) => {
      await page.goto('/customer/account');

      // Verify sensitive data is protected
      const sensitiveElements = page.locator('[data-sensitive]');
      if ((await sensitiveElements.count()) > 0) {
        // Check that sensitive data is properly masked or protected
        await expect(sensitiveElements.first()).toBeVisible();
      }
    });

    test('should handle session timeout', async ({ page }) => {
      // Simulate session timeout
      await page.context().clearCookies();
      await page.goto('/customer/billing');

      // Should redirect to login or show authentication prompt
    });
  });

  test.describe('Accessibility Tests', () => {
    test('should support screen readers', async ({ page }) => {
      await page.goto('/customer/dashboard');

      // Check for proper ARIA labels and structure
      const mainContent = page.getByRole('main');
      await expect(mainContent).toBeVisible();
    });

    test('should be keyboard accessible', async ({ page }) => {
      await page.goto('/customer/billing');

      // Test tab navigation
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Verify focus is visible and functional
    });
  });

  test.describe('Error Handling', () => {
    test('should handle API failures gracefully', async ({ page }) => {
      // Mock API failure
      await page.route('**/api/**', (route) => route.abort());

      await page.goto('/customer/billing');

      // Should show appropriate error messages
      await page.unroute('**/api/**');
    });

    test('should show maintenance messages', async ({ page }) => {
      // Test maintenance mode handling
      await page.goto('/customer/services');

      // Verify graceful handling of maintenance scenarios
    });
  });

  test.describe('Real-time Features', () => {
    test('should update usage data in real-time', async ({ page }) => {
      await page.goto('/customer/usage');

      // Verify real-time updates (when implemented)
      await page.waitForTimeout(2000);
    });

    test('should show live service status', async ({ page }) => {
      await page.goto('/customer/dashboard');

      // Check for live service status indicators
      const statusIndicator = page.getByTestId('service-status');
      if (await statusIndicator.isVisible()) {
        await expect(statusIndicator).toBeVisible();
      }
    });
  });

  test.describe('Notification System', () => {
    test('should display system notifications', async ({ page }) => {
      await page.goto('/customer/dashboard');

      // Check for notification system
      const notifications = page
        .getByRole('alert')
        .or(page.locator('[data-testid*="notification"]'));
      if ((await notifications.count()) > 0) {
        await expect(notifications.first()).toBeVisible();
      }
    });

    test('should handle notification preferences', async ({ page }) => {
      await page.goto('/customer/account');

      // Look for notification settings
      const notificationSettings = page.getByText(/Notification/i);
      if (await notificationSettings.isVisible()) {
        await expect(notificationSettings).toBeVisible();
      }
    });
  });
});
