import { Page, expect } from '@playwright/test';

export interface SessionData {
  userId: string;
  tenantId: string;
  roles: string[];
  permissions: string[];
  sessionId: string;
  loginTime: string;
  lastActivity: string;
}

export interface PortalConfig {
  name: string;
  url: string;
  port: number;
  expectedRoles: string[];
}

export class SessionConsistencyHelper {
  constructor(private page: Page) {}

  /**
   * Test cross-portal session consistency within a tenant
   */
  async testCrossPortalSessionConsistency(
    portals: PortalConfig[],
    tenantId: string,
    userCredentials: { email: string; password: string }
  ): Promise<{ success: boolean; details: string }> {
    try {
      // Login to first portal and capture session
      const firstPortal = portals[0];
      await this.page.goto(firstPortal.url);

      // Perform login and capture session data
      const loginSession = await this.performLoginAndCaptureSession(
        userCredentials,
        firstPortal,
        tenantId
      );

      if (!loginSession.success) {
        return {
          success: false,
          details: `Login failed for ${firstPortal.name}: ${loginSession.error}`,
        };
      }

      const baseSession = loginSession.sessionData;
      const sessionValidations: Array<{ portal: string; valid: boolean; details: string }> = [];

      // Navigate to each portal and verify session consistency
      for (const portal of portals.slice(1)) {
        const validation = await this.validateSessionConsistency(portal, baseSession, tenantId);
        sessionValidations.push({
          portal: portal.name,
          valid: validation.valid,
          details: validation.details,
        });
      }

      // Check if all sessions are consistent
      const allValid = sessionValidations.every((v) => v.valid);
      const details = sessionValidations
        .map((v) => `${v.portal}: ${v.valid ? '✅' : '❌'} ${v.details}`)
        .join('; ');

      return {
        success: allValid,
        details: `Session consistency: ${details}`,
      };
    } catch (error) {
      return {
        success: false,
        details: `Cross-portal session test error: ${error.message}`,
      };
    }
  }

  /**
   * Perform login and capture session data
   */
  private async performLoginAndCaptureSession(
    credentials: { email: string; password: string },
    portal: PortalConfig,
    tenantId: string
  ): Promise<{ success: boolean; sessionData?: SessionData; error?: string }> {
    try {
      // Fill login form
      await this.page.fill('[data-testid="email-input"]', credentials.email);
      await this.page.fill('[data-testid="password-input"]', credentials.password);

      // Capture network requests for session data
      let sessionData: SessionData | null = null;

      this.page.on('response', async (response) => {
        if (response.url().includes('/api/auth/session') && response.status() === 200) {
          try {
            const data = await response.json();
            sessionData = {
              userId: data.user?.id || 'unknown',
              tenantId: data.tenant?.id || tenantId,
              roles: data.user?.roles || [],
              permissions: data.user?.permissions || [],
              sessionId: data.sessionId || 'unknown',
              loginTime: data.loginTime || new Date().toISOString(),
              lastActivity: data.lastActivity || new Date().toISOString(),
            };
          } catch (err) {
            console.warn('Failed to parse session response:', err);
          }
        }
      });

      // Submit login form
      await this.page.click('[data-testid="login-button"]');

      // Wait for navigation to dashboard or home page
      await this.page.waitForURL(new RegExp(`${portal.url}/(dashboard|home)`), { timeout: 10000 });

      // Wait a bit for session response
      await this.page.waitForTimeout(2000);

      // Fallback: extract session from localStorage or cookies if not captured
      if (!sessionData) {
        sessionData = await this.extractSessionFromStorage(tenantId);
      }

      return {
        success: !!sessionData,
        sessionData,
        error: !sessionData ? 'Could not extract session data' : undefined,
      };
    } catch (error) {
      return {
        success: false,
        error: `Login failed: ${error.message}`,
      };
    }
  }

