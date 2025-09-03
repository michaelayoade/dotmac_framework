/**
 * SSO Test Helper - Utilities for E2E SSO testing with mock Identity Providers
 * Handles OIDC and SAML authentication flows, token validation, and error scenarios
 */

import { expect } from '@playwright/test';

export interface OIDCConfig {
  issuer: string;
  clientId: string;
  redirectUri: string;
  scopes: string[];
  responseType?: string;
  authEndpoint?: string;
  tokenEndpoint?: string;
  userinfoEndpoint?: string;
}

export interface SAMLConfig {
  entityId: string;
  ssoUrl: string;
  sloUrl?: string;
  certificate: string;
  nameIdFormat?: string;
  signatureAlgorithm?: string;
}

export interface SSOUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  displayName: string;
  groups?: string[];
  roles?: string[];
  attributes?: Record<string, any>;
}

export interface SSOTestScenario {
  name: string;
  provider: 'oidc' | 'saml';
  user: SSOUser;
  shouldSucceed: boolean;
  expectedError?: string;
  customClaims?: Record<string, any>;
}

export class SSOTestHelper {
  private mockIdPPort = 8040;
  private mockIdPUrl = `http://localhost:${this.mockIdPPort}`;

  constructor(private page: any) {}

  async setup() {
    // Mock OIDC endpoints
    await this.page.route('**/.well-known/openid_configuration', async (route: any) => {
      const config = {
        issuer: this.mockIdPUrl,
        authorization_endpoint: `${this.mockIdPUrl}/oauth2/authorize`,
        token_endpoint: `${this.mockIdPUrl}/oauth2/token`,
        userinfo_endpoint: `${this.mockIdPUrl}/oauth2/userinfo`,
        jwks_uri: `${this.mockIdPUrl}/.well-known/jwks.json`,
        response_types_supported: ['code'],
        subject_types_supported: ['public'],
        id_token_signing_alg_values_supported: ['RS256'],
        scopes_supported: ['openid', 'email', 'profile'],
        token_endpoint_auth_methods_supported: ['client_secret_basic'],
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(config),
      });
    });

