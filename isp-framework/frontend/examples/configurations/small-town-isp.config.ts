/**
 * Example Configuration for Small Town ISP
 * Demonstrates simplified configuration for smaller operations
 */

import { FrameworkConfig } from '@dotmac/headless';

export const smallTownISPConfig: Partial<FrameworkConfig> = {
  locale: {
    primary: 'en-US',
    supported: ['en-US'],
    fallback: 'en-US',
    dateFormat: {
      short: { month: 'numeric', day: 'numeric', year: 'numeric' },
      medium: { month: 'long', day: 'numeric', year: 'numeric' },
      long: { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' },
      time: { hour: 'numeric', minute: '2-digit' },
    },
  },

  currency: {
    primary: 'USD',
    symbol: '$',
    position: 'before',
    precision: 2,
    thousandsSeparator: ',',
    decimalSeparator: '.',
  },

  business: {
    planTypes: {
      basic: {
        label: 'Basic Internet',
        category: 'residential',
        features: ['25 Mbps Download', '3 Mbps Upload', 'Free WiFi Router', 'Local Support'],
      },
      standard: {
        label: 'Standard Internet',
        category: 'residential',
        features: ['50 Mbps Download', '5 Mbps Upload', 'Advanced Router', 'Priority Support'],
      },
      premium: {
        label: 'Premium Internet',
        category: 'residential',
        features: ['100 Mbps Download', '10 Mbps Upload', 'Mesh WiFi', 'Premium Support'],
      },
      business: {
        label: 'Business Internet',
        category: 'business',
        features: ['100 Mbps Symmetric', 'Static IP', 'Business Support', '99% Uptime SLA'],
      },
    },

    statusTypes: {
      active: {
        label: 'Active',
        color: 'success',
        description: 'Service is working normally',
      },
      pending: {
        label: 'Pending Setup',
        color: 'warning',
        description: 'Installation scheduled',
      },
      suspended: {
        label: 'Service Hold',
        color: 'danger',
        description: 'Service temporarily suspended',
      },
      cancelled: {
        label: 'Cancelled',
        color: 'default',
        description: 'Service has been cancelled',
      },
    },

    partnerTiers: {
      referral: {
        label: 'Referral Partner',
        color: 'primary',
        benefits: ['$25 per referral', 'Community recognition'],
        requirements: { customers: 1, revenue: 0 },
      },
      community: {
        label: 'Community Partner',
        color: 'secondary',
        benefits: ['$50 per referral', 'Quarterly bonus', 'Marketing materials'],
        requirements: { customers: 5, revenue: 500 },
      },
      business: {
        label: 'Business Partner',
        color: 'warning',
        benefits: ['5% commission', 'Direct support line', 'Custom pricing'],
        requirements: { customers: 20, revenue: 2000 },
      },
    },

    units: {
      bandwidth: 'mbps',
      data: 'gb',
      currency: 'USD',
    },
  },

  branding: {
    company: {
      name: 'Prairie Connect',
      logo: '/assets/prairie-logo.svg',
      favicon: '/assets/prairie-favicon.ico',
      colors: {
        primary: '#2563eb',
        secondary: '#64748b',
        accent: '#10b981',
      },
    },
    portal: {
      admin: {
        name: 'Management Portal',
        theme: 'minimal',
      },
      customer: {
        name: 'My Account',
        theme: 'friendly',
      },
      reseller: {
        name: 'Partner Program',
        theme: 'friendly',
      },
    },
  },

  features: {
    multiTenancy: false,
    advancedAnalytics: false,
    automatedBilling: true,
    apiAccess: false,
    whiteLabel: false,
    customDomains: false,
    ssoIntegration: false,
    mobileApp: false,
  },

  api: {
    baseUrl: '/api',
    version: 'v1',
    timeout: 15000,
    retries: 2,
  },

  monitoring: {
    analytics: false,
    errorReporting: true,
    performanceMonitoring: false,
  },
};
