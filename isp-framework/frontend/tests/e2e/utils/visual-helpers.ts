/**
 * Visual Testing Helper Utilities
 * Common functions for portal visualization testing
 */

import { Page, expect } from '@playwright/test';

export class VisualTestHelpers {
  constructor(private page: Page) {}

  /**
   * Wait for all images and charts to load before taking screenshots
   */
  async waitForVisualElements(): Promise<void> {
    // Wait for images to load
    await this.page.waitForLoadState('networkidle');

    // Wait for any loading spinners to disappear
    const loadingElements = this.page.locator(
      '[data-testid*="loading"], [class*="loading"], [class*="spinner"]'
    );
    if ((await loadingElements.count()) > 0) {
      await expect(loadingElements.first()).toBeHidden({ timeout: 10000 });
    }

    // Wait for charts/graphs to render (common chart libraries)
    await this.page.waitForTimeout(1000);

    // Check for common chart elements
    const chartElements = this.page.locator(
      'canvas, svg, [class*="chart"], [data-testid*="chart"]'
    );
    const chartCount = await chartElements.count();

    if (chartCount > 0) {
      // Give charts extra time to render
      await this.page.waitForTimeout(2000);
    }
  }

  /**
   * Hide dynamic elements before taking screenshots
   */
  async hideDynamicElements(): Promise<void> {
    // Hide timestamps and dates that change
    await this.page.addStyleTag({
      content: `
        [data-testid*="timestamp"],
        [data-testid*="date"],
        [class*="timestamp"],
        [class*="time"],
        .relative-time {
          visibility: hidden !important;
        }
      `,
    });

    // Hide live indicators and blinking elements
    await this.page.addStyleTag({
      content: `
        [data-testid*="live"],
        [class*="blink"],
        [class*="pulse"],
        .animate-pulse {
          animation: none !important;
          visibility: hidden !important;
        }
      `,
    });
  }

  /**
   * Take a full page screenshot with standardized settings
   */
  async takeFullPageScreenshot(filename: string): Promise<void> {
    await this.waitForVisualElements();
    await this.hideDynamicElements();

    await this.page.screenshot({
      path: `test-results/visual-screenshots/${filename}`,
      fullPage: true,
      animations: 'disabled',
      clip: undefined,
    });
  }

  /**
   * Take a screenshot of a specific element
   */
  async takeElementScreenshot(selector: string, filename: string): Promise<void> {
    await this.waitForVisualElements();

    const element = this.page.locator(selector);
    await expect(element).toBeVisible();

    await element.screenshot({
      path: `test-results/visual-screenshots/${filename}`,
      animations: 'disabled',
    });
  }

  /**
   * Test responsive behavior at different viewport sizes
   */
  async testResponsiveLayout(url: string, testName: string): Promise<void> {
    const viewports = [
      { width: 1920, height: 1080, name: 'desktop-large' },
      { width: 1366, height: 768, name: 'desktop-medium' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 414, height: 896, name: 'mobile-large' },
      { width: 375, height: 667, name: 'mobile-medium' },
      { width: 320, height: 568, name: 'mobile-small' },
    ];

    for (const viewport of viewports) {
      await this.page.setViewportSize({ width: viewport.width, height: viewport.height });
      await this.page.goto(url);
      await this.takeFullPageScreenshot(`${testName}-${viewport.name}.png`);
    }
  }

  /**
   * Test dark mode/theme variations
   */
  async testThemeVariations(url: string, testName: string): Promise<void> {
    const themes = [
      { scheme: 'light', name: 'light-theme' },
      { scheme: 'dark', name: 'dark-theme' },
    ];

    for (const theme of themes) {
      await this.page.emulateMedia({ colorScheme: theme.scheme as 'light' | 'dark' });
      await this.page.goto(url);
      await this.takeFullPageScreenshot(`${testName}-${theme.name}.png`);
    }
  }

  /**
   * Verify chart/visualization is rendered
   */
  async verifyVisualizationRendered(selector?: string): Promise<boolean> {
    const chartSelectors = [
      selector,
      'canvas',
      'svg',
      '[data-testid*="chart"]',
      '[data-testid*="graph"]',
      '[class*="chart"]',
      '[class*="graph"]',
      '.recharts-wrapper',
      '.highcharts-container',
      '.d3-container',
    ].filter(Boolean);

    for (const chartSelector of chartSelectors) {
      const elements = this.page.locator(chartSelector!);
      const count = await elements.count();

      if (count > 0) {
        await expect(elements.first()).toBeVisible();
        return true;
      }
    }

    return false;
  }

  /**
   * Test chart interactivity (hover, click, zoom)
   */
  async testChartInteractivity(chartSelector: string): Promise<void> {
    const chart = this.page.locator(chartSelector);
    await expect(chart).toBeVisible();

    // Test hover interaction
    await chart.hover();
    await this.page.waitForTimeout(500);

    // Test click interaction
    await chart.click();
    await this.page.waitForTimeout(500);

    // Take screenshot after interactions
    await this.takeElementScreenshot(chartSelector, 'chart-after-interaction.png');
  }

