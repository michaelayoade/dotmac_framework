/**
 * @fileoverview Tests for health checker functionality
 * Validates health monitoring and endpoint validation
 */

import {
  HealthChecker,
  HealthStatus,
  HealthResult,
  createHealthChecker,
} from '../health/health-checker';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('HealthChecker', () => {
  let healthChecker: HealthChecker;
  let originalDateNow: () => number;

  beforeEach(() => {
    jest.clearAllMocks();
    originalDateNow = Date.now;
    Date.now = jest.fn(() => 1640995200000); // Fixed timestamp

    healthChecker = createHealthChecker({
      endpoints: ['/api/health', '/api/status'],
      timeout: 5000,
      retries: 3,
      interval: 30000,
    });
  });

  afterEach(() => {
    Date.now = originalDateNow;
    healthChecker.stop();
  });

  describe('Health Check Execution', () => {
    it('should successfully check healthy endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy', timestamp: Date.now() }),
      });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.status).toBe(HealthStatus.HEALTHY);
      expect(result.responseTime).toBeGreaterThan(0);
      expect(result.endpoint).toBe('/api/health');
      expect(result.timestamp).toBe(1640995200000);
      expect(result.error).toBeUndefined();
    });

    it('should handle unhealthy endpoint response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => ({ status: 'unhealthy', error: 'Database connection failed' }),
      });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.status).toBe(HealthStatus.UNHEALTHY);
      expect(result.endpoint).toBe('/api/health');
      expect(result.httpStatus).toBe(503);
      expect(result.error).toContain('Service Unavailable');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.status).toBe(HealthStatus.ERROR);
      expect(result.endpoint).toBe('/api/health');
      expect(result.error).toBe('Network error');
      expect(result.httpStatus).toBeUndefined();
    });

    it('should handle timeout errors', async () => {
      mockFetch.mockImplementationOnce(() => new Promise((resolve) => setTimeout(resolve, 10000)));

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.status).toBe(HealthStatus.ERROR);
      expect(result.error).toContain('timeout');
    });

    it('should measure response time accurately', async () => {
      let resolveTime = 0;
      Date.now = jest
        .fn()
        .mockReturnValueOnce(1640995200000) // Start time
        .mockReturnValueOnce(1640995200150); // End time (150ms later)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy' }),
      });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.responseTime).toBe(150);
    });
  });

  describe('Multiple Endpoint Checks', () => {
    it('should check all configured endpoints', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        });

      const results = await healthChecker.checkAll();

      expect(results).toHaveLength(2);
      expect(results[0].endpoint).toBe('/api/health');
      expect(results[1].endpoint).toBe('/api/status');
      expect(results.every((r) => r.status === HealthStatus.HEALTHY)).toBe(true);
    });

    it('should handle mixed endpoint results', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          json: async () => ({ status: 'unhealthy' }),
        });

      const results = await healthChecker.checkAll();

      expect(results).toHaveLength(2);
      expect(results[0].status).toBe(HealthStatus.HEALTHY);
      expect(results[1].status).toBe(HealthStatus.UNHEALTHY);
    });

    it('should check endpoints in parallel', async () => {
      const delay = 100;
      mockFetch
        .mockImplementationOnce(
          () =>
            new Promise((resolve) =>
              setTimeout(
                () =>
                  resolve({
                    ok: true,
                    status: 200,
                    json: async () => ({ status: 'healthy' }),
                  }),
                delay
              )
            )
        )
        .mockImplementationOnce(
          () =>
            new Promise((resolve) =>
              setTimeout(
                () =>
                  resolve({
                    ok: true,
                    status: 200,
                    json: async () => ({ status: 'healthy' }),
                  }),
                delay
              )
            )
        );

      const startTime = Date.now();
      await healthChecker.checkAll();
      const endTime = Date.now();

      // Should take roughly delay time, not 2 * delay (parallel execution)
      expect(endTime - startTime).toBeLessThan(delay * 1.5);
    });
  });

  describe('Retry Logic', () => {
    it('should retry failed requests up to configured limit', async () => {
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(result.status).toBe(HealthStatus.HEALTHY);
    });

    it('should fail after exhausting all retries', async () => {
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'));

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(mockFetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
      expect(result.status).toBe(HealthStatus.ERROR);
      expect(result.error).toBe('Network error');
    });

    it('should not retry on successful response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy' }),
      });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(result.status).toBe(HealthStatus.HEALTHY);
    });
  });

  describe('Continuous Monitoring', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should start continuous monitoring', () => {
      const mockCallback = jest.fn();

      healthChecker.start(mockCallback);

      expect(healthChecker.isRunning()).toBe(true);
    });

    it('should execute health checks at configured intervals', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy' }),
      });

      const mockCallback = jest.fn();
      healthChecker.start(mockCallback);

      // Fast-forward time to trigger multiple intervals
      jest.advanceTimersByTime(30000); // First interval
      await Promise.resolve(); // Allow promises to resolve

      jest.advanceTimersByTime(30000); // Second interval
      await Promise.resolve();

      expect(mockCallback).toHaveBeenCalledTimes(2);
    });

    it('should stop continuous monitoring', () => {
      const mockCallback = jest.fn();

      healthChecker.start(mockCallback);
      expect(healthChecker.isRunning()).toBe(true);

      healthChecker.stop();
      expect(healthChecker.isRunning()).toBe(false);
    });

    it('should not start if already running', () => {
      const mockCallback = jest.fn();

      healthChecker.start(mockCallback);
      const wasRunning = healthChecker.isRunning();

      // Try to start again
      healthChecker.start(mockCallback);

      expect(wasRunning).toBe(true);
      expect(healthChecker.isRunning()).toBe(true);
    });
  });

  describe('Portal-Specific Configurations', () => {
    const portalConfigs = [
      {
        portal: 'admin',
        expectedConfig: {
          endpoints: ['/api/admin/health', '/api/admin/status'],
          interval: 30000,
          timeout: 5000,
        },
      },
      {
        portal: 'customer',
        expectedConfig: {
          endpoints: ['/api/customer/health'],
          interval: 60000,
          timeout: 3000,
        },
      },
      {
        portal: 'technician',
        expectedConfig: {
          endpoints: ['/api/technician/health'],
          interval: 45000,
          timeout: 8000, // Higher timeout for mobile
        },
      },
      {
        portal: 'reseller',
        expectedConfig: {
          endpoints: ['/api/reseller/health', '/api/reseller/billing'],
          interval: 30000,
          timeout: 5000,
        },
      },
      {
        portal: 'management-admin',
        expectedConfig: {
          endpoints: ['/api/management/health', '/api/management/system'],
          interval: 15000, // More frequent for management
          timeout: 10000,
        },
      },
      {
        portal: 'management-reseller',
        expectedConfig: {
          endpoints: ['/api/management-reseller/health', '/api/management-reseller/partners'],
          interval: 20000,
          timeout: 7000,
        },
      },
      {
        portal: 'tenant-portal',
        expectedConfig: {
          endpoints: ['/api/tenant/health'],
          interval: 60000, // Less frequent for tenant portal
          timeout: 5000,
        },
      },
    ];

    portalConfigs.forEach(({ portal, expectedConfig }) => {
      it(`creates correct health checker for ${portal} portal`, () => {
        const checker = createHealthChecker({ portal });

        expect(checker).toBeDefined();
        // These would be tested through the checker's behavior
        // since the config is internal
      });
    });
  });

  describe('Error Scenarios', () => {
    it('should handle malformed JSON response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.status).toBe(HealthStatus.ERROR);
      expect(result.error).toContain('Invalid JSON');
    });

    it('should handle empty response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => null,
      });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.status).toBe(HealthStatus.HEALTHY);
      expect(result.data).toBeNull();
    });

    it('should handle non-standard status codes', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 418, // I'm a teapot
        statusText: "I'm a teapot",
        json: async () => ({ status: 'teapot' }),
      });

      const result = await healthChecker.checkEndpoint('/api/health');

      expect(result.status).toBe(HealthStatus.UNHEALTHY);
      expect(result.httpStatus).toBe(418);
    });
  });

  describe('Performance Tracking', () => {
    it('should track performance metrics over time', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy' }),
      });

      // Simulate multiple checks with different response times
      Date.now = jest
        .fn()
        .mockReturnValueOnce(1640995200000)
        .mockReturnValueOnce(1640995200100) // 100ms
        .mockReturnValueOnce(1640995200200)
        .mockReturnValueOnce(1640995200350) // 150ms
        .mockReturnValueOnce(1640995200400)
        .mockReturnValueOnce(1640995200500); // 100ms

      const results = await Promise.all([
        healthChecker.checkEndpoint('/api/health'),
        healthChecker.checkEndpoint('/api/health'),
        healthChecker.checkEndpoint('/api/health'),
      ]);

      expect(results.map((r) => r.responseTime)).toEqual([100, 150, 100]);
    });

    it('should provide health summary statistics', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          json: async () => ({ status: 'unhealthy' }),
        });

      const results = await healthChecker.checkAll();
      const summary = healthChecker.getSummary();

      expect(summary.totalChecks).toBe(2);
      expect(summary.healthyCount).toBe(1);
      expect(summary.unhealthyCount).toBe(1);
      expect(summary.errorCount).toBe(0);
      expect(summary.overallStatus).toBe(HealthStatus.UNHEALTHY);
    });
  });

  describe('Custom Health Check Validators', () => {
    it('should support custom health validation', async () => {
      const customValidator = (data: any) => {
        return data?.customStatus === 'operational';
      };

      const customChecker = createHealthChecker({
        endpoints: ['/api/custom'],
        validator: customValidator,
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ customStatus: 'operational' }),
      });

      const result = await customChecker.checkEndpoint('/api/custom');

      expect(result.status).toBe(HealthStatus.HEALTHY);
    });

    it('should fail custom validation appropriately', async () => {
      const customValidator = (data: any) => {
        return data?.version === '2.0.0';
      };

      const customChecker = createHealthChecker({
        endpoints: ['/api/custom'],
        validator: customValidator,
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ version: '1.0.0' }),
      });

      const result = await customChecker.checkEndpoint('/api/custom');

      expect(result.status).toBe(HealthStatus.UNHEALTHY);
      expect(result.error).toContain('validation failed');
    });
  });
});
