/**
 * Visual regression tests for component gallery
 * Tests all component variations for visual consistency
 */

import { expect, test } from '@playwright/test';

test.describe('Component Visual Gallery @visual', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to component gallery/storybook
    await page.goto('/components/gallery');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Button Components', () => {
    test('button variants', async ({ page }) => {
      await page.goto('/components/gallery/buttons');

      // Wait for all buttons to render
      await page.waitForSelector('[data-testid="button-gallery"]');

      // Take screenshot of all button variants
      await expect(page.locator('[data-testid="button-gallery"]')).toHaveScreenshot(
        'buttons-all-variants.png'
      );

      // Test individual button states
      await expect(page.locator('[data-testid="button-primary"]')).toHaveScreenshot(
        'button-primary.png'
      );
      await expect(page.locator('[data-testid="button-secondary"]')).toHaveScreenshot(
        'button-secondary.png'
      );
      await expect(page.locator('[data-testid="button-outline"]')).toHaveScreenshot(
        'button-outline.png'
      );
      await expect(page.locator('[data-testid="button-ghost"]')).toHaveScreenshot(
        'button-ghost.png'
      );

      // Test button sizes
      await expect(page.locator('[data-testid="buttons-sizes"]')).toHaveScreenshot(
        'buttons-sizes.png'
      );

      // Test disabled states
      await expect(page.locator('[data-testid="buttons-disabled"]')).toHaveScreenshot(
        'buttons-disabled.png'
      );

      // Test loading states
      await expect(page.locator('[data-testid="buttons-loading"]')).toHaveScreenshot(
        'buttons-loading.png'
      );
    });

    test('button hover states', async ({ page }) => {
      await page.goto('/components/gallery/buttons');

      const primaryButton = page.locator('[data-testid="button-primary"]');

      // Hover over button
      await primaryButton.hover();
      await expect(primaryButton).toHaveScreenshot('button-primary-hover.png');
    });

    test('button focus states', async ({ page }) => {
      await page.goto('/components/gallery/buttons');

      const primaryButton = page.locator('[data-testid="button-primary"]');

      // Focus button
      await primaryButton.focus();
      await expect(primaryButton).toHaveScreenshot('button-primary-focus.png');
    });
  });

  test.describe('Form Components', () => {
    test('input field variants', async ({ page }) => {
      await page.goto('/components/gallery/inputs');

      // Test all input variants
      await expect(page.locator('[data-testid="inputs-gallery"]')).toHaveScreenshot(
        'inputs-all-variants.png'
      );

      // Test input states
      await expect(page.locator('[data-testid="input-default"]')).toHaveScreenshot(
        'input-default.png'
      );
      await expect(page.locator('[data-testid="input-error"]')).toHaveScreenshot('input-error.png');
      await expect(page.locator('[data-testid="input-success"]')).toHaveScreenshot(
        'input-success.png'
      );
      await expect(page.locator('[data-testid="input-disabled"]')).toHaveScreenshot(
        'input-disabled.png'
      );
    });

    test('input with icons and labels', async ({ page }) => {
      await page.goto('/components/gallery/inputs');

      await expect(page.locator('[data-testid="input-with-icon"]')).toHaveScreenshot(
        'input-with-icon.png'
      );
      await expect(page.locator('[data-testid="input-with-label"]')).toHaveScreenshot(
        'input-with-label.png'
      );
      await expect(page.locator('[data-testid="input-with-helper"]')).toHaveScreenshot(
        'input-with-helper.png'
      );
    });

    test('form validation states', async ({ page }) => {
      await page.goto('/components/gallery/forms');

      // Test form with validation errors
      await expect(page.locator('[data-testid="form-validation"]')).toHaveScreenshot(
        'form-validation.png'
      );

      // Test form with success states
      await expect(page.locator('[data-testid="form-success"]')).toHaveScreenshot(
        'form-success.png'
      );
    });
  });

  test.describe('Data Display Components', () => {
    test('table variants', async ({ page }) => {
      await page.goto('/components/gallery/tables');

      // Test basic table
      await expect(page.locator('[data-testid="table-basic"]')).toHaveScreenshot('table-basic.png');

      // Test table with sorting
      await expect(page.locator('[data-testid="table-sortable"]')).toHaveScreenshot(
        'table-sortable.png'
      );

      // Test table with selection
      await expect(page.locator('[data-testid="table-selectable"]')).toHaveScreenshot(
        'table-selectable.png'
      );

      // Test table with pagination
      await expect(page.locator('[data-testid="table-paginated"]')).toHaveScreenshot(
        'table-paginated.png'
      );
    });

    test('card variants', async ({ page }) => {
      await page.goto('/components/gallery/cards');

      // Test all card variants
      await expect(page.locator('[data-testid="cards-gallery"]')).toHaveScreenshot(
        'cards-all-variants.png'
      );

      // Test individual card types
      await expect(page.locator('[data-testid="card-basic"]')).toHaveScreenshot('card-basic.png');
      await expect(page.locator('[data-testid="card-with-image"]')).toHaveScreenshot(
        'card-with-image.png'
      );
      await expect(page.locator('[data-testid="card-with-actions"]')).toHaveScreenshot(
        'card-with-actions.png'
      );
    });

    test('badge and status indicators', async ({ page }) => {
      await page.goto('/components/gallery/badges');

      // Test all badge variants
      await expect(page.locator('[data-testid="badges-gallery"]')).toHaveScreenshot(
        'badges-all-variants.png'
      );

      // Test status indicators
      await expect(page.locator('[data-testid="status-indicators"]')).toHaveScreenshot(
        'status-indicators.png'
      );
    });
  });

  test.describe('Navigation Components', () => {
    test('navigation bar variants', async ({ page }) => {
      await page.goto('/components/gallery/navigation');

      // Test desktop navigation
      await expect(page.locator('[data-testid="nav-desktop"]')).toHaveScreenshot('nav-desktop.png');

      // Test mobile navigation
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(page.locator('[data-testid="nav-mobile"]')).toHaveScreenshot('nav-mobile.png');

      // Test mobile menu expanded
      await page.click('[data-testid="mobile-menu-button"]');
      await expect(page.locator('[data-testid="nav-mobile-menu"]')).toHaveScreenshot(
        'nav-mobile-menu.png'
      );
    });

    test('breadcrumb navigation', async ({ page }) => {
      await page.goto('/components/gallery/breadcrumbs');

      await expect(page.locator('[data-testid="breadcrumbs"]')).toHaveScreenshot('breadcrumbs.png');
    });

    test('pagination components', async ({ page }) => {
      await page.goto('/components/gallery/pagination');

      await expect(page.locator('[data-testid="pagination"]')).toHaveScreenshot('pagination.png');
      await expect(page.locator('[data-testid="pagination-simple"]')).toHaveScreenshot(
        'pagination-simple.png'
      );
    });
  });

  test.describe('Feedback Components', () => {
    test('loading states', async ({ page }) => {
      await page.goto('/components/gallery/loading');

      // Test loading spinners
      await expect(page.locator('[data-testid="loading-spinners"]')).toHaveScreenshot(
        'loading-spinners.png'
      );

      // Test skeleton loaders
      await expect(page.locator('[data-testid="skeleton-loaders"]')).toHaveScreenshot(
        'skeleton-loaders.png'
      );

      // Test progress bars
      await expect(page.locator('[data-testid="progress-bars"]')).toHaveScreenshot(
        'progress-bars.png'
      );
    });

    test('alert and notification components', async ({ page }) => {
      await page.goto('/components/gallery/alerts');

      // Test all alert variants
      await expect(page.locator('[data-testid="alerts-gallery"]')).toHaveScreenshot(
        'alerts-all-variants.png'
      );

      // Test notification toasts
      await expect(page.locator('[data-testid="toast-notifications"]')).toHaveScreenshot(
        'toast-notifications.png'
      );
    });

    test('modal and dialog components', async ({ page }) => {
      await page.goto('/components/gallery/modals');

      // Open modal
      await page.click('[data-testid="open-modal-button"]');
      await expect(page.locator('[data-testid="modal"]')).toHaveScreenshot('modal-basic.png');

      // Close modal
      await page.click('[data-testid="modal-close"]');

      // Open confirmation dialog
      await page.click('[data-testid="open-confirm-button"]');
      await expect(page.locator('[data-testid="confirm-dialog"]')).toHaveScreenshot(
        'confirm-dialog.png'
      );
    });
  });

  test.describe('Charts and Data Visualization', () => {
    test('chart components', async ({ page }) => {
      await page.goto('/components/gallery/charts');

      // Wait for charts to render
      await page.waitForTimeout(2000);

      // Test line charts
      await expect(page.locator('[data-testid="line-chart"]')).toHaveScreenshot('line-chart.png');

      // Test bar charts
      await expect(page.locator('[data-testid="bar-chart"]')).toHaveScreenshot('bar-chart.png');

      // Test pie charts
      await expect(page.locator('[data-testid="pie-chart"]')).toHaveScreenshot('pie-chart.png');

      // Test area charts
      await expect(page.locator('[data-testid="area-chart"]')).toHaveScreenshot('area-chart.png');
    });

    test('metric display components', async ({ page }) => {
      await page.goto('/components/gallery/metrics');

      // Test metric cards
      await expect(page.locator('[data-testid="metric-cards"]')).toHaveScreenshot(
        'metric-cards.png'
      );

      // Test KPI indicators
      await expect(page.locator('[data-testid="kpi-indicators"]')).toHaveScreenshot(
        'kpi-indicators.png'
      );

      // Test progress indicators
      await expect(page.locator('[data-testid="progress-indicators"]')).toHaveScreenshot(
        'progress-indicators.png'
      );
    });
  });

  test.describe('Theme Variations', () => {
    test('light theme components', async ({ page, colorScheme }) => {
      test.skip(colorScheme !== 'light', 'Light theme test');

      await page.goto('/components/gallery/theme-demo');

      // Test complete theme showcase
      await expect(page.locator('[data-testid="theme-showcase"]')).toHaveScreenshot(
        'theme-light-showcase.png'
      );

      // Test portal-specific themes
      await expect(page.locator('[data-testid="admin-theme"]')).toHaveScreenshot(
        'admin-theme-light.png'
      );
      await expect(page.locator('[data-testid="customer-theme"]')).toHaveScreenshot(
        'customer-theme-light.png'
      );
      await expect(page.locator('[data-testid="reseller-theme"]')).toHaveScreenshot(
        'reseller-theme-light.png'
      );
    });

    test('dark theme components', async ({ page, colorScheme }) => {
      test.skip(colorScheme !== 'dark', 'Dark theme test');

      await page.goto('/components/gallery/theme-demo');

      // Test complete theme showcase
      await expect(page.locator('[data-testid="theme-showcase"]')).toHaveScreenshot(
        'theme-dark-showcase.png'
      );

      // Test portal-specific themes
      await expect(page.locator('[data-testid="admin-theme"]')).toHaveScreenshot(
        'admin-theme-dark.png'
      );
      await expect(page.locator('[data-testid="customer-theme"]')).toHaveScreenshot(
        'customer-theme-dark.png'
      );
      await expect(page.locator('[data-testid="reseller-theme"]')).toHaveScreenshot(
        'reseller-theme-dark.png'
      );
    });
  });

  test.describe('Responsive Design Validation', () => {
    test('components at different breakpoints', async ({ page }) => {
      await page.goto('/components/gallery/responsive-demo');

      // Desktop (1280px)
      await page.setViewportSize({ width: 1280, height: 720 });
      await expect(page.locator('[data-testid="responsive-layout"]')).toHaveScreenshot(
        'responsive-desktop.png'
      );

      // Tablet (768px)
      await page.setViewportSize({ width: 768, height: 1024 });
      await expect(page.locator('[data-testid="responsive-layout"]')).toHaveScreenshot(
        'responsive-tablet.png'
      );

      // Mobile (375px)
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(page.locator('[data-testid="responsive-layout"]')).toHaveScreenshot(
        'responsive-mobile.png'
      );
    });
  });

  test.describe('Portal Branding Validation', () => {
    test('admin portal branding', async ({ page }) => {
      await page.goto('/admin/components/branding-demo');

      await expect(page.locator('[data-testid="portal-branding"]')).toHaveScreenshot(
        'admin-portal-branding.png'
      );
    });

    test('customer portal branding', async ({ page }) => {
      await page.goto('/customer/components/branding-demo');

      await expect(page.locator('[data-testid="portal-branding"]')).toHaveScreenshot(
        'customer-portal-branding.png'
      );
    });

    test('reseller portal branding', async ({ page }) => {
      await page.goto('/reseller/components/branding-demo');

      await expect(page.locator('[data-testid="portal-branding"]')).toHaveScreenshot(
        'reseller-portal-branding.png'
      );
    });
  });

  test.describe('Error State Components', () => {
    test('error boundaries and fallbacks', async ({ page }) => {
      await page.goto('/components/gallery/error-states');

      // Test different error boundary levels
      await expect(page.locator('[data-testid="error-page"]')).toHaveScreenshot(
        'error-boundary-page.png'
      );
      await expect(page.locator('[data-testid="error-section"]')).toHaveScreenshot(
        'error-boundary-section.png'
      );
      await expect(page.locator('[data-testid="error-component"]')).toHaveScreenshot(
        'error-boundary-component.png'
      );
    });

    test('empty states', async ({ page }) => {
      await page.goto('/components/gallery/empty-states');

      await expect(page.locator('[data-testid="empty-table"]')).toHaveScreenshot('empty-table.png');
      await expect(page.locator('[data-testid="empty-dashboard"]')).toHaveScreenshot(
        'empty-dashboard.png'
      );
      await expect(page.locator('[data-testid="empty-search"]')).toHaveScreenshot(
        'empty-search.png'
      );
    });
  });
});
