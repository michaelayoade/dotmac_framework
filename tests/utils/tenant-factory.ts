/**
 * Tenant Factory Utilities
 * 
 * Provides utilities for creating and managing test tenants
 * for E2E testing scenarios. Handles tenant lifecycle,
 * cleanup, and configuration.
 */

import { APIRequestContext } from '@playwright/test';

export interface TestTenantConfig {
  name: string;
  plan?: 'starter' | 'professional' | 'enterprise';
  apps?: string[];
  users?: TestUser[];
  domain?: string;
  billingEnabled?: boolean;
  realtimeEnabled?: boolean;
  notificationsEnabled?: boolean;
  mfaRequired?: boolean;
  mfaMethod?: 'totp' | 'sms';
  customization?: {
    branding?: boolean;
    domain?: string;
    features?: string[];
  };
}

export interface TestUser {
  email: string;
  role: 'admin' | 'manager' | 'user';
  name?: string;
  permissions?: string[];
}

export interface TestTenant {
  id: string;
  name: string;
  domain: string;
  plan: string;
  apps: string[];
  users: TestUser[];
  createdAt: string;
  status: 'provisioning' | 'active' | 'suspended';
  apiKeys: {
    public: string;
    private: string;
  };
}

const MANAGEMENT_API_BASE = process.env.MANAGEMENT_API_URL || 'https://api.dotmac.com';
const TEST_API_KEY = process.env.TEST_API_KEY || 'test_key_12345';

// Store created tenants for cleanup
const createdTenants: string[] = [];

/**
 * Create a test tenant with the specified configuration
 */
export async function createTestTenant(config: TestTenantConfig): Promise<TestTenant> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    },
    body: JSON.stringify({
      name: config.name,
      plan: config.plan || 'professional',
      apps: config.apps || ['isp_framework'],
      domain: config.domain || generateTestDomain(config.name),
      billing_enabled: config.billingEnabled || false,
      realtime_enabled: config.realtimeEnabled || true,
      notifications_enabled: config.notificationsEnabled || true,
      mfa_required: config.mfaRequired || false,
      mfa_method: config.mfaMethod || 'totp',
      users: config.users || [{
        email: `admin@${generateTestDomain(config.name).replace('.dotmac.app', '')}.com`,
        role: 'admin',
        name: 'Test Admin'
      }],
      customization: config.customization || {}
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to create test tenant: ${response.statusText}`);
  }

  const tenant = await response.json();
  
  // Track for cleanup
  createdTenants.push(tenant.id);
  
  // Wait for tenant provisioning to complete
  await waitForTenantProvisioning(tenant.id);
  
  return tenant;
}

/**
 * Create multiple test tenants in parallel
 */
export async function createTestTenants(configs: TestTenantConfig[]): Promise<TestTenant[]> {
  const promises = configs.map(config => createTestTenant(config));
  return Promise.all(promises);
}

/**
 * Get details of an existing test tenant
 */
export async function getTenantDetails(tenantId: string): Promise<TestTenant> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}`, {
    headers: {
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to get tenant details: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Update test tenant configuration
 */
export async function updateTestTenant(tenantId: string, updates: Partial<TestTenantConfig>): Promise<TestTenant> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    },
    body: JSON.stringify(updates)
  });

  if (!response.ok) {
    throw new Error(`Failed to update test tenant: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Add application to existing tenant
 */
export async function addTenantApp(tenantId: string, appName: string, plan: string = 'standard'): Promise<void> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/apps`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    },
    body: JSON.stringify({
      app_name: appName,
      plan: plan
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to add app to tenant: ${response.statusText}`);
  }

  // Wait for app deployment
  await waitForAppDeployment(tenantId, appName);
}

/**
 * Remove application from tenant
 */
export async function removeTenantApp(tenantId: string, appName: string): Promise<void> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/apps/${appName}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to remove app from tenant: ${response.statusText}`);
  }
}

/**
 * Add user to test tenant
 */
export async function addTenantUser(tenantId: string, user: TestUser): Promise<void> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/users`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    },
    body: JSON.stringify(user)
  });

  if (!response.ok) {
    throw new Error(`Failed to add user to tenant: ${response.statusText}`);
  }
}

/**
 * Suspend tenant (for testing suspended state scenarios)
 */
export async function suspendTenant(tenantId: string, reason: string = 'Testing'): Promise<void> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/suspend`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    },
    body: JSON.stringify({ reason })
  });

  if (!response.ok) {
    throw new Error(`Failed to suspend tenant: ${response.statusText}`);
  }
}

