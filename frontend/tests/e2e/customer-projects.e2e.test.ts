import { test, expect } from '@playwright/test';
import { setupAuth } from './auth/auth-helpers';

test.describe('Customer - Projects', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'customer');
  });

  test('renders projects management page', async ({ page }) => {
    await page.goto('/customer/projects');
    await expect(page.getByText('Projects')).toBeVisible();
  });
});