  /**
   * Validate session consistency across portals
   */
  private async validateSessionConsistency(
    portal: PortalConfig,
    baseSession: SessionData,
    tenantId: string
  ): Promise<{ valid: boolean; details: string }> {
    try {
      // Navigate to portal
      await this.page.goto(portal.url);

      // Wait for potential redirect to login or dashboard
      await this.page.waitForTimeout(3000);

      // Check if redirected to login (session not valid)
      const currentUrl = this.page.url();
      if (currentUrl.includes('/login') || currentUrl.includes('/auth')) {
        return {
          valid: false,
          details: 'Redirected to login - session not propagated',
        };
      }

      // Extract current session data
      const currentSession = await this.extractSessionFromStorage(tenantId);

      if (!currentSession) {
        return {
          valid: false,
          details: 'No session data found in portal',
        };
      }

      // Validate session consistency
      const validations = [
        {
          field: 'userId',
          valid: currentSession.userId === baseSession.userId,
          details: `User ID: ${currentSession.userId} vs ${baseSession.userId}`,
        },
        {
          field: 'tenantId',
          valid: currentSession.tenantId === baseSession.tenantId,
          details: `Tenant ID: ${currentSession.tenantId} vs ${baseSession.tenantId}`,
        },
        {
          field: 'sessionId',
          valid: currentSession.sessionId === baseSession.sessionId,
          details: `Session ID: ${currentSession.sessionId} vs ${baseSession.sessionId}`,
        },
      ];

      const invalidValidations = validations.filter((v) => !v.valid);

      return {
        valid: invalidValidations.length === 0,
        details:
          invalidValidations.length === 0
            ? 'All session fields consistent'
            : `Inconsistent: ${invalidValidations.map((v) => v.details).join(', ')}`,
      };
    } catch (error) {
      return {
        valid: false,
        details: `Portal validation error: ${error.message}`,
      };
    }
  }

  /**
   * Extract session data from browser storage
   */
  private async extractSessionFromStorage(tenantId: string): Promise<SessionData | null> {
    try {
      // Try to get session from localStorage first
      const localStorageSession = await this.page.evaluate(() => {
        const sessionStr =
          localStorage.getItem('user-session') ||
          localStorage.getItem('auth-session') ||
          localStorage.getItem('session-data');
        return sessionStr ? JSON.parse(sessionStr) : null;
      });

      if (localStorageSession) {
        return {
          userId: localStorageSession.userId || localStorageSession.user?.id || 'unknown',
          tenantId: localStorageSession.tenantId || localStorageSession.tenant?.id || tenantId,
          roles: localStorageSession.roles || localStorageSession.user?.roles || [],
          permissions:
            localStorageSession.permissions || localStorageSession.user?.permissions || [],
          sessionId: localStorageSession.sessionId || 'unknown',
          loginTime: localStorageSession.loginTime || new Date().toISOString(),
          lastActivity: localStorageSession.lastActivity || new Date().toISOString(),
        };
      }

      // Fallback: try to get from cookies
      const cookies = await this.page.context().cookies();
      const sessionCookie = cookies.find(
        (cookie) =>
          cookie.name.includes('session') ||
          cookie.name.includes('auth') ||
          cookie.name.includes('token')
      );

      if (sessionCookie) {
        // Try to decode if it's a JWT or JSON
        try {
          const decoded = JSON.parse(decodeURIComponent(sessionCookie.value));
          return {
            userId: decoded.userId || decoded.user?.id || 'unknown',
            tenantId: decoded.tenantId || decoded.tenant?.id || tenantId,
            roles: decoded.roles || decoded.user?.roles || [],
            permissions: decoded.permissions || decoded.user?.permissions || [],
            sessionId: decoded.sessionId || sessionCookie.value.slice(0, 20),
            loginTime: decoded.loginTime || new Date().toISOString(),
            lastActivity: decoded.lastActivity || new Date().toISOString(),
          };
        } catch {
          // If not JSON, create basic session from cookie value
          return {
            userId: 'unknown',
            tenantId: tenantId,
            roles: [],
            permissions: [],
            sessionId: sessionCookie.value.slice(0, 20),
            loginTime: new Date().toISOString(),
            lastActivity: new Date().toISOString(),
          };
        }
      }

      return null;
    } catch (error) {
      console.warn('Failed to extract session from storage:', error);
      return null;
    }
  }

