/**
 * Production Monitoring Validation System
 * Comprehensive testing and validation for all monitoring components
 */

import * as Sentry from '@sentry/nextjs';
import type { PortalType } from '../sentry/types';
import { getMonitoringConfig, validateMonitoringConfig } from '../config/monitoring-config';
import { PORTAL_HEALTH_CONFIGS } from '../health';
import { HealthChecker } from '../health/health-checker';

export interface ValidationResult {
  component: string;
  status: 'pass' | 'fail' | 'warn';
  message: string;
  details?: any;
  timestamp: number;
}

export interface MonitoringValidationReport {
  portal: PortalType;
  overallStatus: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  results: ValidationResult[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    warned: number;
  };
}

export class MonitoringValidator {
  private portal: PortalType;
  private config: ReturnType<typeof getMonitoringConfig>;

  constructor(portal: PortalType) {
    this.portal = portal;
    this.config = getMonitoringConfig(portal);
  }

  /**
   * Run comprehensive monitoring validation
   */
  async validateAll(): Promise<MonitoringValidationReport> {
    const results: ValidationResult[] = [];
    const startTime = Date.now();

    console.log(`🔍 Starting monitoring validation for ${this.portal} portal...`);

    // Configuration validation
    results.push(await this.validateConfiguration());

    // Sentry validation
    if (this.config.sentry.enabled) {
      results.push(await this.validateSentry());
    }

    // Health check validation
    if (this.config.health.enabled) {
      results.push(await this.validateHealthChecks());
    }

    // Performance monitoring validation
    if (this.config.performance.enabled) {
      results.push(await this.validatePerformanceMonitoring());
    }

    // Environment validation
    results.push(await this.validateEnvironment());

    // Dependency validation
    results.push(await this.validateDependencies());

    const summary = this.calculateSummary(results);
    const overallStatus = this.determineOverallStatus(summary);

    const report: MonitoringValidationReport = {
      portal: this.portal,
      overallStatus,
      timestamp: new Date().toISOString(),
      results,
      summary,
    };

    console.log(`✅ Monitoring validation completed in ${Date.now() - startTime}ms`);
    console.log(`📊 Summary: ${summary.passed} passed, ${summary.failed} failed, ${summary.warned} warnings`);

    return report;
  }

  /**
   * Validate monitoring configuration
   */
  private async validateConfiguration(): Promise<ValidationResult> {
    const start = Date.now();

    try {
      const validation = validateMonitoringConfig(this.portal);

      return {
        component: 'Configuration',
        status: validation.valid ? (validation.warnings.length > 0 ? 'warn' : 'pass') : 'fail',
        message: validation.valid ?
          (validation.warnings.length > 0 ? 'Configuration valid with warnings' : 'Configuration valid') :
          'Configuration has errors',
        details: {
          errors: validation.errors,
          warnings: validation.warnings,
          config: this.config,
        },
        timestamp: Date.now() - start,
      };
    } catch (error) {
      return {
        component: 'Configuration',
        status: 'fail',
        message: 'Configuration validation failed',
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        timestamp: Date.now() - start,
      };
    }
  }

  /**
   * Validate Sentry integration
   */
  private async validateSentry(): Promise<ValidationResult> {
    const start = Date.now();

    try {
      // Check if Sentry is initialized
      const hub = Sentry.getCurrentHub();
      const client = hub.getClient();

      if (!client) {
        return {
          component: 'Sentry',
          status: 'fail',
          message: 'Sentry client not initialized',
          timestamp: Date.now() - start,
        };
      }

      // Test Sentry capture (development only)
      if (process.env.NODE_ENV === 'development' && process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
        const eventId = Sentry.captureMessage('Monitoring validation test', {
          level: 'info',
          tags: {
            validation: 'true',
            portal: this.portal,
          },
        });

        return {
          component: 'Sentry',
          status: 'pass',
          message: 'Sentry integration working correctly',
          details: {
            dsn: this.config.sentry.dsn ? 'configured' : 'missing',
            eventId,
            clientOptions: client.getOptions(),
          },
          timestamp: Date.now() - start,
        };
      }

      return {
        component: 'Sentry',
        status: 'pass',
        message: 'Sentry client initialized successfully',
        details: {
          dsn: this.config.sentry.dsn ? 'configured' : 'missing',
          options: client.getOptions(),
        },
        timestamp: Date.now() - start,
      };
    } catch (error) {
      return {
        component: 'Sentry',
        status: 'fail',
        message: 'Sentry validation failed',
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        timestamp: Date.now() - start,
      };
    }
  }

