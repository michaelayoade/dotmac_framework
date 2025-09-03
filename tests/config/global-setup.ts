/**
 * Global Setup for Dev 4 Integration Tests
 * 
 * Handles test environment preparation including database setup,
 * mock service initialization, and external service configuration.
 */

import { chromium, FullConfig } from '@playwright/test';
import { TestEnvironment, ciConfig } from './ci.config';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting Dev 4 Integration Test Environment Setup...');
  
  try {
    // 1. Environment validation
    await validateEnvironment();
    
    // 2. Database preparation
    await setupTestDatabase();
    
    // 3. Mock services setup (if using mocks)
    if (ciConfig.useMockServices) {
      await TestEnvironment.setupMockServices();
    }
    
    // 4. Authentication token preparation
    await setupAuthTokens();
    
    // 5. External service validation
    await validateExternalServices();
    
    console.log('✅ Integration test environment ready');
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    process.exit(1);
  }
}

/**
 * Validate required environment variables and dependencies
 */
async function validateEnvironment(): Promise<void> {
  console.log('📋 Validating environment...');
  
  const requiredVars = [
    'DATABASE_URL',
    'REDIS_URL', 
    'MANAGEMENT_API_URL',
    'TEST_API_KEY'
  ];
  
  const missing = requiredVars.filter(key => !process.env[key]);
  
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }
  
  // Validate Node.js version
  const nodeVersion = process.version;
  const majorVersion = parseInt(nodeVersion.substring(1).split('.')[0]);
  if (majorVersion < 16) {
    throw new Error(`Node.js 16+ required, found ${nodeVersion}`);
  }
  
  console.log('✅ Environment validation passed');
}

/**
 * Setup test database with clean schema
 */
async function setupTestDatabase(): Promise<void> {
  console.log('🗄️  Setting up test database...');
  
  try {
    const { spawn } = require('child_process');
    
    // Run database migrations
    const migrate = spawn('poetry', ['run', 'alembic', 'upgrade', 'head'], {
      cwd: './src',
      stdio: 'pipe'
    });
    
    await new Promise((resolve, reject) => {
      migrate.on('close', (code: number) => {
        if (code === 0) {
          resolve(void 0);
        } else {
          reject(new Error(`Database migration failed with code ${code}`));
        }
      });
    });
    
    // Seed test data
    await seedTestData();
    
    console.log('✅ Database setup complete');
    
  } catch (error) {
    throw new Error(`Database setup failed: ${error}`);
  }
}

/**
 * Seed essential test data
 */
async function seedTestData(): Promise<void> {
  const { spawn } = require('child_process');
  
  const seed = spawn('poetry', ['run', 'python', '-c', `
import asyncio
from dotmac_management.database import get_session
from dotmac_management.models.tenant import Tenant
from dotmac_management.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

async def seed_data():
    async for session in get_session():
        # Create test management admin
        admin = User(
            email="admin@dotmac.com",
            username="admin",
            hashed_password="$2b$12$placeholder_hash",
            is_active=True,
            is_superuser=True
        )
        session.add(admin)
        await session.commit()
        print("✅ Test admin user created")
        break

asyncio.run(seed_data())
  `], { cwd: './src', stdio: 'pipe' });
  
  await new Promise((resolve, reject) => {
    seed.on('close', (code: number) => {
      if (code === 0) resolve(void 0);
      else reject(new Error(`Data seeding failed with code ${code}`));
    });
  });
}

/**
 * Setup authentication tokens for API testing
 */
async function setupAuthTokens(): Promise<void> {
  console.log('🔐 Setting up authentication tokens...');
  
  if (ciConfig.useMockServices) {
    // Mock tokens are sufficient
    process.env.MANAGEMENT_AUTH_TOKEN = 'mock_admin_token_12345';
    process.env.TENANT_AUTH_TOKEN = 'mock_tenant_token_67890';
  } else {
    // Generate real test tokens via API
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    
    try {
      // Login to management portal and extract token
      await page.goto(`${ciConfig.realEndpoints.managementApi}/auth/login`);
      await page.fill('[data-testid="email"]', 'admin@dotmac.com');
      await page.fill('[data-testid="password"]', 'admin123');
      await page.click('[data-testid="login-button"]');
      
      // Extract token from storage
      const token = await page.evaluate(() => {
        return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
      });
      
      if (token) {
        process.env.MANAGEMENT_AUTH_TOKEN = token;
      }
      
    } catch (error) {
      console.warn('⚠️  Failed to get real auth tokens, using mock tokens');
      process.env.MANAGEMENT_AUTH_TOKEN = 'mock_admin_token_12345';
    } finally {
      await browser.close();
    }
  }
  
  console.log('✅ Authentication tokens ready');
}

/**
 * Validate external service connections
 */
async function validateExternalServices(): Promise<void> {
  console.log('🌐 Validating external services...');
  
  const services = [];
  
  if (!ciConfig.useMockServices) {
    // Test real service connections
    services.push(
      fetch('https://api.stripe.com/v1/charges', {
        headers: { 'Authorization': `Bearer ${process.env.STRIPE_SECRET_KEY}` }
      }).catch(() => null),
      
      fetch('https://api.sendgrid.com/v3/user/profile', {
        headers: { 'Authorization': `Bearer ${process.env.SENDGRID_API_KEY}` }
      }).catch(() => null)
    );
  }
  
  // Test management API health
  services.push(
    TestEnvironment.waitForService(`${ciConfig.mockEndpoints.managementApi}/api/health`)
  );
  
  const results = await Promise.allSettled(services);
  const failures = results.filter(r => r.status === 'rejected').length;
  
  if (failures > 0) {
    console.warn(`⚠️  ${failures} service validation(s) failed, continuing with mocks`);
    process.env.USE_MOCK_SERVICES = 'true';
  }
  
  console.log('✅ External service validation complete');
}

export default globalSetup;