import { test, expect } from '@playwright/test';
import { setupAuth } from './auth/auth-helpers';

test.describe('Customer - Files', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page, 'customer');
  });

  test('shows upload area and files table', async ({ page }) => {
    await page.goto('/customer/files');
    await expect(page.getByTestId('upload-area')).toBeVisible();
    await expect(page.getByTestId('files-table')).toBeVisible();
  });
});
