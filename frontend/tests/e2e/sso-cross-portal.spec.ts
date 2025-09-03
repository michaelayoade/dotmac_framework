/**
 * Cross-Portal SSO E2E Tests with OIDC and SAML
 * Tests complete SSO flows: OIDC/SAML authentication, cross-portal sessions, logout
 */

import { test, expect } from '@playwright/test';
import { SSOTestHelper, SSOUser } from '../testing/e2e/shared-scenarios/sso-test-helper';

interface PortalConfig {
  name: string;
  url: string;
  loginUrl: string;
  dashboardUrl: string;
  expectedRole: string;
}

class SSOJourney {
  constructor(
    public page: any,
    public ssoHelper: SSOTestHelper
  ) {}

  async testOIDCLoginAcrossPortals(portals: PortalConfig[], user: SSOUser) {
    console.log('Testing OIDC login across all portals');

    for (const portal of portals) {
      console.log(`Testing OIDC login for ${portal.name} portal`);

      // Navigate to portal login page
      await this.page.goto(portal.loginUrl);
      await expect(this.page.getByTestId('login-form')).toBeVisible();

      // Click OIDC SSO login button
      await expect(this.page.getByTestId('oidc-login-button')).toBeVisible();
      await this.page.click('[data-testid="oidc-login-button"]');

      // Should redirect to OIDC provider
      await this.page.waitForURL(/oauth2\/authorize/);
      await expect(this.page.getByText('Mock Identity Provider')).toBeVisible();

      // Complete OIDC authentication
      await this.page.click('#authorize');

      // Should redirect back to portal dashboard
      await expect(this.page).toHaveURL(new RegExp(portal.dashboardUrl));

      // Verify user is logged in with correct identity
      await expect(this.page.getByTestId('user-menu')).toBeVisible();
      await expect(this.page.getByText(user.displayName)).toBeVisible();
      await expect(this.page.getByTestId('user-email')).toContainText(user.email);

      // Verify user has correct role for this portal
      if (user.roles?.includes(portal.expectedRole)) {
        await expect(this.page.getByTestId('role-indicator')).toContainText(portal.expectedRole);
      }

      // Test logout to clean up for next portal
      await this.page.click('[data-testid="user-menu"]');
      await this.page.click('[data-testid="logout"]');

      // Should redirect to OIDC logout
      await this.page.waitForURL(/oauth2\/logout/);

      // Complete logout and return to login page
      await this.page.evaluate(() => {
        window.location.href = '/auth/login';
      });

      await expect(this.page.getByTestId('login-form')).toBeVisible();
    }

    return true;
  }

  async testSAMLLoginAcrossPortals(portals: PortalConfig[], user: SSOUser) {
    console.log('Testing SAML login across all portals');

    for (const portal of portals) {
      console.log(`Testing SAML login for ${portal.name} portal`);

      await this.page.goto(portal.loginUrl);
      await expect(this.page.getByTestId('login-form')).toBeVisible();

      // Click SAML SSO login button
      await expect(this.page.getByTestId('saml-login-button')).toBeVisible();
      await this.page.click('[data-testid="saml-login-button"]');

      // Should redirect to SAML IdP
      await this.page.waitForURL(/saml\/sso/);

      // SAML response should auto-submit and redirect back
      await this.page.waitForURL(new RegExp(portal.dashboardUrl), { timeout: 10000 });

      // Verify successful SAML login
      await expect(this.page.getByTestId('user-menu')).toBeVisible();
      await expect(this.page.getByText(user.displayName)).toBeVisible();
      await expect(this.page.getByTestId('user-email')).toContainText(user.email);

      // Test SAML logout
      await this.page.click('[data-testid="user-menu"]');
      await this.page.click('[data-testid="logout"]');

      // Should initiate SAML SLO
      await this.page.waitForURL(/saml\/slo/);

      // Complete SAML logout
      await this.page.evaluate(() => {
        window.location.href = '/auth/login';
      });

      await expect(this.page.getByTestId('login-form')).toBeVisible();
    }

    return true;
  }