  /**
   * Validate health check system
   */
  private async validateHealthChecks(): Promise<ValidationResult> {
    const start = Date.now();

    try {
      const healthConfig = PORTAL_HEALTH_CONFIGS[this.portal];
      if (!healthConfig) {
        return {
          component: 'Health Checks',
          status: 'fail',
          message: 'Health check configuration not found',
          timestamp: Date.now() - start,
        };
      }

      // Create health checker instance
      const healthChecker = new HealthChecker(healthConfig);

      // Perform actual health check
      const healthResult = await healthChecker.getHealthStatus();

      return {
        component: 'Health Checks',
        status: healthResult.status === 'healthy' ? 'pass' :
                healthResult.status === 'degraded' ? 'warn' : 'fail',
        message: `Health check system ${healthResult.status}`,
        details: {
          portal: healthResult.portal,
          checks: Object.keys(healthResult.checks).length,
          uptime: healthResult.uptime,
          metrics: healthResult.metrics,
        },
        timestamp: Date.now() - start,
      };
    } catch (error) {
      return {
        component: 'Health Checks',
        status: 'fail',
        message: 'Health check validation failed',
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        timestamp: Date.now() - start,
      };
    }
  }

  /**
   * Validate performance monitoring
   */
  private async validatePerformanceMonitoring(): Promise<ValidationResult> {
    const start = Date.now();

    try {
      // Check if Performance API is available
      if (typeof window !== 'undefined' && !window.performance) {
        return {
          component: 'Performance Monitoring',
          status: 'warn',
          message: 'Performance API not available',
          timestamp: Date.now() - start,
        };
      }

      // Validate performance budgets
      const budgets = this.config.performance.budgets;
      const warnings = [];

      if (budgets.renderTime > 50) {
        warnings.push('Render time budget is high');
      }

      if (budgets.memoryUsage > 200 * 1024 * 1024) {
        warnings.push('Memory budget is very high');
      }

      return {
        component: 'Performance Monitoring',
        status: warnings.length > 0 ? 'warn' : 'pass',
        message: warnings.length > 0 ?
          'Performance monitoring configured with warnings' :
          'Performance monitoring configured correctly',
        details: {
          budgets,
          warnings,
          coreWebVitals: this.config.performance.enableCoreWebVitals,
          customMetrics: this.config.performance.enableCustomMetrics,
        },
        timestamp: Date.now() - start,
      };
    } catch (error) {
      return {
        component: 'Performance Monitoring',
        status: 'fail',
        message: 'Performance monitoring validation failed',
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        timestamp: Date.now() - start,
      };
    }
  }

