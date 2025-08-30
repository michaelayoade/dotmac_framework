import { useState, useEffect, useCallback } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  PluginMarketplaceItem,
  PluginSearchFilters,
  PluginInstallRequest,
  UsePluginMarketplaceResult
} from '../types';

const API_ENDPOINTS = {
  MARKETPLACE: '/api/plugins/marketplace',
  MARKETPLACE_SEARCH: '/api/plugins/marketplace/search',
  MARKETPLACE_CATEGORIES: '/api/plugins/marketplace/categories',
  MARKETPLACE_TAGS: '/api/plugins/marketplace/tags',
  MARKETPLACE_DETAILS: '/api/plugins/marketplace/details',
  MARKETPLACE_INSTALL: '/api/plugins/marketplace/install',
  MARKETPLACE_UPDATES: '/api/plugins/marketplace/updates'
} as const;

export function usePluginMarketplace(): UsePluginMarketplaceResult {
  const [items, setItems] = useState<PluginMarketplaceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentFilters, setCurrentFilters] = useState<PluginSearchFilters>({});

  const apiClient = useApiClient();

  const fetchMarketplaceItems = useCallback(async (filters?: PluginSearchFilters) => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get<PluginMarketplaceItem[]>(
        API_ENDPOINTS.MARKETPLACE,
        { params: filters || {} }
      );

      setItems(response.data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch marketplace items';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  const searchPlugins = useCallback(async (query: string, filters?: PluginSearchFilters) => {
    try {
      setLoading(true);
      setError(null);

      const searchParams = {
        q: query,
        ...filters
      };

      const response = await apiClient.get<PluginMarketplaceItem[]>(
        API_ENDPOINTS.MARKETPLACE_SEARCH,
        { params: searchParams }
      );

      setItems(response.data);
      setCurrentFilters({ ...filters, name_pattern: query });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to search plugins';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  const filterByCategory = useCallback((category: string) => {
    const newFilters = { ...currentFilters, category };
    setCurrentFilters(newFilters);
    fetchMarketplaceItems(newFilters);
  }, [currentFilters, fetchMarketplaceItems]);

  const filterByTag = useCallback((tag: string) => {
    const existingTags = currentFilters.tags || [];
    const newTags = existingTags.includes(tag)
      ? existingTags.filter(t => t !== tag)
      : [...existingTags, tag];

    const newFilters = { ...currentFilters, tags: newTags };
    setCurrentFilters(newFilters);
    fetchMarketplaceItems(newFilters);
  }, [currentFilters, fetchMarketplaceItems]);

  const clearFilters = useCallback(() => {
    setCurrentFilters({});
    fetchMarketplaceItems();
  }, [fetchMarketplaceItems]);

  const installFromMarketplace = useCallback(async (item: PluginMarketplaceItem) => {
    try {
      setError(null);

      const installRequest: PluginInstallRequest = {
        plugin_id: item.id,
        version: item.latest_version,
        enable_after_install: true,
        auto_update: true
      };

      await apiClient.post(API_ENDPOINTS.MARKETPLACE_INSTALL, installRequest);

      // Update the item's installed status
      setItems(prev => prev.map(prevItem =>
        prevItem.id === item.id
          ? { ...prevItem, installed: true }
          : prevItem
      ));

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to install plugin from marketplace';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const getPluginDetails = useCallback(async (pluginId: string): Promise<PluginMarketplaceItem | null> => {
    try {
      const response = await apiClient.get<PluginMarketplaceItem>(
        `${API_ENDPOINTS.MARKETPLACE_DETAILS}/${pluginId}`
      );
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to get plugin details';
      setError(message);
      return null;
    }
  }, [apiClient]);

  const getCategories = useCallback((): string[] => {
    const categories = new Set(items.map(item => item.category));
    return Array.from(categories).sort();
  }, [items]);

  const getPopularTags = useCallback((): string[] => {
    const tagCounts = new Map<string, number>();

    items.forEach(item => {
      item.tags.forEach(tag => {
        tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
      });
    });

    // Sort by count descending, return top 20
    return Array.from(tagCounts.entries())
      .sort(([, a], [, b]) => b - a)
      .slice(0, 20)
      .map(([tag]) => tag);
  }, [items]);

  const refreshMarketplace = useCallback(async () => {
    await fetchMarketplaceItems(currentFilters);
  }, [fetchMarketplaceItems, currentFilters]);

  const checkForUpdates = useCallback(async () => {
    try {
      setError(null);

      const response = await apiClient.get<PluginMarketplaceItem[]>(API_ENDPOINTS.MARKETPLACE_UPDATES);

      // Update items with new update availability information
      const updatedItems = response.data;
      const itemMap = new Map(updatedItems.map(item => [item.id, item]));

      setItems(prev => prev.map(item => {
        const updated = itemMap.get(item.id);
        return updated ? { ...item, update_available: updated.update_available } : item;
      }));

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to check for updates';
      setError(message);
    }
  }, [apiClient]);

  // Initial load
  useEffect(() => {
    fetchMarketplaceItems();
  }, [fetchMarketplaceItems]);

  return {
    items,
    loading,
    error,

    // Search and filtering
    searchPlugins,
    filterByCategory,
    filterByTag,
    clearFilters,

    // Installation
    installFromMarketplace,

    // Information
    getPluginDetails,
    getCategories,
    getPopularTags,

    // Management
    refreshMarketplace,
    checkForUpdates
  };
}
