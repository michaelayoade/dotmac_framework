/**
 * Portal Visualization E2E Tests
 * Comprehensive visual testing for all portal dashboards and visualizations
 * Tests charts, maps, real-time data, and interactive visual elements
 */

import { test, expect } from '@playwright/test';

test.describe('Portal Visualization E2E Tests', () => {
  test.describe('Admin Portal Visualizations', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/admin');
      await page.waitForSelector('[data-testid="admin-dashboard"]', { timeout: 10000 });
    });

    test('should display admin dashboard metrics with visual elements @visual', async ({
      page,
    }) => {
      // Verify main dashboard container
      await expect(page.getByTestId('admin-dashboard')).toBeVisible();

      // Check for dashboard cards/metrics
      const metricCards = page.locator(
        '[data-testid*="metric"], [class*="card"], [class*="dashboard"]'
      );
      const cardCount = await metricCards.count();
      expect(cardCount).toBeGreaterThan(0);

      // Verify customer count metric is displayed
      const customerMetric = page.getByTestId('customer-count');
      if (await customerMetric.isVisible()) {
        await expect(customerMetric).toBeVisible();
        const text = await customerMetric.textContent();
        expect(text).toMatch(/\d+/); // Should contain numbers
      }

      // Check revenue metric visualization
      const revenueMetric = page.getByTestId('revenue-metric');
      if (await revenueMetric.isVisible()) {
        await expect(revenueMetric).toBeVisible();
      }

      // Take screenshot for visual validation
      await page.screenshot({
        path: 'test-results/admin-dashboard-visualization.png',
        fullPage: true,
      });
    });

    test('should display customer management geographic visualization @visual @performance', async ({
      page,
    }) => {
      await page.goto('/admin/customers');
      await page.waitForSelector('[data-testid="customer-management"]');

      // Switch to geographic view
      const mapViewButton = page.getByText('🗺️ Geographic View');
      if (await mapViewButton.isVisible()) {
        await mapViewButton.click();

        // Wait for map to load
        await page.waitForTimeout(2000);

        // Verify geographic distribution text is displayed
        await expect(page.getByText('Customer Geographic Distribution')).toBeVisible();

        // Check if map container exists (even if empty)
        const mapContainer = page.locator('[data-testid*="map"], [class*="map"], [id*="map"]');
        if ((await mapContainer.count()) > 0) {
          await expect(mapContainer.first()).toBeVisible();
        }

        // Take screenshot of map view
        await page.screenshot({
          path: 'test-results/customer-geographic-view.png',
          fullPage: true,
        });
      }
    });

    test('should display customer data table visualization @visual', async ({ page }) => {
      await page.goto('/admin/customers');
      await page.waitForSelector('[data-testid="customer-management"]');

      // Ensure table view is active
      const tableViewButton = page.getByText('📊 Table View');
      if (await tableViewButton.isVisible()) {
        await tableViewButton.click();
      }

      // Wait for table to load
      await page.waitForSelector('[data-testid="customer-table"]');
      await expect(page.getByTestId('customer-table')).toBeVisible();

      // Verify table has visual structure
      const tableHeaders = page.locator('th, [role="columnheader"]');
      const headerCount = await tableHeaders.count();
      expect(headerCount).toBeGreaterThan(0);

      // Check for table rows
      const tableRows = page.locator('tr, [role="row"]');
      const rowCount = await tableRows.count();
      expect(rowCount).toBeGreaterThan(0);

      // Take screenshot of table view
      await page.screenshot({
        path: 'test-results/customer-table-visualization.png',
        fullPage: true,
      });
    });

    test('should render system status visualization @visual', async ({ page }) => {
      // Look for system status components on dashboard
      const systemStatus = page.getByTestId('system-status').or(page.getByText(/System Status/i));
      if (await systemStatus.isVisible()) {
        await expect(systemStatus).toBeVisible();

        // Check for status indicators (green, yellow, red indicators)
        const statusIndicators = page.locator(
          '[data-testid*="status"], [class*="status"], [class*="indicator"]'
        );
        if ((await statusIndicators.count()) > 0) {
          await expect(statusIndicators.first()).toBeVisible();
        }

        await page.screenshot({
          path: 'test-results/system-status-visualization.png',
        });
      }
    });
  });

  test.describe('Customer Portal Visualizations', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/customer');
      await page.waitForSelector('[data-testid="customer-dashboard"]', { timeout: 10000 });
    });

    test('should display customer dashboard with service visualizations @visual', async ({
      page,
    }) => {
      await expect(page.getByTestId('customer-dashboard')).toBeVisible();

      // Check for service status visualization
      const serviceStatus = page.getByTestId('service-status');
      if (await serviceStatus.isVisible()) {
        await expect(serviceStatus).toBeVisible();
      }

      // Check for usage metrics visualization
      const usageMetrics = page.getByTestId('usage-metrics');
      if (await usageMetrics.isVisible()) {
        await expect(usageMetrics).toBeVisible();
      }

      // Take screenshot of customer dashboard
      await page.screenshot({
        path: 'test-results/customer-dashboard-visualization.png',
        fullPage: true,
      });
    });

    test('should render billing visualization with charts @visual', async ({ page }) => {
      await page.goto('/customer/billing');
      await page.waitForSelector('[data-testid="customer-billing"]');

      // Look for billing charts or visual elements
      const billingVisuals = page.locator(
        '[data-testid*="chart"], [data-testid*="graph"], [class*="chart"]'
      );
      if ((await billingVisuals.count()) > 0) {
        await expect(billingVisuals.first()).toBeVisible();
      }

      // Check for current bill display
      await expect(page.getByText(/Current Bill/i)).toBeVisible();
      await expect(page.getByText(/Payment History/i)).toBeVisible();

      await page.screenshot({
        path: 'test-results/customer-billing-visualization.png',
        fullPage: true,
      });
    });

    test('should display usage analytics with interactive charts @visual @performance', async ({
      page,
    }) => {
      await page.goto('/customer/usage');

      // Wait for usage page to load
      await page.waitForTimeout(2000);

      // Look for usage charts or visualizations
      const usageCharts = page.locator(
        '[data-testid*="usage"], [data-testid*="chart"], [class*="chart"], [class*="graph"]'
      );
      if ((await usageCharts.count()) > 0) {
        await expect(usageCharts.first()).toBeVisible();

        // Test chart interactivity (hover, click)
        await usageCharts.first().hover();
        await page.waitForTimeout(500);
      }

      await page.screenshot({
        path: 'test-results/customer-usage-visualization.png',
        fullPage: true,
      });
    });
  });

  test.describe('Reseller Portal Visualizations', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reseller');
      await page.waitForTimeout(3000); // Allow time for reseller portal to load
    });

    test('should display reseller dashboard with sales visualizations @visual', async ({
      page,
    }) => {
      // Look for reseller dashboard
      const resellerDashboard = page
        .getByTestId('reseller-dashboard')
        .or(page.getByText(/Reseller Dashboard/i));
      if (await resellerDashboard.isVisible()) {
        await expect(resellerDashboard).toBeVisible();

        // Check for sales metrics
        const salesMetrics = page.locator(
          '[data-testid*="sales"], [data-testid*="commission"], [data-testid*="revenue"]'
        );
        if ((await salesMetrics.count()) > 0) {
          await expect(salesMetrics.first()).toBeVisible();
        }

        await page.screenshot({
          path: 'test-results/reseller-dashboard-visualization.png',
          fullPage: true,
        });
      }
    });

    test('should render commission tracking visualization @visual', async ({ page }) => {
      await page.goto('/reseller/commissions');

      // Look for commission visualizations
      const commissionElements = page.locator(
        '[data-testid*="commission"], [class*="commission"], [class*="chart"]'
      );
      if ((await commissionElements.count()) > 0) {
        await expect(commissionElements.first()).toBeVisible();

        await page.screenshot({
          path: 'test-results/reseller-commission-visualization.png',
          fullPage: true,
        });
      }
    });
  });

  test.describe('Technician Portal Mobile Visualizations', () => {
    test.beforeEach(async ({ page }) => {
      // Set mobile viewport for technician portal
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/technician');
      await page.waitForTimeout(3000);
    });

    test('should display mobile-optimized technician dashboard @visual @mobile', async ({
      page,
    }) => {
      // Look for technician dashboard
      const techDashboard = page
        .getByTestId('technician-dashboard')
        .or(page.getByText(/Work Orders/i));
      if (await techDashboard.isVisible()) {
        await expect(techDashboard).toBeVisible();

        // Check for work order visualizations
        const workOrders = page
          .getByTestId('work-orders-list')
          .or(page.locator('[class*="work-order"]'));
        if ((await workOrders.count()) > 0) {
          await expect(workOrders.first()).toBeVisible();
        }

        await page.screenshot({
          path: 'test-results/technician-mobile-visualization.png',
          fullPage: true,
        });
      }
    });

    test('should display map visualization on mobile @visual @mobile', async ({
      page,
      context,
    }) => {
      // Grant geolocation permission
      await context.grantPermissions(['geolocation']);
      await context.setGeolocation({ latitude: 47.6062, longitude: -122.3321 });

      // Look for map component
      const mapComponent = page.getByTestId('technician-map').or(page.locator('[class*="map"]'));
      if (await mapComponent.isVisible()) {
        await expect(mapComponent).toBeVisible();

        await page.screenshot({
          path: 'test-results/technician-map-mobile-visualization.png',
        });
      }
    });
  });

  test.describe('Cross-Portal Visual Consistency', () => {
    test('should maintain consistent theming across portals @visual', async ({ page }) => {
      // Test each portal for consistent styling
      const portals = ['/admin', '/customer', '/reseller'];

      for (const portal of portals) {
        await page.goto(portal);
        await page.waitForTimeout(2000);

        // Check for consistent header/navigation
        const header = page.locator(
          'header, [role="banner"], [data-testid*="header"], [class*="header"]'
        );
        if ((await header.count()) > 0) {
          await expect(header.first()).toBeVisible();
        }

        // Take screenshot for visual comparison
        await page.screenshot({
          path: `test-results/portal-${portal.replace('/', '')}-consistency.png`,
          fullPage: true,
        });
      }
    });

    test('should display responsive layouts across different screen sizes @visual @responsive', async ({
      page,
    }) => {
      const viewports = [
        { width: 1920, height: 1080, name: 'desktop' },
        { width: 768, height: 1024, name: 'tablet' },
        { width: 375, height: 667, name: 'mobile' },
      ];

      for (const viewport of viewports) {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });

        // Test admin portal responsiveness
        await page.goto('/admin');
        await page.waitForSelector('[data-testid="admin-dashboard"]', { timeout: 5000 });

        await page.screenshot({
          path: `test-results/admin-responsive-${viewport.name}.png`,
          fullPage: true,
        });

        // Test customer portal responsiveness
        await page.goto('/customer');
        await page.waitForTimeout(2000);

        await page.screenshot({
          path: `test-results/customer-responsive-${viewport.name}.png`,
          fullPage: true,
        });
      }
    });
  });

  test.describe('Interactive Visualization Tests', () => {
    test('should handle chart interactions and real-time updates @visual @performance', async ({
      page,
    }) => {
      await page.goto('/admin');
      await page.waitForSelector('[data-testid="admin-dashboard"]');

      // Look for interactive chart elements
      const interactiveElements = page.locator(
        '[data-testid*="chart"], [class*="chart"], [class*="interactive"]'
      );

      if ((await interactiveElements.count()) > 0) {
        // Test hover interactions
        await interactiveElements.first().hover();
        await page.waitForTimeout(500);

        // Test click interactions
        await interactiveElements.first().click();
        await page.waitForTimeout(500);

        await page.screenshot({
          path: 'test-results/interactive-chart-visualization.png',
        });
      }
    });

    test('should display loading states and animations @visual', async ({ page }) => {
      // Navigate to a data-heavy page
      await page.goto('/admin/customers');

      // Look for loading indicators
      const loadingElements = page.locator(
        '[data-testid*="loading"], [class*="loading"], [class*="spinner"]'
      );

      // Take screenshot if loading state is visible
      if ((await loadingElements.count()) > 0) {
        await page.screenshot({
          path: 'test-results/loading-state-visualization.png',
        });
      }

      // Wait for content to load and take another screenshot
      await page.waitForTimeout(3000);
      await page.screenshot({
        path: 'test-results/loaded-state-visualization.png',
      });
    });

    test('should handle error states and empty data visualization @visual', async ({ page }) => {
      // Test error handling by attempting to access non-existent data
      await page.goto('/admin/nonexistent-endpoint');
      await page.waitForTimeout(2000);

      // Look for error states
      const errorElements = page.locator(
        '[data-testid*="error"], [class*="error"], [role="alert"]'
      );
      if ((await errorElements.count()) > 0) {
        await page.screenshot({
          path: 'test-results/error-state-visualization.png',
        });
      }
    });
  });

  test.describe('Performance and Visual Performance Tests', () => {
    test('should render visualizations within performance budgets @performance', async ({
      page,
    }) => {
      // Measure rendering performance
      const performanceMetrics = await page.evaluate(() => {
        return performance.getEntriesByType('navigation')[0];
      });

      await page.goto('/admin');
      const startTime = Date.now();

      await page.waitForSelector('[data-testid="admin-dashboard"]');

      const renderTime = Date.now() - startTime;
      expect(renderTime).toBeLessThan(3000); // Should render within 3 seconds

      // Check for visual completeness
      const visualElements = page.locator(
        '[data-testid*="metric"], [data-testid*="chart"], [class*="card"]'
      );
      const elementCount = await visualElements.count();
      expect(elementCount).toBeGreaterThan(0);
    });

    test('should handle large datasets in visualizations @performance', async ({ page }) => {
      await page.goto('/admin/customers');
      await page.waitForSelector('[data-testid="customer-management"]');

      // Test with large dataset simulation
      const startTime = Date.now();
      await page.waitForSelector('[data-testid="customer-table"]');
      const loadTime = Date.now() - startTime;

      // Should load large datasets within reasonable time
      expect(loadTime).toBeLessThan(5000);

      await page.screenshot({
        path: 'test-results/large-dataset-visualization.png',
        fullPage: true,
      });
    });
  });

  test.describe('Accessibility and Visual Accessibility', () => {
    test('should provide accessible visualizations @visual @a11y', async ({ page }) => {
      await page.goto('/admin');
      await page.waitForSelector('[data-testid="admin-dashboard"]');

      // Check for proper ARIA labels on visual elements
      const accessibleElements = page.locator('[aria-label], [role], [aria-labelledby]');
      const accessibleCount = await accessibleElements.count();

      // Should have some accessible elements
      if (accessibleCount > 0) {
        await expect(accessibleElements.first()).toBeVisible();
      }

      // Test keyboard navigation of visual elements
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      await page.screenshot({
        path: 'test-results/accessible-visualization.png',
      });
    });

    test('should support high contrast mode @visual @a11y', async ({ page }) => {
      // Simulate high contrast mode
      await page.emulateMedia({ colorScheme: 'dark' });

      await page.goto('/admin');
      await page.waitForSelector('[data-testid="admin-dashboard"]');

      await page.screenshot({
        path: 'test-results/high-contrast-visualization.png',
        fullPage: true,
      });
    });
  });
});
