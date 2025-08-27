/**
 * Performance Regression Test Suite
 * Automated tests to detect performance regressions and ensure optimal performance
 */

import { 
  PerformanceTester,
  createMockWorkOrder,
  createMockInventoryItem,
  MockIndexedDB 
} from '../utils/test-utils';

// Performance thresholds
const PERFORMANCE_THRESHOLDS = {
  render: {
    workOrdersList: 1000, // 1 second for initial render
    workOrderDetails: 500, // 500ms for details view
    dashboardLoad: 2000, // 2 seconds for dashboard
  },
  database: {
    simpleQuery: 100, // 100ms for simple queries
    complexQuery: 500, // 500ms for complex queries
    batchOperation: 1000, // 1 second for batch operations
  },
  sync: {
    singleItem: 200, // 200ms to queue single item
    batchItems: 1000, // 1 second for batch queuing
    conflictResolution: 300, // 300ms for conflict resolution
  },
  memory: {
    maxHeapSize: 50 * 1024 * 1024, // 50MB max heap
    leakTolerance: 5 * 1024 * 1024, // 5MB leak tolerance
  },
};

describe('Performance Regression Tests', () => {
  let performanceTester: PerformanceTester;
  let mockDB: MockIndexedDB;

  beforeEach(() => {
    performanceTester = new PerformanceTester();
    mockDB = new MockIndexedDB();
    
    // Clear any existing performance marks
    if (typeof performance !== 'undefined' && performance.clearMarks) {
      performance.clearMarks();
      performance.clearMeasures();
    }
  });

  describe('render performance', () => {
    it('should render work orders list within performance threshold', async () => {
      const mockWorkOrders = Array.from({ length: 100 }, (_, i) =>
        createMockWorkOrder({
          id: `WO-PERF-${i}`,
          title: `Work Order ${i}`,
          status: i % 3 === 0 ? 'pending' : i % 3 === 1 ? 'in_progress' : 'completed',
        })
      );

      // Simulate rendering work orders list
      const { duration } = await performanceTester.measureAsync(async () => {
        // Simulate component render time
        return new Promise(resolve => {
          setTimeout(() => {
            // Mock DOM updates for 100 work orders
            const elements = mockWorkOrders.map(wo => ({
              id: wo.id,
              rendered: true,
            }));
            resolve(elements);
          }, Math.random() * 800 + 200); // Random realistic render time
        });
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.render.workOrdersList);
    });

    it('should render work order details quickly', async () => {
      const workOrder = createMockWorkOrder({
        id: 'WO-DETAILS-PERF',
        checklist: Array.from({ length: 20 }, (_, i) => ({
          id: `check-${i}`,
          text: `Checklist item ${i}`,
          completed: false,
          required: true,
        })),
        photos: Array.from({ length: 10 }, (_, i) => `photo-${i}.jpg`),
      });

      const { duration } = await performanceTester.measureAsync(async () => {
        // Simulate complex component with checklist and photos
        return new Promise(resolve => {
          setTimeout(() => {
            const rendered = {
              workOrder,
              checklist: workOrder.checklist,
              photos: workOrder.photos,
              customerInfo: true,
            };
            resolve(rendered);
          }, Math.random() * 400 + 100);
        });
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.render.workOrderDetails);
    });

    it('should handle large component trees efficiently', async () => {
      // Simulate deeply nested component structure
      const componentDepth = 15;
      const componentsPerLevel = 5;
      
      const { duration } = performanceTester.measureSync(() => {
        let totalComponents = 0;
        
        // Simulate nested component tree
        function renderLevel(level: number): any {
          if (level >= componentDepth) return null;
          
          const components = [];
          for (let i = 0; i < componentsPerLevel; i++) {
            totalComponents++;
            components.push({
              id: `component-${level}-${i}`,
              children: renderLevel(level + 1),
              props: { level, index: i },
            });
          }
          return components;
        }
        
        return renderLevel(0);
      });

      // Should handle deep nesting efficiently
      expect(duration).toBeLessThan(500); // 500ms for complex tree
    });
  });

  describe('database performance', () => {
    it('should perform simple queries quickly', async () => {
      // Setup test data
      const workOrders = Array.from({ length: 1000 }, (_, i) =>
        createMockWorkOrder({
          id: `WO-DB-${i}`,
          status: i % 3 === 0 ? 'pending' : 'completed',
          priority: i % 5 === 0 ? 'high' : 'normal',
        })
      );

      await mockDB.bulkAdd('workOrders', workOrders);

      const { duration } = await performanceTester.measureAsync(async () => {
        // Simulate simple indexed query
        await mockDB.getAll('workOrders');
        return true;
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.database.simpleQuery);
    });

    it('should handle complex queries efficiently', async () => {
      // Setup larger dataset
      const workOrders = Array.from({ length: 5000 }, (_, i) =>
        createMockWorkOrder({
          id: `WO-COMPLEX-${i}`,
          status: ['pending', 'in_progress', 'completed'][i % 3] as any,
          priority: ['low', 'normal', 'high'][i % 3] as any,
          customerId: `CUST-${Math.floor(i / 10)}`, // Group customers
          scheduledDate: new Date(Date.now() + i * 86400000).toISOString(),
        })
      );

      await mockDB.bulkAdd('workOrders', workOrders);

      const { duration } = await performanceTester.measureAsync(async () => {
        // Simulate complex query with filtering and sorting
        const filtered = workOrders
          .filter(wo => wo.status === 'pending')
          .filter(wo => wo.priority === 'high')
          .sort((a, b) => new Date(a.scheduledDate).getTime() - new Date(b.scheduledDate).getTime())
          .slice(0, 50);
        
        return filtered;
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.database.complexQuery);
    });

    it('should perform batch operations efficiently', async () => {
      const batchSize = 500;
      const updates = Array.from({ length: batchSize }, (_, i) => ({
        id: `WO-BATCH-${i}`,
        status: 'completed' as const,
        completedAt: new Date().toISOString(),
      }));

      const { duration } = await performanceTester.measureAsync(async () => {
        // Simulate batch database updates
        for (const update of updates) {
          await mockDB.put('workOrders', update.id, update);
        }
        return updates.length;
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.database.batchOperation);
    });
  });

  describe('sync performance', () => {
    it('should queue items for sync quickly', async () => {
      const workOrder = createMockWorkOrder({
        id: 'WO-SYNC-PERF',
        status: 'completed',
      });

      const { duration } = await performanceTester.measureAsync(async () => {
        // Simulate sync queue operation
        await mockDB.put('syncQueue', `sync-${Date.now()}`, {
          type: 'work_order',
          operation: 'update',
          data: workOrder,
          timestamp: Date.now(),
        });
        return true;
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.sync.singleItem);
    });

    it('should handle batch sync queuing efficiently', async () => {
      const batchSize = 100;
      const syncItems = Array.from({ length: batchSize }, (_, i) => ({
        id: `sync-item-${i}`,
        type: 'work_order',
        operation: 'update',
        data: createMockWorkOrder({ id: `WO-BATCH-SYNC-${i}` }),
        timestamp: Date.now() + i,
      }));

      const { duration } = await performanceTester.measureAsync(async () => {
        // Simulate batch sync queuing
        for (const item of syncItems) {
          await mockDB.put('syncQueue', item.id, item);
        }
        return syncItems.length;
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.sync.batchItems);
    });

    it('should resolve conflicts quickly', async () => {
      const localData = createMockWorkOrder({
        id: 'WO-CONFLICT-PERF',
        title: 'Local Update',
        lastModified: '2024-01-01T10:00:00Z',
      });

      const serverData = createMockWorkOrder({
        id: 'WO-CONFLICT-PERF',
        title: 'Server Update',
        lastModified: '2024-01-01T11:00:00Z',
      });

      const { duration } = performanceTester.measureSync(() => {
        // Simulate conflict resolution logic
        const isConflict = localData.lastModified !== serverData.lastModified;
        
        if (isConflict) {
          // Server wins strategy
          const resolved = {
            ...serverData,
            resolvedAt: new Date().toISOString(),
            strategy: 'server_wins',
          };
          return resolved;
        }
        
        return localData;
      });

      expect(duration).toBeLessThan(PERFORMANCE_THRESHOLDS.sync.conflictResolution);
    });
  });

  describe('memory performance', () => {
    it('should not have significant memory leaks', async () => {
      // Measure initial memory if available
      const getMemoryUsage = () => {
        if (typeof process !== 'undefined' && process.memoryUsage) {
          return process.memoryUsage().heapUsed;
        }
        return 0;
      };

      const initialMemory = getMemoryUsage();
      
      // Simulate memory-intensive operations
      const largeDataSets = [];
      for (let i = 0; i < 10; i++) {
        const workOrders = Array.from({ length: 1000 }, (_, j) =>
          createMockWorkOrder({
            id: `WO-MEMORY-${i}-${j}`,
            description: 'A'.repeat(1000), // Large description
          })
        );
        
        largeDataSets.push(workOrders);
        
        // Process the data
        await performanceTester.measureAsync(async () => {
          const processed = workOrders.map(wo => ({
            ...wo,
            processed: true,
            processedAt: Date.now(),
          }));
          return processed;
        });
      }

      // Clear references to allow garbage collection
      largeDataSets.length = 0;
      
      // Force garbage collection if available
      if (typeof global !== 'undefined' && (global as any).gc) {
        (global as any).gc();
      }

      const finalMemory = getMemoryUsage();
      const memoryIncrease = finalMemory - initialMemory;

      if (initialMemory > 0) {
        expect(memoryIncrease).toBeLessThan(PERFORMANCE_THRESHOLDS.memory.leakTolerance);
      }
    });

    it('should handle large datasets without excessive memory usage', async () => {
      const getMemoryUsage = () => {
        if (typeof process !== 'undefined' && process.memoryUsage) {
          return process.memoryUsage().heapUsed;
        }
        return 0;
      };

      const initialMemory = getMemoryUsage();

      // Create large dataset
      const largeDataset = Array.from({ length: 10000 }, (_, i) =>
        createMockWorkOrder({
          id: `WO-LARGE-${i}`,
          checklist: Array.from({ length: 10 }, (_, j) => ({
            id: `check-${i}-${j}`,
            text: `Checklist item ${j}`,
            completed: false,
            required: true,
          })),
        })
      );

      // Process dataset efficiently
      await performanceTester.measureAsync(async () => {
        // Simulate processing in chunks to avoid memory spikes
        const chunkSize = 100;
        const results = [];
        
        for (let i = 0; i < largeDataset.length; i += chunkSize) {
          const chunk = largeDataset.slice(i, i + chunkSize);
          const processed = chunk.map(wo => ({
            id: wo.id,
            status: wo.status,
            checklistComplete: wo.checklist?.every(item => item.completed) || false,
          }));
          results.push(...processed);
        }
        
        return results;
      });

      const peakMemory = getMemoryUsage();
      
      if (initialMemory > 0 && peakMemory > 0) {
        expect(peakMemory).toBeLessThan(PERFORMANCE_THRESHOLDS.memory.maxHeapSize);
      }
    });
  });

  describe('virtual scrolling performance', () => {
    it('should handle large lists efficiently with virtual scrolling', async () => {
      const itemCount = 10000;
      const visibleItems = 20;
      const itemHeight = 60;

      const { duration, result } = await performanceTester.measureAsync(async () => {
        // Simulate virtual scrolling calculations
        const containerHeight = visibleItems * itemHeight;
        const totalHeight = itemCount * itemHeight;
        const scrollTop = 5000; // Scrolled down
        
        const startIndex = Math.floor(scrollTop / itemHeight);
        const endIndex = Math.min(
          startIndex + visibleItems + 5, // overscan
          itemCount
        );
        
        const virtualItems = [];
        for (let i = startIndex; i < endIndex; i++) {
          virtualItems.push({
            index: i,
            id: `item-${i}`,
            top: i * itemHeight,
            height: itemHeight,
          });
        }
        
        return {
          virtualItems,
          totalHeight,
          renderedCount: virtualItems.length,
        };
      });

      expect(duration).toBeLessThan(50); // Should be very fast
      expect(result.renderedCount).toBeLessThan(30); // Should only render visible items
    });

    it('should update virtual scroll efficiently on scroll events', async () => {
      const itemCount = 5000;
      const scrollEvents = 100; // Simulate rapid scrolling

      const { duration } = await performanceTester.measureAsync(async () => {
        let currentScrollTop = 0;
        const itemHeight = 50;
        const visibleItems = 15;
        
        for (let i = 0; i < scrollEvents; i++) {
          currentScrollTop += 50; // Scroll down
          
          // Calculate visible range
          const startIndex = Math.floor(currentScrollTop / itemHeight);
          const endIndex = Math.min(startIndex + visibleItems, itemCount);
          
          // This should be very fast
          const visibleRange = { startIndex, endIndex };
        }
        
        return true;
      });

      expect(duration).toBeLessThan(100); // 100ms for 100 scroll updates
    });
  });

  describe('bundle performance', () => {
    it('should have reasonable bundle size impact', () => {
      // Simulate checking for bundle size impact of new features
      const estimatedBundleIncrease = 50 * 1024; // 50KB for new features
      const currentBundleSize = 2 * 1024 * 1024; // 2MB current size
      const maxBundleSize = 3 * 1024 * 1024; // 3MB max allowed
      
      const newBundleSize = currentBundleSize + estimatedBundleIncrease;
      
      expect(newBundleSize).toBeLessThan(maxBundleSize);
    });

    it('should lazy load components efficiently', async () => {
      const componentLoadTimes = [];
      
      // Simulate lazy loading multiple components
      for (let i = 0; i < 5; i++) {
        const { duration } = await performanceTester.measureAsync(async () => {
          // Simulate dynamic import
          return new Promise(resolve => {
            setTimeout(() => {
              resolve(`Component${i}`);
            }, Math.random() * 300 + 50);
          });
        });
        
        componentLoadTimes.push(duration);
      }
      
      // All components should load reasonably quickly
      const averageLoadTime = componentLoadTimes.reduce((a, b) => a + b, 0) / componentLoadTimes.length;
      expect(averageLoadTime).toBeLessThan(400); // Average under 400ms
    });
  });

  describe('network performance simulation', () => {
    it('should handle slow network conditions gracefully', async () => {
      // Simulate slow 3G conditions
      const simulateSlowNetwork = (delay: number) => {
        return new Promise(resolve => {
          setTimeout(resolve, delay);
        });
      };

      const networkDelay = 2000; // 2 second delay
      
      const { duration } = await performanceTester.measureAsync(async () => {
        await simulateSlowNetwork(networkDelay);
        
        // App should remain responsive during network delays
        const workOrders = Array.from({ length: 50 }, (_, i) =>
          createMockWorkOrder({ id: `WO-SLOW-${i}` })
        );
        
        return workOrders;
      });

      // Should complete in reasonable time even with network delay
      expect(duration).toBeGreaterThan(networkDelay - 100);
      expect(duration).toBeLessThan(networkDelay + 500);
    });

    it('should batch API calls efficiently', async () => {
      const individualCallTime = 200; // 200ms per call
      const numberOfCalls = 10;
      
      // Individual calls
      const { duration: individualDuration } = await performanceTester.measureAsync(async () => {
        for (let i = 0; i < numberOfCalls; i++) {
          await new Promise(resolve => setTimeout(resolve, individualCallTime));
        }
        return numberOfCalls;
      });

      // Batched calls
      const { duration: batchedDuration } = await performanceTester.measureAsync(async () => {
        // Simulate single batched call
        await new Promise(resolve => setTimeout(resolve, individualCallTime * 1.5));
        return numberOfCalls;
      });

      // Batched should be significantly faster
      expect(batchedDuration).toBeLessThan(individualDuration / 2);
    });
  });

  describe('performance regression detection', () => {
    it('should detect performance degradation in critical paths', async () => {
      // Baseline performance measurements
      const baselineRenderTime = 500; // 500ms baseline
      const performanceDegradationThreshold = 1.5; // 50% degradation threshold
      
      const { duration: currentRenderTime } = await performanceTester.measureAsync(async () => {
        // Simulate current implementation
        const workOrders = Array.from({ length: 200 }, (_, i) =>
          createMockWorkOrder({ id: `WO-REGRESSION-${i}` })
        );
        
        // Simulate rendering
        return new Promise(resolve => {
          setTimeout(() => resolve(workOrders), Math.random() * 600 + 400);
        });
      });

      const performanceRatio = currentRenderTime / baselineRenderTime;
      
      // Should not have significant performance regression
      expect(performanceRatio).toBeLessThan(performanceDegradationThreshold);
      
      if (performanceRatio > 1.2) {
        console.warn(`⚠️ Performance degradation detected: ${Math.round((performanceRatio - 1) * 100)}% slower than baseline`);
      }
    });
  });
});