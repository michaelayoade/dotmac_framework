/**
 * Unified Authentication Helpers for E2E Tests
 * Consistent session validation across all portals
 */

import { Page, Browser, BrowserContext } from '@playwright/test';

export interface TestUser {
  id: string;
  name: string;
  email: string;
  role: string;
  tenant: string;
  token: string;
  permissions: string[];
}

export const TEST_USERS: Record<string, TestUser> = {
  admin: {
    id: 'test-admin-001',
    name: 'Test Admin User',
    email: 'admin@test.dotmac.com',
    role: 'admin',
    tenant: 'test-tenant',
    token: 'test-admin-token-secure-12345',
    permissions: ['read:all', 'write:all', 'delete:all'],
  },
  customer: {
    id: 'test-customer-001',
    name: 'Test Customer User',
    email: 'customer@test.dotmac.com',
    role: 'customer',
    tenant: 'test-tenant',
    token: 'test-customer-token-secure-67890',
    permissions: ['read:own', 'update:profile'],
  },
  technician: {
    id: 'test-technician-001',
    name: 'Test Technician User',
    email: 'technician@test.dotmac.com',
    role: 'technician',
    tenant: 'test-tenant',
    token: 'test-technician-token-secure-11111',
    permissions: ['read:workorders', 'update:workorders', 'create:reports'],
  },
  reseller: {
    id: 'test-reseller-001',
    name: 'Test Reseller User',
    email: 'reseller@test.dotmac.com',
    role: 'reseller',
    tenant: 'test-tenant',
    token: 'test-reseller-token-secure-22222',
    permissions: ['read:customers', 'create:customers', 'read:commissions'],
  },
};

/**
 * Setup authentication for a specific user type
 */
export async function setupAuth(page: Page, userType: keyof typeof TEST_USERS) {
  const user = TEST_USERS[userType];

  await page.addInitScript(
    ({ user, userType }) => {
      // Set authentication tokens
      localStorage.setItem(`${userType}_auth_token`, user.token);
      localStorage.setItem(`${userType}_user`, JSON.stringify(user));
      localStorage.setItem('auth_expires_at', String(Date.now() + 24 * 60 * 60 * 1000));
      localStorage.setItem('auth_user_type', userType);

      // Set session state
      sessionStorage.setItem(`${userType}_session_active`, 'true');
      sessionStorage.setItem('csrf_token', 'test-csrf-token');
      sessionStorage.setItem('session_id', `test-session-${userType}-123`);
    },
    { user, userType }
  );
}

/**
 * Setup comprehensive auth API mocking with validation
 */
export async function setupAuthAPIMocks(page: Page, userType: keyof typeof TEST_USERS) {
  const user = TEST_USERS[userType];

  // Mock auth validation endpoint
  await page.route('/api/auth/validate', async (route) => {
    const token = route.request().headers()['authorization']?.replace('Bearer ', '');

    if (token === user.token) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: true,
          user,
          expires_at: Date.now() + 24 * 60 * 60 * 1000,
        }),
      });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          valid: false,
          error: 'Invalid token',
        }),
      });
    }
  });

  // Mock session endpoint
  await page.route('/api/auth/session', async (route) => {
    const token = route.request().headers()['authorization']?.replace('Bearer ', '');

    if (token === user.token) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          authenticated: true,
          user,
          session_id: `test-session-${userType}-123`,
          expires_at: Date.now() + 24 * 60 * 60 * 1000,
        }),
      });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          authenticated: false,
          error: 'Session expired',
        }),
      });
    }
  });

  // Mock refresh endpoint
  await page.route('/api/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        token: `${user.token}-refreshed`,
        expires_at: Date.now() + 24 * 60 * 60 * 1000,
        user,
      }),
    });
  });

  // Mock logout endpoint
  await page.route('/api/auth/logout', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        message: 'Logged out successfully',
      }),
    });
  });
}

/**
 * Validate authentication state in browser
 */
export async function validateAuthState(page: Page, userType: keyof typeof TEST_USERS) {
  const user = TEST_USERS[userType];

  const authState = await page.evaluate(
    ({ userType, user }) => {
      const token = localStorage.getItem(`${userType}_auth_token`);
      const userData = localStorage.getItem(`${userType}_user`);
      const expiresAt = localStorage.getItem('auth_expires_at');
      const sessionActive = sessionStorage.getItem(`${userType}_session_active`);
      const csrfToken = sessionStorage.getItem('csrf_token');

      return {
        hasToken: !!token,
        tokenMatches: token === user.token,
        hasUserData: !!userData,
        userDataValid: userData ? JSON.parse(userData).id === user.id : false,
        sessionActive: sessionActive === 'true',
        hasCsrfToken: !!csrfToken,
        notExpired: expiresAt ? parseInt(expiresAt) > Date.now() : false,
      };
    },
    { userType, user }
  );

  return authState;
}

/**
 * Test session expiration and renewal flow
 */
export async function testSessionRenewal(page: Page, userType: keyof typeof TEST_USERS) {
  // Set expired token
  await page.evaluate(
    ({ userType }) => {
      localStorage.setItem('auth_expires_at', String(Date.now() - 1000)); // Expired 1 second ago
    },
    { userType }
  );

  // Mock refresh API
  await setupAuthAPIMocks(page, userType);

  // Navigate to protected page - should trigger refresh
  await page.goto('/dashboard');

  // Wait for auto-refresh to complete
  await page.waitForFunction(() => {
    const expiresAt = localStorage.getItem('auth_expires_at');
    return expiresAt && parseInt(expiresAt) > Date.now();
  });

  // Verify page loads successfully
  await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });
}

/**
 * Test logout flow and cleanup
 */
export async function testLogoutFlow(page: Page, userType: keyof typeof TEST_USERS) {
  // Setup auth state first
  await setupAuth(page, userType);
  await setupAuthAPIMocks(page, userType);

  await page.goto('/dashboard');

  // Verify authenticated state
  await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();

  // Trigger logout
  await page.click('[data-testid="logout-btn"]');

  // Verify redirect to login
  await expect(page.url()).toContain('/login');

  // Verify auth state cleared
  const authCleared = await page.evaluate(
    ({ userType }) => {
      const token = localStorage.getItem(`${userType}_auth_token`);
      const user = localStorage.getItem(`${userType}_user`);
      const sessionActive = sessionStorage.getItem(`${userType}_session_active`);

      return {
        tokenCleared: !token,
        userCleared: !user,
        sessionCleared: !sessionActive,
      };
    },
    { userType }
  );

  return authCleared;
}

/**
 * Setup cross-portal session sharing test
 */
export async function testCrossPortalAuth(browser: Browser) {
  // Setup admin session
  const adminContext = await browser.newContext();
  const adminPage = await adminContext.newPage();
  await setupAuth(adminPage, 'admin');

  // Save admin auth state
  const adminState = await adminContext.storageState();
  await adminContext.close();

  // Create new context with admin auth
  const sharedContext = await browser.newContext({ storageState: adminState });
  const sharedPage = await sharedContext.newPage();

  // Navigate to customer portal (should inherit admin session)
  await sharedPage.goto('/customer');

  // Verify admin user is recognized across portals
  const crossPortalAuth = await sharedPage.evaluate(() => {
    const adminUser = localStorage.getItem('admin_user');
    return adminUser ? JSON.parse(adminUser) : null;
  });

  await sharedContext.close();

  return crossPortalAuth;
}
