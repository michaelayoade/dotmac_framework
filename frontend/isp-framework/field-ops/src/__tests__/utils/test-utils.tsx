/**
 * Testing Utilities
 * Comprehensive utilities for testing React components and application logic
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
// Note: QueryClient would be imported if using react-query
// import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Import application types and utilities
import type { WorkOrder, Customer, InventoryItem, TechnicianProfile } from '../../lib/offline-db';

// Test wrapper component that provides all necessary contexts
interface AllTheProvidersProps {
  children: React.ReactNode;
}

function AllTheProviders({ children }: AllTheProvidersProps) {
  // For now, just return children wrapped in a div
  // In the future, this would include QueryClient, AuthProvider, etc.
  return <div data-testid='test-provider'>{children}</div>;
}

// Custom render function that includes providers
const customRender = (ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) =>
  render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything from RTL
export * from '@testing-library/react';
export { customRender as render };
export { userEvent };

// Custom testing utilities

/**
 * Wait for element to appear with better error messages
 */
export async function waitForElementToAppear(
  query: () => HTMLElement | null,
  timeout = 5000
): Promise<HTMLElement> {
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    const checkForElement = () => {
      const element = query();

      if (element) {
        resolve(element);
        return;
      }

      if (Date.now() - startTime >= timeout) {
        reject(new Error(`Element did not appear within ${timeout}ms`));
        return;
      }

      setTimeout(checkForElement, 100);
    };

    checkForElement();
  });
}

/**
 * Mock IndexedDB operations
 */
export class MockIndexedDB {
  private stores: Map<string, Map<string, any>> = new Map();

  constructor() {
    this.stores.set('workOrders', new Map());
    this.stores.set('customers', new Map());
    this.stores.set('inventory', new Map());
    this.stores.set('profile', new Map());
    this.stores.set('syncQueue', new Map());
    this.stores.set('settings', new Map());
  }

  getStore(storeName: string): Map<string, any> {
    if (!this.stores.has(storeName)) {
      this.stores.set(storeName, new Map());
    }
    return this.stores.get(storeName)!;
  }

  async put(storeName: string, key: string, value: any): Promise<void> {
    const store = this.getStore(storeName);
    store.set(key, { ...value, id: key });
  }

  async get(storeName: string, key: string): Promise<any> {
    const store = this.getStore(storeName);
    return store.get(key) || null;
  }

  async getAll(storeName: string): Promise<any[]> {
    const store = this.getStore(storeName);
    return Array.from(store.values());
  }

  async delete(storeName: string, key: string): Promise<void> {
    const store = this.getStore(storeName);
    store.delete(key);
  }

  async clear(storeName: string): Promise<void> {
    const store = this.getStore(storeName);
    store.clear();
  }

  async count(storeName: string): Promise<number> {
    const store = this.getStore(storeName);
    return store.size;
  }

  // Simulate transaction
  async transaction(
    storeNames: string[],
    mode: 'readonly' | 'readwrite',
    callback: () => Promise<any>
  ): Promise<any> {
    return callback();
  }

  // Bulk operations
  async bulkAdd(storeName: string, items: any[]): Promise<void> {
    const store = this.getStore(storeName);
    items.forEach((item) => {
      const id = item.id || `item_${Date.now()}_${Math.random()}`;
      store.set(id, { ...item, id });
    });
  }

  async bulkPut(storeName: string, items: any[]): Promise<void> {
    return this.bulkAdd(storeName, items);
  }
}

/**
 * Create mock work order data
 */
export function createMockWorkOrder(overrides?: Partial<WorkOrder>): WorkOrder {
  const baseWorkOrder: WorkOrder = {
    id: `WO-TEST-${Math.random().toString(36).substr(2, 9)}`,
    customerId: 'CUST-TEST-001',
    technicianId: 'TECH-TEST-001',
    title: 'Test Installation',
    description: 'Test work order for unit testing',
    priority: 'normal',
    status: 'pending',
    scheduledDate: new Date().toISOString(),
    assignedAt: new Date().toISOString(),
    location: {
      address: '123 Test Street, Test City, TC 12345',
      coordinates: [40.7128, -74.006],
      apartment: 'Apt 1A',
      accessNotes: 'Ring doorbell',
    },
    customer: {
      name: 'Test Customer',
      phone: '555-0123',
      email: 'test@example.com',
      serviceId: 'SRV-TEST-001',
    },
    equipment: {
      type: 'router',
      model: 'Test Model X1',
      required: ['Router', 'Cables', 'Modem'],
    },
    checklist: [
      {
        id: 'check-1',
        text: 'Verify equipment',
        completed: false,
        required: true,
      },
      {
        id: 'check-2',
        text: 'Test connection',
        completed: false,
        required: true,
      },
    ],
    photos: [],
    notes: 'Test work order notes',
    syncStatus: 'synced',
    lastModified: new Date().toISOString(),
  };

  return { ...baseWorkOrder, ...overrides };
}

