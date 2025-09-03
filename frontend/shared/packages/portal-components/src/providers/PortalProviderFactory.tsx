'use client';

import { ReactNode } from 'react';
import { UniversalProviders } from '@dotmac/providers';
import { UniversalThemeProvider } from '@dotmac/primitives/themes';
import { themeGenerator } from '@dotmac/design-system';
import { QueryClient } from '@tanstack/react-query';

export interface PortalConfig {
  portal:
    | 'management'
    | 'customer'
    | 'reseller'
    | 'technician'
    | 'admin'
    | 'management-admin'
    | 'management-reseller'
    | 'tenant-portal';
  authVariant: 'enterprise' | 'customer' | 'public';
  apiBaseUrl?: string;
  density?: 'compact' | 'cozy' | 'comfortable';
  colorScheme?: 'light' | 'dark' | 'system';
  features?: {
    notifications?: boolean;
    realtime?: boolean;
    analytics?: boolean;
    tenantManagement?: boolean;
    errorHandling?: boolean;
    toasts?: boolean;
    devtools?: boolean;
    enableBatchOperations?: boolean;
    enableRealTimeSync?: boolean;
    enableAdvancedAnalytics?: boolean;
    enableAuditLogging?: boolean;
  };
  queryClient?: QueryClient;
  productionInit?: boolean;
}

export interface PortalProviderFactoryProps {
  config: PortalConfig;
  children: ReactNode;
  customProviders?: ReactNode;
}

export function PortalProviderFactory({
  config,
  children,
  customProviders,
}: PortalProviderFactoryProps) {
  const {
    portal,
    authVariant,
    apiBaseUrl,
    density,
    colorScheme = 'system',
    features = {},
    queryClient,
    productionInit = false,
  } = config;

  // Default feature sets per portal type
  const defaultFeatures = {
    management: {
      notifications: true,
      realtime: true,
      analytics: true,
      tenantManagement: true,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: true,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: true,
      enableAuditLogging: true,
      devtools: process.env.NODE_ENV === 'development',
    },
    'management-admin': {
      notifications: true,
      realtime: true,
      analytics: true,
      tenantManagement: true,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: true,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: true,
      enableAuditLogging: true,
      devtools: process.env.NODE_ENV === 'development',
    },
    'management-reseller': {
      notifications: true,
      realtime: true,
      analytics: true,
      tenantManagement: true,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: true,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: true,
      enableAuditLogging: true,
      devtools: process.env.NODE_ENV === 'development',
    },
    customer: {
      notifications: true,
      realtime: true,
      analytics: false,
      tenantManagement: false,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: false,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: false,
      enableAuditLogging: false,
      devtools: process.env.NODE_ENV === 'development',
    },
    reseller: {
      notifications: true,
      realtime: true,
      analytics: true,
      tenantManagement: true,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: true,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: true,
      enableAuditLogging: true,
      devtools: process.env.NODE_ENV === 'development',
    },
    technician: {
      notifications: true,
      realtime: true,
      analytics: false,
      tenantManagement: false,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: false,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: false,
      enableAuditLogging: false,
      devtools: process.env.NODE_ENV === 'development',
    },
    admin: {
      notifications: true,
      realtime: true,
      analytics: true,
      tenantManagement: true,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: true,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: true,
      enableAuditLogging: true,
      devtools: process.env.NODE_ENV === 'development',
    },
    'tenant-portal': {
      notifications: true,
      realtime: true,
      analytics: true,
      tenantManagement: true,
      errorHandling: true,
      toasts: true,
      enableBatchOperations: true,
      enableRealTimeSync: true,
      enableAdvancedAnalytics: true,
      enableAuditLogging: true,
      devtools: process.env.NODE_ENV === 'development',
    },
  };

  const mergedFeatures = {
    ...defaultFeatures[portal],
    ...features,
  };

  // Map portal to theme variant
  const themeVariant =
    portal === 'management-admin' || portal === 'management'
      ? 'management'
      : portal === 'management-reseller'
        ? 'reseller'
        : portal === 'tenant-portal'
          ? 'management'
          : portal;

  // Default density per portal
  const defaultDensity: Record<PortalConfig['portal'], 'compact' | 'cozy' | 'comfortable'> = {
    management: 'comfortable',
    'management-admin': 'comfortable',
    'management-reseller': 'comfortable',
    admin: 'comfortable',
    customer: 'cozy',
    reseller: 'cozy',
    technician: 'compact',
    'tenant-portal': 'cozy',
  };

  const resolvedDensity = density || defaultDensity[portal];

  return (
    <UniversalThemeProvider
      config={{
        variant: themeVariant,
        density: resolvedDensity,
        colorScheme,
        accentColor: 'primary',
        showBrandElements: true,
        animationsEnabled: true,
        highContrast: false,
        reducedMotion: false,
      }}
    >
      <UniversalProviders
        portal={portal}
        authVariant={authVariant}
        features={mergedFeatures}
        queryClient={queryClient}
        config={{
          productionInit,
          toastConfig: {
            maxToasts: 5,
            defaultDuration: 5000,
          },
        }}
      >
        {customProviders}
        {children}
      </UniversalProviders>
    </UniversalThemeProvider>
  );
}
