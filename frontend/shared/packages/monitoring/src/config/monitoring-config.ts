/**
 * Centralized Monitoring Configuration
 * Production-ready configuration management for all monitoring systems
 */

import type { PortalType } from '../sentry/types';

export interface MonitoringConfig {
  sentry: {
    enabled: boolean;
    dsn?: string;
    environment: string;
    release?: string;
    enableReplay: boolean;
    enableProfiling: boolean;
    sampleRates: {
      traces: number;
      profiles: number;
      replays: number;
      replayOnError: number;
    };
  };
  health: {
    enabled: boolean;
    cacheTtl: number;
    timeout: number;
    criticalChecks: string[];
    optionalChecks: string[];
  };
  performance: {
    enabled: boolean;
    enableCoreWebVitals: boolean;
    enableCustomMetrics: boolean;
    budgets: {
      renderTime: number;
      interactionTime: number;
      memoryUsage: number;
      bundleSize: number;
    };
  };
  analytics: {
    enabled: boolean;
    trackPageViews: boolean;
    trackUserInteractions: boolean;
    trackPerformance: boolean;
  };
}

/**
 * Production-ready monitoring configurations for each portal
 */
export const PRODUCTION_MONITORING_CONFIGS: Record<PortalType, MonitoringConfig> = {
  customer: {
    sentry: {
      enabled: true,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION,
      enableReplay: true,
      enableProfiling: true,
      sampleRates: {
        traces: 0.1, // 10% tracing for high traffic
        profiles: 0.1, // 10% profiling
        replays: 0.01, // 1% session replay
        replayOnError: 1.0, // 100% replay on errors
      },
    },
    health: {
      enabled: true,
      cacheTtl: 30000, // 30 seconds
      timeout: 5000, // 5 seconds
      criticalChecks: ['memory', 'environment', 'dependencies'],
      optionalChecks: ['performance', 'external-apis'],
    },
    performance: {
      enabled: true,
      enableCoreWebVitals: true,
      enableCustomMetrics: true,
      budgets: {
        renderTime: 16, // 60fps target
        interactionTime: 100, // Fast interaction
        memoryUsage: 50 * 1024 * 1024, // 50MB
        bundleSize: 2 * 1024 * 1024, // 2MB
      },
    },
    analytics: {
      enabled: false, // Privacy-focused customer portal
      trackPageViews: false,
      trackUserInteractions: false,
      trackPerformance: true,
    },
  },

  admin: {
    sentry: {
      enabled: true,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION,
      enableReplay: true,
      enableProfiling: false,
      sampleRates: {
        traces: 0.3, // 30% tracing for admin actions
        profiles: 0, // No profiling for admin
        replays: 0.1, // 10% session replay
        replayOnError: 1.0,
      },
    },
    health: {
      enabled: true,
      cacheTtl: 30000,
      timeout: 5000,
      criticalChecks: ['memory', 'environment', 'dependencies', 'database-connection'],
      optionalChecks: ['performance', 'admin-features'],
    },
    performance: {
      enabled: true,
      enableCoreWebVitals: true,
      enableCustomMetrics: true,
      budgets: {
        renderTime: 33, // 30fps acceptable for admin
        interactionTime: 200, // Admin users are more patient
        memoryUsage: 100 * 1024 * 1024, // 100MB
        bundleSize: 3 * 1024 * 1024, // 3MB
      },
    },
    analytics: {
      enabled: true,
      trackPageViews: true,
      trackUserInteractions: true,
      trackPerformance: true,
    },
  },

  reseller: {
    sentry: {
      enabled: true,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION,
      enableReplay: true,
      enableProfiling: false,
      sampleRates: {
        traces: 0.3,
        profiles: 0,
        replays: 0.05, // 5% session replay
        replayOnError: 1.0,
      },
    },
    health: {
      enabled: true,
      cacheTtl: 30000,
      timeout: 5000,
      criticalChecks: ['memory', 'environment', 'dependencies'],
      optionalChecks: ['performance', 'billing-api', 'reseller-features'],
    },
    performance: {
      enabled: false, // Lighter monitoring for reseller portal
      enableCoreWebVitals: true,
      enableCustomMetrics: false,
      budgets: {
        renderTime: 33,
        interactionTime: 200,
        memoryUsage: 75 * 1024 * 1024,
        bundleSize: 2.5 * 1024 * 1024,
      },
    },
    analytics: {
      enabled: true,
      trackPageViews: true,
      trackUserInteractions: true,
      trackPerformance: false,
    },
  },

  technician: {
    sentry: {
      enabled: true,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION,
      enableReplay: false, // Mobile-friendly - no replay
      enableProfiling: false,
      sampleRates: {
        traces: 0.5, // Higher sampling for fewer users
        profiles: 0,
        replays: 0, // No replays on mobile
        replayOnError: 0,
      },
    },
    health: {
      enabled: true,
      cacheTtl: 45000, // Longer cache for mobile
      timeout: 3000, // Shorter timeout for mobile
      criticalChecks: ['memory', 'environment', 'dependencies'],
      optionalChecks: ['performance'],
    },
    performance: {
      enabled: false, // Minimal monitoring for mobile
      enableCoreWebVitals: true,
      enableCustomMetrics: false,
      budgets: {
        renderTime: 50, // Mobile-friendly
        interactionTime: 300,
        memoryUsage: 30 * 1024 * 1024, // 30MB for mobile
        bundleSize: 1 * 1024 * 1024, // 1MB for mobile
      },
    },
    analytics: {
      enabled: false,
      trackPageViews: false,
      trackUserInteractions: false,
      trackPerformance: false,
    },
  },

  'management-admin': {
    sentry: {
      enabled: true,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION,
      enableReplay: true,
      enableProfiling: true, // High importance portal
      sampleRates: {
        traces: 0.2, // 20% tracing
        profiles: 0.1, // 10% profiling
        replays: 0.1, // 10% session replay
        replayOnError: 1.0,
      },
    },
    health: {
      enabled: true,
      cacheTtl: 20000, // More frequent checks
      timeout: 7000, // Longer timeout for complex checks
      criticalChecks: ['memory', 'environment', 'dependencies', 'database-connection'],
      optionalChecks: ['performance', 'external-apis', 'cache-status'],
    },
    performance: {
      enabled: true,
      enableCoreWebVitals: true,
      enableCustomMetrics: true,
      budgets: {
        renderTime: 25,
        interactionTime: 150,
        memoryUsage: 150 * 1024 * 1024, // 150MB
        bundleSize: 4 * 1024 * 1024, // 4MB
      },
    },
    analytics: {
      enabled: true,
      trackPageViews: true,
      trackUserInteractions: true,
      trackPerformance: true,
    },
  },

  'management-reseller': {
    sentry: {
      enabled: true,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION,
      enableReplay: true,
      enableProfiling: false,
      sampleRates: {
        traces: 0.3,
        profiles: 0,
        replays: 0.05,
        replayOnError: 1.0,
      },
    },
    health: {
      enabled: true,
      cacheTtl: 30000,
      timeout: 5000,
      criticalChecks: ['memory', 'environment', 'dependencies'],
      optionalChecks: ['performance', 'billing-integration'],
    },
    performance: {
      enabled: false,
      enableCoreWebVitals: true,
      enableCustomMetrics: false,
      budgets: {
        renderTime: 33,
        interactionTime: 200,
        memoryUsage: 100 * 1024 * 1024,
        bundleSize: 3 * 1024 * 1024,
      },
    },
    analytics: {
      enabled: true,
      trackPageViews: true,
      trackUserInteractions: true,
      trackPerformance: false,
    },
  },

  'tenant-portal': {
    sentry: {
      enabled: true,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION,
      enableReplay: true,
      enableProfiling: false,
      sampleRates: {
        traces: 0.4, // 40% tracing for smaller user base
        profiles: 0,
        replays: 0.1, // 10% session replay
        replayOnError: 1.0,
      },
    },
    health: {
      enabled: true,
      cacheTtl: 30000,
      timeout: 5000,
      criticalChecks: ['memory', 'environment', 'dependencies'],
      optionalChecks: ['performance', 'tenant-isolation'],
    },
    performance: {
      enabled: false,
      enableCoreWebVitals: true,
      enableCustomMetrics: false,
      budgets: {
        renderTime: 33,
        interactionTime: 200,
        memoryUsage: 75 * 1024 * 1024,
        bundleSize: 2.5 * 1024 * 1024,
      },
    },
    analytics: {
      enabled: false, // Privacy-focused
      trackPageViews: false,
      trackUserInteractions: false,
      trackPerformance: true,
    },
  },
};

