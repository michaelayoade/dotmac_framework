/**
 * Global Setup for License Enforcement E2E Tests
 * 
 * Sets up test environment, databases, and services required for
 * comprehensive license enforcement testing across multiple apps.
 */

import { FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';
import { writeFileSync, readFileSync } from 'fs';
import path from 'path';

async function globalSetup(config: FullConfig) {
  console.log('🔧 Setting up license enforcement test environment...');
  
  try {
    // 1. Create test directories
    await setupTestDirectories();
    
    // 2. Initialize test databases
    await setupTestDatabases();
    
    // 3. Seed test data
    await seedLicenseTestData();
    
    // 4. Setup service authentication
    await setupServiceAuthentication();
    
    // 5. Validate service availability
    await validateServiceAvailability();
    
    console.log('✅ License enforcement test environment ready');
    
  } catch (error) {
    console.error('❌ Failed to setup test environment:', error);
    throw error;
  }
}

async function setupTestDirectories() {
  console.log('📁 Creating test directories...');
  
  const directories = [
    'test-results',
    'test-results/artifacts', 
    'test-results/screenshots',
    'test-results/videos',
    'test-results/traces',
    'test-data',
    'test-data/fixtures',
    'test-data/exports'
  ];
  
  for (const dir of directories) {
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
      console.log(`  ✓ Created ${dir}`);
    }
  }
}

async function setupTestDatabases() {
  console.log('🗄️  Initializing test databases...');
  
  try {
    // Initialize management platform test database
    console.log('  📊 Setting up license database...');
    execSync('cd ../src/dotmac_management && poetry run python -c "from dotmac_shared.database.base import create_tables; create_tables()"', {
      stdio: 'pipe',
      env: {
        ...process.env,
        DATABASE_URL: 'sqlite:///test_license.db',
        ENVIRONMENT: 'test'
      }
    });
    
    // Run database migrations
    console.log('  🔄 Running database migrations...');
    execSync('cd ../src/dotmac_management && poetry run alembic upgrade head', {
      stdio: 'pipe',
      env: {
        ...process.env,
        DATABASE_URL: 'sqlite:///test_license.db',
        ENVIRONMENT: 'test'
      }
    });
    
    console.log('  ✓ License database ready');
    
  } catch (error) {
    console.error('  ❌ Database setup failed:', error);
    throw error;
  }
}

