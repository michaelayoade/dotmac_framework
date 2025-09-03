import { chromium, type FullConfig } from '@playwright/test';
import path from 'path';

/**
 * Global setup for Playwright tests
 * Runs once before all tests
 */
async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global setup...');

  // Create a browser instance for setup
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // Wait for the development server to be ready
    console.log('⏳ Waiting for development server...');
    await waitForServer(page);

    // Setup authentication states for different user roles
    await setupAuthenticationStates(browser);

    // Verify API endpoints are accessible
    await verifyAPIEndpoints(page);

    console.log('✅ Global setup completed successfully');
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

async function waitForServer(page: any, maxAttempts = 30): Promise<void> {
  const baseURL = 'http://localhost:3000';
  let attempts = 0;

  while (attempts < maxAttempts) {
    try {
      const response = await page.goto(baseURL, {
        waitUntil: 'domcontentloaded',
        timeout: 5000,
      });

      if (response && response.ok()) {
        console.log('✅ Development server is ready');
        return;
      }
    } catch (error) {
      attempts++;
      console.log(`⏳ Attempt ${attempts}/${maxAttempts} - Server not ready, retrying...`);
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }

  throw new Error('Development server failed to start within timeout');
}

async function setupAuthenticationStates(browser: any): Promise<void> {
  console.log('🔐 Setting up authentication states...');

  const roles = ['admin', 'manager', 'user'];

  for (const role of roles) {
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
      // Mock authentication for this role
      await mockAuthForRole(page, role);

      // Perform login
      await page.goto('/login');
      await page.fill('input[type="email"]', `${role}@dotmac.com`);
      await page.fill('input[type="password"]', `${role}123`);
      await page.click('button[type="submit"]');

      // Wait for successful login
      await page.waitForURL('/dashboard', { timeout: 10000 });

      // Save authentication state
      const authFile = path.join(__dirname, `../auth-states/${role}-auth.json`);
      await context.storageState({ path: authFile });

      console.log(`✅ ${role} authentication state saved`);
    } catch (error) {
      console.warn(`⚠️ Failed to setup ${role} auth state:`, error);
    } finally {
      await context.close();
    }
  }
}

async function mockAuthForRole(page: any, role: string): Promise<void> {
  const userData = {
    admin: {
      id: 'admin-1',
      email: 'admin@dotmac.com',
      firstName: 'Admin',
      lastName: 'User',
      role: 'admin',
      permissions: ['*'],
    },
    manager: {
      id: 'manager-1',
      email: 'manager@dotmac.com',
      firstName: 'Manager',
      lastName: 'User',
      role: 'manager',
      permissions: ['read:tenants', 'write:tenants', 'read:users'],
    },
    user: {
      id: 'user-1',
      email: 'user@dotmac.com',
      firstName: 'Regular',
      lastName: 'User',
      role: 'user',
      permissions: ['read:tenants', 'read:users'],
    },
  };

  const user = userData[role as keyof typeof userData];

  // Mock login endpoint
  await page.route('**/api/auth/login', (route: any) => {
    route.fulfill({
      status: 200,
      headers: {
        'set-cookie': `auth-token=mock-jwt-${role}; HttpOnly; Path=/; SameSite=Strict`,
      },
      body: JSON.stringify({
        user,
        token: `mock-jwt-${role}`,
      }),
    });
  });

  // Mock user profile endpoint
  await page.route('**/api/auth/me', (route: any) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({ user }),
    });
  });
}

async function verifyAPIEndpoints(page: any): Promise<void> {
  console.log('🔍 Verifying API endpoints...');

  const endpoints = ['/api/health', '/api/auth/csrf'];

  for (const endpoint of endpoints) {
    try {
      const response = await page.request.get(`http://localhost:3000${endpoint}`);
      if (response.ok()) {
        console.log(`✅ ${endpoint} is accessible`);
      } else {
        console.warn(`⚠️ ${endpoint} returned status ${response.status()}`);
      }
    } catch (error) {
      console.warn(`⚠️ Failed to verify ${endpoint}:`, error);
    }
  }
}

export default globalSetup;
