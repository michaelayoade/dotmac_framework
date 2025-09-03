/**
 * Admin Management Visual Baselines Tests
 * Creates and maintains visual regression tests for admin dashboards
 */

import { test, expect } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';
import { APIBehaviorTester } from '../fixtures/api-behaviors';
import { AdminManagementMocks } from '../fixtures/admin-mocks';

test.describe('Admin Management Visual Baselines', () => {
  let apiTester: APIBehaviorTester;
  let adminMocks: AdminManagementMocks;

  test.beforeEach(async ({ page }) => {
    // Setup authentication
    await setupAuth(page, 'admin');

    // Initialize deterministic API mocking
    apiTester = new APIBehaviorTester(page, {
      enableMocking: true,
      simulateLatency: false, // Disable for consistent visual tests
    });

    adminMocks = new AdminManagementMocks(apiTester);
    await adminMocks.setupAll();

    // Set consistent viewport for visual tests
    await page.setViewportSize({ width: 1920, height: 1080 });
  });

  test.describe('Device Management Visual Tests', () => {
    test('should match device management dashboard baseline', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Wait for data to load completely
      await page.waitForSelector('[data-testid="management-table"]');
      await page.waitForLoadState('networkidle');

      // Hide dynamic elements that change between runs
      await page.addStyleTag({
        content: `
          [data-testid="timestamp"], 
          [data-testid="last-updated"],
          .animate-pulse,
          .animate-spin {
            visibility: hidden !important;
          }
        `,
      });

      // Take full page screenshot
      await expect(page).toHaveScreenshot('device-management-dashboard.png');
    });

    test('should match device management metrics section', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="metrics-grid"]');

      // Hide dynamic timestamps
      await page.addStyleTag({
        content: `[data-testid="last-updated"] { visibility: hidden !important; }`,
      });

      // Screenshot just the metrics section
      await expect(page.locator('[data-testid="metrics-grid"]')).toHaveScreenshot(
        'device-metrics.png'
      );
    });

    test('should match device table layout', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="management-table"]');

      // Screenshot the table section
      await expect(page.locator('[data-testid="management-table"]')).toHaveScreenshot(
        'device-table.png'
      );
    });

    test('should match device filters layout', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="filters-section"]');

      // Open all filters for consistent baseline
      await page.click('[data-testid="filter-device-type"]');
      await page.click('[data-testid="filter-status"]');
      await page.click('[data-testid="filter-vendor"]');

      // Screenshot filters section
      await expect(page.locator('[data-testid="filters-section"]')).toHaveScreenshot(
        'device-filters.png'
      );
    });

    test('should match device detail drawer', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Click on first device to open detail drawer
      await page.click('[data-testid="device-row"]:first-child');
      await page.waitForSelector('[data-testid="device-detail-drawer"]');

      // Hide dynamic timestamps and monitoring data
      await page.addStyleTag({
        content: `
          [data-testid="last-seen"],
          [data-testid="uptime"],
          .monitoring-chart {
            visibility: hidden !important;
          }
        `,
      });

      // Screenshot detail drawer
      await expect(page.locator('[data-testid="device-detail-drawer"]')).toHaveScreenshot(
        'device-detail-drawer.png'
      );
    });
  });

  test.describe('IPAM Management Visual Tests', () => {
    test('should match IPAM dashboard baseline', async ({ page }) => {
      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]');
      await page.waitForLoadState('networkidle');

      // Hide dynamic elements
      await page.addStyleTag({
        content: `
          [data-testid="timestamp"],
          .animate-pulse {
            visibility: hidden !important;
          }
        `,
      });

      await expect(page).toHaveScreenshot('ipam-management-dashboard.png');
    });

    test('should match IPAM utilization bars', async ({ page }) => {
      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="management-table"]');

      // Screenshot utilization visualizations
      await expect(page.locator('[data-testid="utilization-column"]')).toHaveScreenshot(
        'ipam-utilization-bars.png'
      );
    });

    test('should match subnet creation form', async ({ page }) => {
      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]');

      // Open create subnet drawer
      await page.click('[data-testid="create-button"]');
      await page.waitForSelector('[data-testid="create-subnet-drawer"]');

      await expect(page.locator('[data-testid="create-subnet-drawer"]')).toHaveScreenshot(
        'subnet-creation-form.png'
      );
    });
  });

  test.describe('Project Management Visual Tests', () => {
    test('should match project dashboard baseline', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');
      await page.waitForLoadState('networkidle');

      // Hide dynamic dates and progress animations
      await page.addStyleTag({
        content: `
          [data-testid="due-date"],
          [data-testid="updated-at"],
          .progress-animation {
            visibility: hidden !important;
          }
        `,
      });

      await expect(page).toHaveScreenshot('project-management-dashboard.png');
    });

    test('should match project progress visualization', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="management-table"]');

      // Screenshot progress bars column
      await expect(page.locator('[data-testid="progress-column"]')).toHaveScreenshot(
        'project-progress-bars.png'
      );
    });

    test('should match project creation form', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      // Open create project drawer
      await page.click('[data-testid="create-button"]');
      await page.waitForSelector('[data-testid="create-project-drawer"]');

      await expect(page.locator('[data-testid="create-project-drawer"]')).toHaveScreenshot(
        'project-creation-form.png'
      );
    });

    test('should match project kanban view', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      // Switch to board view
      await page.click('[data-testid="board-view-toggle"]');
      await page.waitForSelector('[data-testid="project-kanban-board"]');

      // Hide dynamic dates
      await page.addStyleTag({
        content: `[data-testid="due-date"] { visibility: hidden !important; }`,
      });

      await expect(page.locator('[data-testid="project-kanban-board"]')).toHaveScreenshot(
        'project-kanban-board.png'
      );
    });
  });

  test.describe('Container Management Visual Tests', () => {
    test('should match container dashboard baseline', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');
      await page.waitForLoadState('networkidle');

      // Hide dynamic metrics
      await page.addStyleTag({
        content: `
          [data-testid="cpu-usage"],
          [data-testid="memory-usage"],
          [data-testid="uptime"] {
            visibility: hidden !important;
          }
        `,
      });

      await expect(page).toHaveScreenshot('container-management-dashboard.png');
    });

    test('should match container resource usage bars', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="management-table"]');

      // Screenshot resource usage visualizations
      await expect(page.locator('[data-testid="cpu-usage-column"]')).toHaveScreenshot(
        'container-cpu-usage.png'
      );
      await expect(page.locator('[data-testid="memory-usage-column"]')).toHaveScreenshot(
        'container-memory-usage.png'
      );
    });

    test('should match container health status indicators', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="management-table"]');

      // Screenshot health status column
      await expect(page.locator('[data-testid="health-status-column"]')).toHaveScreenshot(
        'container-health-status.png'
      );
    });

    test('should match container detail drawer with logs', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Open container details
      await page.click('[data-testid="container-row"]:first-child');
      await page.waitForSelector('[data-testid="container-detail-drawer"]');

      // Navigate to logs tab
      await page.click('[data-testid="logs-tab"]');
      await page.waitForSelector('[data-testid="container-logs"]');

      // Hide dynamic log timestamps
      await page.addStyleTag({
        content: `
          .log-timestamp {
            visibility: hidden !important;
          }
        `,
      });

      await expect(page.locator('[data-testid="container-detail-drawer"]')).toHaveScreenshot(
        'container-detail-with-logs.png'
      );
    });
  });

  test.describe('Responsive Visual Tests', () => {
    test('should match tablet layout for device management', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      await expect(page).toHaveScreenshot('device-management-tablet.png');
    });

    test('should match mobile layout for device management', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      await expect(page).toHaveScreenshot('device-management-mobile.png');
    });

    test('should match tablet layout for project management', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });

      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      await expect(page).toHaveScreenshot('project-management-tablet.png');
    });
  });

  test.describe('Dark Mode Visual Tests', () => {
    test.beforeEach(async ({ page }) => {
      // Enable dark mode
      await page.addInitScript(() => {
        localStorage.setItem('theme', 'dark');
      });
    });

    test('should match dark mode device management', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Wait for dark mode to apply
      await page.waitForSelector('[data-theme="dark"]');

      await expect(page).toHaveScreenshot('device-management-dark.png');
    });

    test('should match dark mode project management', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');
      await page.waitForSelector('[data-theme="dark"]');

      await expect(page).toHaveScreenshot('project-management-dark.png');
    });
  });

  test.describe('High Contrast Visual Tests', () => {
    test.beforeEach(async ({ page }) => {
      // Enable high contrast mode
      await page.addInitScript(() => {
        localStorage.setItem('contrast', 'high');
      });
    });

    test('should match high contrast device management', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');
      await page.waitForSelector('[data-contrast="high"]');

      await expect(page).toHaveScreenshot('device-management-high-contrast.png');
    });
  });

  test.describe('Loading State Visual Tests', () => {
    test('should match device management loading state', async ({ page }) => {
      // Mock slow API response
      await apiTester.mockAndLog('/api/admin/devices', async () => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        return { body: { devices: [], total: 0, metrics: {} } };
      });

      await page.goto('/admin/devices');

      // Capture loading state before data loads
      await page.waitForSelector('[data-testid="loading-spinner"]');
      await expect(page.locator('[data-testid="device-management"]')).toHaveScreenshot(
        'device-management-loading.png'
      );
    });
  });

  test.describe('Error State Visual Tests', () => {
    test('should match device management error state', async ({ page }) => {
      // Mock API error
      await apiTester.mockAndLog('/api/admin/devices', async () => ({
        status: 500,
        body: { error: 'Internal server error' },
      }));

      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="error-state"]');

      await expect(page.locator('[data-testid="device-management"]')).toHaveScreenshot(
        'device-management-error.png'
      );
    });

    test('should match empty state for projects', async ({ page }) => {
      // Mock empty response
      await apiTester.mockAndLog('/api/admin/projects', async () => ({
        body: {
          projects: [],
          total: 0,
          metrics: { active_projects: 0, on_schedule: 0, budget_used: 0, team_members: 0 },
        },
      }));

      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="empty-state"]');

      await expect(page.locator('[data-testid="project-management"]')).toHaveScreenshot(
        'project-management-empty.png'
      );
    });
  });

  test.afterEach(async ({ page }) => {
    // Clear any custom styles added during tests
    await page.evaluate(() => {
      const customStyles = document.querySelectorAll('style[data-testid="custom-style"]');
      customStyles.forEach((style) => style.remove());
    });
  });
});