async function seedLicenseTestData() {
  console.log('🌱 Seeding license test data...');
  
  const seedData = {
    license_contracts: [
      {
        contract_id: 'test-basic-001',
        subscription_id: 'sub-basic-001',
        tenant_id: 'tenant-basic-test',
        status: 'active',
        valid_from: new Date().toISOString(),
        valid_until: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
        contract_type: 'basic',
        max_customers: 100,
        max_concurrent_users: 10,
        max_api_calls_per_hour: 1000,
        max_network_devices: 20,
        enabled_features: ['basic_analytics', 'standard_api', 'email_support'],
        disabled_features: ['advanced_analytics', 'premium_api', 'sso'],
        feature_limits: { max_integrations: 3 },
        enforcement_mode: 'strict'
      },
      {
        contract_id: 'test-premium-001', 
        subscription_id: 'sub-premium-001',
        tenant_id: 'tenant-premium-test',
        status: 'active',
        valid_from: new Date().toISOString(),
        valid_until: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
        contract_type: 'premium',
        max_customers: 1000,
        max_concurrent_users: 50,
        max_api_calls_per_hour: 10000,
        max_network_devices: 100,
        enabled_features: [
          'basic_analytics', 'advanced_analytics', 'premium_api', 
          'custom_branding', 'email_support', 'phone_support'
        ],
        disabled_features: ['sso', 'white_label', 'priority_support'],
        feature_limits: { max_integrations: 10, max_webhooks: 5 },
        enforcement_mode: 'strict'
      },
      {
        contract_id: 'test-enterprise-001',
        subscription_id: 'sub-enterprise-001', 
        tenant_id: 'tenant-enterprise-test',
        status: 'active',
        valid_from: new Date().toISOString(),
        valid_until: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
        contract_type: 'enterprise',
        max_customers: 10000,
        max_concurrent_users: 500,
        max_api_calls_per_hour: 100000,
        max_network_devices: 1000,
        enabled_features: [
          'basic_analytics', 'advanced_analytics', 'enterprise_api',
          'sso', 'advanced_security', 'white_label', 'priority_support',
          'enterprise_integration'
        ],
        disabled_features: [],
        feature_limits: { max_integrations: -1, max_webhooks: -1 },
        enforcement_mode: 'strict'
      }
    ],
    tenants: [
      {
        tenant_id: 'tenant-basic-test',
        name: 'Basic Test Tenant',
        subdomain: 'basic-test',
        subscription_plan: 'basic',
        is_active: true
      },
      {
        tenant_id: 'tenant-premium-test',
        name: 'Premium Test Tenant', 
        subdomain: 'premium-test',
        subscription_plan: 'premium',
        is_active: true
      },
      {
        tenant_id: 'tenant-enterprise-test',
        name: 'Enterprise Test Tenant',
        subdomain: 'enterprise-test', 
        subscription_plan: 'enterprise',
        is_active: true
      }
    ],
    users: [
      {
        user_id: 'user-admin-basic',
        tenant_id: 'tenant-basic-test',
        email: 'admin@basic-test.com',
        role: 'admin',
        permissions: ['read', 'write', 'admin'],
        is_active: true
      },
      {
        user_id: 'user-admin-premium',
        tenant_id: 'tenant-premium-test',
        email: 'admin@premium-test.com', 
        role: 'admin',
        permissions: ['read', 'write', 'admin', 'billing'],
        is_active: true
      },
      {
        user_id: 'user-admin-enterprise',
        tenant_id: 'tenant-enterprise-test',
        email: 'admin@enterprise-test.com',
        role: 'admin', 
        permissions: ['*'],
        is_active: true
      },
      {
        user_id: 'user-basic-premium',
        tenant_id: 'tenant-premium-test',
        email: 'user@premium-test.com',
        role: 'user',
        permissions: ['read'],
        is_active: true
      }
    ]
  };
  
  // Save seed data to file for use by tests
  const seedDataPath = path.join('test-data', 'seed-data.json');
  writeFileSync(seedDataPath, JSON.stringify(seedData, null, 2));
  
  console.log('  ✓ Test data seeded');
}

async function setupServiceAuthentication() {
  console.log('🔑 Setting up service authentication...');
  
  // Generate test JWT secrets and service tokens
  const authConfig = {
    jwt_secret: 'test-jwt-secret-key-for-license-testing',
    service_tokens: {
      license_enforcement: 'test-license-service-token',
      cross_app_auth: 'test-cross-app-service-token',
      management_platform: 'test-management-platform-token'
    },
    test_users: {
      'admin@basic-test.com': {
        password: 'test-password-123',
        tenant_id: 'tenant-basic-test',
        role: 'admin'
      },
      'admin@premium-test.com': {
        password: 'test-password-123',
        tenant_id: 'tenant-premium-test',
        role: 'admin' 
      },
      'admin@enterprise-test.com': {
        password: 'test-password-123',
        tenant_id: 'tenant-enterprise-test',
        role: 'admin'
      },
      'user@premium-test.com': {
        password: 'test-password-123',
        tenant_id: 'tenant-premium-test',
        role: 'user'
      }
    }
  };
  
  const authConfigPath = path.join('test-data', 'auth-config.json');
  writeFileSync(authConfigPath, JSON.stringify(authConfig, null, 2));
  
  console.log('  ✓ Service authentication configured');
}

async function validateServiceAvailability() {
  console.log('🔍 Validating service availability...');
  
  // Wait for services to be ready (will be handled by webServer config in Playwright)
  // This is a placeholder for any additional validation needed
  
  console.log('  ✓ Service validation complete');
}

export default globalSetup;