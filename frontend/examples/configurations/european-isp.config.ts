/**
 * Example Configuration for European ISP
 * Demonstrates multi-currency, multi-locale configuration
 */

import { FrameworkConfig } from '@dotmac/headless';

export const europeanISPConfig: Partial<FrameworkConfig> = {
  locale: {
    primary: 'de-DE',
    supported: ['de-DE', 'fr-FR', 'en-GB', 'es-ES', 'it-IT'],
    fallback: 'en-GB',
    dateFormat: {
      short: { day: '2-digit', month: '2-digit', year: 'numeric' },
      medium: { day: 'numeric', month: 'long', year: 'numeric' },
      long: { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' },
      time: { hour: '2-digit', minute: '2-digit', hour12: false },
    },
  },

  currency: {
    primary: 'EUR',
    symbol: '€',
    position: 'after',
    precision: 2,
    thousandsSeparator: '.',
    decimalSeparator: ',',
  },

  business: {
    planTypes: {
      home_basic: {
        label: 'Home Basic',
        category: 'residential',
        features: ['50 Mbit/s Download', '10 Mbit/s Upload', 'WLAN Router', '24/7 Support'],
      },
      home_comfort: {
        label: 'Home Comfort',
        category: 'residential',
        features: ['100 Mbit/s Download', '40 Mbit/s Upload', 'Premium Router', 'TV Package'],
      },
      home_premium: {
        label: 'Home Premium',
        category: 'residential',
        features: ['250 Mbit/s Download', '50 Mbit/s Upload', 'Mesh System', 'Premium TV'],
      },
      business_start: {
        label: 'Business Start',
        category: 'business',
        features: ['100 Mbit/s symmetrisch', 'Statische IP', 'Business Support', 'SLA 99,5%'],
      },
      business_pro: {
        label: 'Business Pro',
        category: 'business',
        features: ['500 Mbit/s symmetrisch', 'Multiple IPs', 'Priority Support', 'SLA 99,9%'],
      },
      enterprise: {
        label: 'Enterprise',
        category: 'enterprise',
        features: ['Dedicated Line', 'Custom Config', 'Account Manager', 'SLA 99,99%'],
      },
    },

    statusTypes: {
      active: {
        label: 'Aktiv',
        color: 'success',
        description: 'Service läuft einwandfrei',
      },
      pending: {
        label: 'Wartend',
        color: 'warning',
        description: 'Aktivierung in Bearbeitung',
      },
      suspended: {
        label: 'Gesperrt',
        color: 'danger',
        description: 'Service vorübergehend gesperrt',
      },
      maintenance: {
        label: 'Wartung',
        color: 'info',
        description: 'Planmäßige Wartungsarbeiten',
      },
    },

    partnerTiers: {
      bronze: {
        label: 'Bronze Partner',
        color: 'secondary',
        benefits: ['3% Provision', 'Basis Support', 'Marketing Materialien'],
        requirements: { customers: 5, revenue: 2500 },
      },
      silver: {
        label: 'Silber Partner',
        color: 'primary',
        benefits: ['5% Provision', 'Priority Support', 'Co-Marketing'],
        requirements: { customers: 15, revenue: 7500 },
      },
      gold: {
        label: 'Gold Partner',
        color: 'warning',
        benefits: ['8% Provision', 'Dedicated Support', 'Custom Materials'],
        requirements: { customers: 30, revenue: 20000 },
      },
      platinum: {
        label: 'Platin Partner',
        color: 'success',
        benefits: ['12% Provision', 'Account Manager', 'API Access'],
        requirements: { customers: 75, revenue: 50000 },
      },
    },

    units: {
      bandwidth: 'mbps',
      data: 'gb',
      currency: 'EUR',
    },
  },

  branding: {
    company: {
      name: 'NetConnect Deutschland',
      logo: '/assets/netconnect-logo.svg',
      favicon: '/assets/netconnect-favicon.ico',
      colors: {
        primary: '#1a365d',
        secondary: '#2d3748',
        accent: '#38a169',
      },
    },
    portal: {
      admin: {
        name: 'Admin Portal',
        theme: 'professional',
      },
      customer: {
        name: 'Kunden Portal',
        theme: 'friendly',
      },
      reseller: {
        name: 'Partner Portal',
        theme: 'business',
      },
    },
  },

  features: {
    multiTenancy: true,
    advancedAnalytics: true,
    automatedBilling: true,
    apiAccess: true,
    whiteLabel: true,
    customDomains: true,
    ssoIntegration: true,
    mobileApp: false,
  },

  api: {
    baseUrl: 'https://api.netconnect.de',
    version: 'v1',
    timeout: 30000,
    retries: 3,
  },

  monitoring: {
    analytics: true,
    errorReporting: true,
    performanceMonitoring: true,
    endpoint: 'https://analytics.netconnect.de/metrics',
  },
};
