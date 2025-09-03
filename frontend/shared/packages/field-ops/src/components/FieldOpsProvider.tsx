import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import { useAuth } from '@dotmac/headless';
import { useGPSTracking } from '../gps';
import { workOrderDb } from '../work-orders';
import type { LocationTrackingSettings } from '../gps/types';

interface FieldOpsConfig {
  gpsSettings: LocationTrackingSettings;
  offlineMode: boolean;
  autoSync: boolean;
  syncInterval: number;
  workflowValidation: boolean;
}

interface FieldOpsContextValue {
  config: FieldOpsConfig;
  updateConfig: (config: Partial<FieldOpsConfig>) => void;
  isInitialized: boolean;
  error: string | null;
}

const FieldOpsContext = createContext<FieldOpsContextValue | null>(null);

interface FieldOpsProviderProps {
  children: ReactNode;
  config?: Partial<FieldOpsConfig>;
}

const DEFAULT_CONFIG: FieldOpsConfig = {
  gpsSettings: {
    enabled: true,
    accuracy: 'high',
    updateInterval: 5000,
    backgroundTracking: true,
    geoFenceRadius: 100,
    maxLocationAge: 60000,
  },
  offlineMode: true,
  autoSync: true,
  syncInterval: 30000,
  workflowValidation: true,
};

export function FieldOpsProvider({ children, config: configOverride = {} }: FieldOpsProviderProps) {
  const { user } = useAuth();
  const [config, setConfig] = React.useState<FieldOpsConfig>({
    ...DEFAULT_CONFIG,
    ...configOverride,
  });
  const [isInitialized, setIsInitialized] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Initialize GPS tracking
  const gpsTracking = useGPSTracking({
    settings: config.gpsSettings,
    autoStart: false, // Will start manually when needed
  });

  // Initialize database and services
  useEffect(() => {
    const initializeFieldOps = async () => {
      try {
        setError(null);

        // Initialize database
        await workOrderDb.open();
        console.log('Field ops database initialized');

        // Check GPS permissions if enabled
        if (config.gpsSettings.enabled) {
          const permissionStatus = await gpsTracking.requestPermissions();
          if (!permissionStatus.granted) {
            console.warn('GPS permissions not granted, location features will be limited');
          }
        }

        setIsInitialized(true);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to initialize field operations';
        setError(errorMessage);
        console.error('Field ops initialization failed:', err);
      }
    };

    if (user) {
      initializeFieldOps();
    }
  }, [user, config.gpsSettings.enabled]);

  // Update configuration
  const updateConfig = React.useCallback(
    (newConfig: Partial<FieldOpsConfig>) => {
      setConfig((prev) => {
        const updated = { ...prev, ...newConfig };

        // Update GPS settings if changed
        if (newConfig.gpsSettings) {
          gpsTracking.updateSettings(newConfig.gpsSettings);
        }

        return updated;
      });
    },
    [gpsTracking]
  );

  const contextValue: FieldOpsContextValue = {
    config,
    updateConfig,
    isInitialized,
    error,
  };

  return <FieldOpsContext.Provider value={contextValue}>{children}</FieldOpsContext.Provider>;
}

export function useFieldOps(): FieldOpsContextValue {
  const context = useContext(FieldOpsContext);

  if (!context) {
    throw new Error('useFieldOps must be used within a FieldOpsProvider');
  }

  return context;
}
