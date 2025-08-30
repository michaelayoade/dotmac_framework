/**
 * DRY Test Data Factories - Generate consistent test data across all apps.
 * Follows Factory pattern for maintainable test data.
 */

// Types for our factories
interface FakeOptions {
  min?: number;
  max?: number;
}

interface FakeDate {
  recent: () => Date;
  past: () => Date;
  future: () => Date;
}

interface FakeHelpers {
  arrayElement: <T>(arr: T[]) => T;
  arrayElements: <T>(arr: T[], count?: number) => T[];
  slugify: (str: string) => string;
}

interface FakeDatatype {
  uuid: () => string;
  number: (opts?: FakeOptions) => number;
  boolean: () => boolean;
}

// Mock faker to avoid ES module issues
const faker = {
  person: {
    firstName: (): string => 'John',
    lastName: (): string => 'Doe',
    fullName: (): string => 'John Doe',
  },
  internet: {
    email: (): string => 'test@example.com',
    password: (): string => 'password123',
    ipv4: (): string => '192.168.1.1',
    color: (): string => '#FF5733',
  },
  phone: {
    number: (): string => '+1-555-123-4567',
  },
  image: {
    avatar: (): string => 'https://picsum.photos/100/100',
    url: (): string => 'https://picsum.photos/300/200',
  },
  company: {
    name: (): string => 'Test Company LLC',
  },
  datatype: {
    uuid: (): string => 'test-uuid-' + Math.random().toString(36).substr(2, 9),
    number: (opts?: FakeOptions): number => Math.floor(Math.random() * (opts?.max || 100)) + (opts?.min || 1),
    boolean: (): boolean => Math.random() > 0.5,
  } as FakeDatatype,
  number: {
    int: (opts?: FakeOptions): number => Math.floor(Math.random() * (opts?.max || 100)) + (opts?.min || 1),
    float: (opts?: FakeOptions): number => (Math.random() * (opts?.max || 100)) + (opts?.min || 0),
  },
  date: {
    recent: (): Date => new Date(),
    past: (): Date => new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    future: (): Date => new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
  } as FakeDate,
  lorem: {
    sentence: (): string => 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
    paragraph: (): string => 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
    paragraphs: (count?: number): string => Array(count || 1).fill('Lorem ipsum dolor sit amet, consectetur adipiscing elit.').join('\n\n'),
  },
  finance: {
    amount: (): string => '99.99',
    creditCardNumber: (): string => '4111-1111-1111-1111',
  },
  commerce: {
    price: (): string => '49.99',
  },
  location: {
    streetAddress: (): string => '123 Main St',
    city: (): string => 'Anytown',
    state: (): string => 'CA',
    zipCode: (): string => '90210',
    country: (): string => 'USA',
  },
  helpers: {
    arrayElement: <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)],
    arrayElements: <T>(arr: T[], count?: number): T[] => {
      const result: T[] = [];
      for (let i = 0; i < (count || arr.length); i++) {
        result.push(arr[Math.floor(Math.random() * arr.length)]);
      }
      return result;
    },
    slugify: (str: string): string => str.toLowerCase().replace(/\s+/g, '-'),
  } as FakeHelpers
};

/**
 * Base factory class for DRY data generation
 */
abstract class BaseFactory {
  static build(overrides: Record<string, any> = {}): any {
    return { ...this.definition(), ...overrides };
  }

  static buildList(count: number, overrides: Record<string, any> = {}): any[] {
    return Array.from({ length: count }, () => this.build(overrides));
  }

  static create(overrides: Record<string, any> = {}): any {
    // For integration with API mocks
    return this.build(overrides);
  }

  protected static definition(): any {
    throw new Error('Definition method must be implemented by subclass');
  }
}

// User types
interface UserProfile {
  firstName: string;
  lastName: string;
  phone: string;
  avatar: string;
}

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  tenantId: string;
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;
  profile: UserProfile;
  permissions?: string[];
  subscription?: Subscription;
  skills?: string[];
}

