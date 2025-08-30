'use client';

import { ReactNode } from 'react';
import { UniversalProviders } from '@dotmac/providers';
import { UniversalThemeProvider } from '@dotmac/primitives/themes';
import { themeGenerator } from '@dotmac/design-system';
import { QueryClient } from '@tanstack/react-query';

export interface PortalConfig {
  portal: 'management' | 'customer' | 'reseller' | 'technician';
  authVariant: 'enterprise' | 'customer' | 'public';
  apiBaseUrl?: string;
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
  customProviders
}: PortalProviderFactoryProps) {
  const {
    portal,
    authVariant,
    apiBaseUrl,
    features = {},
    queryClient,
    productionInit = false
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
      devtools: process.env.NODE_ENV === 'development'
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
      devtools: process.env.NODE_ENV === 'development'
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
      devtools: process.env.NODE_ENV === 'development'
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
      devtools: process.env.NODE_ENV === 'development'
    }
  };

  const mergedFeatures = {
    ...defaultFeatures[portal],
    ...features
  };

  // Map portal to theme variant
  const themeVariant = portal === 'management' ? 'management' : portal;

  return (
    <UniversalThemeProvider
      config={{
        variant: themeVariant,
        density: 'comfortable',
        colorScheme: 'system',
        accentColor: 'primary',
        showBrandElements: true,
        animationsEnabled: true,
        highContrast: false,
        reducedMotion: false
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
          }
        }}
      >
        {customProviders}
        {children}
      </UniversalProviders>
    </UniversalThemeProvider>
  );
}
