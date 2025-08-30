import { useCallback, useEffect, useState } from 'react';
import { useTenantStore } from '@dotmac/headless/stores';
import { OfflineDatabase, CacheRecord, AssetRecord } from './OfflineDatabase';
import { MobileCacheOptions, CacheStatistics } from './types';

export function useMobileCache(options: MobileCacheOptions = {}) {
  const {
    useIndexedDB = true,
    cacheAssets = true,
    maxCacheSize = 50, // MB
    prefetchStrategy = 'conservative'
  } = options;

  const { currentTenant } = useTenantStore();
  const [db] = useState(() => new OfflineDatabase());
  const [statistics, setStatistics] = useState<CacheStatistics | null>(null);

  // Update cache statistics
  const updateStatistics = useCallback(async () => {
    try {
      const stats = await db.getCacheStatistics();
      setStatistics(stats);
    } catch (error) {
      console.warn('Failed to update cache statistics:', error);
    }
  }, [db]);

  // Enhanced cache get with IndexedDB
  const cacheGet = useCallback(async <T>(
    key: string,
    params?: Record<string, unknown>
  ): Promise<T | null> => {
    if (!currentTenant?.tenant?.id) return null;

    const cacheKey = params ? `${key}:${JSON.stringify(params)}` : key;

    if (useIndexedDB) {
      try {
        const record = await db.cache
          .where('key')
          .equals(cacheKey)
          .and(record => record.tenantId === currentTenant.tenant.id)
          .first();

        if (!record) return null;

        // Check TTL
        if (Date.now() > record.timestamp + record.ttl) {
          await db.cache.delete(record.id!);
          return null;
        }

        // Update access time
        await db.cache.update(record.id!, { accessed: Date.now() });

        return typeof record.data === 'string'
          ? JSON.parse(record.data)
          : record.data;

      } catch (error) {
        console.warn('IndexedDB cache get failed:', error);
        return null;
      }
    } else {
      // Fallback to localStorage
      try {
        const stored = localStorage.getItem(`dotmac-mobile-cache:${cacheKey}`);
        if (!stored) return null;

        const parsed = JSON.parse(stored);
        if (Date.now() > parsed.timestamp + parsed.ttl) {
          localStorage.removeItem(`dotmac-mobile-cache:${cacheKey}`);
          return null;
        }

        return parsed.data;
      } catch (error) {
        return null;
      }
    }
  }, [currentTenant?.tenant?.id, useIndexedDB, db]);

  // Enhanced cache set with IndexedDB
  const cacheSet = useCallback(async <T>(
    key: string,
    data: T,
    ttl: number = 5 * 60 * 1000, // 5 minutes default
    params?: Record<string, unknown>,
    options: {
      etag?: string;
      version?: number;
      priority?: number;
    } = {}
  ): Promise<void> => {
    if (!currentTenant?.tenant?.id) return;

    const cacheKey = params ? `${key}:${JSON.stringify(params)}` : key;
    const serializedData = JSON.stringify(data);
    const size = new Blob([serializedData]).size;

    if (useIndexedDB) {
      try {
        const record: Omit<CacheRecord, 'id'> = {
          key: cacheKey,
          data: serializedData,
          timestamp: Date.now(),
          ttl,
          tenantId: currentTenant.tenant.id,
          size,
          accessed: Date.now(),
          etag: options.etag,
          version: options.version
        };

        // Check if already exists and update, otherwise add
        const existing = await db.cache
          .where('key')
          .equals(cacheKey)
          .and(record => record.tenantId === currentTenant.tenant.id)
          .first();

        if (existing) {
          await db.cache.update(existing.id!, record);
        } else {
          await db.cache.add(record);
        }

        // Check cache size and optimize if needed
        const currentSize = await db.getCacheSize();
        const maxBytes = maxCacheSize * 1024 * 1024;

        if (currentSize > maxBytes) {
          await db.optimizeStorage(maxBytes * 0.8); // Target 80% of max
        }

      } catch (error) {
        console.warn('IndexedDB cache set failed:', error);
      }
    } else {
      // Fallback to localStorage
      try {
        const record = {
          data,
          timestamp: Date.now(),
          ttl,
          tenantId: currentTenant.tenant.id
        };

        localStorage.setItem(
          `dotmac-mobile-cache:${cacheKey}`,
          JSON.stringify(record)
        );
      } catch (error) {
        // localStorage full or other error
        console.warn('localStorage cache set failed:', error);
      }
    }

    await updateStatistics();
  }, [currentTenant?.tenant?.id, useIndexedDB, db, maxCacheSize, updateStatistics]);

  // Cache delete
  const cacheDelete = useCallback(async (
    key: string,
    params?: Record<string, unknown>
  ): Promise<void> => {
    if (!currentTenant?.tenant?.id) return;

    const cacheKey = params ? `${key}:${JSON.stringify(params)}` : key;

    if (useIndexedDB) {
      try {
        await db.cache
          .where('key')
          .equals(cacheKey)
          .and(record => record.tenantId === currentTenant.tenant.id)
          .delete();
      } catch (error) {
        console.warn('IndexedDB cache delete failed:', error);
      }
    } else {
      try {
        localStorage.removeItem(`dotmac-mobile-cache:${cacheKey}`);
      } catch (error) {
        console.warn('localStorage cache delete failed:', error);
      }
    }

    await updateStatistics();
  }, [currentTenant?.tenant?.id, useIndexedDB, db, updateStatistics]);

  // Asset caching for images, etc.
  const cacheAsset = useCallback(async (
    url: string,
    force: boolean = false
  ): Promise<string | null> => {
    if (!cacheAssets || !currentTenant?.tenant?.id) return url;

    try {
      // Check if already cached
      if (!force) {
        const existing = await db.assets
          .where('url')
          .equals(url)
          .and(asset => asset.tenantId === currentTenant.tenant.id)
          .first();

        if (existing) {
          // Update access time
          await db.assets.update(existing.id!, { accessed: Date.now() });
          return URL.createObjectURL(existing.data);
        }
      }

      // Fetch and cache asset
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Failed to fetch: ${response.status}`);

      const blob = await response.blob();
      const contentType = response.headers.get('content-type') || 'application/octet-stream';

      const record: Omit<AssetRecord, 'id'> = {
        url,
        data: blob,
        type: contentType,
        size: blob.size,
        timestamp: Date.now(),
        tenantId: currentTenant.tenant.id,
        accessed: Date.now()
      };

      await db.assets.add(record);
      return URL.createObjectURL(blob);

    } catch (error) {
      console.warn('Asset caching failed:', error);
      return url; // Return original URL on failure
    }
  }, [cacheAssets, currentTenant?.tenant?.id, db]);

  // Prefetch strategy implementation
  const prefetchData = useCallback(async (
    resources: Array<{ key: string; fetcher: () => Promise<any>; ttl?: number; priority?: number }>
  ): Promise<void> => {
    if (prefetchStrategy === 'minimal') return;

    // Sort by priority if provided
    const sortedResources = resources.sort((a, b) => (b.priority || 0) - (a.priority || 0));

    // Limit prefetch based on strategy
    const limit = prefetchStrategy === 'aggressive' ? sortedResources.length : Math.min(5, sortedResources.length);
    const toPrefetch = sortedResources.slice(0, limit);

    const prefetchPromises = toPrefetch.map(async (resource) => {
      try {
        // Check if already cached
        const cached = await cacheGet(resource.key);
        if (cached) return;

        // Fetch and cache
        const data = await resource.fetcher();
        await cacheSet(resource.key, data, resource.ttl);
      } catch (error) {
        console.warn(`Prefetch failed for ${resource.key}:`, error);
      }
    });

    // Execute with some concurrency control
    const batchSize = 3;
    for (let i = 0; i < prefetchPromises.length; i += batchSize) {
      const batch = prefetchPromises.slice(i, i + batchSize);
      await Promise.allSettled(batch);

      // Small delay between batches to avoid overwhelming
      if (i + batchSize < prefetchPromises.length) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
  }, [prefetchStrategy, cacheGet, cacheSet]);

  // Clear tenant cache
  const clearCache = useCallback(async (tenantOnly: boolean = true): Promise<void> => {
    try {
      if (tenantOnly && currentTenant?.tenant?.id) {
        await db.clearTenantData(currentTenant.tenant.id);
      } else {
        // Clear all cache
        await db.cache.clear();
        await db.assets.clear();

        if (!useIndexedDB) {
          // Clear localStorage cache
          const keys = Object.keys(localStorage);
          keys.forEach(key => {
            if (key.startsWith('dotmac-mobile-cache:')) {
              localStorage.removeItem(key);
            }
          });
        }
      }

      await updateStatistics();
    } catch (error) {
      console.warn('Cache clear failed:', error);
    }
  }, [currentTenant?.tenant?.id, db, useIndexedDB, updateStatistics]);

  // Initialize statistics
  useEffect(() => {
    updateStatistics();
  }, [updateStatistics]);

  return {
    // Core cache operations
    cacheGet,
    cacheSet,
    cacheDelete,
    clearCache,

    // Asset caching
    cacheAsset,

    // Prefetching
    prefetchData,

    // Statistics and info
    statistics,
    updateStatistics,

    // Configuration
    isIndexedDBEnabled: useIndexedDB,
    isAssetCachingEnabled: cacheAssets,
    prefetchStrategy,
    maxCacheSize
  };
}