  async testCrossPortalSession(portals: PortalConfig[], provider: 'oidc' | 'saml', user: SSOUser) {
    console.log(`Testing cross-portal session with ${provider}`);

    // Login to first portal
    const firstPortal = portals[0];
    await this.page.goto(firstPortal.loginUrl);

    if (provider === 'oidc') {
      await this.page.click('[data-testid="oidc-login-button"]');
      await this.page.waitForURL(/oauth2\/authorize/);
      await this.page.click('#authorize');
    } else {
      await this.page.click('[data-testid="saml-login-button"]');
      await this.page.waitForURL(/saml\/sso/);
      // SAML auto-submits
    }

    // Verify login to first portal
    await expect(this.page).toHaveURL(new RegExp(firstPortal.dashboardUrl));
    await expect(this.page.getByTestId('user-menu')).toBeVisible();

    // Navigate to other portals - should be automatically authenticated
    for (let i = 1; i < portals.length; i++) {
      const portal = portals[i];
      console.log(`Testing automatic login to ${portal.name}`);

      await this.page.goto(portal.url);

      // Should automatically redirect to dashboard (SSO session active)
      await expect(this.page).toHaveURL(new RegExp(portal.dashboardUrl));
      await expect(this.page.getByTestId('user-menu')).toBeVisible();
      await expect(this.page.getByText(user.displayName)).toBeVisible();

      // Verify role-based access for this portal
      if (user.roles?.includes(portal.expectedRole)) {
        await expect(this.page.getByTestId('dashboard-content')).toBeVisible();
      } else {
        // Should show access denied if user lacks role
        await expect(this.page.getByTestId('access-denied')).toBeVisible();
      }
    }

    return true;
  }

  async testSSOErrorScenarios(portalUrl: string) {
    console.log('Testing SSO error scenarios');

    // Test OIDC authorization denied
    await this.page.goto(portalUrl);
    await this.page.click('[data-testid="oidc-login-button"]');
    await this.page.waitForURL(/oauth2\/authorize/);

    // Click deny instead of authorize
    await this.page.click('#deny');

    // Should return to login with error
    await expect(this.page).toHaveURL(/\/auth\/login/);
    await expect(this.page.getByTestId('sso-error')).toBeVisible();
    await expect(this.page.getByText(/authorization denied|access denied/i)).toBeVisible();

    // Test invalid OIDC token
    await this.page.evaluate(() => {
      sessionStorage.setItem('mock_token_expired', 'true');
    });

    await this.page.click('[data-testid="oidc-login-button"]');
    await this.page.waitForURL(/oauth2\/authorize/);
    await this.page.click('#authorize');

    // Should show token error
    await expect(this.page.getByTestId('token-error')).toBeVisible();

    // Reset for next test
    await this.page.evaluate(() => {
      sessionStorage.setItem('mock_token_expired', 'false');
    });

    // Test SAML authentication failure
    await this.page.evaluate(() => {
      sessionStorage.setItem('mock_saml_fail', 'true');
    });

    await this.page.click('[data-testid="saml-login-button"]');
    await this.page.waitForURL(/saml\/sso/);

    // Should show SAML error
    await expect(this.page.getByTestId('saml-error')).toBeVisible();
    await expect(this.page.getByText(/authentication failed/i)).toBeVisible();

    // Reset
    await this.page.evaluate(() => {
      sessionStorage.setItem('mock_saml_fail', 'false');
    });

    return true;
  }

  async testRoleBasedAccess(portals: PortalConfig[], user: SSOUser, provider: 'oidc' | 'saml') {
    console.log('Testing role-based access control');

    // Login with SSO
    await this.page.goto(portals[0].loginUrl);

    if (provider === 'oidc') {
      await this.page.click('[data-testid="oidc-login-button"]');
      await this.page.waitForURL(/oauth2\/authorize/);
      await this.page.click('#authorize');
    } else {
      await this.page.click('[data-testid="saml-login-button"]');
      await this.page.waitForURL(/saml\/sso/);
    }

    // Test access to each portal based on user roles
    for (const portal of portals) {
      console.log(`Testing access to ${portal.name} with role ${portal.expectedRole}`);

      await this.page.goto(portal.url);

      if (user.roles?.includes(portal.expectedRole)) {
        // User has required role - should have access
        await expect(this.page.getByTestId('dashboard-content')).toBeVisible();
        await expect(this.page.getByTestId('navigation-menu')).toBeVisible();

        // Test specific role-based features
        if (portal.expectedRole === 'admin') {
          await expect(this.page.getByTestId('admin-settings')).toBeVisible();
        } else if (portal.expectedRole === 'customer') {
          await expect(this.page.getByTestId('customer-dashboard')).toBeVisible();
        } else if (portal.expectedRole === 'technician') {
          await expect(this.page.getByTestId('technician-tools')).toBeVisible();
        } else if (portal.expectedRole === 'reseller') {
          await expect(this.page.getByTestId('reseller-portal')).toBeVisible();
        }
      } else {
        // User lacks required role - should be denied access
        await expect(this.page.getByTestId('access-denied')).toBeVisible();
        await expect(this.page.getByText(/insufficient permissions|access denied/i)).toBeVisible();

        // Should not see sensitive navigation
        await expect(this.page.getByTestId('admin-settings')).not.toBeVisible();
        await expect(this.page.getByTestId('navigation-menu')).not.toBeVisible();
      }
    }

    return true;
  }

