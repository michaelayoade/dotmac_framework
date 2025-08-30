/**
 * Advanced Health Checker with caching and comprehensive monitoring
 */

import { NextRequest, NextResponse } from 'next/server';
import type {
  HealthCheckResult,
  HealthStatus,
  HealthCheck,
  HealthMetrics,
  PortalHealthConfig,
  HealthCheckFunction,
  HealthCheckRegistry
} from './types';

interface ApplicationMetrics {
  startTime: number;
  requestCount: number;
  errorCount: number;
  responseTimes: number[];
  lastError: string | null;
}

interface HealthCache {
  result: HealthCheckResult | null;
  timestamp: number;
  ttl: number;
}

export class HealthChecker {
  private metrics: ApplicationMetrics;
  private cache: HealthCache;
  private registry: Map<string, { check: HealthCheckFunction; critical: boolean }>;
  private config: PortalHealthConfig;

  constructor(config: PortalHealthConfig) {
    this.config = config;
    this.metrics = {
      startTime: Date.now(),
      requestCount: 0,
      errorCount: 0,
      responseTimes: [],
      lastError: null,
    };

    this.cache = {
      result: null,
      timestamp: 0,
      ttl: config.cacheTtl,
    };

    this.registry = new Map();
    this.initializeDefaultChecks();
  }

  /**
   * Main health check endpoint handler
   */
  async handleHealthCheck(request: NextRequest): Promise<NextResponse> {
    const startTime = Date.now();
    this.metrics.requestCount++;

    try {
      const healthResult = await this.getHealthStatus();

      // Track response time
      const responseTime = Date.now() - startTime;
      this.updateResponseTime(responseTime);

      // Add current request response time
      healthResult.checks.healthCheck = {
        name: 'Health Check Response',
        status: 'pass',
        duration: responseTime,
      };

      const statusCode = this.getHttpStatusCode(healthResult.status);

      return NextResponse.json(healthResult, {
        status: statusCode,
        headers: this.getHealthHeaders(responseTime),
      });

    } catch (error) {
      this.metrics.errorCount++;
      this.metrics.lastError = error instanceof Error ? error.message : 'Unknown error';

      const errorResult = this.createErrorResult(error, Date.now() - startTime);

      return NextResponse.json(errorResult, {
        status: 503,
        headers: this.getHealthHeaders(Date.now() - startTime),
      });
    }
  }

  /**
   * Get comprehensive health status with caching
   */
  async getHealthStatus(): Promise<HealthCheckResult> {
    const now = Date.now();

    // Check cache validity
    if (this.cache.result && (now - this.cache.timestamp) < this.cache.ttl) {
      // Update timestamp and uptime for cached result
      return {
        ...this.cache.result,
        timestamp: new Date().toISOString(),
        uptime: now - this.metrics.startTime,
      };
    }

    // Perform fresh health checks
    const result = await this.performHealthChecks();

    // Update cache
    this.cache = {
      result,
      timestamp: now,
      ttl: this.config.cacheTtl,
    };

    return result;
  }

  /**
   * Register a custom health check
   */
  registerCheck(name: string, check: HealthCheckFunction, critical = false): void {
    this.registry.set(name, { check, critical });
  }

  /**
   * Unregister a health check
   */
  unregisterCheck(name: string): void {
    this.registry.delete(name);
  }

  /**
   * Update metrics (call from middleware or request handlers)
   */
  updateMetrics(responseTime?: number, error?: boolean): void {
    if (responseTime !== undefined) {
      this.updateResponseTime(responseTime);
    }

    if (error) {
      this.metrics.errorCount++;
    }

    this.metrics.requestCount++;
  }

  private async performHealthChecks(): Promise<HealthCheckResult> {
    const checks: Record<string, HealthCheck> = {};
    const checkPromises: Array<Promise<void>> = [];

    // Execute all registered checks with timeout
    for (const [name, { check, critical }] of this.registry) {
      const promise = this.executeCheckWithTimeout(name, check, critical)
        .then(result => {
          checks[name] = result;
        })
        .catch(error => {
          checks[name] = {
            name,
            status: 'fail',
            duration: 0,
            error: error.message,
            critical,
          };
        });

      checkPromises.push(promise);
    }

    // Wait for all checks with global timeout
    await Promise.allSettled(checkPromises);

    const overallStatus = this.determineOverallStatus(checks);

    return {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      version: process.env.NEXT_PUBLIC_APP_VERSION || process.env.npm_package_version || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      uptime: Date.now() - this.metrics.startTime,
      portal: this.config.name,
      checks,
      metrics: this.generateMetrics(),
    };
  }

