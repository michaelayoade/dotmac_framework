/**
 * Unified Global Setup for E2E Tests
 * Eliminates duplication and ensures consistent test environment
 */

import { chromium, type FullConfig } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

// Portal configuration mapping
const PORTAL_CONFIGS = {
  admin: { port: 3000, path: 'isp-framework/admin' },
  customer: { port: 3001, path: 'isp-framework/customer' },
  'field-ops': { port: 3002, path: 'isp-framework/field-ops' },
  reseller: { port: 3003, path: 'isp-framework/reseller' },
  'management-admin': { port: 3004, path: 'management-portal/admin' },
  'management-reseller': { port: 3005, path: 'management-portal/reseller' },
  'tenant-portal': { port: 3006, path: 'management-portal/tenant' },
} as const;

interface TestUser {
  id: string;
  name: string;
  email: string;
  role: string;
  tenant: string;
  token: string;
  permissions: string[];
}

const TEST_USERS: Record<string, TestUser> = {
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

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting unified E2E test environment setup...');

  // Ensure auth directory exists
  const authDir = path.resolve(__dirname, '../auth');
  await fs.mkdir(authDir, { recursive: true });

  // Create API mock server setup
  await setupApiMocks();

  // Setup authentication for each portal
  await setupPortalAuthentication();

  // Verify application readiness
  await verifyApplications();

  console.log('✅ Unified E2E test environment setup complete');
}

async function setupApiMocks() {
  console.log('🔧 Setting up API mocks...');

  // Create comprehensive API mock responses
  const mockData = {
    '/api/v1/customer/dashboard': {
      account: {
        id: 'CUST-TEST-001',
        name: 'Test Customer',
        status: 'active',
        plan: 'Fiber 1000Mbps',
        monthly_cost: 89.99,
      },
      service: {
        status: 'online',
        connection_speed: '1000 Mbps',
        uptime: 99.8,
      },
    },
    '/api/v1/admin/customers': {
      customers: [
        {
          id: 'CUST-TEST-001',
          name: 'Test Customer',
          email: 'customer@test.dotmac.com',
          status: 'active',
          plan: 'Fiber 1000Mbps',
        },
      ],
      total: 1,
    },
    '/api/v1/technician/work-orders': {
      work_orders: [
        {
          id: 'WO-TEST-001',
          customer_name: 'Test Customer',
          type: 'installation',
          status: 'scheduled',
          priority: 'high',
        },
      ],
    },
    '/api/v1/reseller/dashboard': {
      summary: {
        total_customers: 50,
        monthly_revenue: 4500.0,
        commission_rate: 15.0,
      },
    },
  };

  // Write mock data to be used by tests
  await fs.writeFile(
    path.resolve(__dirname, '../fixtures/api-mocks.json'),
    JSON.stringify(mockData, null, 2)
  );
}

async function setupPortalAuthentication() {
  console.log('🔐 Setting up portal authentication...');

  const browser = await chromium.launch({ headless: true });

  for (const [portalType, user] of Object.entries(TEST_USERS)) {
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
      // Set authentication state
      await page.addInitScript(
        ({ user, portalType }) => {
          // Set tokens
          localStorage.setItem(`${portalType}_auth_token`, user.token);
          localStorage.setItem(`${portalType}_user`, JSON.stringify(user));
          localStorage.setItem('auth_expires_at', String(Date.now() + 24 * 60 * 60 * 1000));

          // Set session state
          sessionStorage.setItem(`${portalType}_session_active`, 'true');
          sessionStorage.setItem('csrf_token', 'test-csrf-token');

          // Mock auth validation API
          window.fetch = new Proxy(window.fetch, {
            apply(target, thisArg, argArray) {
              const [url] = argArray;

              // Mock auth endpoints
              if (url.includes('/api/auth/validate')) {
                return Promise.resolve(
                  new Response(
                    JSON.stringify({
                      valid: true,
                      user,
                      expires_at: Date.now() + 24 * 60 * 60 * 1000,
                    })
                  )
                );
              }

              // Mock session endpoints
              if (url.includes('/api/auth/session')) {
                return Promise.resolve(
                  new Response(
                    JSON.stringify({
                      authenticated: true,
                      user,
                      session_id: 'test-session-123',
                    })
                  )
                );
              }

              return target.apply(thisArg, argArray);
            },
          });
        },
        { user, portalType }
      );

      // Save authentication state
      const authPath = path.resolve(__dirname, `../auth/${portalType}-auth.json`);
      await page.context().storageState({ path: authPath });

      console.log(`✅ Authentication setup complete for ${portalType}`);
    } catch (error) {
      console.error(`❌ Failed to setup auth for ${portalType}:`, error);
    } finally {
      await context.close();
    }
  }

  await browser.close();
}

async function verifyApplications() {
  console.log('🔍 Verifying application readiness...');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Check each portal if running multi-portal tests
    for (const [portalName, config] of Object.entries(PORTAL_CONFIGS)) {
      try {
        await page.goto(`http://localhost:${config.port}/health`, {
          timeout: 10000,
          waitUntil: 'networkidle',
        });
        console.log(`✅ ${portalName} portal ready on port ${config.port}`);
      } catch (error) {
        console.log(`⚠️  ${portalName} portal not ready (this is okay for single-portal tests)`);
      }
    }
  } finally {
    await browser.close();
  }
}

export default globalSetup;