/**
 * User Factory - DRY user data generation
 */
class UserFactory extends BaseFactory {
  protected static definition(): User {
    return {
      id: faker.datatype.uuid(),
      email: faker.internet.email(),
      name: faker.person.fullName(),
      role: faker.helpers.arrayElement(['admin', 'user', 'technician', 'reseller']),
      tenantId: faker.datatype.uuid(),
      createdAt: faker.date.past(),
      updatedAt: faker.date.recent(),
      isActive: true,
      profile: {
        firstName: faker.person.firstName(),
        lastName: faker.person.lastName(),
        phone: faker.phone.number(),
        avatar: faker.image.avatar()
      }
    };
  }

  // Specialized user types (DRY role-specific data)
  static admin(overrides: Record<string, any> = {}): User {
    return this.build({
      role: 'admin',
      permissions: ['read', 'write', 'delete', 'admin'],
      ...overrides
    });
  }

  static customer(overrides: Record<string, any> = {}): User {
    return this.build({
      role: 'customer',
      permissions: ['read'],
      subscription: SubscriptionFactory.build(),
      ...overrides
    });
  }

  static technician(overrides: Record<string, any> = {}): User {
    return this.build({
      role: 'technician',
      permissions: ['read', 'write'],
      skills: faker.helpers.arrayElements(['networking', 'hardware', 'software']),
      ...overrides
    });
  }
}

// Tenant types
interface TenantSettings {
  branding: {
    logo: string;
    primaryColor: string;
    companyName: string;
  };
  features: {
    billing: boolean;
    analytics: boolean;
    support: boolean;
  };
  limits: {
    maxCustomers: number;
    maxTechnicians: number;
  };
}