/**
 * Create mock customer data
 */
export function createMockCustomer(overrides?: Partial<Customer>): Customer {
  const baseCustomer: Customer = {
    id: `CUST-TEST-${Math.random().toString(36).substr(2, 9)}`,
    name: 'Test Customer',
    email: 'test@example.com',
    phone: '555-0123',
    address: '123 Test Street, Test City, TC 12345',
    coordinates: [40.7128, -74.006],
    serviceId: 'SRV-TEST-001',
    planName: 'Premium Plan',
    planSpeed: '100 Mbps',
    status: 'active',
    installDate: new Date('2024-01-01').toISOString(),
    serviceHistory: [
      {
        id: 'SH-TEST-001',
        date: new Date('2024-01-01').toISOString(),
        type: 'installation',
        description: 'Initial installation',
        technicianId: 'TECH-TEST-001',
        technicianName: 'Test Technician',
        status: 'completed',
      },
    ],
    notes: 'Test customer notes',
    syncStatus: 'synced',
    lastModified: new Date().toISOString(),
  };

  return { ...baseCustomer, ...overrides };
}

/**
 * Create mock inventory item data
 */
export function createMockInventoryItem(overrides?: Partial<InventoryItem>): InventoryItem {
  const baseItem: InventoryItem = {
    id: `INV-TEST-${Math.random().toString(36).substr(2, 9)}`,
    name: 'Test Router Model X1',
    category: 'networking',
    sku: 'TEST-RTR-X1',
    barcode: '123456789012',
    description: 'High-performance test router for residential use',
    quantity: 10,
    unitPrice: 199.99,
    location: 'Warehouse A-1',
    supplier: 'Test Supplier Inc.',
    lastRestocked: new Date('2024-01-15').toISOString(),
    minStock: 5,
    maxStock: 50,
    reserved: 2,
    syncStatus: 'synced',
    lastModified: new Date().toISOString(),
  };

  return { ...baseItem, ...overrides };
}

/**
 * Create mock technician profile data
 */
export function createMockTechnicianProfile(
  overrides?: Partial<TechnicianProfile>
): TechnicianProfile {
  const baseProfile: TechnicianProfile = {
    id: `TECH-TEST-${Math.random().toString(36).substr(2, 9)}`,
    name: 'Test Technician',
    email: 'technician@test.com',
    phone: '555-0456',
    employeeId: 'EMP-TEST-001',
    role: 'Senior Technician',
    department: 'Field Operations',
    skills: ['Installation', 'Troubleshooting', 'Customer Service'],
    certifications: [
      {
        name: 'Network+ Certification',
        issuer: 'CompTIA',
        issueDate: '2023-01-01',
        expiryDate: '2026-01-01',
        certificateId: 'CERT-TEST-001',
      },
    ],
    territory: {
      name: 'Test Territory North',
      boundaries: [
        [40.7, -74.02],
        [40.72, -74.02],
        [40.72, -73.98],
        [40.7, -73.98],
      ],
    },
    schedule: {
      workingHours: {
        start: '08:00',
        end: '17:00',
      },
      workingDays: [1, 2, 3, 4, 5], // Monday to Friday
    },
    vehicle: {
      make: 'Ford',
      model: 'Transit',
      year: 2022,
      licensePlate: 'TEST-123',
    },
    syncStatus: 'synced',
    lastModified: new Date().toISOString(),
  };

  return { ...baseProfile, ...overrides };
}

/**
 * Mock API responses
 */
export class MockApiClient {
  private workOrders: WorkOrder[] = [];
  private customers: Customer[] = [];
  private inventory: InventoryItem[] = [];

  constructor() {
    // Initialize with some default data
    this.workOrders = [
      createMockWorkOrder({ status: 'pending' }),
      createMockWorkOrder({ status: 'in_progress' }),
      createMockWorkOrder({ status: 'completed' }),
    ];

    this.customers = [createMockCustomer(), createMockCustomer({ status: 'suspended' })];

    this.inventory = [
      createMockInventoryItem({ quantity: 10 }),
      createMockInventoryItem({ quantity: 0, category: 'cables' }),
      createMockInventoryItem({ quantity: 2, minStock: 5, category: 'modems' }),
    ];
  }

  // Work Order API
  async getWorkOrders(filters?: any) {
    let filtered = [...this.workOrders];

    if (filters?.status) {
      filtered = filtered.filter((wo) => wo.status === filters.status);
    }

    return { success: true, data: filtered };
  }

