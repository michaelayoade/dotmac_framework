/**
 * Production-ready health check system
 * Provides comprehensive health monitoring for all DotMac portals
 */

export { HealthChecker, createHealthRouter } from './health-checker';
export { AdvancedHealthCheck } from './advanced-health-check';
export type {
  HealthCheckResult,
  HealthStatus,
  HealthCheck,
  HealthMetrics,
  PortalHealthConfig,
} from './types';

// Default health check configurations for each portal
export const PORTAL_HEALTH_CONFIGS = {
  customer: {
    name: 'Customer Portal',
    critical: ['memory', 'environment', 'dependencies'],
    optional: ['performance', 'external-apis'],
    cacheTtl: 30000, // 30 seconds
    timeout: 5000, // 5 seconds
  },
  admin: {
    name: 'Admin Portal',
    critical: ['memory', 'environment', 'dependencies'],
    optional: ['performance', 'database-connection'],
    cacheTtl: 30000,
    timeout: 5000,
  },
  reseller: {
    name: 'Reseller Portal',
    critical: ['memory', 'environment', 'dependencies'],
    optional: ['performance', 'billing-api'],
    cacheTtl: 30000,
    timeout: 5000,
  },
  technician: {
    name: 'Technician Portal',
    critical: ['memory', 'environment', 'dependencies'],
    optional: ['performance', 'inventory-api'],
    cacheTtl: 45000, // Longer cache for mobile
    timeout: 3000, // Shorter timeout for mobile
  },
  'management-admin': {
    name: 'Management Admin Portal',
    critical: ['memory', 'environment', 'dependencies', 'database-connection'],
    optional: ['performance', 'external-apis', 'cache-status'],
    cacheTtl: 20000, // More frequent checks
    timeout: 7000, // Longer timeout for complex checks
  },
  'management-reseller': {
    name: 'Management Reseller Portal',
    critical: ['memory', 'environment', 'dependencies'],
    optional: ['performance', 'billing-integration'],
    cacheTtl: 30000,
    timeout: 5000,
  },
  'tenant-portal': {
    name: 'Tenant Portal',
    critical: ['memory', 'environment', 'dependencies'],
    optional: ['performance', 'tenant-isolation'],
    cacheTtl: 30000,
    timeout: 5000,
  },
} as const;
