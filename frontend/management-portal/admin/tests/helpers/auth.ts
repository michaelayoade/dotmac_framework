import { type Page, type BrowserContext } from '@playwright/test';
import { testUsers } from '../fixtures/test-data';

/**
 * Authentication helper functions for E2E tests
 */

export async function loginAsAdmin(page: Page): Promise<void> {
  await login(page, testUsers.admin.email, testUsers.admin.password);
}

export async function loginAsManager(page: Page): Promise<void> {
  await login(page, testUsers.manager.email, testUsers.manager.password);
}

export async function loginAsUser(page: Page): Promise<void> {
  await login(page, testUsers.user.email, testUsers.user.password);
}

export async function login(page: Page, email: string, password: string): Promise<void> {
  // Navigate to login page
  await page.goto('/login');

  // Fill in credentials
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await page.waitForURL('/dashboard');
}

export async function logout(page: Page): Promise<void> {
  // Click user menu
  await page.click('[data-testid="user-menu"]');

  // Click logout
  await page.click('[data-testid="logout-button"]');

  // Wait for redirect to login
  await page.waitForURL('/login');
}

/**
 * Create authenticated browser context
 */
export async function createAuthenticatedContext(
  browser: any,
  role: 'admin' | 'manager' | 'user' = 'admin'
): Promise<BrowserContext> {
  const context = await browser.newContext();
  const page = await context.newPage();

  const user = testUsers[role];
  await login(page, user.email, user.password);

  await page.close();
  return context;
}

/**
 * Setup authentication state for reuse
 */
export async function setupAuthState(
  page: Page,
  role: 'admin' | 'manager' | 'user' = 'admin'
): Promise<void> {
  const user = testUsers[role];

  // Mock successful authentication response
  await page.route('**/api/auth/login', (route) => {
    route.fulfill({
      status: 200,
      headers: {
        'set-cookie': 'auth-token=mock-jwt-token; HttpOnly; Path=/; SameSite=Strict',
      },
      body: JSON.stringify({
        user: {
          id: 'user-' + role,
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
          role: user.role,
        },
        permissions: role === 'admin' ? ['*'] : ['read:tenants', 'read:users'],
      }),
    });
  });

  // Mock user profile endpoint
  await page.route('**/api/auth/me', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        user: {
          id: 'user-' + role,
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
          role: user.role,
        },
      }),
    });
  });

  // Login
  await login(page, user.email, user.password);
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  try {
    // Check if we're on a protected route and not redirected to login
    const currentUrl = page.url();
    return !currentUrl.includes('/login') && currentUrl.includes('/dashboard');
  } catch {
    return false;
  }
}

/**
 * Wait for authentication to complete
 */
export async function waitForAuthentication(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => {
      // Check for auth token in cookies or localStorage
      return document.cookie.includes('auth-token') || localStorage.getItem('auth-token') !== null;
    },
    { timeout }
  );
}

/**
 * Clear authentication state
 */
export async function clearAuthState(page: Page): Promise<void> {
  // Clear cookies
  await page.context().clearCookies();

  // Clear localStorage and sessionStorage
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}

/**
 * Mock MFA challenge for testing
 */
export async function mockMFAChallenge(page: Page, required = false): Promise<void> {
  await page.route('**/api/v1/mfa/challenge', (route) => {
    if (required) {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          challengeId: 'challenge-123',
          availableMethods: ['totp', 'backup'],
          expiresAt: new Date(Date.now() + 300000).toISOString(), // 5 minutes
          attemptsRemaining: 3,
        }),
      });
    } else {
      route.fulfill({
        status: 404,
        body: JSON.stringify({ message: 'No MFA challenge required' }),
      });
    }
  });
}

/**
 * Simulate MFA setup completion
 */
export async function completeMFASetup(page: Page): Promise<void> {
  // Mock TOTP setup
  await page.route('**/api/v1/mfa/setup/totp', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        secret: 'JBSWY3DPEHPK3PXP',
        qrCodeUrl: 'otpauth://totp/Test:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Test',
        manualEntryCode: 'JBSWY3DPEHPK3PXP',
        backupCodes: [],
      }),
    });
  });

  // Mock TOTP verification
  await page.route('**/api/v1/mfa/setup/totp/verify', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        success: true,
        backupCodes: [
          'CODE1234',
          'CODE5678',
          'CODE9012',
          'CODEABCD',
          'CODEEFGH',
          'CODEIJKL',
          'CODEMNOP',
          'CODEQRST',
        ],
      }),
    });
  });

  // Mock MFA config as enabled
  await page.route('**/api/v1/mfa/config', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        userId: 'user-123',
        primaryMethod: 'totp',
        enabledMethods: ['totp'],
        status: 'enabled',
        backupCodesRemaining: 8,
        lastUsed: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }),
    });
  });
}

/**
 * Test different permission levels
 */
export const permissions = {
  admin: ['*'], // All permissions
  manager: [
    'read:tenants',
    'write:tenants',
    'read:users',
    'write:users',
    'read:analytics',
    'read:settings',
  ],
  user: ['read:tenants', 'read:users', 'read:analytics'],
};

export function hasPermission(userRole: string, permission: string): boolean {
  const userPermissions = permissions[userRole as keyof typeof permissions] || [];
  return userPermissions.includes('*') || userPermissions.includes(permission);
}
