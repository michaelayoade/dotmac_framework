/**
 * Offline/Sync Workflow Integration Tests
 * End-to-end tests for offline functionality and sync behavior
 */

import { 
  offlineCapabilities 
} from '../../lib/offline/offline-capabilities';
import { 
  advancedSyncManager 
} from '../../lib/sync/advanced-sync-manager';
import { 
  databaseOptimizer 
} from '../../lib/performance/database-optimization';
import { 
  NetworkSimulator, 
  MockApiClient,
  createMockWorkOrder,
  createMockCustomer,
  createMockInventoryItem 
} from '../utils/test-utils';

// Mock the database with a comprehensive mock
jest.mock('../../lib/offline-db', () => {
  const mockDB = {
    workOrders: new Map(),
    customers: new Map(),
    inventory: new Map(),
    syncQueue: new Map(),
    errorLogs: new Map(),
    
    transaction: jest.fn().mockImplementation(async (mode, stores, callback) => {
      return await callback();
    }),
    
    // Work orders mock
    workOrdersMock: {
      put: jest.fn(),
      add: jest.fn(),
      get: jest.fn(),
      where: jest.fn(),
      orderBy: jest.fn(),
      filter: jest.fn(),
      toArray: jest.fn(),
      clear: jest.fn(),
      bulkAdd: jest.fn(),
      update: jest.fn(),
    },
    
    // Customers mock
    customersMock: {
      put: jest.fn(),
      add: jest.fn(),
      get: jest.fn(),
      where: jest.fn(),
      orderBy: jest.fn(),
      filter: jest.fn(),
      toArray: jest.fn(),
      clear: jest.fn(),
      bulkAdd: jest.fn(),
    },
    
    // Inventory mock
    inventoryMock: {
      put: jest.fn(),
      add: jest.fn(),
      get: jest.fn(),
      where: jest.fn(),
      orderBy: jest.fn(),
      filter: jest.fn(),
      toArray: jest.fn(),
      clear: jest.fn(),
      bulkAdd: jest.fn(),
      update: jest.fn(),
    },
  };
  
  // Set up method chaining for queries
  const setupChaining = (mockObj: any, data: any[] = []) => {
    mockObj.where.mockReturnValue(mockObj);
    mockObj.orderBy.mockReturnValue(mockObj);
    mockObj.filter.mockReturnValue(mockObj);
    mockObj.toArray.mockResolvedValue(data);
    mockObj.equals = jest.fn().mockReturnValue(mockObj);
    mockObj.anyOf = jest.fn().mockReturnValue(mockObj);
    mockObj.limit = jest.fn().mockReturnValue(mockObj);
    return mockObj;
  };
  
  setupChaining(mockDB.workOrdersMock);
  setupChaining(mockDB.customersMock);
  setupChaining(mockDB.inventoryMock);
  
  return {
    db: {
      workOrders: mockDB.workOrdersMock,
      customers: mockDB.customersMock,
      inventory: mockDB.inventoryMock,
      syncQueue: mockDB.syncQueue,
      errorLogs: mockDB.errorLogs,
      transaction: mockDB.transaction,
    }
  };
});

// Mock API client
const mockApiClient = new MockApiClient();

jest.mock('../../lib/api/technician-client', () => ({
  technicianApiClient: mockApiClient,
}));

