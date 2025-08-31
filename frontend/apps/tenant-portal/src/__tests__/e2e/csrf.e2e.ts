/**
 * CSRF Integration E2E Tests
 * Validates that X-CSRF-Token is sent on mutating requests when cookie is present.
 */

import { test, expect } from '@playwright/test';

test.describe('CSRF Double-Submit Pattern', () => {
  test('injects X-CSRF-Token from cookie on login', async ({ page, context }) => {
    // Seed CSRF cookie as if /auth/csrf was called
    await context.addCookies([
      {
        name: 'csrf_token',
        value: 'test-csrf-token-1234567890123456',
        domain: 'localhost',
        path: '/',
        httpOnly: false,
        secure: false,
      },
    ]);

    // Intercept login to assert header presence
    let sawHeader = false;
    await page.route('/api/v1/tenant-admin/auth/login', async (route) => {
      const headers = route.request().headers();
      sawHeader = !!headers['x-csrf-token'] && headers['x-csrf-token'] === 'test-csrf-token-1234567890123456';
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: '',
          refresh_token: '',
          expires_in: 900,
          user: { id: 'user_1', email: 'test@example.com', roles: ['tenant_admin'] },
          tenant: { id: 'tenant_1', name: 'Test Tenant' },
        }),
      });
    });

    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    await expect.poll(() => sawHeader, { timeout: 2000 }).toBe(true);
  });
});