  async testTokenRefresh(portalUrl: string) {
    console.log('Testing SSO token refresh');

    // Login with OIDC
    await this.page.goto(portalUrl);
    await this.page.click('[data-testid="oidc-login-button"]');
    await this.page.waitForURL(/oauth2\/authorize/);
    await this.page.click('#authorize');

    // Verify successful login
    await expect(this.page.getByTestId('user-menu')).toBeVisible();

    // Simulate token expiration by setting short expiry
    await this.page.evaluate(() => {
      const tokenData = {
        access_token: 'expired_token',
        expires_in: 1, // 1 second
        refresh_token: 'refresh_token_123',
      };
      sessionStorage.setItem('oidc_tokens', JSON.stringify(tokenData));
    });

    // Wait for token to expire and trigger refresh
    await this.page.waitForTimeout(2000);

    // Make an authenticated request that should trigger token refresh
    await this.page.click('[data-testid="user-menu"]');

    // Should successfully refresh token and maintain session
    await expect(this.page.getByTestId('user-dropdown')).toBeVisible();

    return true;
  }

  async testSSOProviderFallback(portalUrl: string) {
    console.log('Testing SSO provider fallback');

    await this.page.goto(portalUrl);

    // Test when OIDC provider is unavailable
    await this.page.route('**/.well-known/openid_configuration', async (route: any) => {
      await route.fulfill({ status: 500 });
    });

    await this.page.click('[data-testid="oidc-login-button"]');

    // Should show provider unavailable error
    await expect(this.page.getByTestId('provider-unavailable-error')).toBeVisible();

    // Should allow fallback to regular login
    await expect(this.page.getByTestId('fallback-login')).toBeVisible();
    await this.page.click('[data-testid="fallback-login"]');

    await expect(this.page.getByTestId('email-password-form')).toBeVisible();

    return true;
  }
}

