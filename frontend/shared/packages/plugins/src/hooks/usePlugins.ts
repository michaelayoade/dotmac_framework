import { useState, useEffect, useCallback } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  Plugin,
  PluginInstallRequest,
  PluginUpdateRequest,
  PluginUninstallRequest,
  PluginSearchFilters,
  PluginHealth,
  PluginSystemHealth,
  UsePluginsResult,
} from '../types';

const API_ENDPOINTS = {
  PLUGINS: '/api/plugins',
  PLUGIN_INSTALL: '/api/plugins/install',
  PLUGIN_UPDATE: '/api/plugins/update',
  PLUGIN_UNINSTALL: '/api/plugins/uninstall',
  PLUGIN_ENABLE: '/api/plugins/enable',
  PLUGIN_DISABLE: '/api/plugins/disable',
  PLUGIN_RESTART: '/api/plugins/restart',
  PLUGIN_HEALTH: '/api/plugins/health',
  SYSTEM_HEALTH: '/api/plugins/system/health',
} as const;

export function usePlugins(): UsePluginsResult {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const fetchPlugins = useCallback(
    async (domain?: string) => {
      try {
        setLoading(true);
        setError(null);

        const params = domain ? { domain } : {};
        const response = await apiClient.get<Plugin[]>(API_ENDPOINTS.PLUGINS, { params });

        setPlugins(response.data);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to fetch plugins';
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [apiClient]
  );

  const installPlugin = useCallback(
    async (request: PluginInstallRequest) => {
      try {
        setError(null);

        await apiClient.post(API_ENDPOINTS.PLUGIN_INSTALL, request);

        // Refresh plugins list after installation
        await fetchPlugins();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to install plugin';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient, fetchPlugins]
  );

  const updatePlugin = useCallback(
    async (request: PluginUpdateRequest) => {
      try {
        setError(null);

        await apiClient.post(API_ENDPOINTS.PLUGIN_UPDATE, request);

        // Refresh plugins list after update
        await fetchPlugins();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update plugin';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient, fetchPlugins]
  );

  const uninstallPlugin = useCallback(
    async (request: PluginUninstallRequest) => {
      try {
        setError(null);

        await apiClient.post(API_ENDPOINTS.PLUGIN_UNINSTALL, request);

        // Refresh plugins list after uninstallation
        await fetchPlugins();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to uninstall plugin';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient, fetchPlugins]
  );

  const enablePlugin = useCallback(
    async (pluginKey: string) => {
      try {
        setError(null);

        await apiClient.post(API_ENDPOINTS.PLUGIN_ENABLE, { plugin_key: pluginKey });

        // Update plugin status in local state
        setPlugins((prev) =>
          prev.map((plugin) => {
            const key = `${plugin.metadata.domain}.${plugin.metadata.name}`;
            if (key === pluginKey) {
              return { ...plugin, status: 'active' as any };
            }
            return plugin;
          })
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to enable plugin';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient]
  );

  const disablePlugin = useCallback(
    async (pluginKey: string) => {
      try {
        setError(null);

        await apiClient.post(API_ENDPOINTS.PLUGIN_DISABLE, { plugin_key: pluginKey });

        // Update plugin status in local state
        setPlugins((prev) =>
          prev.map((plugin) => {
            const key = `${plugin.metadata.domain}.${plugin.metadata.name}`;
            if (key === pluginKey) {
              return { ...plugin, status: 'inactive' as any };
            }
            return plugin;
          })
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to disable plugin';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient]
  );

  const restartPlugin = useCallback(
    async (pluginKey: string) => {
      try {
        setError(null);

        await apiClient.post(API_ENDPOINTS.PLUGIN_RESTART, { plugin_key: pluginKey });

        // Refresh plugins list to get updated status
        await fetchPlugins();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to restart plugin';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient, fetchPlugins]
  );

  const getPlugin = useCallback(
    (domain: string, name: string): Plugin | null => {
      return (
        plugins.find(
          (plugin) => plugin.metadata.domain === domain && plugin.metadata.name === name
        ) || null
      );
    },
    [plugins]
  );

  const getPluginHealth = useCallback(
    async (pluginKey: string): Promise<PluginHealth> => {
      try {
        const response = await apiClient.get<PluginHealth>(
          `${API_ENDPOINTS.PLUGIN_HEALTH}/${pluginKey}`
        );
        return response.data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to get plugin health';
        throw new Error(message);
      }
    },
    [apiClient]
  );

  const findPlugins = useCallback(
    (filters: PluginSearchFilters): Plugin[] => {
      return plugins.filter((plugin) => {
        // Filter by domain
        if (filters.domain && plugin.metadata.domain !== filters.domain) {
          return false;
        }

        // Filter by status
        if (filters.status && plugin.status !== filters.status) {
          return false;
        }

        // Filter by category
        if (filters.category && !plugin.metadata.categories.includes(filters.category)) {
          return false;
        }

        // Filter by tags
        if (filters.tags && filters.tags.length > 0) {
          const hasMatchingTag = filters.tags.some((tag) => plugin.metadata.tags.includes(tag));
          if (!hasMatchingTag) {
            return false;
          }
        }

        // Filter by name pattern
        if (filters.name_pattern) {
          const pattern = new RegExp(filters.name_pattern, 'i');
          if (
            !pattern.test(plugin.metadata.name) &&
            !pattern.test(plugin.metadata.description || '')
          ) {
            return false;
          }
        }

        // Filter by author
        if (filters.author && plugin.metadata.author !== filters.author) {
          return false;
        }

        return true;
      });
    },
    [plugins]
  );

  const getAvailableDomains = useCallback((): string[] => {
    const domains = new Set(plugins.map((plugin) => plugin.metadata.domain));
    return Array.from(domains).sort();
  }, [plugins]);

  const enableMultiplePlugins = useCallback(
    async (pluginKeys: string[]): Promise<Record<string, boolean>> => {
      const results: Record<string, boolean> = {};

      for (const pluginKey of pluginKeys) {
        try {
          await enablePlugin(pluginKey);
          results[pluginKey] = true;
        } catch (err) {
          results[pluginKey] = false;
        }
      }

      return results;
    },
    [enablePlugin]
  );

  const disableMultiplePlugins = useCallback(
    async (pluginKeys: string[]): Promise<Record<string, boolean>> => {
      const results: Record<string, boolean> = {};

      for (const pluginKey of pluginKeys) {
        try {
          await disablePlugin(pluginKey);
          results[pluginKey] = true;
        } catch (err) {
          results[pluginKey] = false;
        }
      }

      return results;
    },
    [disablePlugin]
  );

  const getSystemHealth = useCallback(async (): Promise<PluginSystemHealth> => {
    try {
      const response = await apiClient.get<PluginSystemHealth>(API_ENDPOINTS.SYSTEM_HEALTH);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to get system health';
      throw new Error(message);
    }
  }, [apiClient]);

  const refreshPlugins = useCallback(async () => {
    await fetchPlugins();
  }, [fetchPlugins]);

  // Initial load
  useEffect(() => {
    fetchPlugins();
  }, [fetchPlugins]);

  return {
    plugins,
    loading,
    error,

    // Plugin management
    installPlugin,
    updatePlugin,
    uninstallPlugin,

    // Plugin control
    enablePlugin,
    disablePlugin,
    restartPlugin,

    // Plugin information
    getPlugin,
    getPluginHealth,

    // Filtering and search
    findPlugins,
    getAvailableDomains,

    // Bulk operations
    enableMultiplePlugins,
    disableMultiplePlugins,

    // System operations
    getSystemHealth,
    refreshPlugins,
  };
}
