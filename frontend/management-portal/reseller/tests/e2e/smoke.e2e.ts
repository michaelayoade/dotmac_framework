import { test, expect } from '@playwright/test';

test.describe('Management Reseller Portal - Smoke', () => {
  test('root redirects or loads without crash', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/(login|dashboard|partners)/, { timeout: 20000 });
    await expect(page).toHaveTitle(/Reseller|Management|DotMac|Login/i);
  });
});