/**
 * Reactivate suspended tenant
 */
export async function reactivateTenant(tenantId: string): Promise<void> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/reactivate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to reactivate tenant: ${response.statusText}`);
  }
}

/**
 * Clean up a specific test tenant
 */
export async function cleanupTestTenant(tenantId: string): Promise<void> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    }
  });

  if (!response.ok) {
    console.warn(`Failed to cleanup test tenant ${tenantId}: ${response.statusText}`);
    return;
  }

  // Remove from tracking
  const index = createdTenants.indexOf(tenantId);
  if (index > -1) {
    createdTenants.splice(index, 1);
  }
}

/**
 * Clean up all created test tenants (usually called after test suite)
 */
export async function cleanupAllTestTenants(): Promise<void> {
  const cleanupPromises = createdTenants.map(tenantId => 
    cleanupTestTenant(tenantId).catch(error => 
      console.warn(`Failed to cleanup tenant ${tenantId}:`, error)
    )
  );

  await Promise.allSettled(cleanupPromises);
  createdTenants.length = 0; // Clear array
}

/**
 * Wait for tenant provisioning to complete
 */
async function waitForTenantProvisioning(tenantId: string, timeout: number = 300000): Promise<void> {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/status`, {
        headers: {
          'Authorization': `Bearer ${TEST_API_KEY}`,
          'X-Test-Mode': 'true'
        }
      });

      if (response.ok) {
        const status = await response.json();
        
        if (status.status === 'active') {
          return;
        } else if (status.status === 'failed') {
          throw new Error(`Tenant provisioning failed: ${status.error}`);
        }
      }
    } catch (error) {
      console.warn('Error checking tenant status:', error);
    }
    
    // Wait 5 seconds before next check
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  throw new Error(`Tenant provisioning timeout after ${timeout}ms`);
}

/**
 * Wait for app deployment to complete
 */
async function waitForAppDeployment(tenantId: string, appName: string, timeout: number = 180000): Promise<void> {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/apps/${appName}/status`, {
        headers: {
          'Authorization': `Bearer ${TEST_API_KEY}`,
          'X-Test-Mode': 'true'
        }
      });

      if (response.ok) {
        const status = await response.json();
        
        if (status.status === 'deployed') {
          return;
        } else if (status.status === 'failed') {
          throw new Error(`App deployment failed: ${status.error}`);
        }
      }
    } catch (error) {
      console.warn('Error checking app deployment status:', error);
    }
    
    await new Promise(resolve => setTimeout(resolve, 3000));
  }
  
  throw new Error(`App deployment timeout after ${timeout}ms`);
}

/**
 * Generate a test domain name from tenant name
 */
function generateTestDomain(tenantName: string): string {
  const sanitized = tenantName
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
    .substring(0, 20);
  
  const timestamp = Date.now().toString().slice(-6);
  return `test-${sanitized}-${timestamp}.dotmac.app`;
}

/**
 * Create tenant with specific resource limits (for load testing)
 */
export async function createTenantWithLimits(
  config: TestTenantConfig,
  limits: {
    cpu?: string;
    memory?: string;
    storage?: string;
    users?: number;
  }
): Promise<TestTenant> {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    },
    body: JSON.stringify({
      ...config,
      resource_limits: limits
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to create test tenant with limits: ${response.statusText}`);
  }

  const tenant = await response.json();
  createdTenants.push(tenant.id);
  
  await waitForTenantProvisioning(tenant.id);
  return tenant;
}

/**
 * Get tenant resource usage statistics
 */
export async function getTenantResourceUsage(tenantId: string) {
  const response = await fetch(`${MANAGEMENT_API_BASE}/api/v1/test/tenants/${tenantId}/resources`, {
    headers: {
      'Authorization': `Bearer ${TEST_API_KEY}`,
      'X-Test-Mode': 'true'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to get tenant resource usage: ${response.statusText}`);
  }

  return await response.json();
}