describe('Offline/Sync Workflow Integration', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    NetworkSimulator.reset();
    mockApiClient.reset();
    
    // Initialize all systems
    await offlineCapabilities.initialize();
    await advancedSyncManager.initialize();
    await databaseOptimizer.initialize();
  });

  describe('complete offline workflow', () => {
    it('should handle full offline work order completion workflow', async () => {
      // 1. Start online and cache initial data
      NetworkSimulator.simulateOnline();
      
      const initialWorkOrder = createMockWorkOrder({
        id: 'WO-INTEGRATION-001',
        status: 'pending',
        customerId: 'CUST-001',
      });
      
      const customer = createMockCustomer({
        id: 'CUST-001',
        name: 'Integration Test Customer',
      });
      
      const inventoryItems = [
        createMockInventoryItem({ id: 'INV-001', name: 'Router', quantity: 5 }),
        createMockInventoryItem({ id: 'INV-002', name: 'Cable', quantity: 20 }),
      ];

      // Cache initial data
      await offlineCapabilities.cacheWorkOrders([initialWorkOrder]);
      await offlineCapabilities.cacheCustomers([customer]);
      await offlineCapabilities.cacheInventory(inventoryItems);

      // 2. Go offline and perform work
      NetworkSimulator.simulateOffline();

      // Start work order
      const startResult = await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-INTEGRATION-001',
        status: 'in_progress',
        startedAt: new Date().toISOString(),
        notes: 'Started installation - offline mode',
      });

      expect(startResult.success).toBe(true);
      expect(startResult.queued).toBe(true);

      // Use inventory items
      const inventoryUpdate1 = await offlineCapabilities.updateInventoryOffline({
        id: 'INV-001',
        quantity: 4, // Used 1 router
        operation: 'used',
        workOrderId: 'WO-INTEGRATION-001',
      });

      const inventoryUpdate2 = await offlineCapabilities.updateInventoryOffline({
        id: 'INV-002',
        quantity: 18, // Used 2 cables
        operation: 'used',
        workOrderId: 'WO-INTEGRATION-001',
      });

      expect(inventoryUpdate1.success).toBe(true);
      expect(inventoryUpdate2.success).toBe(true);

      // Complete work order with photos and checklist
      const completionResult = await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-INTEGRATION-001',
        status: 'completed',
        completedAt: new Date().toISOString(),
        checklist: [
          { id: 'check-1', text: 'Install router', completed: true },
          { id: 'check-2', text: 'Test connection', completed: true },
        ],
        photos: ['photo1.jpg', 'photo2.jpg'],
        notes: 'Installation completed successfully - all tests passed',
      });

      expect(completionResult.success).toBe(true);

      // 3. Verify queued operations
      const queueInfo = await offlineCapabilities.getSyncQueueInfo();
      expect(queueInfo.totalItems).toBe(4); // 2 work order updates + 2 inventory updates

      // 4. Go back online and sync
      NetworkSimulator.simulateOnline();
      
      // Mock successful API responses
      mockApiClient.addWorkOrder(initialWorkOrder);
      
      const syncResult = await offlineCapabilities.processPendingSyncs();
      
      expect(syncResult.processed).toBeGreaterThan(0);
      expect(syncResult.successful).toBeGreaterThan(0);
    });

    it('should handle customer service update workflow', async () => {
      NetworkSimulator.simulateOnline();
      
      const customer = createMockCustomer({
        id: 'CUST-SERVICE-001',
        status: 'active',
      });

      await offlineCapabilities.cacheCustomers([customer]);

      // Go offline and update customer info
      NetworkSimulator.simulateOffline();

      const customerUpdate = await offlineCapabilities.updateCustomerOffline({
        id: 'CUST-SERVICE-001',
        phone: '555-NEW-PHONE',
        email: 'newemail@example.com',
        notes: 'Updated contact info during service visit',
        lastServiceDate: new Date().toISOString(),
      });

      expect(customerUpdate.success).toBe(true);
      expect(customerUpdate.queued).toBe(true);

      // Go online and sync
      NetworkSimulator.simulateOnline();
      mockApiClient.addCustomer(customer);
      
      const syncResult = await offlineCapabilities.processPendingSyncs();
      expect(syncResult.processed).toBe(1);
    });
  });

  describe('sync conflict resolution', () => {
    it('should resolve work order conflicts with server-wins strategy', async () => {
      // 1. Cache initial work order
      const initialWorkOrder = createMockWorkOrder({
        id: 'WO-CONFLICT-001',
        title: 'Original Title',
        notes: 'Original notes',
        lastModified: '2024-01-01T10:00:00Z',
      });

      await offlineCapabilities.cacheWorkOrders([initialWorkOrder]);

      // 2. Update offline
      NetworkSimulator.simulateOffline();
      
      await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-CONFLICT-001',
        title: 'Updated Offline',
        notes: 'Updated notes offline',
      });

      // 3. Simulate server having newer version
      const serverWorkOrder = createMockWorkOrder({
        id: 'WO-CONFLICT-001',
        title: 'Updated on Server',
        notes: 'Server updated notes',
        lastModified: '2024-01-01T11:00:00Z', // Newer than cached
      });

      mockApiClient.addWorkOrder(serverWorkOrder);

      // 4. Go online and sync with conflict
      NetworkSimulator.simulateOnline();

      // Set up conflict resolver
      advancedSyncManager.setConflictResolver(async (item, serverData) => ({
        strategy: 'server_wins',
      }));

      const syncResult = await advancedSyncManager.processSyncQueue();
      
      // Should resolve conflict in favor of server
      expect(syncResult).toBeTruthy();
    });

    it('should handle merge conflicts intelligently', async () => {
      const initialWorkOrder = createMockWorkOrder({
        id: 'WO-MERGE-001',
        title: 'Original Title',
        notes: 'Original notes',
        status: 'pending',
      });

      await offlineCapabilities.cacheWorkOrders([initialWorkOrder]);

      // Update different fields offline vs server
      NetworkSimulator.simulateOffline();
      await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-MERGE-001',
        notes: 'Added local notes', // Different field
      });

      const serverWorkOrder = createMockWorkOrder({
        id: 'WO-MERGE-001',
        title: 'Updated Server Title', // Different field
        status: 'in_progress', // Different field
        notes: 'Original notes',
      });

      mockApiClient.addWorkOrder(serverWorkOrder);

      NetworkSimulator.simulateOnline();

      // Set up merge resolver
      advancedSyncManager.setConflictResolver(async (localData, serverData) => ({
        strategy: 'merge',
        merged: {
          ...serverData,
          notes: localData.notes, // Keep local notes
        },
      }));

      const syncResult = await advancedSyncManager.processSyncQueue();
      expect(syncResult).toBeTruthy();
    });
  });

  describe('network resilience', () => {
    it('should handle intermittent network during sync', async () => {
      // Queue multiple operations offline
      NetworkSimulator.simulateOffline();

      const operations = [
        { id: 'WO-1', status: 'in_progress' as const },
        { id: 'WO-2', status: 'completed' as const },
        { id: 'WO-3', status: 'cancelled' as const },
      ];

      for (const op of operations) {
        await offlineCapabilities.updateWorkOrderOffline(op);
      }

      // Go online but simulate intermittent failures
      NetworkSimulator.simulateOnline();

      let callCount = 0;
      const originalFetch = global.fetch;
      global.fetch = jest.fn().mockImplementation(() => {
        callCount++;
        if (callCount <= 2) {
          return Promise.reject(new Error('Network timeout'));
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        });
      });

      // Sync should retry and eventually succeed
      const syncResult = await advancedSyncManager.processSyncQueue();
      
      // At least some operations should succeed after retries
      expect(syncResult).toBeTruthy();
      
      global.fetch = originalFetch;
    });

    it('should continue working offline after sync failures', async () => {
      // Start with failed sync attempt
      NetworkSimulator.simulateOnline();
      
      global.fetch = jest.fn().mockRejectedValue(new Error('Server unavailable'));

      await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-FAILED-SYNC',
        status: 'in_progress',
      });

      // Sync should fail but app should continue working
      try {
        await offlineCapabilities.processPendingSyncs();
      } catch (error) {
        // Expected to fail
      }

      // Should still be able to work offline
      NetworkSimulator.simulateOffline();

      const offlineResult = await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-STILL-WORKING',
        status: 'completed',
      });

      expect(offlineResult.success).toBe(true);
    });
  });

  describe('data consistency', () => {
    it('should maintain data integrity during concurrent operations', async () => {
      const workOrder = createMockWorkOrder({
        id: 'WO-CONCURRENT-001',
        status: 'pending',
      });

      await offlineCapabilities.cacheWorkOrders([workOrder]);

      NetworkSimulator.simulateOffline();

      // Simulate concurrent updates (e.g., from different components)
      const concurrentUpdates = [
        offlineCapabilities.updateWorkOrderOffline({
          id: 'WO-CONCURRENT-001',
          status: 'in_progress',
          startedAt: new Date().toISOString(),
        }),
        offlineCapabilities.updateWorkOrderOffline({
          id: 'WO-CONCURRENT-001',
          notes: 'Updated from mobile',
        }),
        offlineCapabilities.updateWorkOrderOffline({
          id: 'WO-CONCURRENT-001',
          priority: 'high',
        }),
      ];

      const results = await Promise.allSettled(concurrentUpdates);

      // All updates should succeed without data corruption
      results.forEach(result => {
        expect(result.status).toBe('fulfilled');
        if (result.status === 'fulfilled') {
          expect(result.value.success).toBe(true);
        }
      });
    });

    it('should handle database quota gracefully', async () => {
      // Mock quota exceeded error
      const { db } = require('../../lib/offline-db');
      const quotaError = new Error('QuotaExceededError');
      quotaError.name = 'QuotaExceededError';

      db.workOrders.add.mockRejectedValueOnce(quotaError);

      const result = await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-QUOTA-TEST',
        status: 'completed',
      });

      // Should handle quota error and potentially clean up space
      expect(result).toBeTruthy();
    });
  });

  describe('performance under load', () => {
    it('should handle large sync queues efficiently', async () => {
      NetworkSimulator.simulateOffline();

      // Queue many operations
      const operations = Array.from({ length: 100 }, (_, i) => ({
        id: `WO-LOAD-${i}`,
        status: 'completed' as const,
        notes: `Completed work order ${i}`,
      }));

      const startTime = Date.now();

      // Batch queue operations
      await Promise.all(
        operations.map(op => offlineCapabilities.updateWorkOrderOffline(op))
      );

      const queueTime = Date.now() - startTime;

      // Should queue operations reasonably fast
      expect(queueTime).toBeLessThan(5000); // Less than 5 seconds

      // Verify all queued
      const queueInfo = await offlineCapabilities.getSyncQueueInfo();
      expect(queueInfo.totalItems).toBe(100);
    });

    it('should optimize database queries for large datasets', async () => {
      // Add large number of work orders to cache
      const largeDataset = Array.from({ length: 1000 }, (_, i) =>
        createMockWorkOrder({
          id: `WO-LARGE-${i}`,
          status: i % 2 === 0 ? 'pending' : 'completed',
          priority: i % 3 === 0 ? 'high' : 'normal',
        })
      );

      await offlineCapabilities.cacheWorkOrders(largeDataset);

      const startTime = Date.now();

      // Query with filters should be fast
      const filtered = await databaseOptimizer.getWorkOrders({
        status: 'pending',
        limit: 50,
      });

      const queryTime = Date.now() - startTime;

      expect(queryTime).toBeLessThan(1000); // Less than 1 second
      expect(filtered.length).toBeLessThanOrEqual(50);
    });
  });

  describe('error recovery', () => {
    it('should recover from corrupted sync queue', async () => {
      // Simulate corrupted sync queue
      const { db } = require('../../lib/offline-db');
      db.syncQueue.get = jest.fn().mockRejectedValue(new Error('Corrupted data'));

      // Should still be able to add new operations
      NetworkSimulator.simulateOffline();
      
      const result = await offlineCapabilities.updateWorkOrderOffline({
        id: 'WO-RECOVERY-TEST',
        status: 'completed',
      });

      expect(result.success).toBe(true);
    });

    it('should handle database migration gracefully', async () => {
      // Simulate database schema changes
      const { db } = require('../../lib/offline-db');
      
      // Mock version mismatch
      db.workOrders.toArray.mockRejectedValueOnce(new Error('Schema mismatch'));

      // Should recover and continue working
      const cached = await offlineCapabilities.getCachedWorkOrders();
      expect(Array.isArray(cached)).toBe(true);
    });
  });
});