  /**
   * Validate environment setup
   */
  private async validateEnvironment(): Promise<ValidationResult> {
    const start = Date.now();

    try {
      const requiredEnvVars = [
        'NODE_ENV',
        'NEXT_PUBLIC_API_URL',
      ];

      const optionalEnvVars = [
        'NEXT_PUBLIC_SENTRY_DSN',
        'NEXT_PUBLIC_APP_VERSION',
      ];

      const missing = requiredEnvVars.filter(varName => !process.env[varName]);
      const missingOptional = optionalEnvVars.filter(varName => !process.env[varName]);

      return {
        component: 'Environment',
        status: missing.length > 0 ? 'fail' : (missingOptional.length > 0 ? 'warn' : 'pass'),
        message: missing.length > 0 ?
          `Missing required environment variables` :
          missingOptional.length > 0 ?
            `Missing optional environment variables` :
            `All environment variables configured`,
        details: {
          required: {
            total: requiredEnvVars.length,
            configured: requiredEnvVars.length - missing.length,
            missing,
          },
          optional: {
            total: optionalEnvVars.length,
            configured: optionalEnvVars.length - missingOptional.length,
            missing: missingOptional,
          },
          nodeEnv: process.env.NODE_ENV,
        },
        timestamp: Date.now() - start,
      };
    } catch (error) {
      return {
        component: 'Environment',
        status: 'fail',
        message: 'Environment validation failed',
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        timestamp: Date.now() - start,
      };
    }
  }

  /**
   * Validate dependencies
   */
  private async validateDependencies(): Promise<ValidationResult> {
    const start = Date.now();

    try {
      const requiredDependencies = [
        'react',
        'next',
        '@sentry/nextjs',
        '@tanstack/react-query',
      ];

      const failed: string[] = [];
      const versions: Record<string, string> = {};

      for (const dep of requiredDependencies) {
        try {
          const module = require(dep);
          if (dep === 'react') {
            versions[dep] = require('react/package.json').version;
          } else if (dep === 'next') {
            versions[dep] = require('next/package.json').version;
          } else {
            versions[dep] = 'available';
          }
        } catch {
          failed.push(dep);
        }
      }

      return {
        component: 'Dependencies',
        status: failed.length > 0 ? 'fail' : 'pass',
        message: failed.length > 0 ?
          'Some required dependencies are missing' :
          'All dependencies are available',
        details: {
          required: requiredDependencies,
          available: Object.keys(versions),
          failed,
          versions,
          nodeVersion: process.version,
        },
        timestamp: Date.now() - start,
      };
    } catch (error) {
      return {
        component: 'Dependencies',
        status: 'fail',
        message: 'Dependency validation failed',
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        timestamp: Date.now() - start,
      };
    }
  }

  private calculateSummary(results: ValidationResult[]) {
    return results.reduce(
      (acc, result) => {
        acc.total++;
        if (result.status === 'pass') acc.passed++;
        else if (result.status === 'fail') acc.failed++;
        else if (result.status === 'warn') acc.warned++;
        return acc;
      },
      { total: 0, passed: 0, failed: 0, warned: 0 }
    );
  }

  private determineOverallStatus(summary: ReturnType<typeof this.calculateSummary>) {
    if (summary.failed > 0) return 'unhealthy' as const;
    if (summary.warned > 0) return 'degraded' as const;
    return 'healthy' as const;
  }
}

/**
 * Quick validation function for runtime checks
 */
export async function validateMonitoring(portal: PortalType): Promise<MonitoringValidationReport> {
  const validator = new MonitoringValidator(portal);
  return await validator.validateAll();
}

/**
 * Development-only monitoring test
 */
export function runMonitoringTests(portal: PortalType) {
  if (process.env.NODE_ENV !== 'development') {
    console.warn('Monitoring tests only run in development mode');
    return;
  }

  console.log(`🧪 Running monitoring tests for ${portal} portal...`);

  // Test Sentry
  if (process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
    Sentry.captureException(new Error(`Test error from ${portal} portal`), {
      tags: { test: 'true', portal },
    });
    console.log('✅ Sentry test error sent');
  }

  // Test performance monitoring
  if (typeof window !== 'undefined') {
    performance.mark('test-start');
    setTimeout(() => {
      performance.mark('test-end');
      performance.measure('test-duration', 'test-start', 'test-end');
      console.log('✅ Performance monitoring test completed');
    }, 100);
  }

  console.log('🎉 Monitoring tests completed');
}
