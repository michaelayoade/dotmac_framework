/**
 * @fileoverview Tests for monitoring configuration
 * Validates monitoring setup and configuration validation
 */

import { MonitoringConfig, createMonitoringConfig, validateMonitoringConfig } from '../config/monitoring-config';

describe('MonitoringConfig', () => {
  describe('Default Configuration', () => {
    it('should create default monitoring config', () => {
      const config = createMonitoringConfig();

      expect(config).toBeDefined();
      expect(config.sentry).toBeDefined();
      expect(config.performance).toBeDefined();
      expect(config.health).toBeDefined();
      expect(config.validation).toBeDefined();
    });

    it('should have correct default sentry configuration', () => {
      const config = createMonitoringConfig();

      expect(config.sentry.enabled).toBe(true);
      expect(config.sentry.environment).toBe('development');
      expect(config.sentry.debug).toBe(false);
      expect(config.sentry.tracesSampleRate).toBe(1.0);
      expect(config.sentry.replaysSessionSampleRate).toBe(0.1);
      expect(config.sentry.replaysOnErrorSampleRate).toBe(1.0);
    });

    it('should have correct default performance configuration', () => {
      const config = createMonitoringConfig();

      expect(config.performance.enabled).toBe(true);
      expect(config.performance.trackWebVitals).toBe(true);
      expect(config.performance.trackUserInteractions).toBe(true);
      expect(config.performance.reportThresholds.cls).toBe(0.1);
      expect(config.performance.reportThresholds.fid).toBe(100);
      expect(config.performance.reportThresholds.lcp).toBe(2500);
    });

    it('should have correct default health configuration', () => {
      const config = createMonitoringConfig();

      expect(config.health.enabled).toBe(true);
      expect(config.health.interval).toBe(30000);
      expect(config.health.retries).toBe(3);
      expect(config.health.timeout).toBe(5000);
      expect(config.health.endpoints).toContain('/api/health');
    });

    it('should have correct default validation configuration', () => {
      const config = createMonitoringConfig();

      expect(config.validation.enabled).toBe(true);
      expect(config.validation.strictMode).toBe(false);
      expect(config.validation.validateSchemas).toBe(true);
      expect(config.validation.validatePermissions).toBe(true);
    });
  });

  describe('Portal-Specific Configurations', () => {
    const portals: Array<{ portal: string; expectedFeatures: Record<string, any> }> = [
      {
        portal: 'admin',
        expectedFeatures: {
          performance: { trackUserInteractions: true },
          sentry: { debug: false }
        }
      },
      {
        portal: 'customer',
        expectedFeatures: {
          performance: { trackWebVitals: true },
          sentry: { environment: 'production' }
        }
      },
      {
        portal: 'technician',
        expectedFeatures: {
          performance: { trackWebVitals: true },
          health: { interval: 60000 }
        }
      },
      {
        portal: 'reseller',
        expectedFeatures: {
          validation: { strictMode: true }
        }
      },
      {
        portal: 'management-admin',
        expectedFeatures: {
          sentry: { debug: true },
          validation: { strictMode: true }
        }
      },
      {
        portal: 'management-reseller',
        expectedFeatures: {
          sentry: { debug: false },
          validation: { strictMode: true },
          performance: { trackUserInteractions: true }
        }
      },
      {
        portal: 'tenant-portal',
        expectedFeatures: {
          performance: { trackWebVitals: false },
          health: { interval: 60000 },
          validation: { strictMode: false }
        }
      }
    ];

    portals.forEach(({ portal, expectedFeatures }) => {
      it(`creates correct monitoring config for ${portal} portal`, () => {
        const config = createMonitoringConfig({ portal });

        expect(config).toBeDefined();
        expect(config.portal).toBe(portal);

        // Check portal-specific features are applied
        Object.entries(expectedFeatures).forEach(([section, features]) => {
          Object.entries(features).forEach(([key, value]) => {
            expect((config as any)[section][key]).toBe(value);
          });
        });
      });
    });
  });

  describe('Environment-Specific Configurations', () => {
    const environments = ['development', 'staging', 'production'];

    environments.forEach((env) => {
      it(`creates correct monitoring config for ${env} environment`, () => {
        const config = createMonitoringConfig({ environment: env });

        expect(config.sentry.environment).toBe(env);

        if (env === 'production') {
          expect(config.sentry.debug).toBe(false);
          expect(config.validation.strictMode).toBe(true);
          expect(config.performance.reportThresholds.lcp).toBe(2500);
        } else if (env === 'development') {
          expect(config.sentry.debug).toBe(true);
          expect(config.validation.strictMode).toBe(false);
        }
      });
    });
  });

  describe('Custom Configuration Overrides', () => {
    it('should merge custom sentry configuration', () => {
      const customConfig = {
        sentry: {
          dsn: 'custom-dsn',
          tracesSampleRate: 0.5,
          debug: true
        }
      };

      const config = createMonitoringConfig(customConfig);

      expect(config.sentry.dsn).toBe('custom-dsn');
      expect(config.sentry.tracesSampleRate).toBe(0.5);
      expect(config.sentry.debug).toBe(true);
      expect(config.sentry.enabled).toBe(true); // Should retain defaults
    });

    it('should merge custom performance configuration', () => {
      const customConfig = {
        performance: {
          trackWebVitals: false,
          reportThresholds: {
            cls: 0.2,
            lcp: 3000
          }
        }
      };

      const config = createMonitoringConfig(customConfig);

      expect(config.performance.trackWebVitals).toBe(false);
      expect(config.performance.reportThresholds.cls).toBe(0.2);
      expect(config.performance.reportThresholds.lcp).toBe(3000);
      expect(config.performance.reportThresholds.fid).toBe(100); // Should retain default
    });

    it('should merge custom health configuration', () => {
      const customConfig = {
        health: {
          interval: 60000,
          endpoints: ['/api/health', '/api/status']
        }
      };

      const config = createMonitoringConfig(customConfig);

      expect(config.health.interval).toBe(60000);
      expect(config.health.endpoints).toEqual(['/api/health', '/api/status']);
      expect(config.health.retries).toBe(3); // Should retain default
    });

    it('should handle deep merge of nested configurations', () => {
      const customConfig = {
        sentry: {
          integrations: {
            replay: { enabled: true }
          }
        },
        performance: {
          reportThresholds: {
            cls: 0.15
          }
        }
      };

      const config = createMonitoringConfig(customConfig);

      expect(config.sentry.integrations?.replay?.enabled).toBe(true);
      expect(config.performance.reportThresholds.cls).toBe(0.15);
      expect(config.performance.reportThresholds.fid).toBe(100); // Should retain default
    });
  });

  describe('Configuration Validation', () => {
    it('should validate correct configuration', () => {
      const config = createMonitoringConfig();
      const result = validateMonitoringConfig(config);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect invalid sentry configuration', () => {
      const config = createMonitoringConfig({
        sentry: {
          tracesSampleRate: 2.0 // Invalid: > 1.0
        }
      });

      const result = validateMonitoringConfig(config);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Sentry tracesSampleRate must be between 0 and 1');
    });

    it('should detect invalid performance thresholds', () => {
      const config = createMonitoringConfig({
        performance: {
          reportThresholds: {
            cls: -0.1, // Invalid: negative
            fid: 0,    // Invalid: should be positive
            lcp: -100  // Invalid: negative
          }
        }
      });

      const result = validateMonitoringConfig(config);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContainEqual(expect.stringMatching(/CLS threshold must be positive/));
      expect(result.errors).toContainEqual(expect.stringMatching(/FID threshold must be positive/));
      expect(result.errors).toContainEqual(expect.stringMatching(/LCP threshold must be positive/));
    });

    it('should detect invalid health configuration', () => {
      const config = createMonitoringConfig({
        health: {
          interval: -1000, // Invalid: negative
          retries: -1,     // Invalid: negative
          timeout: 0       // Invalid: should be positive
        }
      });

      const result = validateMonitoringConfig(config);

      expect(result.isValid).toBe(false);
      expect(result.errors).toContainEqual(expect.stringMatching(/Health interval must be positive/));
      expect(result.errors).toContainEqual(expect.stringMatching(/Health retries must be non-negative/));
      expect(result.errors).toContainEqual(expect.stringMatching(/Health timeout must be positive/));
    });

    it('should handle missing required fields', () => {
      const incompleteConfig = {} as MonitoringConfig;
      const result = validateMonitoringConfig(incompleteConfig);

      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('Portal-Specific Feature Flags', () => {
    it('should enable appropriate features for admin portal', () => {
      const config = createMonitoringConfig({ portal: 'admin' });

      expect(config.sentry.enabled).toBe(true);
      expect(config.performance.trackUserInteractions).toBe(true);
      expect(config.validation.validatePermissions).toBe(true);
    });

    it('should optimize for customer portal', () => {
      const config = createMonitoringConfig({ portal: 'customer' });

      expect(config.performance.trackWebVitals).toBe(true);
      expect(config.health.interval).toBe(30000);
    });

    it('should configure for mobile technician portal', () => {
      const config = createMonitoringConfig({ portal: 'technician' });

      expect(config.health.interval).toBeGreaterThanOrEqual(30000);
      expect(config.performance.enabled).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should handle undefined input gracefully', () => {
      const config = createMonitoringConfig(undefined);

      expect(config).toBeDefined();
      expect(config.sentry.enabled).toBe(true);
    });

    it('should handle null input gracefully', () => {
      const config = createMonitoringConfig(null as any);

      expect(config).toBeDefined();
      expect(config.sentry.enabled).toBe(true);
    });

    it('should handle empty object input', () => {
      const config = createMonitoringConfig({});

      expect(config).toBeDefined();
      expect(config.sentry.enabled).toBe(true);
    });
  });

  describe('Type Safety', () => {
    it('should have correct TypeScript types', () => {
      const config: MonitoringConfig = createMonitoringConfig();

      expect(typeof config.sentry.enabled).toBe('boolean');
      expect(typeof config.sentry.tracesSampleRate).toBe('number');
      expect(typeof config.performance.enabled).toBe('boolean');
      expect(typeof config.health.interval).toBe('number');
      expect(Array.isArray(config.health.endpoints)).toBe(true);
    });

    it('should enforce portal type constraints', () => {
      const validPortals = ['admin', 'customer', 'technician', 'reseller', 'management-admin', 'management-reseller', 'tenant-portal'];

      validPortals.forEach(portal => {
        const config = createMonitoringConfig({ portal });
        expect(config.portal).toBe(portal);
      });
    });
  });
});
