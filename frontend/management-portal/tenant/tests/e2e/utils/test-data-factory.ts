/**
 * Test Data Factory for Tenant Portal E2E Tests
 * Provides consistent test data across all test suites
 */

import { faker } from '@faker-js/faker';

export interface TestTenant {
  id: string;
  name: string;
  email: string;
  domain: string;
  plan: 'starter' | 'professional' | 'enterprise';
  subscriptions: TestSubscription[];
  users: TestUser[];
}

export interface TestSubscription {
  id: string;
  appId: string;
  appName: string;
  appCategory: 'ISP' | 'CRM' | 'E-commerce' | 'Project Management';
  tier: 'basic' | 'standard' | 'premium' | 'enterprise';
  status: 'active' | 'cancelled' | 'expired' | 'pending';
  startDate: string;
  endDate?: string;
  licenses: number;
  usedLicenses: number;
  monthlyPrice: number;
  features: string[];
}

export interface TestUser {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'user';
  permissions: string[];
  lastLogin?: string;
  status: 'active' | 'inactive' | 'pending';
}

export interface TestLicense {
  id: string;
  appId: string;
  userId?: string;
  feature: string;
  limit: number;
  used: number;
  expiryDate?: string;
}

export class TestDataFactory {
  /**
   * Create a test tenant with default subscriptions
   */
  static createTenant(overrides: Partial<TestTenant> = {}): TestTenant {
    const tenant: TestTenant = {
      id: faker.string.uuid(),
      name: faker.company.name(),
      email: faker.internet.email(),
      domain: faker.internet.domainName(),
      plan: 'professional',
      subscriptions: [],
      users: [],
      ...overrides,
    };

    // Add default subscriptions if none provided
    if (tenant.subscriptions.length === 0) {
      tenant.subscriptions = [
        this.createSubscription({ appCategory: 'ISP', appName: 'ISP Management Suite' }),
        this.createSubscription({
          appCategory: 'CRM',
          appName: 'Customer CRM Pro',
          status: 'pending',
        }),
      ];
    }

    // Add default admin user if none provided
    if (tenant.users.length === 0) {
      tenant.users = [
        this.createUser({ role: 'admin', email: tenant.email }),
        this.createUser({ role: 'manager' }),
        this.createUser({ role: 'user' }),
      ];
    }

    return tenant;
  }

  /**
   * Create a test subscription
   */
  static createSubscription(overrides: Partial<TestSubscription> = {}): TestSubscription {
    const baseFeatures = ['Dashboard', 'Reports', 'User Management'];
    const premiumFeatures = [
      ...baseFeatures,
      'Advanced Analytics',
      'API Access',
      'Custom Integrations',
    ];

    const subscription: TestSubscription = {
      id: faker.string.uuid(),
      appId: faker.string.uuid(),
      appName: faker.commerce.productName(),
      appCategory: 'ISP',
      tier: 'standard',
      status: 'active',
      startDate: faker.date.past().toISOString(),
      licenses: 10,
      usedLicenses: faker.number.int({ min: 1, max: 8 }),
      monthlyPrice: faker.number.int({ min: 29, max: 299 }),
      features: baseFeatures,
      ...overrides,
    };

    // Adjust features based on tier
    if (subscription.tier === 'premium' || subscription.tier === 'enterprise') {
      subscription.features = premiumFeatures;
      subscription.monthlyPrice = faker.number.int({ min: 99, max: 999 });
    }

    return subscription;
  }

  /**
   * Create a test user
   */
  static createUser(overrides: Partial<TestUser> = {}): TestUser {
    const basePermissions = ['read'];
    const managerPermissions = [...basePermissions, 'write', 'manage_users'];
    const adminPermissions = [...managerPermissions, 'admin', 'billing', 'settings'];

    const user: TestUser = {
      id: faker.string.uuid(),
      email: faker.internet.email(),
      name: faker.person.fullName(),
      role: 'user',
      permissions: basePermissions,
      lastLogin: faker.date.recent().toISOString(),
      status: 'active',
      ...overrides,
    };

    // Adjust permissions based on role
    switch (user.role) {
      case 'admin':
        user.permissions = adminPermissions;
        break;
      case 'manager':
        user.permissions = managerPermissions;
        break;
      default:
        user.permissions = basePermissions;
    }

    return user;
  }

  /**
   * Create a test license
   */
  static createLicense(overrides: Partial<TestLicense> = {}): TestLicense {
    return {
      id: faker.string.uuid(),
      appId: faker.string.uuid(),
      feature: faker.commerce.productName(),
      limit: faker.number.int({ min: 1, max: 100 }),
      used: faker.number.int({ min: 0, max: 50 }),
      expiryDate: faker.date.future().toISOString(),
      ...overrides,
    };
  }

  /**
   * Create multiple test tenants
   */
  static createTenants(count: number = 3): TestTenant[] {
    return Array.from({ length: count }, () => this.createTenant());
  }

  /**
   * Create app catalog data
   */
  static createAppCatalog() {
    return {
      categories: [
        {
          id: 'isp',
          name: 'ISP Management',
          description: 'Complete ISP management solutions',
          apps: [
            {
              id: 'isp-core',
              name: 'ISP Core Management',
              description: 'Complete ISP operations management',
              category: 'ISP',
              tiers: ['basic', 'standard', 'premium'],
              basePrice: 49,
              features: ['Customer Management', 'Billing', 'Network Monitoring'],
            },
            {
              id: 'isp-billing',
              name: 'Advanced Billing Suite',
              description: 'Comprehensive billing and invoicing',
              category: 'ISP',
              tiers: ['standard', 'premium'],
              basePrice: 29,
              features: ['Automated Billing', 'Payment Processing', 'Tax Management'],
            },
          ],
        },
        {
          id: 'crm',
          name: 'Customer Relationship Management',
          description: 'CRM solutions for customer management',
          apps: [
            {
              id: 'crm-pro',
              name: 'CRM Professional',
              description: 'Professional CRM with automation',
              category: 'CRM',
              tiers: ['basic', 'standard', 'premium', 'enterprise'],
              basePrice: 39,
              features: ['Contact Management', 'Sales Pipeline', 'Email Integration'],
            },
          ],
        },
        {
          id: 'ecommerce',
          name: 'E-commerce',
          description: 'Online store and e-commerce solutions',
          apps: [
            {
              id: 'store-builder',
              name: 'Store Builder Pro',
              description: 'Complete e-commerce platform',
              category: 'E-commerce',
              tiers: ['basic', 'standard', 'premium'],
              basePrice: 59,
              features: ['Online Store', 'Payment Gateway', 'Inventory Management'],
            },
          ],
        },
        {
          id: 'project',
          name: 'Project Management',
          description: 'Project and team management tools',
          apps: [
            {
              id: 'project-manager',
              name: 'Project Manager Enterprise',
              description: 'Enterprise project management suite',
              category: 'Project Management',
              tiers: ['standard', 'premium', 'enterprise'],
              basePrice: 79,
              features: ['Task Management', 'Team Collaboration', 'Time Tracking'],
            },
          ],
        },
      ],
    };
  }
}

// Default test tenant for consistent testing
export const DEFAULT_TEST_TENANT = TestDataFactory.createTenant({
  name: 'Acme ISP Solutions',
  email: 'admin@acme-isp.test',
  domain: 'acme-isp.test',
  plan: 'professional',
});