  /**
   * Test session timeout consistency across portals
   */
  async testSessionTimeoutConsistency(
    portals: PortalConfig[],
    tenantId: string,
    timeoutMinutes: number = 30
  ): Promise<{ success: boolean; details: string }> {
    try {
      const results: Array<{ portal: string; timeoutValid: boolean; details: string }> = [];

      for (const portal of portals) {
        await this.page.goto(portal.url);

        // Set session timestamp to simulate timeout
        await this.page.evaluate((timeout) => {
          const pastTime = new Date(Date.now() - (timeout + 5) * 60 * 1000).toISOString();
          localStorage.setItem('session-last-activity', pastTime);

          // Also update any session objects
          const sessionKeys = ['user-session', 'auth-session', 'session-data'];
          sessionKeys.forEach((key) => {
            const session = localStorage.getItem(key);
            if (session) {
              try {
                const parsed = JSON.parse(session);
                parsed.lastActivity = pastTime;
                localStorage.setItem(key, JSON.stringify(parsed));
              } catch (e) {
                // Ignore parse errors
              }
            }
          });
        }, timeoutMinutes);

        // Refresh page to trigger timeout check
        await this.page.reload();
        await this.page.waitForTimeout(2000);

        // Check if redirected to login
        const currentUrl = this.page.url();
        const redirectedToLogin = currentUrl.includes('/login') || currentUrl.includes('/auth');

        results.push({
          portal: portal.name,
          timeoutValid: redirectedToLogin,
          details: redirectedToLogin ? 'Correctly timed out' : 'Session still active',
        });
      }

      const allValid = results.every((r) => r.timeoutValid);
      const details = results
        .map((r) => `${r.portal}: ${r.timeoutValid ? '✅' : '❌'} ${r.details}`)
        .join('; ');

      return {
        success: allValid,
        details: `Session timeout consistency: ${details}`,
      };
    } catch (error) {
      return {
        success: false,
        details: `Session timeout test error: ${error.message}`,
      };
    }
  }

  /**
   * Test concurrent session handling
   */
  async testConcurrentSessionHandling(
    portals: PortalConfig[],
    tenantId: string,
    userCredentials: { email: string; password: string }
  ): Promise<{ success: boolean; details: string }> {
    try {
      // Create multiple browser contexts to simulate concurrent sessions
      const contexts = await Promise.all([
        this.page.context().browser()!.newContext(),
        this.page.context().browser()!.newContext(),
      ]);

      const pages = await Promise.all(contexts.map((ctx) => ctx.newPage()));
      const sessionResults: Array<{ context: number; portal: string; success: boolean }> = [];

      // Login from multiple contexts to same portal
      for (let i = 0; i < pages.length; i++) {
        const page = pages[i];
        const portal = portals[0]; // Test on first portal

        try {
          await page.goto(portal.url);
          await page.fill('[data-testid="email-input"]', userCredentials.email);
          await page.fill('[data-testid="password-input"]', userCredentials.password);
          await page.click('[data-testid="login-button"]');

          await page.waitForTimeout(3000);
          const loggedIn = !page.url().includes('/login');

          sessionResults.push({
            context: i + 1,
            portal: portal.name,
            success: loggedIn,
          });
        } catch (error) {
          sessionResults.push({
            context: i + 1,
            portal: portal.name,
            success: false,
          });
        }
      }

      // Clean up contexts
      await Promise.all(contexts.map((ctx) => ctx.close()));

      // Validate concurrent session handling
      const successfulSessions = sessionResults.filter((r) => r.success).length;
      const details = sessionResults
        .map((r) => `Context ${r.context}: ${r.success ? '✅' : '❌'} ${r.portal}`)
        .join('; ');

      return {
        success: successfulSessions > 0, // At least one should succeed
        details: `Concurrent sessions (${successfulSessions}/${sessionResults.length}): ${details}`,
      };
    } catch (error) {
      return {
        success: false,
        details: `Concurrent session test error: ${error.message}`,
      };
    }
  }

  /**
   * Test role-based access consistency across portals
   */
  async testRoleBasedAccessConsistency(
    portals: PortalConfig[],
    tenantId: string,
    userRole: string
  ): Promise<{ success: boolean; details: string }> {
    try {
      const accessResults: Array<{ portal: string; accessible: boolean; expectedAccess: boolean }> =
        [];

      for (const portal of portals) {
        const expectedAccess = portal.expectedRoles.includes(userRole);

        await this.page.goto(portal.url);
        await this.page.waitForTimeout(3000);

        const currentUrl = this.page.url();
        const accessible =
          !currentUrl.includes('/unauthorized') &&
          !currentUrl.includes('/forbidden') &&
          !currentUrl.includes('/login');

        accessResults.push({
          portal: portal.name,
          accessible,
          expectedAccess,
        });
      }

      // Check if access matches expectations
      const correctAccess = accessResults.filter((r) => r.accessible === r.expectedAccess).length;
      const allCorrect = correctAccess === accessResults.length;

      const details = accessResults
        .map(
          (r) =>
            `${r.portal}: ${r.accessible === r.expectedAccess ? '✅' : '❌'} ${r.accessible ? 'accessible' : 'blocked'} (expected: ${r.expectedAccess ? 'accessible' : 'blocked'})`
        )
        .join('; ');

      return {
        success: allCorrect,
        details: `Role-based access (${userRole}): ${details}`,
      };
    } catch (error) {
      return {
        success: false,
        details: `Role-based access test error: ${error.message}`,
      };
    }
  }
}
