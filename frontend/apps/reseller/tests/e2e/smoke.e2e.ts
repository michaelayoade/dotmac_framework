import { test, expect } from '@playwright/test';

test.describe('Reseller Portal - Smoke', () => {
  test('root redirects or loads without crash', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/(login|dashboard)/, { timeout: 15000 });
    await expect(page).toHaveTitle(/Reseller|DotMac|Login/i);
  });
});

