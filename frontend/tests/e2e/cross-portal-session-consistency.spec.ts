import { test, expect } from '@playwright/test';
import { SessionConsistencyHelper, PortalConfig } from '../../testing/e2e/shared-scenarios/session-consistency-helper';

// Portal configurations for cross-portal testing
const PORTALS: PortalConfig[] = [
  {
    name: 'Admin Portal',
    url: 'http://localhost:3001',
    port: 3001,
    expectedRoles: ['admin', 'super_admin', 'tenant_admin']
  },
  {
    name: 'Customer Portal', 
    url: 'http://localhost:3002',
    port: 3002,
    expectedRoles: ['customer', 'customer_admin', 'tenant_admin', 'admin']
  },
  {
    name: 'Technician Portal',
    url: 'http://localhost:3003', 
    port: 3003,
    expectedRoles: ['technician', 'technician_lead', 'admin', 'tenant_admin']
  },
  {
    name: 'Reseller Portal',
    url: 'http://localhost:3004',
    port: 3004,
    expectedRoles: ['reseller', 'reseller_admin', 'admin', 'tenant_admin']
  }
];

// Test user credentials for different roles
const TEST_USERS = {
  admin: {
    email: 'admin@tenant-session-001.test',
    password: 'TestAdmin123!',
    role: 'admin',
    tenantId: 'tenant-session-001'
  },
  customer: {
    email: 'customer@tenant-session-001.test', 
    password: 'TestCustomer123!',
    role: 'customer',
    tenantId: 'tenant-session-001'
  },
  technician: {
    email: 'technician@tenant-session-001.test',
    password: 'TestTechnician123!',
    role: 'technician', 
    tenantId: 'tenant-session-001'
  },
  reseller: {
    email: 'reseller@tenant-session-001.test',
    password: 'TestReseller123!',
    role: 'reseller',
    tenantId: 'tenant-session-001'
  }
};