interface Tenant {
  id: string;
  name: string;
  slug: string;
  domain: string;
  status: string;
  plan: string;
  settings: TenantSettings;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Tenant Factory - DRY tenant/ISP data
 */
class TenantFactory extends BaseFactory {
  protected static definition(): Tenant {
    const companyName = faker.company.name();
    return {
      id: faker.datatype.uuid(),
      name: companyName,
      slug: faker.helpers.slugify(companyName),
      domain: `${faker.helpers.slugify(companyName)}.dotmac.io`,
      status: 'active',
      plan: faker.helpers.arrayElement(['starter', 'professional', 'enterprise']),
      settings: {
        branding: {
          logo: faker.image.url(),
          primaryColor: faker.internet.color(),
          companyName: companyName
        },
        features: {
          billing: true,
          analytics: true,
          support: true
        },
        limits: {
          maxCustomers: faker.number.int({ min: 100, max: 10000 }),
          maxTechnicians: faker.number.int({ min: 5, max: 100 })
        }
      },
      createdAt: faker.date.past(),
      updatedAt: faker.date.recent()
    };
  }
}

// Customer types
interface Address {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

interface BillingInfo {
  balance: number;
  lastPayment: Date;
  nextBilling: Date;
}

interface ServiceInfo {
  connectionStatus: string;
  ipAddress: string;
  dataUsage: number;
}

interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  address: Address;
  status: string;
  plan: string;
  billingInfo: BillingInfo;
  serviceInfo: ServiceInfo;
  tenantId: string;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Customer Factory - DRY customer data
 */
class CustomerFactory extends BaseFactory {
  protected static definition(): Customer {
    return {
      id: faker.datatype.uuid(),
      name: faker.person.fullName(),
      email: faker.internet.email(),
      phone: faker.phone.number(),
      address: {
        street: faker.location.streetAddress(),
        city: faker.location.city(),
        state: faker.location.state(),
        zipCode: faker.location.zipCode(),
        country: faker.location.country()
      },
      status: faker.helpers.arrayElement(['active', 'inactive', 'suspended']),
      plan: faker.helpers.arrayElement(['basic', 'premium', 'enterprise']),
      billingInfo: {
        balance: parseFloat(faker.finance.amount()),
        lastPayment: faker.date.recent(),
        nextBilling: faker.date.future()
      },
      serviceInfo: {
        connectionStatus: faker.helpers.arrayElement(['connected', 'disconnected', 'maintenance']),
        ipAddress: faker.internet.ipv4(),
        dataUsage: parseFloat(faker.number.float({ min: 0, max: 1000 }).toString())
      },
      tenantId: faker.datatype.uuid(),
      createdAt: faker.date.past(),
      updatedAt: faker.date.recent()
    };
  }
}

// Subscription types
interface Subscription {
  id: string;
  planId: string;
  planName: string;
  price: number;
  currency: string;
  status: string;
  billingCycle: string;
  startDate: Date;
  endDate: Date;
  features: string[];
}

/**
 * Subscription Factory - DRY subscription data
 */
class SubscriptionFactory extends BaseFactory {
  protected static definition(): Subscription {
    return {
      id: faker.datatype.uuid(),
      planId: faker.datatype.uuid(),
      planName: faker.helpers.arrayElement(['Basic Internet', 'Premium Package', 'Enterprise Solution']),
      price: parseFloat(faker.commerce.price()),
      currency: 'USD',
      status: faker.helpers.arrayElement(['active', 'cancelled', 'past_due']),
      billingCycle: faker.helpers.arrayElement(['monthly', 'yearly']),
      startDate: faker.date.past(),
      endDate: faker.date.future(),
      features: faker.helpers.arrayElements([
        'High-speed Internet',
        'Static IP',
        'Priority Support',
        '24/7 Monitoring',
        'Advanced Security'
      ])
    };
  }
}

// Comment types
interface Comment {
  id: string;
  content: string;
  authorId: string;
  authorName: string;
  createdAt: Date;
  isInternal: boolean;
}

/**
 * Comment Factory - DRY comment/message data
 */
class CommentFactory extends BaseFactory {
  protected static definition(): Comment {
    return {
      id: faker.datatype.uuid(),
      content: faker.lorem.paragraphs(1),
      authorId: faker.datatype.uuid(),
      authorName: faker.person.fullName(),
      createdAt: faker.date.recent(),
      isInternal: faker.datatype.boolean()
    };
  }
}

// Ticket types
interface Ticket {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  category: string;
  customerId: string;
  assignedTo: string;
  createdAt: Date;
  updatedAt: Date;
  comments: Comment[];
}

/**
 * Ticket Factory - DRY support ticket data
 */
class TicketFactory extends BaseFactory {
  protected static definition(): Ticket {
    return {
      id: faker.datatype.uuid(),
      title: faker.lorem.sentence(),
      description: faker.lorem.paragraphs(2),
      status: faker.helpers.arrayElement(['open', 'in_progress', 'resolved', 'closed']),
      priority: faker.helpers.arrayElement(['low', 'medium', 'high', 'critical']),
      category: faker.helpers.arrayElement(['technical', 'billing', 'general', 'feature_request']),
      customerId: faker.datatype.uuid(),
      assignedTo: faker.datatype.uuid(),
      createdAt: faker.date.past(),
      updatedAt: faker.date.recent(),
      comments: CommentFactory.buildList(faker.number.int({ min: 0, max: 5 }))
    };
  }
}

// Analytics types
interface Analytics {
  id: string;
  metric: string;
  value: number;
  previousValue: number;
  change: number;
  changeType: string;
  period: string;
  timestamp: Date;
}

interface DashboardAnalytics {
  revenue: Analytics;
  customers: Analytics;
  tickets: Analytics;
  uptime: Analytics;
}

/**
 * Analytics Factory - DRY analytics data
 */
class AnalyticsFactory extends BaseFactory {
  protected static definition(): Analytics {
    return {
      id: faker.datatype.uuid(),
      metric: faker.helpers.arrayElement(['revenue', 'customers', 'tickets', 'uptime']),
      value: parseFloat(faker.number.float({ min: 0, max: 10000 }).toString()),
      previousValue: parseFloat(faker.number.float({ min: 0, max: 10000 }).toString()),
      change: parseFloat(faker.number.float({ min: -50, max: 50 }).toString()),
      changeType: faker.helpers.arrayElement(['increase', 'decrease', 'neutral']),
      period: faker.helpers.arrayElement(['daily', 'weekly', 'monthly', 'yearly']),
      timestamp: faker.date.recent()
    };
  }

