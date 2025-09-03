import { test, expect } from '@playwright/test';

test.describe('Management Admin Portal - Smoke', () => {
  test('root redirects or loads without crash', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/(login|dashboard|tenants)/, { timeout: 20000 });
    await expect(page).toHaveTitle(/Management|DotMac|Login/i);
  });
});