  async getWorkOrder(id: string) {
    const workOrder = this.workOrders.find((wo) => wo.id === id);
    return { success: !!workOrder, data: workOrder };
  }

  async updateWorkOrder(id: string, updates: Partial<WorkOrder>) {
    const index = this.workOrders.findIndex((wo) => wo.id === id);
    if (index >= 0) {
      this.workOrders[index] = { ...this.workOrders[index], ...updates };
      return { success: true, data: this.workOrders[index] };
    }
    return { success: false, message: 'Work order not found' };
  }

  // Customer API
  async getCustomer(id: string) {
    const customer = this.customers.find((c) => c.id === id);
    return { success: !!customer, data: customer };
  }

  // Inventory API
  async getInventory() {
    return { success: true, data: [...this.inventory] };
  }

  async updateInventoryQuantity(id: string, quantityChange: number) {
    const index = this.inventory.findIndex((item) => item.id === id);
    if (index >= 0) {
      this.inventory[index].quantity += quantityChange;
      return { success: true, data: this.inventory[index] };
    }
    return { success: false, message: 'Inventory item not found' };
  }

  // Utility methods for testing
  addWorkOrder(workOrder: WorkOrder) {
    this.workOrders.push(workOrder);
  }

  addCustomer(customer: Customer) {
    this.customers.push(customer);
  }

  addInventoryItem(item: InventoryItem) {
    this.inventory.push(item);
  }

  reset() {
    this.workOrders = [];
    this.customers = [];
    this.inventory = [];
  }
}

/**
 * Performance testing utilities
 */
export class PerformanceTester {
  private startTime: number = 0;
  private endTime: number = 0;

  start(): void {
    this.startTime = performance.now();
  }

  end(): number {
    this.endTime = performance.now();
    return this.endTime - this.startTime;
  }

  async measureAsync<T>(operation: () => Promise<T>): Promise<{ result: T; duration: number }> {
    this.start();
    const result = await operation();
    const duration = this.end();
    return { result, duration };
  }

  measureSync<T>(operation: () => T): { result: T; duration: number } {
    this.start();
    const result = operation();
    const duration = this.end();
    return { result, duration };
  }

  async measureRender(
    component: ReactElement
  ): Promise<{ duration: number; element: HTMLElement }> {
    this.start();
    const { container } = render(component);
    await waitFor(() => container.firstChild);
    const duration = this.end();
    return { duration, element: container.firstChild as HTMLElement };
  }
}

/**
 * Accessibility testing utilities
 */
export async function expectAccessible(element: HTMLElement): Promise<void> {
  // Basic accessibility checks
  const interactiveElements = element.querySelectorAll('button, a, input, select, textarea');

  interactiveElements.forEach((el) => {
    const htmlEl = el as HTMLElement;

    // Check for accessible names
    const hasAccessibleName =
      htmlEl.getAttribute('aria-label') ||
      htmlEl.getAttribute('aria-labelledby') ||
      htmlEl.textContent?.trim() ||
      (htmlEl.tagName === 'INPUT' && htmlEl.getAttribute('placeholder'));

    if (!hasAccessibleName) {
      throw new Error(
        `Interactive element missing accessible name: ${htmlEl.outerHTML.slice(0, 100)}...`
      );
    }

    // Check for proper contrast (simplified check)
    const styles = window.getComputedStyle(htmlEl);
    if (styles.color === styles.backgroundColor) {
      throw new Error(`Poor contrast detected on element: ${htmlEl.outerHTML.slice(0, 100)}...`);
    }
  });
}

/**
 * Network condition simulation
 */
export class NetworkSimulator {
  static simulateOffline(): void {
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: false,
    });

    // Trigger offline event
    window.dispatchEvent(new Event('offline'));
  }

  static simulateOnline(): void {
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });

    // Trigger online event
    window.dispatchEvent(new Event('online'));
  }

  static simulateSlowConnection(): void {
    Object.defineProperty(navigator, 'connection', {
      writable: true,
      value: {
        effectiveType: '2g',
        downlink: 0.5,
        rtt: 2000,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      },
    });
  }

  static simulateFastConnection(): void {
    Object.defineProperty(navigator, 'connection', {
      writable: true,
      value: {
        effectiveType: '4g',
        downlink: 10,
        rtt: 50,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      },
    });
  }

  static reset(): void {
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });

    Object.defineProperty(navigator, 'connection', {
      writable: true,
      value: {
        effectiveType: '4g',
        downlink: 10,
        rtt: 50,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      },
    });
  }
}

// Export singleton instances for convenience
export const mockDB = new MockIndexedDB();
export const mockApiClient = new MockApiClient();
export const performanceTester = new PerformanceTester();
export const networkSimulator = NetworkSimulator;