  private async executeCheckWithTimeout(
    name: string,
    check: HealthCheckFunction,
    critical: boolean
  ): Promise<HealthCheck> {
    const startTime = Date.now();

    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Health check timeout')), this.config.timeout);
    });

    try {
      const result = await Promise.race([check(), timeoutPromise]);
      return {
        ...result,
        name,
        duration: Date.now() - startTime,
        critical,
      };
    } catch (error) {
      return {
        name,
        status: 'fail',
        duration: Date.now() - startTime,
        error: error instanceof Error ? error.message : 'Unknown error',
        critical,
      };
    }
  }

  private determineOverallStatus(checks: Record<string, HealthCheck>): HealthStatus {
    let hasFailures = false;
    let hasWarnings = false;
    let hasCriticalFailures = false;

    for (const check of Object.values(checks)) {
      if (check.status === 'fail') {
        hasFailures = true;
        if (check.critical) {
          hasCriticalFailures = true;
        }
      } else if (check.status === 'warn') {
        hasWarnings = true;
      }
    }

    if (hasCriticalFailures) return 'unhealthy';
    if (hasFailures) return 'degraded';
    if (hasWarnings) return 'degraded';
    return 'healthy';
  }

  private generateMetrics(): HealthMetrics {
    const memoryUsage = process.memoryUsage();
    const responseTimes = this.metrics.responseTimes;

    return {
      memory: {
        used: Math.round(memoryUsage.heapUsed / 1024 / 1024),
        total: Math.round(memoryUsage.heapTotal / 1024 / 1024),
        percentage: Math.round((memoryUsage.heapUsed / memoryUsage.heapTotal) * 100),
      },
      requests: {
        total: this.metrics.requestCount,
        errors: this.metrics.errorCount,
        errorRate: this.metrics.requestCount > 0 ?
          Math.round((this.metrics.errorCount / this.metrics.requestCount) * 100) / 100 : 0,
      },
      performance: {
        avgResponseTime: responseTimes.length > 0 ?
          Math.round(responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length) : 0,
        p95ResponseTime: responseTimes.length > 0 ?
          this.calculatePercentile(responseTimes, 95) : 0,
      },
    };
  }

  private updateResponseTime(responseTime: number): void {
    this.metrics.responseTimes.push(responseTime);

    // Keep only last 100 response times
    if (this.metrics.responseTimes.length > 100) {
      this.metrics.responseTimes.shift();
    }
  }

  private calculatePercentile(values: number[], percentile: number): number {
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return Math.round(sorted[index] || 0);
  }

  private getHttpStatusCode(status: HealthStatus): number {
    switch (status) {
      case 'healthy':
        return 200;
      case 'degraded':
        return 200; // Still operational
      case 'unhealthy':
        return 503;
      default:
        return 503;
    }
  }

  private getHealthHeaders(responseTime: number): Record<string, string> {
    return {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Content-Type': 'application/json',
      'X-Health-Check': 'true',
      'X-Response-Time': responseTime.toString(),
      'X-Portal': this.config.name,
    };
  }

  private createErrorResult(error: any, duration: number): HealthCheckResult {
    return {
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      uptime: Date.now() - this.metrics.startTime,
      portal: this.config.name,
      checks: {
        healthCheck: {
          name: 'Health Check System',
          status: 'fail',
          duration,
          error: error instanceof Error ? error.message : 'Health check failed',
        },
      },
      metrics: this.generateMetrics(),
    };
  }

  private initializeDefaultChecks(): void {
    // Memory check
    this.registerCheck('memory', async () => {
      const start = Date.now();
      const memoryUsage = process.memoryUsage();
      const percentage = (memoryUsage.heapUsed / memoryUsage.heapTotal) * 100;

      return {
        name: 'Memory Usage',
        status: percentage > 90 ? 'fail' : percentage > 75 ? 'warn' : 'pass',
        duration: Date.now() - start,
        details: {
          heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024),
          heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024),
          percentage: Math.round(percentage),
        },
        error: percentage > 90 ? `High memory usage: ${Math.round(percentage)}%` : undefined,
      };
    }, true);

    // Environment variables check
    this.registerCheck('environment', async () => {
      const start = Date.now();
      const required = ['NODE_ENV', 'NEXT_PUBLIC_API_URL'];
      const missing: string[] = [];

      for (const varName of required) {
        if (!process.env[varName]) {
          missing.push(varName);
        }
      }

      return {
        name: 'Environment Variables',
        status: missing.length > 0 ? 'fail' : 'pass',
        duration: Date.now() - start,
        details: {
          required: required.length - missing.length,
          missing: missing.length,
          environment: process.env.NODE_ENV,
        },
        error: missing.length > 0 ? `Missing: ${missing.join(', ')}` : undefined,
      };
    }, true);

    // Dependencies check
    this.registerCheck('dependencies', async () => {
      const start = Date.now();
      const modules = ['react', 'next'];
      const failed: string[] = [];

      for (const module of modules) {
        try {
          require.resolve(module);
        } catch {
          failed.push(module);
        }
      }

      return {
        name: 'Dependencies',
        status: failed.length > 0 ? 'fail' : 'pass',
        duration: Date.now() - start,
        details: {
          total: modules.length,
          available: modules.length - failed.length,
          nodeVersion: process.version,
        },
        error: failed.length > 0 ? `Missing: ${failed.join(', ')}` : undefined,
      };
    }, true);

    // Performance check
    this.registerCheck('performance', async () => {
      const start = Date.now();
      const metrics = this.generateMetrics();

      const isHealthy = metrics.performance.avgResponseTime < 1000 &&
                       metrics.requests.errorRate < 0.05;

      return {
        name: 'Performance Metrics',
        status: isHealthy ? 'pass' : 'warn',
        duration: Date.now() - start,
        details: {
          avgResponseTime: metrics.performance.avgResponseTime,
          errorRate: metrics.requests.errorRate,
          requestCount: metrics.requests.total,
        },
      };
    });
  }
}

/**
 * Create a health check router for Next.js API routes
 */
export function createHealthRouter(config: PortalHealthConfig) {
  const healthChecker = new HealthChecker(config);

  return {
    GET: (request: NextRequest) => healthChecker.handleHealthCheck(request),
    healthChecker, // Expose for custom checks
  };
}
