/**
 * Test Data Factory
 * Generates consistent test data for automated tests
 */

import { faker } from '@faker-js/faker';

export interface CustomerData {
  email: string;
  password: string;
  name: string;
  companyName: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  plan: string;
}

export interface UserData {
  email: string;
  password: string;
  name: string;
  role: string;
  department?: string;
}

export interface DeviceData {
  name: string;
  ip: string;
  type: string;
  location: string;
  macAddress?: string;
  firmwareVersion?: string;
}

export interface InvoiceData {
  amount: string;
  description: string;
  dueDate: string;
  items: Array<{
    description: string;
    quantity: number;
    unitPrice: string;
  }>;
}

export class DataFactory {
  private seed: number = 12345;

  constructor() {
    faker.seed(this.seed);
  }

  // Customer Data Generation
  generateCustomerData(): CustomerData {
    const firstName = faker.person.firstName();
    const lastName = faker.person.lastName();
    const companyName = faker.company.name();

    return {
      email: faker.internet.email({ firstName, lastName }).toLowerCase(),
      password: 'TestPassword123!',
      name: `${firstName} ${lastName}`,
      companyName,
      phone: faker.phone.number(),
      address: faker.location.streetAddress(),
      city: faker.location.city(),
      state: faker.location.stateAbbr(),
      zipCode: faker.location.zipCode(),
      plan: faker.helpers.arrayElement(['starter', 'professional', 'enterprise'])
    };
  }

  generateMultipleCustomers(count: number): CustomerData[] {
    return Array.from({ length: count }, () => this.generateCustomerData());
  }

  // User Data Generation
  generateUserData(): UserData {
    const firstName = faker.person.firstName();
    const lastName = faker.person.lastName();

    return {
      email: faker.internet.email({ firstName, lastName }).toLowerCase(),
      password: 'UserPassword123!',
      name: `${firstName} ${lastName}`,
      role: faker.helpers.arrayElement(['admin', 'user', 'manager', 'support']),
      department: faker.commerce.department()
    };
  }

  generateMultipleUsers(count: number): UserData[] {
    return Array.from({ length: count }, () => this.generateUserData());
  }

  // Device Data Generation
  generateDeviceData(): DeviceData {
    const deviceTypes = ['router', 'switch', 'access_point', 'firewall', 'server'];
    const deviceType = faker.helpers.arrayElement(deviceTypes);

    return {
      name: `${faker.commerce.productName()} ${deviceType}`,
      ip: faker.internet.ip(),
      type: deviceType,
      location: `${faker.location.city()}, ${faker.location.stateAbbr()}`,
      macAddress: faker.internet.mac(),
      firmwareVersion: `v${faker.number.int({ min: 1, max: 5 })}.${faker.number.int({ min: 0, max: 9 })}.${faker.number.int({ min: 0, max: 9 })}`
    };
  }

  generateMultipleDevices(count: number): DeviceData[] {
    return Array.from({ length: count }, () => this.generateDeviceData());
  }

  // Network Data Generation
  generateNetworkData(): {
    subnet: string;
    gateway: string;
    dnsServers: string[];
    vlanId: number;
  } {
    return {
      subnet: `${faker.internet.ip()}/24`,
      gateway: faker.internet.ip(),
      dnsServers: [
        faker.internet.ip(),
        faker.internet.ip()
      ],
      vlanId: faker.number.int({ min: 1, max: 4094 })
    };
  }

  // Billing Data Generation
  generateInvoiceData(): InvoiceData {
    const itemCount = faker.number.int({ min: 1, max: 5 });
    const items = Array.from({ length: itemCount }, () => ({
      description: faker.commerce.productDescription(),
      quantity: faker.number.int({ min: 1, max: 10 }),
      unitPrice: `$${faker.number.int({ min: 10, max: 500 })}`
    }));

    const totalAmount = items.reduce((sum, item) => {
      const price = parseFloat(item.unitPrice.replace('$', ''));
      return sum + (price * item.quantity);
    }, 0);

    return {
      amount: `$${totalAmount.toFixed(2)}`,
      description: `Invoice for ${faker.company.name()}`,
      dueDate: faker.date.future().toISOString().split('T')[0],
      items
    };
  }

