import { test, expect } from '@playwright/test';

test.describe('Technician Portal - Smoke', () => {
  test('root redirects or loads without crash', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/(login|work-orders|map|dashboard)/, { timeout: 20000 });
    await expect(page).toHaveTitle(/Technician|DotMac|Login/i);
  });
});