    // Mock OIDC authorization endpoint
    await this.page.route('**/oauth2/authorize**', async (route: any) => {
      const request = route.request();
      const url = new URL(request.url());
      const redirectUri = url.searchParams.get('redirect_uri');
      const state = url.searchParams.get('state');
      const clientId = url.searchParams.get('client_id');

      // Store auth request for later validation
      await this.page.evaluate(
        (data) => {
          sessionStorage.setItem('oidc_auth_request', JSON.stringify(data));
        },
        { redirectUri, state, clientId }
      );

      // Return mock authorization page
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: this.generateOIDCAuthPage(redirectUri, state),
      });
    });

    // Mock OIDC token endpoint
    await this.page.route('**/oauth2/token', async (route: any) => {
      const request = route.request();
      const body = request.postDataJSON();

      if (body.grant_type === 'authorization_code' && body.code) {
        const tokenResponse = await this.generateOIDCTokenResponse(body.code);
        await route.fulfill({
          status: tokenResponse.status,
          contentType: 'application/json',
          body: JSON.stringify(tokenResponse.body),
        });
      } else {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'invalid_request' }),
        });
      }
    });

    // Mock OIDC userinfo endpoint
    await this.page.route('**/oauth2/userinfo', async (route: any) => {
      const authHeader = route.request().headers()['authorization'];
      if (authHeader && authHeader.startsWith('Bearer ')) {
        const token = authHeader.substring(7);
        const userInfo = await this.getUserInfoFromToken(token);

        await route.fulfill({
          status: userInfo ? 200 : 401,
          contentType: 'application/json',
          body: JSON.stringify(userInfo || { error: 'invalid_token' }),
        });
      } else {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'invalid_token' }),
        });
      }
    });

    // Mock SAML endpoints
    await this.page.route('**/saml/sso**', async (route: any) => {
      const request = route.request();
      const samlRequest = request.postData();

      if (samlRequest) {
        const samlResponse = await this.generateSAMLResponse(samlRequest);
        await route.fulfill({
          status: 200,
          contentType: 'text/html',
          body: samlResponse,
        });
      } else {
        await route.fulfill({ status: 400 });
      }
    });

    // Mock JWKS endpoint
    await this.page.route('**/.well-known/jwks.json', async (route: any) => {
      const jwks = {
        keys: [
          {
            kty: 'RSA',
            use: 'sig',
            kid: 'mock-key-id',
            n: 'mock-modulus',
            e: 'AQAB',
          },
        ],
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(jwks),
      });
    });

    // Initialize test data
    await this.initializeTestData();
  }

  async cleanup() {
    await this.clearTestData();
  }

  async testOIDCLogin(
    portalUrl: string,
    config: OIDCConfig,
    user: SSOUser,
    shouldSucceed: boolean = true
  ) {
    console.log(`Testing OIDC login for ${portalUrl}`);

    // Store user data for mock responses
    await this.page.evaluate((userData) => {
      sessionStorage.setItem('mock_oidc_user', JSON.stringify(userData));
    }, user);

    // Navigate to portal
    await this.page.goto(portalUrl);

    // Click SSO login button
    await expect(this.page.getByTestId('sso-login-button')).toBeVisible();
    await this.page.click('[data-testid="sso-login-button"]');

    // Should redirect to OIDC provider
    await this.page.waitForURL(/oauth2\/authorize/);

    if (shouldSucceed) {
      // Complete successful authentication
      await this.completeOIDCAuth(user);

      // Should redirect back to portal
      await expect(this.page).toHaveURL(
        new RegExp(portalUrl.replace('http://localhost:', '').replace(/\/.*/, ''))
      );

      // Verify user is logged in
      await expect(this.page.getByTestId('user-menu')).toBeVisible();
      await expect(this.page.getByText(user.displayName)).toBeVisible();
    } else {
      // Complete failed authentication
      await this.completeOIDCAuth(user, false);

      // Should show error message
      await expect(this.page.getByTestId('sso-error')).toBeVisible();
    }

    return true;
  }

  async testSAMLLogin(
    portalUrl: string,
    config: SAMLConfig,
    user: SSOUser,
    shouldSucceed: boolean = true
  ) {
    console.log(`Testing SAML login for ${portalUrl}`);

    // Store user data for mock responses
    await this.page.evaluate((userData) => {
      sessionStorage.setItem('mock_saml_user', JSON.stringify(userData));
    }, user);

    await this.page.goto(portalUrl);

    // Click SAML SSO button
    await expect(this.page.getByTestId('saml-login-button')).toBeVisible();
    await this.page.click('[data-testid="saml-login-button"]');

    // Should redirect to SAML IdP
    await this.page.waitForURL(/saml\/sso/);

    if (shouldSucceed) {
      // Complete SAML authentication
      await this.completeSAMLAuth(user);

      // Should redirect back to portal
      await expect(this.page).toHaveURL(
        new RegExp(portalUrl.replace('http://localhost:', '').replace(/\/.*/, ''))
      );

      // Verify user is logged in
      await expect(this.page.getByTestId('user-menu')).toBeVisible();
      await expect(this.page.getByText(user.displayName)).toBeVisible();
    } else {
      // Complete failed authentication
      await this.completeSAMLAuth(user, false);

      // Should show error message
      await expect(this.page.getByTestId('saml-error')).toBeVisible();
    }

    return true;
  }

  async testSSOLogout(portalUrl: string, provider: 'oidc' | 'saml') {
    console.log(`Testing SSO logout for ${provider} on ${portalUrl}`);

    // Assume user is already logged in via SSO
    await this.page.goto(portalUrl);

    // Click logout
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout"]');

    if (provider === 'oidc') {
      // Should redirect to OIDC end session endpoint
      await this.page.waitForURL(/oauth2\/logout/);

      // Mock OIDC logout completion
      await this.page.evaluate(() => {
        window.location.href = '/auth/login';
      });
    } else if (provider === 'saml') {
      // Should initiate SAML SLO
      await this.page.waitForURL(/saml\/slo/);

      // Complete SAML logout
      await this.completeSAMLLogout();
    }

    // Should redirect to login page
    await expect(this.page).toHaveURL(/\/auth\/login/);
    await expect(this.page.getByTestId('login-form')).toBeVisible();

    return true;
  }

  async testCrossPortalSSO(portals: string[], provider: 'oidc' | 'saml', user: SSOUser) {
    console.log(`Testing cross-portal SSO with ${provider}`);

    // Login to first portal
    if (provider === 'oidc') {
      await this.testOIDCLogin(portals[0], this.getDefaultOIDCConfig(), user);
    } else {
      await this.testSAMLLogin(portals[0], this.getDefaultSAMLConfig(), user);
    }

    // Navigate to other portals - should be automatically authenticated
    for (let i = 1; i < portals.length; i++) {
      await this.page.goto(portals[i]);

      // Should automatically redirect to dashboard (no login required)
      await expect(this.page.getByTestId('dashboard')).toBeVisible();
      await expect(this.page.getByTestId('user-menu')).toBeVisible();
      await expect(this.page.getByText(user.displayName)).toBeVisible();
    }

    return true;
  }

  async testInvalidTokenScenarios(portalUrl: string) {
    console.log('Testing invalid token scenarios');

    // Test expired token
    await this.page.evaluate(() => {
      sessionStorage.setItem('mock_token_expired', 'true');
    });

    await this.page.goto(portalUrl);
    await this.page.click('[data-testid="sso-login-button"]');

    // Should show token expired error
    await expect(this.page.getByTestId('token-expired-error')).toBeVisible();

    // Test invalid signature
    await this.page.evaluate(() => {
      sessionStorage.setItem('mock_token_expired', 'false');
      sessionStorage.setItem('mock_invalid_signature', 'true');
    });

    await this.page.reload();
    await this.page.click('[data-testid="sso-login-button"]');

    // Should show invalid token error
    await expect(this.page.getByTestId('invalid-token-error')).toBeVisible();

    return true;
  }

  private generateOIDCAuthPage(redirectUri: string | null, state: string | null): string {
    return `
      <!DOCTYPE html>
      <html>
        <head><title>Mock OIDC Provider</title></head>
        <body>
          <h1>Mock Identity Provider</h1>
          <p>Authorize application access?</p>
          <button id="authorize" onclick="authorize()">Authorize</button>
          <button id="deny" onclick="deny()">Deny</button>
          
          <script>
            function authorize() {
              const code = 'mock_auth_code_' + Date.now();
              const url = '${redirectUri}?code=' + code + '&state=${state}';
              window.location.href = url;
            }
            
            function deny() {
              const url = '${redirectUri}?error=access_denied&state=${state}';
              window.location.href = url;
            }
          </script>
        </body>
      </html>
    `;
  }

  private async generateOIDCTokenResponse(code: string) {
    const user = await this.page.evaluate(() => {
      return JSON.parse(sessionStorage.getItem('mock_oidc_user') || '{}');
    });

    const shouldFail = await this.page.evaluate(() => {
      return (
        sessionStorage.getItem('mock_token_expired') === 'true' ||
        sessionStorage.getItem('mock_invalid_signature') === 'true'
      );
    });

    if (shouldFail) {
      return {
        status: 400,
        body: {
          error: 'invalid_request',
          error_description: 'Invalid or expired authorization code',
        },
      };
    }

    const token = `mock_access_token_${Date.now()}`;
    const idToken = this.generateMockJWT(user);

    return {
      status: 200,
      body: {
        access_token: token,
        token_type: 'Bearer',
        expires_in: 3600,
        id_token: idToken,
        scope: 'openid email profile',
      },
    };
  }

  private generateMockJWT(user: SSOUser): string {
    const header = { alg: 'RS256', typ: 'JWT', kid: 'mock-key-id' };
    const payload = {
      iss: this.mockIdPUrl,
      sub: user.id,
      aud: 'mock-client-id',
      exp: Math.floor(Date.now() / 1000) + 3600,
      iat: Math.floor(Date.now() / 1000),
      email: user.email,
      given_name: user.firstName,
      family_name: user.lastName,
      name: user.displayName,
      groups: user.groups || [],
      ...user.customClaims,
    };

    // Mock JWT (not actually signed for testing)
    const encodedHeader = btoa(JSON.stringify(header));
    const encodedPayload = btoa(JSON.stringify(payload));
    return `${encodedHeader}.${encodedPayload}.mock_signature`;
  }

  private async getUserInfoFromToken(token: string) {
    const user = await this.page.evaluate(() => {
      return JSON.parse(sessionStorage.getItem('mock_oidc_user') || '{}');
    });

    if (!user.id) return null;

    return {
      sub: user.id,
      email: user.email,
      given_name: user.firstName,
      family_name: user.lastName,
      name: user.displayName,
      groups: user.groups || [],
    };
  }

  private async generateSAMLResponse(samlRequest: string): string {
    const user = await this.page.evaluate(() => {
      return JSON.parse(sessionStorage.getItem('mock_saml_user') || '{}');
    });

    const shouldFail = await this.page.evaluate(() => {
      return sessionStorage.getItem('mock_saml_fail') === 'true';
    });

    if (shouldFail) {
      return `
        <html>
          <body>
            <h1>Authentication Failed</h1>
            <p>Unable to authenticate user</p>
          </body>
        </html>
      `;
    }

    // Generate mock SAML response
    const samlResponse = this.generateMockSAMLAssertion(user);

    return `
      <!DOCTYPE html>
      <html>
        <body onload="document.forms[0].submit()">
          <form method="post" action="/auth/saml/callback">
            <input type="hidden" name="SAMLResponse" value="${btoa(samlResponse)}" />
            <input type="hidden" name="RelayState" value="mock-relay-state" />
          </form>
        </body>
      </html>
    `;
  }

  private generateMockSAMLAssertion(user: SSOUser): string {
    const now = new Date().toISOString();
    const notAfter = new Date(Date.now() + 3600000).toISOString(); // 1 hour

    return `<?xml version="1.0"?>
      <saml2:Assertion xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion" ID="mock-assertion-id" IssueInstant="${now}" Version="2.0">
        <saml2:Issuer>mock-saml-idp</saml2:Issuer>
        <saml2:Subject>
          <saml2:NameID Format="urn:oasis:names:tc:SAML:2.0:nameid-format:email">${user.email}</saml2:NameID>
          <saml2:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
            <saml2:SubjectConfirmationData NotOnOrAfter="${notAfter}" Recipient="/auth/saml/callback"/>
          </saml2:SubjectConfirmation>
        </saml2:Subject>
        <saml2:Conditions NotBefore="${now}" NotOnOrAfter="${notAfter}">
          <saml2:AudienceRestriction>
            <saml2:Audience>mock-service-provider</saml2:Audience>
          </saml2:AudienceRestriction>
        </saml2:Conditions>
        <saml2:AttributeStatement>
          <saml2:Attribute Name="email">
            <saml2:AttributeValue>${user.email}</saml2:AttributeValue>
          </saml2:Attribute>
          <saml2:Attribute Name="firstName">
            <saml2:AttributeValue>${user.firstName}</saml2:AttributeValue>
          </saml2:Attribute>
          <saml2:Attribute Name="lastName">
            <saml2:AttributeValue>${user.lastName}</saml2:AttributeValue>
          </saml2:Attribute>
          <saml2:Attribute Name="displayName">
            <saml2:AttributeValue>${user.displayName}</saml2:AttributeValue>
          </saml2:Attribute>
        </saml2:AttributeStatement>
        <saml2:AuthnStatement AuthnInstant="${now}">
          <saml2:AuthnContext>
            <saml2:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml2:AuthnContextClassRef>
          </saml2:AuthnContext>
        </saml2:AuthnStatement>
      </saml2:Assertion>
    `;
  }

  private async completeOIDCAuth(user: SSOUser, shouldSucceed: boolean = true) {
    if (shouldSucceed) {
      // Click authorize button in mock OIDC page
      await this.page.click('#authorize');
    } else {
      // Click deny button
      await this.page.click('#deny');
    }
  }

  private async completeSAMLAuth(user: SSOUser, shouldSucceed: boolean = true) {
    await this.page.evaluate((success) => {
      sessionStorage.setItem('mock_saml_fail', success ? 'false' : 'true');
    }, shouldSucceed);

    // The SAML response will be automatically submitted by the form
    await this.page.waitForTimeout(1000);
  }

  private async completeSAMLLogout() {
    // Mock SAML SLO completion
    await this.page.evaluate(() => {
      window.location.href = '/auth/login';
    });
  }

  private getDefaultOIDCConfig(): OIDCConfig {
    return {
      issuer: this.mockIdPUrl,
      clientId: 'mock-client-id',
      redirectUri: '/auth/oidc/callback',
      scopes: ['openid', 'email', 'profile'],
      responseType: 'code',
    };
  }

  private getDefaultSAMLConfig(): SAMLConfig {
    return {
      entityId: 'mock-saml-idp',
      ssoUrl: `${this.mockIdPUrl}/saml/sso`,
      certificate: 'mock-certificate',
      nameIdFormat: 'urn:oasis:names:tc:SAML:2.0:nameid-format:email',
    };
  }

  private async initializeTestData() {
    await this.page.evaluate(() => {
      sessionStorage.setItem('mock_oidc_user', '{}');
      sessionStorage.setItem('mock_saml_user', '{}');
      sessionStorage.setItem('mock_token_expired', 'false');
      sessionStorage.setItem('mock_invalid_signature', 'false');
      sessionStorage.setItem('mock_saml_fail', 'false');
    });
  }

  private async clearTestData() {
    await this.page.evaluate(() => {
      sessionStorage.removeItem('mock_oidc_user');
      sessionStorage.removeItem('mock_saml_user');
      sessionStorage.removeItem('mock_token_expired');
      sessionStorage.removeItem('mock_invalid_signature');
      sessionStorage.removeItem('mock_saml_fail');
      sessionStorage.removeItem('oidc_auth_request');
    });
  }

  // Utility methods for common test scenarios
  static getTestUsers(): { [key: string]: SSOUser } {
    return {
      adminUser: {
        id: 'admin-123',
        email: 'admin@dotmac.local',
        firstName: 'Admin',
        lastName: 'User',
        displayName: 'Admin User',
        groups: ['admins', 'users'],
        roles: ['admin', 'user'],
      },
      customerUser: {
        id: 'customer-456',
        email: 'customer@dotmac.local',
        firstName: 'Customer',
        lastName: 'User',
        displayName: 'Customer User',
        groups: ['customers', 'users'],
        roles: ['customer'],
      },
      technicianUser: {
        id: 'tech-789',
        email: 'technician@dotmac.local',
        firstName: 'Tech',
        lastName: 'User',
        displayName: 'Tech User',
        groups: ['technicians', 'users'],
        roles: ['technician'],
      },
      resellerUser: {
        id: 'reseller-101',
        email: 'reseller@dotmac.local',
        firstName: 'Reseller',
        lastName: 'User',
        displayName: 'Reseller User',
        groups: ['resellers', 'users'],
        roles: ['reseller'],
      },
    };
  }
}
