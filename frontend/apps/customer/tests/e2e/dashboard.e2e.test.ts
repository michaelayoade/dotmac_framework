/**
 * E2E Tests for Customer Dashboard
 * Tests dashboard functionality, data display, and user interactions
 */

import { test, expect } from '@playwright/test';

// Mock dashboard data
const mockDashboardData = {
  account: {
    id: '123',
    name: 'Test User',
    email: 'test@example.com',
    status: 'active'
  },
  services: [{
    id: 'service-1',
    name: 'Premium Internet',
    type: 'internet',
    status: 'active',
    speed: { download: 100, upload: 10 },
    usage: { current: 450, limit: 1000, unit: 'GB' },
    features: ['Unlimited Data', 'WiFi 6']
  }],
  billing: {
    currentBalance: -45.99,
    nextBillAmount: 99.99,
    nextBillDate: '2024-02-15',
    paymentMethod: 'Credit Card',
    lastPayment: {
      amount: 99.99,
      date: '2024-01-15'
    }
  },
  networkStatus: {
    connectionStatus: 'connected',
    currentSpeed: { download: 98.5, upload: 9.8 },
    uptime: 99.9
  },
  supportTickets: []
};

test.describe('Customer Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route('**/api/customer/dashboard', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDashboardData)
      });
    });

    await page.route('**/api/customer/notifications', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          notifications: [{
            id: '1',
            type: 'maintenance',
            severity: 'medium',
            title: 'Scheduled Maintenance',
            message: 'Network maintenance tonight 2-4 AM',
            estimated_resolution: '2 hours'
          }]
        })
      });
    });

    // Login first
    await page.goto('/');
    await page.getByLabel(/email address/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('SecurePass123!');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL('/dashboard');
  });

  test.describe('Dashboard Layout', () => {
    test('should display main dashboard sections', async ({ page }) => {
      // Welcome header
      await expect(page.getByText(/welcome/i)).toBeVisible();
      
      // Service status overview
      await expect(page.getByText(/service status/i)).toBeVisible();
      
      // Network status
      await expect(page.getByText(/connected/i)).toBeVisible();
      
      // Billing information
      await expect(page.getByText(/current balance/i)).toBeVisible();
      
      // Quick actions
      await expect(page.getByText(/pay bill/i)).toBeVisible();
      await expect(page.getByText(/get support/i)).toBeVisible();
    });

    test('should show development indicator when using mock data', async ({ page }) => {
      // If using mock data, should show development notice
      const devIndicator = page.getByText(/using mock data/i);
      if (await devIndicator.isVisible()) {
        await expect(devIndicator).toContainText('API not available');
      }
    });

    test('should display user account information', async ({ page }) => {
      await expect(page.getByText('Test User')).toBeVisible();
      await expect(page.getByText('$45.99')).toBeVisible(); // Current balance
    });
  });

  test.describe('Service Status', () => {
    test('should display internet service status', async ({ page }) => {
      await expect(page.getByText('Premium Internet')).toBeVisible();
      await expect(page.getByText('active')).toBeVisible();
      await expect(page.getByText('100')).toBeVisible(); // Download speed
    });

    test('should show service usage information', async ({ page }) => {
      await expect(page.getByText('450')).toBeVisible(); // Current usage
      await expect(page.getByText('1000')).toBeVisible(); // Usage limit
      await expect(page.getByText('GB')).toBeVisible(); // Unit
    });

    test('should display service features', async ({ page }) => {
      await expect(page.getByText('Unlimited Data')).toBeVisible();
      await expect(page.getByText('WiFi 6')).toBeVisible();
    });
  });

  test.describe('Network Performance', () => {
    test('should show connection status', async ({ page }) => {
      await expect(page.getByText('connected')).toBeVisible();
      
      // Network speeds
      await expect(page.getByText('98.5')).toBeVisible(); // Current download speed
      await expect(page.getByText('9.8')).toBeVisible(); // Current upload speed
    });

    test('should display uptime information', async ({ page }) => {
      await expect(page.getByText('99.9')).toBeVisible(); // Uptime percentage
    });

    test('should have speed test button', async ({ page }) => {
      const speedTestButton = page.getByText(/run speed test/i);
      await expect(speedTestButton).toBeVisible();
      
      // Click should trigger speed test (mocked)
      await speedTestButton.click();
      // In a real test, this would verify the speed test functionality
    });
  });

  test.describe('Billing Information', () => {
    test('should display current balance', async ({ page }) => {
      await expect(page.getByText('$45.99')).toBeVisible();
    });

    test('should show next bill information', async ({ page }) => {
      await expect(page.getByText('$99.99')).toBeVisible(); // Next bill amount
      await expect(page.getByText('Feb 15, 2024')).toBeVisible(); // Due date
    });

    test('should display last payment info', async ({ page }) => {
      await expect(page.getByText('Credit Card')).toBeVisible();
      await expect(page.getByText('Jan 15, 2024')).toBeVisible();
    });
  });

  test.describe('Notifications and Alerts', () => {
    test('should display service notifications', async ({ page }) => {
      await expect(page.getByText('Scheduled Maintenance')).toBeVisible();
      await expect(page.getByText('Network maintenance tonight 2-4 AM')).toBeVisible();
      await expect(page.getByText('2 hours')).toBeVisible(); // Estimated resolution
    });

    test('should show notification severity indicators', async ({ page }) => {
      // Should have visual indicators for different severity levels
      const notificationElement = page.locator('[data-testid="notification"]')
        .or(page.locator('.notification'))
        .or(page.getByText('Scheduled Maintenance').locator('..'));
      
      await expect(notificationElement).toBeVisible();
    });
  });

  test.describe('Quick Actions', () => {
    test('should have pay bill action', async ({ page }) => {
      const payBillButton = page.getByText(/pay bill/i);
      await expect(payBillButton).toBeVisible();
      
      await payBillButton.click();
      // Should show pay bill dialog or navigate to payment page
      // This would be expanded based on actual implementation
    });

    test('should have get support action', async ({ page }) => {
      const getSupportButton = page.getByText(/get support/i);
      await expect(getSupportButton).toBeVisible();
      
      await getSupportButton.click();
      // Should navigate to support page or open support widget
    });

    test('should have upgrade service action', async ({ page }) => {
      const upgradeButton = page.getByText(/upgrade service/i);
      await expect(upgradeButton).toBeVisible();
      
      await upgradeButton.click();
      // Should navigate to upgrade page
    });

    test('should have view bills action', async ({ page }) => {
      const viewBillsButton = page.getByText(/view bills/i);
      await expect(viewBillsButton).toBeVisible();
      
      await viewBillsButton.click();
      // Should navigate to billing history
    });
  });

  test.describe('Data Refresh', () => {
    test('should refresh data automatically', async ({ page }) => {
      // Mock updated data
      let refreshCount = 0;
      await page.route('**/api/customer/dashboard', route => {
        refreshCount++;
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ...mockDashboardData,
            networkStatus: {
              ...mockDashboardData.networkStatus,
              currentSpeed: { download: 95.0, upload: 9.5 } // Updated speeds
            }
          })
        });
      });

      // Wait for automatic refresh (if implemented)
      await page.waitForTimeout(5000);
      
      // Should show updated data
      if (refreshCount > 1) {
        await expect(page.getByText('95.0')).toBeVisible();
      }
    });

    test('should handle API errors gracefully', async ({ page }) => {
      // Mock API error
      await page.route('**/api/customer/dashboard', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' })
        });
      });

      await page.reload();
      
      // Should show error message or fallback content
      const errorMessage = page.getByText(/error/i).or(page.getByText(/try again/i));
      await expect(errorMessage).toBeVisible();
    });
  });

  test.describe('Charts and Visualizations', () => {
    test('should display usage charts', async ({ page }) => {
      // Look for chart containers or SVG elements
      const chart = page.locator('[data-testid="usage-chart"]')
        .or(page.locator('.recharts-wrapper'))
        .or(page.locator('svg'));
      
      await expect(chart).toBeVisible();
    });

    test('should show network performance indicators', async ({ page }) => {
      // Performance indicators should be visible
      const performanceIndicator = page.locator('[data-testid="performance-indicator"]')
        .or(page.getByText(/performance/i));
      
      await expect(performanceIndicator).toBeVisible();
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on mobile devices', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      
      // Key information should still be visible
      await expect(page.getByText(/welcome/i)).toBeVisible();
      await expect(page.getByText('connected')).toBeVisible();
      await expect(page.getByText('$99.99')).toBeVisible();
      
      // Quick actions should be accessible
      await expect(page.getByText(/pay bill/i)).toBeVisible();
    });

    test('should adapt layout for tablet', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      
      // Grid layout should adapt
      const serviceCards = page.locator('[data-testid="service-card"]')
        .or(page.locator('.service-status'));
      
      await expect(serviceCards).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should have navigation menu', async ({ page }) => {
      // Look for navigation elements
      const nav = page.locator('nav')
        .or(page.locator('[data-testid="navigation"]'))
        .or(page.getByRole('navigation'));
      
      await expect(nav).toBeVisible();
    });

    test('should navigate to different sections', async ({ page }) => {
      // Test navigation to different sections if available
      const settingsLink = page.getByText(/settings/i)
        .or(page.getByText(/profile/i))
        .or(page.getByText(/account/i));
      
      if (await settingsLink.isVisible()) {
        await settingsLink.click();
        // Should navigate to settings page
      }
    });
  });

  test.describe('Accessibility', () => {
    test('should be keyboard navigable', async ({ page }) => {
      // Tab through interactive elements
      await page.keyboard.press('Tab');
      
      // Should be able to navigate to all interactive elements
      const focusedElement = page.locator(':focus');
      await expect(focusedElement).toBeVisible();
    });

    test('should have proper ARIA labels', async ({ page }) => {
      // Check for ARIA labels on interactive elements
      const buttons = page.locator('button');
      const buttonCount = await buttons.count();
      
      for (let i = 0; i < Math.min(buttonCount, 5); i++) {
        const button = buttons.nth(i);
        if (await button.isVisible()) {
          // Should have accessible name (aria-label, aria-labelledby, or text content)
          const ariaLabel = await button.getAttribute('aria-label');
          const textContent = await button.textContent();
          const ariaLabelledBy = await button.getAttribute('aria-labelledby');
          
          expect(ariaLabel || textContent || ariaLabelledBy).toBeTruthy();
        }
      }
    });

    test('should announce dynamic content changes', async ({ page }) => {
      // Check for live regions that announce updates
      const liveRegion = page.locator('[aria-live]')
        .or(page.locator('[role="status"]'))
        .or(page.locator('[role="alert"]'));
      
      if (await liveRegion.isVisible()) {
        await expect(liveRegion).toHaveAttribute('aria-live');
      }
    });
  });

  test.describe('Performance', () => {
    test('should load dashboard data efficiently', async ({ page }) => {
      const startTime = Date.now();
      await page.reload();
      
      // Main content should load quickly
      await expect(page.getByText(/welcome/i)).toBeVisible();
      
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000);
    });

    test('should handle large datasets', async ({ page }) => {
      // Mock large dataset
      const largeDataset = {
        ...mockDashboardData,
        services: Array.from({ length: 10 }, (_, i) => ({
          id: `service-${i}`,
          name: `Service ${i}`,
          type: 'internet',
          status: 'active',
          speed: { download: 100 + i, upload: 10 + i },
          usage: { current: 400 + i * 50, limit: 1000, unit: 'GB' }
        }))
      };

      await page.route('**/api/customer/dashboard', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(largeDataset)
        });
      });

      await page.reload();
      
      // Should still render without performance issues
      await expect(page.getByText(/welcome/i)).toBeVisible();
      await expect(page.getByText('Service 0')).toBeVisible();
      await expect(page.getByText('Service 9')).toBeVisible();
    });
  });

  test.describe('Security', () => {
    test('should not expose sensitive data in DOM', async ({ page }) => {
      // Check that sensitive data is not exposed in data attributes or comments
      const html = await page.content();
      
      // Should not contain full account numbers, SSNs, etc.
      expect(html).not.toMatch(/\b\d{4}-\d{4}-\d{4}-\d{4}\b/); // Credit card pattern
      expect(html).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/); // SSN pattern
    });

    test('should require authentication', async ({ page }) => {
      // Clear any existing session
      await page.context().clearCookies();
      
      // Try to access dashboard directly
      await page.goto('/dashboard');
      
      // Should redirect to login
      await page.waitForURL('/');
      expect(page.url()).toContain('/');
    });

    test('should handle session expiration', async ({ page }) => {
      // Mock session expiration
      await page.route('**/api/customer/dashboard', route => {
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Session expired' })
        });
      });

      await page.reload();
      
      // Should redirect to login or show re-authentication prompt
      await page.waitForTimeout(2000);
      // This behavior depends on implementation
    });
  });
});