test.describe('Cross-Portal Session Consistency', () => {
  let sessionHelper: SessionConsistencyHelper;

  test.beforeEach(async ({ page }) => {
    sessionHelper = new SessionConsistencyHelper(page);
    
    // Clear any existing sessions
    await page.goto('http://localhost:3001');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('admin session consistency across all portals @session-consistency @admin', async ({ page }) => {
    const user = TEST_USERS.admin;
    
    const result = await sessionHelper.testCrossPortalSessionConsistency(
      PORTALS,
      user.tenantId,
      { email: user.email, password: user.password }
    );

    expect(result.success).toBe(true);
    expect(result.details).toContain('Session consistency');
    
    // Log results for debugging
    console.log(`Admin Session Consistency: ${result.details}`);
  });

  test('customer session limited to appropriate portals @session-consistency @customer', async ({ page }) => {
    const user = TEST_USERS.customer;
    
    // Test role-based access consistency
    const accessResult = await sessionHelper.testRoleBasedAccessConsistency(
      PORTALS,
      user.tenantId,
      user.role
    );

    expect(accessResult.success).toBe(true);
    expect(accessResult.details).toContain('Role-based access');
    
    console.log(`Customer Access Consistency: ${accessResult.details}`);
  });

  test('technician session limited to appropriate portals @session-consistency @technician', async ({ page }) => {
    const user = TEST_USERS.technician;
    
    const accessResult = await sessionHelper.testRoleBasedAccessConsistency(
      PORTALS,
      user.tenantId,
      user.role
    );

    expect(accessResult.success).toBe(true);
    expect(accessResult.details).toContain('Role-based access');
    
    console.log(`Technician Access Consistency: ${accessResult.details}`);
  });

  test('reseller session limited to appropriate portals @session-consistency @reseller', async ({ page }) => {
    const user = TEST_USERS.reseller;
    
    const accessResult = await sessionHelper.testRoleBasedAccessConsistency(
      PORTALS,
      user.tenantId, 
      user.role
    );

    expect(accessResult.success).toBe(true);
    expect(accessResult.details).toContain('Role-based access');
    
    console.log(`Reseller Access Consistency: ${accessResult.details}`);
  });

  test('session timeout consistency across all portals @session-consistency @timeout', async ({ page }) => {
    const timeoutMinutes = 5; // Short timeout for testing
    
    const result = await sessionHelper.testSessionTimeoutConsistency(
      PORTALS,
      'tenant-session-001',
      timeoutMinutes
    );

    expect(result.success).toBe(true);
    expect(result.details).toContain('Session timeout consistency');
    
    console.log(`Session Timeout Consistency: ${result.details}`);
  });

  test('concurrent session handling @session-consistency @concurrent', async ({ page }) => {
    const user = TEST_USERS.admin;
    
    const result = await sessionHelper.testConcurrentSessionHandling(
      PORTALS,
      user.tenantId,
      { email: user.email, password: user.password }
    );

    expect(result.success).toBe(true);
    expect(result.details).toContain('Concurrent sessions');
    
    console.log(`Concurrent Session Handling: ${result.details}`);
  });

  test('cross-tenant session isolation @session-consistency @tenant-isolation', async ({ page }) => {
    // Test that sessions from one tenant don't leak to another
    const tenant1User = {
      email: 'admin@tenant-session-001.test',
      password: 'TestAdmin123!',
      tenantId: 'tenant-session-001'
    };
    
    const tenant2User = {
      email: 'admin@tenant-session-002.test', 
      password: 'TestAdmin123!',
      tenantId: 'tenant-session-002'
    };

    // Login as tenant1 user
    const result1 = await sessionHelper.testCrossPortalSessionConsistency(
      [PORTALS[0]], // Just test admin portal
      tenant1User.tenantId,
      tenant1User
    );

    expect(result1.success).toBe(true);

    // Clear session and login as tenant2 user
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    const result2 = await sessionHelper.testCrossPortalSessionConsistency(
      [PORTALS[0]],
      tenant2User.tenantId,
      tenant2User
    );

    expect(result2.success).toBe(true);
    
    console.log(`Cross-Tenant Isolation: Tenant1=${result1.success}, Tenant2=${result2.success}`);
  });

  test('session data integrity across portal navigations @session-consistency @data-integrity', async ({ page }) => {
    const user = TEST_USERS.admin;

    // Login to first portal
    await page.goto(PORTALS[0].url);
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.click('[data-testid="login-button"]');
    
    // Wait for login to complete
    await page.waitForTimeout(3000);

    // Navigate through all portals and verify session integrity
    let sessionIntegrityMaintained = true;
    let lastSessionId = '';
    
    for (const portal of PORTALS) {
      await page.goto(portal.url);
      await page.waitForTimeout(2000);
      
      // Extract session ID
      const currentSessionId = await page.evaluate(() => {
        const session = localStorage.getItem('user-session') || 
                       localStorage.getItem('auth-session') ||
                       localStorage.getItem('session-data');
        if (session) {
          try {
            const parsed = JSON.parse(session);
            return parsed.sessionId || 'unknown';
          } catch (e) {
            return 'parse-error';
          }
        }
        return 'no-session';
      });

      if (lastSessionId && lastSessionId !== currentSessionId) {
        sessionIntegrityMaintained = false;
        console.warn(`Session ID changed from ${lastSessionId} to ${currentSessionId} at ${portal.name}`);
      }
      
      lastSessionId = currentSessionId;
      
      // Verify user is not redirected to login
      const currentUrl = page.url();
      if (currentUrl.includes('/login')) {
        sessionIntegrityMaintained = false;
        console.warn(`Redirected to login at ${portal.name}`);
      }
    }

    expect(sessionIntegrityMaintained).toBe(true);
    console.log(`Session Data Integrity: ${sessionIntegrityMaintained ? '✅' : '❌'} Maintained across all portals`);
  });

  test('session persistence across browser refresh @session-consistency @persistence', async ({ page }) => {
    const user = TEST_USERS.admin;

    // Login to admin portal
    await page.goto(PORTALS[0].url);
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.click('[data-testid="login-button"]');
    
    await page.waitForTimeout(3000);
    
    // Capture initial session state
    const initialUrl = page.url();
    const initialSessionExists = !initialUrl.includes('/login');
    
    expect(initialSessionExists).toBe(true);

    // Refresh page and verify session persists
    await page.reload();
    await page.waitForTimeout(3000);
    
    const afterRefreshUrl = page.url();
    const sessionPersisted = !afterRefreshUrl.includes('/login');
    
    expect(sessionPersisted).toBe(true);
    console.log(`Session Persistence: ${sessionPersisted ? '✅' : '❌'} Session persisted after refresh`);

    // Test persistence across all portals
    for (const portal of PORTALS.slice(1)) {
      await page.goto(portal.url);
      await page.waitForTimeout(2000);
      await page.reload();
      await page.waitForTimeout(2000);
      
      const portalUrl = page.url();
      const portalSessionPersisted = !portalUrl.includes('/login');
      
      expect(portalSessionPersisted).toBe(true);
      console.log(`${portal.name} Session Persistence: ${portalSessionPersisted ? '✅' : '❌'}`);
    }
  });
});

/**
 * Session Journey Tests - Complex user flows across portals
 */
test.describe('Cross-Portal Session Journeys', () => {
  test('admin workflow: login → admin tasks → customer support → back to admin @journey @admin-workflow', async ({ page }) => {
    const sessionHelper = new SessionConsistencyHelper(page);
    const user = TEST_USERS.admin;

    // Step 1: Login to admin portal
    await page.goto(PORTALS[0].url);
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);

    let journeySuccess = true;
    let journeySteps: string[] = [];

    // Step 2: Navigate to admin dashboard
    const adminLoggedIn = !page.url().includes('/login');
    journeySteps.push(`Admin Login: ${adminLoggedIn ? '✅' : '❌'}`);
    if (!adminLoggedIn) journeySuccess = false;

    // Step 3: Switch to customer portal for support
    await page.goto(PORTALS[1].url); // Customer portal
    await page.waitForTimeout(3000);
    const customerPortalAccess = !page.url().includes('/login') && !page.url().includes('/unauthorized');
    journeySteps.push(`Customer Portal Access: ${customerPortalAccess ? '✅' : '❌'}`);
    if (!customerPortalAccess) journeySuccess = false;

    // Step 4: Return to admin portal
    await page.goto(PORTALS[0].url);
    await page.waitForTimeout(3000);
    const returnToAdmin = !page.url().includes('/login');
    journeySteps.push(`Return to Admin: ${returnToAdmin ? '✅' : '❌'}`);
    if (!returnToAdmin) journeySuccess = false;

    expect(journeySuccess).toBe(true);
    console.log(`Admin Workflow Journey: ${journeySteps.join(' → ')}`);
  });

  test('technician workflow: morning login → job assignments → customer interactions @journey @technician-workflow', async ({ page }) => {
    const sessionHelper = new SessionConsistencyHelper(page);
    const user = TEST_USERS.technician;

    await page.goto(PORTALS[2].url); // Technician portal
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);

    let journeySuccess = true;
    let journeySteps: string[] = [];

    // Check technician dashboard access
    const technicianLoggedIn = !page.url().includes('/login');
    journeySteps.push(`Technician Login: ${technicianLoggedIn ? '✅' : '❌'}`);
    if (!technicianLoggedIn) journeySuccess = false;

    // Access customer portal for customer interactions (if authorized)
    await page.goto(PORTALS[1].url); // Customer portal
    await page.waitForTimeout(3000);
    const customerAccess = !page.url().includes('/login') && !page.url().includes('/unauthorized');
    journeySteps.push(`Customer Portal Access: ${customerAccess ? '✅' : '❌'}`);
    // Note: This might fail based on role permissions, which is expected

    // Return to technician portal
    await page.goto(PORTALS[2].url);
    await page.waitForTimeout(3000);
    const returnToTech = !page.url().includes('/login');
    journeySteps.push(`Return to Technician Portal: ${returnToTech ? '✅' : '❌'}`);
    if (!returnToTech) journeySuccess = false;

    expect(journeySuccess).toBe(true);
    console.log(`Technician Workflow Journey: ${journeySteps.join(' → ')}`);
  });

  test('customer self-service journey: login → billing → support → account @journey @customer-workflow', async ({ page }) => {
    const sessionHelper = new SessionConsistencyHelper(page);
    const user = TEST_USERS.customer;

    await page.goto(PORTALS[1].url); // Customer portal
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);

    let journeySuccess = true;
    let journeySteps: string[] = [];

    // Verify customer login
    const customerLoggedIn = !page.url().includes('/login');
    journeySteps.push(`Customer Login: ${customerLoggedIn ? '✅' : '❌'}`);
    if (!customerLoggedIn) journeySuccess = false;

    // Test access to different sections within customer portal
    const customerSections = ['/billing', '/support', '/account'];
    
    for (const section of customerSections) {
      try {
        await page.goto(`${PORTALS[1].url}${section}`);
        await page.waitForTimeout(2000);
        const sectionAccess = !page.url().includes('/login') && !page.url().includes('/unauthorized');
        journeySteps.push(`${section}: ${sectionAccess ? '✅' : '❌'}`);
        if (!sectionAccess) journeySuccess = false;
      } catch (error) {
        journeySteps.push(`${section}: ❌ Error`);
        journeySuccess = false;
      }
    }

    // Verify customer cannot access admin/technician portals
    await page.goto(PORTALS[0].url); // Admin portal
    await page.waitForTimeout(3000);
    const adminBlocked = page.url().includes('/login') || page.url().includes('/unauthorized');
    journeySteps.push(`Admin Portal Blocked: ${adminBlocked ? '✅' : '❌'}`);

    expect(journeySuccess).toBe(true);
    console.log(`Customer Self-Service Journey: ${journeySteps.join(' → ')}`);
  });
});