  // Support Ticket Data Generation
  generateTicketData(): {
    subject: string;
    description: string;
    category: string;
    priority: string;
    tags: string[];
  } {
    const categories = ['technical', 'billing', 'general', 'feature_request'];
    const priorities = ['low', 'medium', 'high', 'urgent'];

    return {
      subject: faker.lorem.sentence(),
      description: faker.lorem.paragraphs(2),
      category: faker.helpers.arrayElement(categories),
      priority: faker.helpers.arrayElement(priorities),
      tags: faker.helpers.arrayElements(
        ['urgent', 'vip', 'follow-up', 'escalated', 'resolved'],
        faker.number.int({ min: 0, max: 3 })
      )
    };
  }

  // Performance Data Generation
  generatePerformanceData(): {
    cpuUsage: number;
    memoryUsage: number;
    diskUsage: number;
    networkIn: number;
    networkOut: number;
    uptime: number;
  } {
    return {
      cpuUsage: faker.number.int({ min: 0, max: 100 }),
      memoryUsage: faker.number.int({ min: 0, max: 100 }),
      diskUsage: faker.number.int({ min: 0, max: 100 }),
      networkIn: faker.number.int({ min: 0, max: 1000000 }), // bytes
      networkOut: faker.number.int({ min: 0, max: 1000000 }), // bytes
      uptime: faker.number.int({ min: 0, max: 31536000 }) // seconds (1 year)
    };
  }

  // Form Data Generation
  generateFormData(): {
    textField: string;
    emailField: string;
    numberField: number;
    selectField: string;
    checkboxField: boolean;
    dateField: string;
  } {
    return {
      textField: faker.lorem.sentence(),
      emailField: faker.internet.email(),
      numberField: faker.number.int({ min: 1, max: 1000 }),
      selectField: faker.helpers.arrayElement(['option1', 'option2', 'option3']),
      checkboxField: faker.datatype.boolean(),
      dateField: faker.date.future().toISOString().split('T')[0]
    };
  }

  // Error Data Generation
  generateErrorData(): {
    code: string;
    message: string;
    details: Record<string, any>;
    timestamp: string;
  } {
    const errorCodes = ['VALIDATION_ERROR', 'NOT_FOUND', 'PERMISSION_DENIED', 'INTERNAL_ERROR'];
    const errorMessages = [
      'Invalid input provided',
      'Resource not found',
      'Access denied',
      'Internal server error occurred'
    ];

    return {
      code: faker.helpers.arrayElement(errorCodes),
      message: faker.helpers.arrayElement(errorMessages),
      details: {
        field: faker.lorem.word(),
        value: faker.lorem.word(),
        reason: faker.lorem.sentence()
      },
      timestamp: faker.date.recent().toISOString()
    };
  }

  // Bulk Data Generation
  generateBulkData(type: 'customers' | 'users' | 'devices', count: number): any[] {
    switch (type) {
      case 'customers':
        return this.generateMultipleCustomers(count);
      case 'users':
        return this.generateMultipleUsers(count);
      case 'devices':
        return this.generateMultipleDevices(count);
      default:
        throw new Error(`Unknown data type: ${type}`);
    }
  }

  // Seeded Generation for Consistency
  setSeed(seed: number): void {
    this.seed = seed;
    faker.seed(seed);
  }

  resetSeed(): void {
    faker.seed(this.seed);
  }

  // Utility Methods
  generateId(prefix: string = 'test'): string {
    return `${prefix}_${Date.now()}_${faker.string.alphanumeric(6)}`;
  }

  generateTimestamp(): string {
    return faker.date.recent().toISOString();
  }

  generateUUID(): string {
    return faker.string.uuid();
  }

  generateRandomString(length: number = 10): string {
    return faker.string.alphanumeric(length);
  }

  generateRandomNumber(min: number = 0, max: number = 100): number {
    return faker.number.int({ min, max });
  }

  generateBoolean(): boolean {
    return faker.datatype.boolean();
  }

  generateURL(): string {
    return faker.internet.url();
  }

  generateIPAddress(): string {
    return faker.internet.ip();
  }
}