  static dashboard(): DashboardAnalytics {
    return {
      revenue: this.build({ metric: 'revenue', value: 45230.50 }),
      customers: this.build({ metric: 'customers', value: 1247 }),
      tickets: this.build({ metric: 'tickets', value: 23 }),
      uptime: this.build({ metric: 'uptime', value: 99.8 })
    };
  }
}

// API Response types
interface ApiSuccess<T = any> {
  success: true;
  data: T;
  message: string;
  timestamp: string;
}

interface ApiError {
  success: false;
  error: {
    message: string;
    code: number;
    details: string;
  };
  timestamp: string;
}

interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  pages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

interface PaginatedResponse<T = any> {
  items: T[];
  pagination: PaginationMeta;
}

/**
 * API Response Factory - DRY API response data
 */
class ApiResponseFactory extends BaseFactory {
  static success<T = any>(data: T = {} as T): ApiSuccess<T> {
    return {
      success: true,
      data,
      message: 'Operation completed successfully',
      timestamp: new Date().toISOString()
    };
  }

  static error(message: string = 'An error occurred', code: number = 400): ApiError {
    return {
      success: false,
      error: {
        message,
        code,
        details: faker.lorem.sentence()
      },
      timestamp: new Date().toISOString()
    };
  }

  static paginated<T = any>(items: T[], page: number = 1, limit: number = 10): ApiSuccess<PaginatedResponse<T>> {
    const total = items.length;
    const pages = Math.ceil(total / limit);
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;

    return this.success({
      items: items.slice(startIndex, endIndex),
      pagination: {
        page,
        limit,
        total,
        pages,
        hasNext: page < pages,
        hasPrev: page > 1
      }
    });
  }
}

// Export all factories using ES modules
export const factories = {
  User: UserFactory,
  Tenant: TenantFactory,
  Customer: CustomerFactory,
  Subscription: SubscriptionFactory,
  Ticket: TicketFactory,
  Comment: CommentFactory,
  Analytics: AnalyticsFactory,
  ApiResponse: ApiResponseFactory
};

// Quick access functions for common patterns
export const createMockData = {
  user: (overrides?: Record<string, any>): User => UserFactory.build(overrides),
  admin: (overrides?: Record<string, any>): User => UserFactory.admin(overrides),
  customer: (overrides?: Record<string, any>): Customer => CustomerFactory.build(overrides),
  tenant: (overrides?: Record<string, any>): Tenant => TenantFactory.build(overrides),
  ticket: (overrides?: Record<string, any>): Ticket => TicketFactory.build(overrides),

  // Bulk data generation
  customers: (count: number = 10): Customer[] => CustomerFactory.buildList(count),
  tickets: (count: number = 5): Ticket[] => TicketFactory.buildList(count),
  users: (count: number = 5): User[] => UserFactory.buildList(count)
};

// Export individual factories
export {
  UserFactory,
  TenantFactory,
  CustomerFactory,
  SubscriptionFactory,
  TicketFactory,
  CommentFactory,
  AnalyticsFactory,
  ApiResponseFactory
};

// Export types for use in tests
export type {
  User,
  Tenant,
  Customer,
  Subscription,
  Ticket,
  Comment,
  Analytics,
  ApiSuccess,
  ApiError,
  PaginatedResponse
};
