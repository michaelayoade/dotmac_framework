/**
 * API Integration Tests
 * Tests for API client integration with error handling and resilience
 */

import { technicianApiClient } from '../../lib/api/technician-client';
import { retryOperation, circuitBreakers } from '../../lib/resilience/enhanced-retry-logic';
import { NetworkSimulator, createMockWorkOrder } from '../utils/test-utils';

// Mock fetch for controlled testing
global.fetch = jest.fn();

describe('API Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    NetworkSimulator.reset();
    circuitBreakers.api.reset();
  });

  describe('work order operations', () => {
    it('should fetch work orders with proper error handling', async () => {
      const mockWorkOrders = [
        createMockWorkOrder({ id: 'WO-1', status: 'pending' }),
        createMockWorkOrder({ id: 'WO-2', status: 'in_progress' }),
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockWorkOrders,
        }),
      });

      const result = await technicianApiClient.getWorkOrders();

      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
      expect(result.data[0].id).toBe('WO-1');
    });

    it('should handle API errors with retry logic', async () => {
      // First two calls fail, third succeeds
      (global.fetch as jest.Mock)
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Server error'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: [],
          }),
        });

      const result = await retryOperation.api(() => 
        technicianApiClient.getWorkOrders()
      );

      expect(result.success).toBe(true);
      expect(result.attempts).toBe(3);
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should update work order status', async () => {
      const workOrderUpdate = {
        status: 'completed' as const,
        completedAt: new Date().toISOString(),
        notes: 'Work completed successfully',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { id: 'WO-1', ...workOrderUpdate },
        }),
      });

      const result = await technicianApiClient.updateWorkOrder('WO-1', workOrderUpdate);

      expect(result.success).toBe(true);
      expect(result.data.status).toBe('completed');
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/work-orders/WO-1'),
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify(workOrderUpdate),
        })
      );
    });

    it('should upload work order photos', async () => {
      const mockPhoto = new File(['photo data'], 'photo.jpg', { type: 'image/jpeg' });
      
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: {
            photoId: 'PHOTO-123',
            url: 'https://example.com/photos/photo.jpg',
          },
        }),
      });

      const result = await technicianApiClient.uploadPhoto('WO-1', mockPhoto);

      expect(result.success).toBe(true);
      expect(result.data.photoId).toBe('PHOTO-123');
      
      const [url, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/work-orders/WO-1/photos');
      expect(options.method).toBe('POST');
      expect(options.body).toBeInstanceOf(FormData);
    });
  });

  describe('customer operations', () => {
    it('should fetch customer details', async () => {
      const mockCustomer = {
        id: 'CUST-1',
        name: 'John Doe',
        email: 'john@example.com',
        phone: '555-0123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockCustomer,
        }),
      });

      const result = await technicianApiClient.getCustomer('CUST-1');

      expect(result.success).toBe(true);
      expect(result.data.name).toBe('John Doe');
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/customers/CUST-1'),
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should update customer information', async () => {
      const customerUpdate = {
        phone: '555-9999',
        email: 'newemail@example.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { id: 'CUST-1', ...customerUpdate },
        }),
      });

      const result = await technicianApiClient.updateCustomer('CUST-1', customerUpdate);

      expect(result.success).toBe(true);
      expect(result.data.phone).toBe('555-9999');
    });
  });

  describe('inventory operations', () => {
    it('should fetch inventory levels', async () => {
      const mockInventory = [
        { id: 'INV-1', name: 'Router', quantity: 10 },
        { id: 'INV-2', name: 'Cable', quantity: 5 },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockInventory,
        }),
      });

      const result = await technicianApiClient.getInventory();

      expect(result.success).toBe(true);
      expect(result.data).toHaveLength(2);
    });

    it('should update inventory quantities', async () => {
      const inventoryUpdate = {
        quantity: 8, // Used 2 items
        operation: 'used' as const,
        workOrderId: 'WO-1',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { id: 'INV-1', quantity: 8 },
        }),
      });

      const result = await technicianApiClient.updateInventory('INV-1', inventoryUpdate);

      expect(result.success).toBe(true);
      expect(result.data.quantity).toBe(8);
    });
  });

  describe('authentication integration', () => {
    it('should handle token refresh automatically', async () => {
      // First call returns 401, second call (after refresh) succeeds
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: false,
          status: 401,
          json: () => Promise.resolve({
            success: false,
            error: 'Token expired',
          }),
        })
        .mockResolvedValueOnce({ // Token refresh call
          ok: true,
          json: () => Promise.resolve({
            success: true,
            token: 'new-token-123',
          }),
        })
        .mockResolvedValueOnce({ // Retry original call
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: [],
          }),
        });

      const result = await technicianApiClient.getWorkOrders();

      expect(result.success).toBe(true);
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should redirect to login after max auth failures', async () => {
      // Multiple 401 responses
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({
          success: false,
          error: 'Unauthorized',
        }),
      });

      const result = await technicianApiClient.getWorkOrders();

      expect(result.success).toBe(false);
      expect(result.error).toContain('Unauthorized');
    });
  });

  describe('network resilience', () => {
    it('should handle network failures gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network failure'));

      const result = await retryOperation.api(() => 
        technicianApiClient.getWorkOrders()
      );

      expect(result.success).toBe(false);
      expect(result.error?.message).toBe('Network failure');
      expect(result.attempts).toBeGreaterThan(1);
    });

    it('should respect circuit breaker state', async () => {
      // Cause circuit breaker to open by triggering failures
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Service unavailable'));

      // Multiple failures to trigger circuit breaker
      for (let i = 0; i < 5; i++) {
        try {
          await circuitBreakers.api.execute(() => technicianApiClient.getWorkOrders());
        } catch {}
      }

      expect(circuitBreakers.api.getState()).toBe('open');

      // Next call should fail immediately without hitting the API
      const startTime = Date.now();
      
      try {
        await circuitBreakers.api.execute(() => technicianApiClient.getWorkOrders());
      } catch (error: any) {
        expect(error.message).toContain('Circuit breaker is OPEN');
      }

      const endTime = Date.now();
      expect(endTime - startTime).toBeLessThan(100); // Should fail quickly
    });

    it('should adapt to network conditions', async () => {
      NetworkSimulator.simulateSlowConnection();

      // Mock slow response
      (global.fetch as jest.Mock).mockImplementation(() => 
        new Promise(resolve => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: () => Promise.resolve({
                success: true,
                data: [],
              }),
            });
          }, 2000); // Slow response
        })
      );

      const startTime = Date.now();
      const result = await technicianApiClient.getWorkOrders({ timeout: 5000 });
      const endTime = Date.now();

      expect(result.success).toBe(true);
      expect(endTime - startTime).toBeGreaterThan(1900); // Should have waited
    });
  });

  describe('data validation', () => {
    it('should validate API responses', async () => {
      // Invalid response format
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          // Missing 'success' field
          data: 'invalid format',
        }),
      });

      const result = await technicianApiClient.getWorkOrders();

      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid response format');
    });

    it('should sanitize input data', async () => {
      const maliciousUpdate = {
        notes: '<script>alert("xss")</script>Normal notes',
        status: 'completed' as const,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { id: 'WO-1', ...maliciousUpdate },
        }),
      });

      await technicianApiClient.updateWorkOrder('WO-1', maliciousUpdate);

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options.body);
      
      // Should sanitize script tags
      expect(body.notes).not.toContain('<script>');
      expect(body.notes).toContain('Normal notes');
    });
  });

  describe('performance optimization', () => {
    it('should cache frequent API calls', async () => {
      const mockData = [{ id: 'INV-1', name: 'Router' }];

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockData,
        }),
      });

      // First call
      const result1 = await technicianApiClient.getInventory();
      
      // Second call within cache window
      const result2 = await technicianApiClient.getInventory();

      expect(result1.success).toBe(true);
      expect(result2.success).toBe(true);
      expect(result1.data).toEqual(result2.data);
      
      // Should only make one actual API call due to caching
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should batch multiple requests', async () => {
      const batchRequests = [
        { type: 'work_order', id: 'WO-1' },
        { type: 'work_order', id: 'WO-2' },
        { type: 'customer', id: 'CUST-1' },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: [
            { id: 'WO-1', type: 'work_order', data: {} },
            { id: 'WO-2', type: 'work_order', data: {} },
            { id: 'CUST-1', type: 'customer', data: {} },
          ],
        }),
      });

      const results = await technicianApiClient.batchRequest(batchRequests);

      expect(results.success).toBe(true);
      expect(results.data).toHaveLength(3);
      expect(global.fetch).toHaveBeenCalledTimes(1); // Single batched call
    });
  });

  describe('offline queue integration', () => {
    it('should queue requests when offline', async () => {
      NetworkSimulator.simulateOffline();

      const result = await technicianApiClient.updateWorkOrder('WO-1', {
        status: 'completed',
      });

      expect(result.success).toBe(true);
      expect(result.queued).toBe(true);
      expect(result.message).toContain('offline');
    });

    it('should process queued requests when online', async () => {
      // Queue request while offline
      NetworkSimulator.simulateOffline();
      
      await technicianApiClient.updateWorkOrder('WO-1', {
        status: 'in_progress',
      });

      // Go online and process queue
      NetworkSimulator.simulateOnline();

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { id: 'WO-1', status: 'in_progress' },
        }),
      });

      const result = await technicianApiClient.processOfflineQueue();

      expect(result.processed).toBeGreaterThan(0);
      expect(result.successful).toBeGreaterThan(0);
      expect(global.fetch).toHaveBeenCalled();
    });
  });

  describe('error recovery', () => {
    it('should recover from temporary server errors', async () => {
      // Server error followed by success
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          json: () => Promise.resolve({
            success: false,
            error: 'Internal server error',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: [],
          }),
        });

      const result = await retryOperation.api(() => 
        technicianApiClient.getWorkOrders()
      );

      expect(result.success).toBe(true);
      expect(result.attempts).toBe(2);
    });

    it('should handle malformed responses', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      const result = await technicianApiClient.getWorkOrders();

      expect(result.success).toBe(false);
      expect(result.error).toContain('Invalid JSON');
    });
  });
});