/**
 * Get monitoring configuration for a specific portal
 */
export function getMonitoringConfig(portal: PortalType): MonitoringConfig {
  const config = PRODUCTION_MONITORING_CONFIGS[portal];

  if (!config) {
    throw new Error(`Unknown portal type: ${portal}`);
  }

  // Override with environment-specific configurations
  return {
    ...config,
    sentry: {
      ...config.sentry,
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || process.env.SENTRY_DSN,
      environment: process.env.NODE_ENV || 'production',
      release: process.env.NEXT_PUBLIC_APP_VERSION || process.env.APP_VERSION,
      enabled: config.sentry.enabled && !!process.env.NEXT_PUBLIC_SENTRY_DSN,
    },
  };
}

/**
 * Validate monitoring configuration
 */
export function validateMonitoringConfig(portal: PortalType): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const config = getMonitoringConfig(portal);
  const errors: string[] = [];
  const warnings: string[] = [];

  // Sentry validation
  if (config.sentry.enabled && !config.sentry.dsn) {
    errors.push('Sentry is enabled but SENTRY_DSN is not configured');
  }

  if (config.sentry.enableReplay && config.sentry.sampleRates.replays === 0) {
    warnings.push('Session replay is enabled but sample rate is 0');
  }

  // Health check validation
  if (config.health.enabled && config.health.timeout < 1000) {
    warnings.push('Health check timeout is very low (<1s)');
  }

  if (config.health.cacheTtl < 10000) {
    warnings.push('Health check cache TTL is very low (<10s)');
  }

  // Performance validation
  if (config.performance.enabled && config.performance.budgets.renderTime > 100) {
    warnings.push('Render time budget is very high (>100ms)');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}
