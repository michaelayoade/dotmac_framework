/**
 * DRY Authentication Scenarios - Reusable across all portals
 * Eliminates duplicate auth test code
 */

import { expect, Page } from '@playwright/test';

/**
 * DRY login scenario - reusable across all portals
 */
interface Credentials {
  email: string;
  password: string;
}

interface LoginOptions {
  loginUrl?: string;
  expectedRedirect?: string;
  portal?: string;
}

export async function performLogin(
  page: Page,
  credentials: Credentials,
  options: LoginOptions = {}
): Promise<void> {
  const { loginUrl = '/login', expectedRedirect = '/dashboard', portal = 'admin' } = options;

  // Navigate to login page
  await page.goto(loginUrl);

  // Verify login page elements
  await expect(page.getByTestId('email-input')).toBeVisible();
  await expect(page.getByTestId('password-input')).toBeVisible();
  await expect(page.getByTestId('login-button')).toBeVisible();

  // Fill credentials
  await page.fill('[data-testid="email-input"]', credentials.email);
  await page.fill('[data-testid="password-input"]', credentials.password);

  // Submit form
  await page.click('[data-testid="login-button"]');

  // Wait for navigation
  await page.waitForURL(expectedRedirect, { timeout: 10000 });

  // Verify successful login
  await expect(page.getByText('Dashboard')).toBeVisible();

  // Portal-specific verifications
  if (portal === 'admin') {
    await expect(page.getByTestId('admin-navigation')).toBeVisible();
  } else if (portal === 'customer') {
    await expect(page.getByTestId('customer-navigation')).toBeVisible();
  }
}

/**
 * DRY logout scenario
 */
interface LogoutOptions {
  expectedRedirect?: string;
}

export async function performLogout(page: Page, options: LogoutOptions = {}): Promise<void> {
  const { expectedRedirect = '/login' } = options;

  // Click user menu
  await page.click('[data-testid="user-menu-button"]');

  // Click logout
  await page.click('[data-testid="logout-button"]');

  // Wait for redirect
  await page.waitForURL(expectedRedirect, { timeout: 5000 });

  // Verify logged out
  await expect(page.getByTestId('login-form')).toBeVisible();
}

/**
 * DRY password reset scenario
 */
interface ResetOptions {
  resetUrl?: string;
}

export async function performPasswordReset(
  page: Page,
  email: string,
  options: ResetOptions = {}
): Promise<void> {
  const { resetUrl = '/forgot-password' } = options;

  // Navigate to reset page
  await page.goto(resetUrl);

  // Fill email
  await page.fill('[data-testid="reset-email-input"]', email);

  // Submit
  await page.click('[data-testid="reset-submit-button"]');

  // Verify success message
  await expect(page.getByText(/reset link sent/i)).toBeVisible();
}

/**
 * DRY session validation scenario
 */
export async function verifySessionPersistence(page: Page): Promise<void> {
  // Reload page
  await page.reload();

  // Should still be authenticated
  await expect(page.getByText('Dashboard')).toBeVisible();

  // Check for auth indicators
  await expect(page.getByTestId('user-menu-button')).toBeVisible();
}

/**
 * DRY multi-factor authentication scenario
 */
interface MFAOptions {
  skipVerification?: boolean;
}

export async function performMFASetup(page: Page, options: MFAOptions = {}): Promise<void> {
  const { skipVerification = false } = options;

  // Navigate to MFA setup
  await page.goto('/settings/security');

  // Click setup MFA
  await page.click('[data-testid="setup-mfa-button"]');

  // Verify QR code displayed
  await expect(page.getByTestId('mfa-qr-code')).toBeVisible();

  if (!skipVerification) {
    // Enter verification code (in real tests, you'd get this from test authenticator)
    await page.fill('[data-testid="mfa-code-input"]', '123456');
    await page.click('[data-testid="verify-mfa-button"]');

    // Verify success
    await expect(page.getByText(/MFA enabled successfully/i)).toBeVisible();
  }
}

/**
 * DRY role-based access scenario
 */
export async function verifyRoleAccess(
  page: Page,
  userRole: string,
  restrictedPaths: string[] = []
): Promise<void> {
  for (const path of restrictedPaths) {
    // Try to access restricted path
    await page.goto(path);

    // Should be redirected or show access denied
    const currentUrl = page.url();

    if (userRole !== 'admin') {
      expect(currentUrl).not.toContain(path);

      // Check for access denied message
      const accessDenied = page.getByText(/access denied|unauthorized/i);
      if (await accessDenied.isVisible()) {
        await expect(accessDenied).toBeVisible();
      }
    }
  }
}

/**
 * DRY tenant isolation scenario
 */
export async function verifyTenantIsolation(page: Page, tenantId: string): Promise<void> {
  // Navigate to tenant-specific page
  await page.goto('/dashboard');

  // Verify tenant context in UI
  const tenantDisplay = page.getByTestId('current-tenant');
  if (await tenantDisplay.isVisible()) {
    await expect(tenantDisplay).toContainText(tenantId);
  }

  // Verify API requests include tenant context
  const apiRequest = page.waitForRequest(/\/api\/v1\/.*/);
  await page.reload();
  const request = await apiRequest;

  expect(request.headers()['x-tenant-id']).toBe(tenantId);
}

/**
 * DRY credentials for different environments and roles
 */
export const testCredentials = {
  admin: {
    email: 'admin@dotmac.io',
    password: 'admin123',
  },
  customer: {
    email: 'customer@example.com',
    password: 'customer123',
  },
  technician: {
    email: 'tech@dotmac.io',
    password: 'tech123',
  },
  reseller: {
    email: 'reseller@partner.com',
    password: 'reseller123',
  },
};

/**
 * DRY test data for different portals
 */
export const portalConfig = {
  admin: {
    loginUrl: '/login',
    dashboardUrl: '/dashboard',
    restrictedPaths: ['/system/config', '/users/admin'],
    navigation: 'admin-navigation',
  },
  customer: {
    loginUrl: '/login',
    dashboardUrl: '/dashboard',
    restrictedPaths: ['/admin', '/system'],
    navigation: 'customer-navigation',
  },
  technician: {
    loginUrl: '/login',
    dashboardUrl: '/mobile-dashboard',
    restrictedPaths: ['/admin', '/billing'],
    navigation: 'mobile-navigation',
  },
  reseller: {
    loginUrl: '/login',
    dashboardUrl: '/partner-dashboard',
    restrictedPaths: ['/admin', '/system'],
    navigation: 'partner-navigation',
  },
};
