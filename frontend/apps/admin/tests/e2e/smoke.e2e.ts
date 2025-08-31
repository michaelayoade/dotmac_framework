import { test, expect } from '@playwright/test';

test.describe('Admin Portal - Smoke', () => {
  test('root redirects or loads without crash', async ({ page }) => {
    await page.goto('/');
    // Either login or dashboard should be reachable
    await expect(page).toHaveURL(/\/(login|dashboard)/, { timeout: 15000 });
    await expect(page).toHaveTitle(/Admin|DotMac|Login/i);
  });
});