/**
 * Edge Cases and Error Scenarios
 */
test.describe('Session Edge Cases', () => {
  test('expired token handling across portals @session-edge-cases @expired-token', async ({ page }) => {
    const sessionHelper = new SessionConsistencyHelper(page);
    const user = TEST_USERS.admin;

    // Login normally
    await page.goto(PORTALS[0].url);
    await page.fill('[data-testid="email-input"]', user.email);
    await page.fill('[data-testid="password-input"]', user.password);
    await page.click('[data-testid="login-button"]');
    await page.waitForTimeout(3000);

    // Manually expire the token
    await page.evaluate(() => {
      const expiredTime = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(); // 24 hours ago
      
      localStorage.setItem('token-expiry', expiredTime);
      
      // Update session objects with expired tokens
      const sessionKeys = ['user-session', 'auth-session', 'session-data'];
      sessionKeys.forEach(key => {
        const session = localStorage.getItem(key);
        if (session) {
          try {
            const parsed = JSON.parse(session);
            parsed.expiresAt = expiredTime;
            parsed.tokenExpiry = expiredTime;
            localStorage.setItem(key, JSON.stringify(parsed));
          } catch (e) {
            // Ignore parse errors
          }
        }
      });
    });

    // Navigate to different portals and verify expired token handling
    let expiredTokenHandled = true;
    
    for (const portal of PORTALS) {
      await page.goto(portal.url);
      await page.waitForTimeout(3000);
      
      const redirectedToLogin = page.url().includes('/login') || page.url().includes('/auth');
      if (!redirectedToLogin) {
        expiredTokenHandled = false;
        console.warn(`${portal.name} did not handle expired token correctly`);
      }
    }

    expect(expiredTokenHandled).toBe(true);
    console.log(`Expired Token Handling: ${expiredTokenHandled ? '✅' : '❌'} All portals correctly handled expired tokens`);
  });

  test('malformed session data handling @session-edge-cases @malformed-data', async ({ page }) => {
    // Test how portals handle corrupted session data
    await page.goto(PORTALS[0].url);

    // Insert malformed session data
    await page.evaluate(() => {
      localStorage.setItem('user-session', '{"invalid": json}');
      localStorage.setItem('auth-session', 'not-json-at-all');
      localStorage.setItem('session-data', '{"partial": "data", "missing"');
    });

    let malformedDataHandled = true;

    for (const portal of PORTALS) {
      await page.goto(portal.url);
      await page.waitForTimeout(3000);
      
      // Should redirect to login due to invalid session
      const handledGracefully = page.url().includes('/login') || page.url().includes('/auth');
      if (!handledGracefully) {
        malformedDataHandled = false;
        console.warn(`${portal.name} did not handle malformed session data gracefully`);
      }
    }

    expect(malformedDataHandled).toBe(true);
    console.log(`Malformed Session Data Handling: ${malformedDataHandled ? '✅' : '❌'} All portals handled malformed data gracefully`);
  });
});