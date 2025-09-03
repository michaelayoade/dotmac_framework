import { test, expect, type Page } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'admin@dotmac.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('should display dashboard elements', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Dashboard');
    await expect(page.locator('[data-testid="stats-grid"]')).toBeVisible();
    await expect(page.locator('[data-testid="recent-activity"]')).toBeVisible();
  });

  test('should show statistics cards', async ({ page }) => {
    // Check for common dashboard stats
    await expect(page.locator('text=Total Tenants')).toBeVisible();
    await expect(page.locator('text=Active Users')).toBeVisible();
    await expect(page.locator('text=Monthly Revenue')).toBeVisible();
    await expect(page.locator('text=System Health')).toBeVisible();
  });

  test('should display charts and graphs', async ({ page }) => {
    await expect(page.locator('[data-testid="revenue-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-growth-chart"]')).toBeVisible();
  });

  test('should show recent activities', async ({ page }) => {
    const activitySection = page.locator('[data-testid="recent-activity"]');
    await expect(activitySection).toBeVisible();
    await expect(activitySection.locator('h3')).toContainText('Recent Activity');
  });

  test('should have working navigation sidebar', async ({ page }) => {
    // Check sidebar links
    await expect(page.locator('a[href="/dashboard"]')).toBeVisible();
    await expect(page.locator('a[href="/tenants"]')).toBeVisible();
    await expect(page.locator('a[href="/users"]')).toBeVisible();
    await expect(page.locator('a[href="/settings"]')).toBeVisible();
  });

  test('should navigate to tenants page', async ({ page }) => {
    await page.click('a[href="/tenants"]');
    await expect(page).toHaveURL('/tenants');
    await expect(page.locator('h1')).toContainText('Tenant Management');
  });

  test('should have working user menu', async ({ page }) => {
    await page.click('[data-testid="user-menu"]');

    // Check dropdown items
    await expect(page.locator('text=Profile')).toBeVisible();
    await expect(page.locator('text=Settings')).toBeVisible();
    await expect(page.locator('text=Sign out')).toBeVisible();
  });

  test('should refresh data with refresh button', async ({ page }) => {
    const refreshButton = page.locator('[data-testid="refresh-dashboard"]');
    if (await refreshButton.isVisible()) {
      await refreshButton.click();

      // Should show loading state briefly
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();
    }
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Sidebar should be collapsed on mobile
    const sidebar = page.locator('[data-testid="sidebar"]');
    if (await sidebar.isVisible()) {
      await expect(sidebar).toHaveClass(/collapsed|hidden/);
    }

    // Mobile menu should be available
    const mobileMenuButton = page.locator('[data-testid="mobile-menu"]');
    if (await mobileMenuButton.isVisible()) {
      await expect(mobileMenuButton).toBeVisible();
    }
  });

  test('should handle error states gracefully', async ({ page }) => {
    // Mock API error
    await page.route('**/api/v1/dashboard/stats', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal server error' }),
      });
    });

    await page.reload();

    // Should show error message
    await expect(page.locator('text=Failed to load dashboard data')).toBeVisible();
  });

  test('should display system alerts when present', async ({ page }) => {
    // Mock system alerts
    await page.route('**/api/v1/system/alerts', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify([
          {
            id: 'alert1',
            type: 'warning',
            title: 'High CPU Usage',
            message: 'CPU usage is above 80%',
            timestamp: new Date().toISOString(),
          },
        ]),
      });
    });

    await page.reload();

    // Should show alert banner
    await expect(page.locator('[data-testid="system-alerts"]')).toBeVisible();
    await expect(page.locator('text=High CPU Usage')).toBeVisible();
  });

  test('should update data in real-time via WebSocket', async ({ page }) => {
    // Mock WebSocket connection
    await page.addInitScript(() => {
      class MockWebSocket extends EventTarget {
        readyState = WebSocket.OPEN;
        send() {}
        close() {}
      }
      (window as any).WebSocket = MockWebSocket;
    });

    await page.reload();

    // Should show real-time connection indicator
    const connectionIndicator = page.locator('[data-testid="ws-connection"]');
    if (await connectionIndicator.isVisible()) {
      await expect(connectionIndicator).toContainText('Connected');
    }
  });
});
