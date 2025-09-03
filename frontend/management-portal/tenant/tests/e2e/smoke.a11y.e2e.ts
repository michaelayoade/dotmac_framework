import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y } from '@axe-core/playwright';

test.describe('Tenant Portal - Smoke + A11y', () => {
  test('root redirects or loads and passes basic axe', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/(login|dashboard)/, { timeout: 20000 });

    await injectAxe(page);
    await checkA11y(page, undefined, {
      detailedReport: true,
      detailedReportOptions: { html: true },
      axeOptions: {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa'],
        },
      },
    });
  });
});
