import { useState, useEffect, useCallback, useRef } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  PluginHealth,
  PluginConfigValidation,
  UsePluginLifecycleResult
} from '../types';

const API_ENDPOINTS = {
  PLUGIN_INITIALIZE: '/api/plugins/lifecycle/initialize',
  PLUGIN_SHUTDOWN: '/api/plugins/lifecycle/shutdown',
  PLUGIN_RESTART: '/api/plugins/lifecycle/restart',
  PLUGIN_HEALTH: '/api/plugins/lifecycle/health',
  PLUGIN_CONFIG: '/api/plugins/lifecycle/config',
  PLUGIN_CONFIG_VALIDATE: '/api/plugins/lifecycle/config/validate',
  HEALTH_MONITORING: '/api/plugins/lifecycle/health-monitoring',
  BULK_INITIALIZE: '/api/plugins/lifecycle/bulk/initialize',
  BULK_SHUTDOWN: '/api/plugins/lifecycle/bulk/shutdown'
} as const;

export function usePluginLifecycle(): UsePluginLifecycleResult {
  const [healthMonitoringActive, setHealthMonitoringActive] = useState(false);
  const [lastHealthCheck, setLastHealthCheck] = useState<string | null>(null);
  const healthCheckInterval = useRef<NodeJS.Timeout | null>(null);

  const apiClient = useApiClient();

  const initializePlugin = useCallback(async (pluginKey: string): Promise<boolean> => {
    try {
      await apiClient.post(API_ENDPOINTS.PLUGIN_INITIALIZE, { plugin_key: pluginKey });
      return true;
    } catch (err) {
      console.error(`Failed to initialize plugin ${pluginKey}:`, err);
      return false;
    }
  }, [apiClient]);

  const shutdownPlugin = useCallback(async (pluginKey: string): Promise<boolean> => {
    try {
      await apiClient.post(API_ENDPOINTS.PLUGIN_SHUTDOWN, { plugin_key: pluginKey });
      return true;
    } catch (err) {
      console.error(`Failed to shutdown plugin ${pluginKey}:`, err);
      return false;
    }
  }, [apiClient]);

  const restartPlugin = useCallback(async (pluginKey: string): Promise<boolean> => {
    try {
      await apiClient.post(API_ENDPOINTS.PLUGIN_RESTART, { plugin_key: pluginKey });
      return true;
    } catch (err) {
      console.error(`Failed to restart plugin ${pluginKey}:`, err);
      return false;
    }
  }, [apiClient]);

  const performHealthCheck = useCallback(async (pluginKey: string): Promise<PluginHealth> => {
    try {
      const response = await apiClient.get<PluginHealth>(
        `${API_ENDPOINTS.PLUGIN_HEALTH}/${pluginKey}`
      );

      setLastHealthCheck(new Date().toISOString());
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Health check failed';
      throw new Error(`Failed to perform health check for ${pluginKey}: ${message}`);
    }
  }, [apiClient]);

  const startHealthMonitoring = useCallback(async () => {
    try {
      await apiClient.post(API_ENDPOINTS.HEALTH_MONITORING, { action: 'start' });
      setHealthMonitoringActive(true);

      // Start local health check interval (every minute)
      if (healthCheckInterval.current) {
        clearInterval(healthCheckInterval.current);
      }

      healthCheckInterval.current = setInterval(() => {
        setLastHealthCheck(new Date().toISOString());
      }, 60000);

    } catch (err) {
      console.error('Failed to start health monitoring:', err);
      throw new Error('Failed to start health monitoring');
    }
  }, [apiClient]);

  const stopHealthMonitoring = useCallback(async () => {
    try {
      await apiClient.post(API_ENDPOINTS.HEALTH_MONITORING, { action: 'stop' });
      setHealthMonitoringActive(false);

      // Clear local health check interval
      if (healthCheckInterval.current) {
        clearInterval(healthCheckInterval.current);
        healthCheckInterval.current = null;
      }

    } catch (err) {
      console.error('Failed to stop health monitoring:', err);
      throw new Error('Failed to stop health monitoring');
    }
  }, [apiClient]);

  const updatePluginConfig = useCallback(async (
    pluginKey: string,
    config: Record<string, any>
  ) => {
    try {
      await apiClient.post(API_ENDPOINTS.PLUGIN_CONFIG, {
        plugin_key: pluginKey,
        config
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Configuration update failed';
      throw new Error(`Failed to update configuration for ${pluginKey}: ${message}`);
    }
  }, [apiClient]);

  const validatePluginConfig = useCallback(async (
    pluginKey: string,
    config: Record<string, any>
  ): Promise<PluginConfigValidation> => {
    try {
      const response = await apiClient.post<PluginConfigValidation>(
        API_ENDPOINTS.PLUGIN_CONFIG_VALIDATE,
        {
          plugin_key: pluginKey,
          config
        }
      );

      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Configuration validation failed';
      throw new Error(`Failed to validate configuration for ${pluginKey}: ${message}`);
    }
  }, [apiClient]);

  const initializePluginsByDomain = useCallback(async (
    domain: string
  ): Promise<Record<string, boolean>> => {
    try {
      const response = await apiClient.post<Record<string, boolean>>(
        API_ENDPOINTS.BULK_INITIALIZE,
        { domain }
      );

      return response.data;
    } catch (err) {
      console.error(`Failed to initialize plugins in domain ${domain}:`, err);
      return {};
    }
  }, [apiClient]);

  const shutdownPluginsByDomain = useCallback(async (
    domain: string
  ): Promise<Record<string, boolean>> => {
    try {
      const response = await apiClient.post<Record<string, boolean>>(
        API_ENDPOINTS.BULK_SHUTDOWN,
        { domain }
      );

      return response.data;
    } catch (err) {
      console.error(`Failed to shutdown plugins in domain ${domain}:`, err);
      return {};
    }
  }, [apiClient]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (healthCheckInterval.current) {
        clearInterval(healthCheckInterval.current);
      }
    };
  }, []);

  return {
    // Lifecycle operations
    initializePlugin,
    shutdownPlugin,
    restartPlugin,

    // Health monitoring
    performHealthCheck,
    startHealthMonitoring,
    stopHealthMonitoring,

    // Configuration
    updatePluginConfig,
    validatePluginConfig,

    // Bulk operations
    initializePluginsByDomain,
    shutdownPluginsByDomain,

    // Monitoring state
    healthMonitoringActive,
    lastHealthCheck
  };
}
