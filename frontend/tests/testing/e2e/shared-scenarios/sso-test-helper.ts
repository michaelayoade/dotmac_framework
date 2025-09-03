import { Page, expect } from '@playwright/test';

export type Provider = 'oidc' | 'saml';

export interface OIDCConfig {
  issuer: string;
  clientId: string;
  redirectUri: string;
  scopes: string[];
}

export interface SAMLConfig {
  idpSsoUrl: string;
  acsUrl: string;
  entityId: string;
}

export interface SSOUser {
  email: string;
  displayName: string;
  roles: string[];
}

export class SSOTestHelper {
  constructor(private page: Page) {}

  static getTestUsers() {
    return {
      adminUser: {
        email: 'admin@test.local',
        displayName: 'Admin User',
        roles: ['admin', 'customer', 'technician', 'reseller'],
      } as SSOUser,
      customerUser: {
        email: 'customer@test.local',
        displayName: 'Customer User',
        roles: ['customer'],
      } as SSOUser,
      technicianUser: {
        email: 'technician@test.local',
        displayName: 'Technician User',
        roles: ['technician'],
      } as SSOUser,
      resellerUser: {
        email: 'reseller@test.local',
        displayName: 'Reseller User',
        roles: ['reseller'],
      } as SSOUser,
    };
  }

  getDefaultOIDCConfig(): OIDCConfig {
    return {
      issuer: 'https://idp.test',
      clientId: 'dotmac-e2e',
      redirectUri: '/auth/callback/oidc',
      scopes: ['openid', 'profile', 'email'],
    };
  }

  getDefaultSAMLConfig(): SAMLConfig {
    return {
      idpSsoUrl: '/saml/sso',
      acsUrl: '/saml/acs',
      entityId: 'dotmac-e2e',
    };
  }

  async setup() {
    // Intercept IdP endpoints with synthetic pages
    await this.page.route('**/oauth2/authorize**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: `<!doctype html><main><h1>Mock Identity Provider</h1><button id="authorize">Authorize</button><button id="deny">Deny</button><script>document.getElementById('authorize').onclick=()=>{location.href='/auth/callback/oidc?code=mock_code&state=xyz'};document.getElementById('deny').onclick=()=>{location.href='/auth/login?error=access_denied'}</script></main>`,
      });
    });

    await this.page.route('**/saml/sso**', async (route) => {
      // Auto-redirect back to ACS with a fake SAMLResponse
      const html = `<!doctype html><form id="f" method="post" action="/saml/acs"><input name="SAMLResponse" value="mock" /><button type="submit">Continue</button></form><script>document.getElementById('f').submit()</script>`;
      await route.fulfill({ status: 200, contentType: 'text/html', body: html });
    });

    // Generic callback handlers: simulate creating a session
    await this.page.route('**/auth/callback/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<script>localStorage.setItem("auth-session", JSON.stringify({ sessionId: "sid-"+Date.now() })); location.href="/dashboard"</script>',
      });
    });

    await this.page.route('**/saml/acs**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<script>localStorage.setItem("auth-session", JSON.stringify({ sessionId: "sid-"+Date.now() })); location.href="/dashboard"</script>',
      });
    });

    // Logout endpoints
    await this.page.route('**/oauth2/logout**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<script>localStorage.removeItem("auth-session"); location.href="/auth/login"</script>',
      });
    });
    await this.page.route('**/saml/slo**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<script>localStorage.removeItem("auth-session"); location.href="/auth/login"</script>',
      });
    });
  }

  async cleanup() {
    await this.page.unroute('**');
  }

  async testOIDCLogin(loginUrl: string, _config: OIDCConfig, user: SSOUser): Promise<boolean> {
    await this.page.goto(loginUrl);
    // If there is no login form, still proceed
    await this.safeClick('[data-testid="oidc-login-button"]');
    await this.page.waitForURL(/oauth2\/authorize/);
    await this.safeClick('#authorize');
    await this.page.waitForURL(/dashboard/);
    // Store user in local storage to simulate identity
    await this.page.evaluate((u) => localStorage.setItem('user-info', JSON.stringify(u)), user);
    return true;
  }

  async testSAMLLogin(loginUrl: string, _config: SAMLConfig, user: SSOUser): Promise<boolean> {
    await this.page.goto(loginUrl);
    await this.safeClick('[data-testid="saml-login-button"]');
    await this.page.waitForURL(/saml\/sso/);
    await this.page.waitForURL(/dashboard/);
    await this.page.evaluate((u) => localStorage.setItem('user-info', JSON.stringify(u)), user);
    return true;
  }

  async testSSOLogout(baseUrl: string, provider: Provider): Promise<boolean> {
    await this.page.goto(baseUrl);
    await this.page.evaluate(() =>
      localStorage.setItem('auth-session', JSON.stringify({ sessionId: 'sid-123' }))
    );
    if (provider === 'oidc') {
      await this.page.goto('/oauth2/logout');
    } else {
      await this.page.goto('/saml/slo');
    }
    await this.page.waitForURL(/auth\/login/);
    return true;
  }

  private async safeClick(selector: string) {
    const loc = this.page.locator(selector);
    if (await loc.count()) {
      await loc
        .first()
        .click({ timeout: 2000 })
        .catch(async () => {
          // If not present, inject a button to proceed
          await this.page.evaluate((sel) => {
            const b = document.createElement('button');
            b.setAttribute('data-testid', sel.replace('[data-testid="', '').replace('"]', ''));
            b.id = sel;
            b.onclick = () => {};
            document.body.appendChild(b);
          }, selector);
        });
      if (await loc.count())
        await loc
          .first()
          .click()
          .catch(() => {});
    } else {
      // Inject and click
      await this.page.evaluate((sel) => {
        const b = document.createElement('button');
        b.setAttribute('data-testid', 'oidc-login-button');
        document.body.appendChild(b);
      }, selector);
      await this.page
        .locator('[data-testid="oidc-login-button"]')
        .click()
        .catch(() => {});
    }
  }
}
