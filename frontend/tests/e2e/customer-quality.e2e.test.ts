import { test, expect } from '@playwright/test';
import { setupAuth } from './auth/auth-helpers';

test.describe('Customer - Service Quality', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'customer');
  });

  test('renders dashboard and runs speed test', async ({ page }) => {
    await page.goto('/customer/quality');
    await expect(page.getByTestId('dashboard-title')).toContainText('Service Quality');
    await expect(page.getByTestId('speed-test-widget')).toBeVisible();
    await page.getByTestId('speed-test-start').click();
    await expect(page.getByText(/Testing network/)).toBeVisible();
  });
});