test.describe('Cross-Portal SSO Authentication', () => {
  let ssoHelper: SSOTestHelper;

  // Portal configurations
  const portals: PortalConfig[] = [
    {
      name: 'Customer',
      url: 'http://localhost:3001',
      loginUrl: 'http://localhost:3001/auth/login',
      dashboardUrl: '/dashboard',
      expectedRole: 'customer',
    },
    {
      name: 'Admin',
      url: 'http://localhost:3002',
      loginUrl: 'http://localhost:3002/auth/login',
      dashboardUrl: '/admin/dashboard',
      expectedRole: 'admin',
    },
    {
      name: 'Technician',
      url: 'http://localhost:3003',
      loginUrl: 'http://localhost:3003/auth/login',
      dashboardUrl: '/technician/dashboard',
      expectedRole: 'technician',
    },
    {
      name: 'Reseller',
      url: 'http://localhost:3004',
      loginUrl: 'http://localhost:3004/auth/login',
      dashboardUrl: '/reseller/dashboard',
      expectedRole: 'reseller',
    },
  ];

  const testUsers = SSOTestHelper.getTestUsers();

  test.beforeAll(async () => {
    console.log('Setting up SSO test infrastructure...');
  });

  test.beforeEach(async ({ page }) => {
    ssoHelper = new SSOTestHelper(page);
    await ssoHelper.setup();
  });

  test.afterEach(async ({ page }) => {
    await ssoHelper.cleanup();
  });

  // Test OIDC login for each portal
  for (const portal of portals) {
    test(`completes OIDC login flow for ${portal.name} portal @sso @oidc @${portal.name.toLowerCase()}`, async ({
      page,
    }) => {
      const journey = new SSOJourney(page, ssoHelper);
      const user = testUsers[`${portal.name.toLowerCase()}User`];

      await test.step(`OIDC login for ${portal.name}`, async () => {
        const result = await ssoHelper.testOIDCLogin(
          portal.loginUrl,
          ssoHelper.getDefaultOIDCConfig(),
          user
        );
        expect(result).toBe(true);
      });
    });

    test(`completes SAML login flow for ${portal.name} portal @sso @saml @${portal.name.toLowerCase()}`, async ({
      page,
    }) => {
      const journey = new SSOJourney(page, ssoHelper);
      const user = testUsers[`${portal.name.toLowerCase()}User`];

      await test.step(`SAML login for ${portal.name}`, async () => {
        const result = await ssoHelper.testSAMLLogin(
          portal.loginUrl,
          ssoHelper.getDefaultSAMLConfig(),
          user
        );
        expect(result).toBe(true);
      });
    });
  }

  test('maintains OIDC session across all portals @sso @oidc @cross-portal', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);
    const user = testUsers.adminUser; // Admin has access to all portals

    await test.step('test cross-portal OIDC session', async () => {
      const result = await journey.testCrossPortalSession(portals, 'oidc', user);
      expect(result).toBe(true);
    });
  });

  test('maintains SAML session across all portals @sso @saml @cross-portal', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);
    const user = testUsers.adminUser; // Admin has access to all portals

    await test.step('test cross-portal SAML session', async () => {
      const result = await journey.testCrossPortalSession(portals, 'saml', user);
      expect(result).toBe(true);
    });
  });

  test('enforces role-based access with OIDC @sso @oidc @rbac', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);

    // Test with customer user who should only have access to customer portal
    const customerUser = testUsers.customerUser;

    await test.step('test OIDC role-based access', async () => {
      const result = await journey.testRoleBasedAccess(portals, customerUser, 'oidc');
      expect(result).toBe(true);
    });
  });

  test('enforces role-based access with SAML @sso @saml @rbac', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);

    // Test with technician user who should only have access to technician portal
    const techUser = testUsers.technicianUser;

    await test.step('test SAML role-based access', async () => {
      const result = await journey.testRoleBasedAccess(portals, techUser, 'saml');
      expect(result).toBe(true);
    });
  });

  test('handles SSO error scenarios @sso @errors', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);
    const portal = portals[0]; // Use customer portal for error testing

    await test.step('test SSO error scenarios', async () => {
      const result = await journey.testSSOErrorScenarios(portal.loginUrl);
      expect(result).toBe(true);
    });
  });

  test('handles SSO token refresh @sso @oidc @tokens', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);
    const portal = portals[0];

    await test.step('test token refresh', async () => {
      const result = await journey.testTokenRefresh(portal.loginUrl);
      expect(result).toBe(true);
    });
  });

  test('handles SSO provider unavailability @sso @fallback', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);
    const portal = portals[0];

    await test.step('test provider fallback', async () => {
      const result = await journey.testSSOProviderFallback(portal.loginUrl);
      expect(result).toBe(true);
    });
  });

  test('completes SSO logout flows @sso @logout', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);
    const portal = portals[0];
    const user = testUsers.customerUser;

    await test.step('test OIDC logout', async () => {
      // Login first
      await ssoHelper.testOIDCLogin(portal.loginUrl, ssoHelper.getDefaultOIDCConfig(), user);

      // Test logout
      const result = await ssoHelper.testSSOLogout(portal.url, 'oidc');
      expect(result).toBe(true);
    });

    await test.step('test SAML logout', async () => {
      // Login first
      await ssoHelper.testSAMLLogin(portal.loginUrl, ssoHelper.getDefaultSAMLConfig(), user);

      // Test logout
      const result = await ssoHelper.testSSOLogout(portal.url, 'saml');
      expect(result).toBe(true);
    });
  });

  test('SSO performance across portals @sso @performance', async ({ page }) => {
    const journey = new SSOJourney(page, ssoHelper);
    const user = testUsers.adminUser;

    const startTime = Date.now();

    // Test OIDC login across first 2 portals
    await journey.testOIDCLoginAcrossPortals(portals.slice(0, 2), user);

    // Test cross-portal session
    await journey.testCrossPortalSession(portals.slice(0, 2), 'oidc', user);

    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(60000); // 1 minute max for complete SSO flow
  });

  test('SSO accessibility @sso @a11y', async ({ page }) => {
    const portal = portals[0];

    await page.goto(portal.loginUrl);

    // Check SSO button accessibility
    const oidcButton = page.getByTestId('oidc-login-button');
    await expect(oidcButton).toHaveAttribute('role', 'button');
    await expect(oidcButton).toHaveAttribute('aria-label');

    const samlButton = page.getByTestId('saml-login-button');
    await expect(samlButton).toHaveAttribute('role', 'button');
    await expect(samlButton).toHaveAttribute('aria-label');

    // Test keyboard navigation
    await page.keyboard.press('Tab'); // Should focus on first SSO button
    await expect(oidcButton).toBeFocused();

    await page.keyboard.press('Tab'); // Should focus on second SSO button
    await expect(samlButton).toBeFocused();

    // Test screen reader announcements
    await oidcButton.click();
    await page.waitForURL(/oauth2\/authorize/);

    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('button', { name: /authorize/i })).toBeVisible();
  });
});

export { SSOJourney };
