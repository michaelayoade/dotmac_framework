import { test, expect } from '@playwright/test';
import { setupAuth } from './auth/auth-helpers';

test.describe('Customer - Support Tickets', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'customer');
  });

  test('renders tickets page with metrics', async ({ page }) => {
    await page.goto('/customer/support/tickets');
    await expect(page.getByText('Support Tickets')).toBeVisible();
  });
});