  /**
   * Verify data visualization has loaded with actual data
   */
  async verifyDataVisualizationHasContent(): Promise<void> {
    // Check for common data visualization patterns
    const dataElements = this.page.locator(
      [
        '[data-testid*="metric"]',
        '[data-testid*="count"]',
        '[data-testid*="total"]',
        '.metric-value',
        '.data-value',
        '.count',
        '.amount',
      ].join(', ')
    );

    const count = await dataElements.count();

    if (count > 0) {
      // Verify at least one element has numeric content
      for (let i = 0; i < count; i++) {
        const text = await dataElements.nth(i).textContent();
        if (text && /\d/.test(text)) {
          // Found numeric data
          return;
        }
      }
    }

    // If no numeric data found, at least verify visual elements exist
    const visualElements = this.page.locator(
      ['canvas', 'svg', '[class*="chart"]', '[class*="graph"]'].join(', ')
    );

    const visualCount = await visualElements.count();
    expect(visualCount).toBeGreaterThan(0);
  }

  /**
   * Compare visual elements across different portals for consistency
   */
  async comparePortalConsistency(
    portals: string[],
    elementSelector: string,
    testName: string
  ): Promise<void> {
    for (const portal of portals) {
      await this.page.goto(portal);
      await this.waitForVisualElements();

      const element = this.page.locator(elementSelector);
      if (await element.isVisible()) {
        await this.takeElementScreenshot(
          elementSelector,
          `${testName}-${portal.replace('/', '')}.png`
        );
      }
    }
  }

  /**
   * Test loading states and transitions
   */
  async testLoadingStates(url: string): Promise<void> {
    // Navigate to page and immediately check for loading states
    await this.page.goto(url);

    // Look for loading indicators
    const loadingElements = this.page.locator(
      [
        '[data-testid*="loading"]',
        '[class*="loading"]',
        '[class*="spinner"]',
        '.skeleton',
        '.shimmer',
      ].join(', ')
    );

    // If loading state is visible, capture it
    if (await loadingElements.first().isVisible({ timeout: 1000 })) {
      await this.takeFullPageScreenshot('loading-state.png');
    }

    // Wait for loading to complete and capture final state
    await this.waitForVisualElements();
    await this.takeFullPageScreenshot('loaded-state.png');
  }

  /**
   * Setup visual test environment
   */
  static async setupVisualTestEnvironment(): Promise<void> {
    const fs = await import('fs');
    const path = await import('path');

    // Create screenshot directories
    const screenshotDir = 'test-results/visual-screenshots';
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
  }
}

/**
 * Custom visual assertions
 */
export class VisualAssertions {
  constructor(private page: Page) {}

  /**
   * Assert that a chart or visualization is rendered and visible
   */
  async assertVisualizationExists(selector?: string): Promise<void> {
    const helper = new VisualTestHelpers(this.page);
    const hasVisualization = await helper.verifyVisualizationRendered(selector);
    expect(hasVisualization).toBe(true);
  }

  /**
   * Assert that visual elements have consistent styling
   */
  async assertConsistentStyling(selectors: string[]): Promise<void> {
    const styles: { [key: string]: string }[] = [];

    for (const selector of selectors) {
      const element = this.page.locator(selector).first();
      if (await element.isVisible()) {
        const computedStyle = await element.evaluate((el) => {
          const style = window.getComputedStyle(el);
          return {
            color: style.color,
            backgroundColor: style.backgroundColor,
            fontSize: style.fontSize,
            fontFamily: style.fontFamily,
          };
        });
        styles.push(computedStyle);
      }
    }

    // Check that key styles are consistent
    if (styles.length > 1) {
      const firstStyle = styles[0];
      for (let i = 1; i < styles.length; i++) {
        expect(styles[i].fontFamily).toBe(firstStyle.fontFamily);
        // Add more consistency checks as needed
      }
    }
  }

  /**
   * Assert that responsive breakpoints work correctly
   */
  async assertResponsiveBreakpoints(url: string): Promise<void> {
    const mobileWidth = 768;
    const desktopWidth = 1024;

    // Test mobile layout
    await this.page.setViewportSize({ width: mobileWidth - 1, height: 800 });
    await this.page.goto(url);
    await this.page.waitForLoadState('networkidle');

    // Mobile specific assertions
    const mobileMenu = this.page.locator('[data-testid*="mobile"], [class*="mobile"]');
    if ((await mobileMenu.count()) > 0) {
      await expect(mobileMenu.first()).toBeVisible();
    }

    // Test desktop layout
    await this.page.setViewportSize({ width: desktopWidth, height: 800 });
    await this.page.reload();
    await this.page.waitForLoadState('networkidle');

    // Desktop specific assertions
    const desktopNav = this.page.locator('[data-testid*="nav"], [data-testid*="sidebar"]');
    if ((await desktopNav.count()) > 0) {
      await expect(desktopNav.first()).toBeVisible();
    }
  }
}

export default VisualTestHelpers;
