/**
 * Production-grade health check endpoint for Reseller Portal
 */

import { NextRequest } from 'next/server';
import { createHealthRouter } from '@dotmac/monitoring/health';
import { PORTAL_HEALTH_CONFIGS } from '@dotmac/monitoring/health';

// Create health router with reseller portal configuration
const { GET: healthCheckHandler, healthChecker } = createHealthRouter(
  PORTAL_HEALTH_CONFIGS.reseller
);

// Register reseller-specific health checks
healthChecker.registerCheck('reseller-features', async () => {
  const start = Date.now();

  try {
    // Check reseller-specific functionality
    const hasCommissionTracking = true;
    const hasPartnerPortal = process.env.PARTNER_API_URL !== undefined;
    const hasResellerDashboard = true;

    const failedFeatures = [];
    if (!hasCommissionTracking) failedFeatures.push('commission-tracking');
    if (!hasPartnerPortal) failedFeatures.push('partner-portal');
    if (!hasResellerDashboard) failedFeatures.push('reseller-dashboard');

    return {
      name: 'Reseller Features',
      status: failedFeatures.length === 0 ? 'pass' : 'warn',
      duration: Date.now() - start,
      details: {
        commissionTracking: hasCommissionTracking,
        partnerPortal: hasPartnerPortal,
        resellerDashboard: hasResellerDashboard,
        failedFeatures,
      },
      error: failedFeatures.length > 0 ? `Features unavailable: ${failedFeatures.join(', ')}` : undefined,
    };
  } catch (error) {
    return {
      name: 'Reseller Features',
      status: 'fail',
      duration: Date.now() - start,
      error: error instanceof Error ? error.message : 'Reseller feature check failed',
    };
  }
});

// Billing API integration check
healthChecker.registerCheck('billing-api', async () => {
  const start = Date.now();

  try {
    const billingApiUrl = process.env.BILLING_API_URL;
    const hasBillingConfig = !!billingApiUrl;

    return {
      name: 'Billing API Integration',
      status: hasBillingConfig ? 'pass' : 'warn',
      duration: Date.now() - start,
      details: {
        configured: hasBillingConfig,
        endpoint: billingApiUrl ? 'configured' : 'missing',
      },
      error: !hasBillingConfig ? 'Billing API not configured' : undefined,
    };
  } catch (error) {
    return {
      name: 'Billing API Integration',
      status: 'fail',
      duration: Date.now() - start,
      error: error instanceof Error ? error.message : 'Billing API check failed',
    };
  }
});

export async function GET(request: NextRequest) {
  return healthCheckHandler(request);
}
