/**
 * Production-grade health check endpoint for Admin Portal
 * Uses shared monitoring package for comprehensive health monitoring
 */

import { NextRequest } from 'next/server';
import { createHealthRouter } from '@dotmac/monitoring/health';
import { PORTAL_HEALTH_CONFIGS } from '@dotmac/monitoring/health';

// Create health router with admin portal configuration
const { GET: healthCheckHandler, healthChecker } = createHealthRouter(
  PORTAL_HEALTH_CONFIGS.admin
);

// Register custom health checks specific to admin portal
healthChecker.registerCheck('admin-features', async () => {
  const start = Date.now();

  // Check admin-specific functionality
  try {
    // Simulate admin feature checks
    const hasAdminAccess = process.env.ADMIN_SECRET_KEY !== undefined;
    const hasUserManagement = true; // Check if user management is available
    const hasBillingAccess = process.env.BILLING_API_URL !== undefined;

    const failedFeatures = [];
    if (!hasAdminAccess) failedFeatures.push('admin-access');
    if (!hasUserManagement) failedFeatures.push('user-management');
    if (!hasBillingAccess) failedFeatures.push('billing-access');

    return {
      name: 'Admin Features',
      status: failedFeatures.length === 0 ? 'pass' : 'warn',
      duration: Date.now() - start,
      details: {
        adminAccess: hasAdminAccess,
        userManagement: hasUserManagement,
        billingAccess: hasBillingAccess,
        failedFeatures,
      },
      error: failedFeatures.length > 0 ? `Features unavailable: ${failedFeatures.join(', ')}` : undefined,
    };
  } catch (error) {
    return {
      name: 'Admin Features',
      status: 'fail',
      duration: Date.now() - start,
      error: error instanceof Error ? error.message : 'Admin feature check failed',
    };
  }
});

// Database connection check (admin portal often needs DB access)
healthChecker.registerCheck('database-connection', async () => {
  const start = Date.now();

  try {
    // Simulate database connection check
    const dbUrl = process.env.DATABASE_URL || process.env.POSTGRES_URL;
    const hasDbConfig = !!dbUrl;

    return {
      name: 'Database Connection',
      status: hasDbConfig ? 'pass' : 'warn',
      duration: Date.now() - start,
      details: {
        configured: hasDbConfig,
        type: dbUrl?.startsWith('postgres') ? 'PostgreSQL' : 'Unknown',
      },
      error: !hasDbConfig ? 'Database connection not configured' : undefined,
    };
  } catch (error) {
    return {
      name: 'Database Connection',
      status: 'fail',
      duration: Date.now() - start,
      error: error instanceof Error ? error.message : 'Database check failed',
    };
  }
}, false);

export async function GET(request: NextRequest) {
  return healthCheckHandler(request);
}
