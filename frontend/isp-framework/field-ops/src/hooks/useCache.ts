/**
 * Cache Hook
 * React hooks for caching operations and cache management
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiCache, api } from '../lib/cache/api-cache';
import { memoryCache, persistentCache } from '../lib/cache/cache-manager';

interface UseCacheOptions {
  ttl?: number;
  tags?: string[];
  staleWhileRevalidate?: boolean;
  persistent?: boolean;
  autoRefetch?: boolean;
  refetchInterval?: number;
}

interface CacheState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  isStale: boolean;
  lastFetch: Date | null;
}

// Hook for API data with caching
export function useApiCache<T>(url: string | null, options: UseCacheOptions = {}) {
  const {
    ttl = 5 * 60 * 1000, // 5 minutes
    tags = [],
    staleWhileRevalidate = true,
    persistent = false,
    autoRefetch = false,
    refetchInterval = 30 * 1000, // 30 seconds
  } = options;

  const [state, setState] = useState<CacheState<T>>({
    data: null,
    loading: false,
    error: null,
    isStale: false,
    lastFetch: null,
  });

  const refetchTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(
    async (force = false) => {
      if (!url) return;

      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const data = await apiCache.get<T>(url, {
          ttl,
          tags: persistent ? [...tags, 'persistent'] : tags,
          staleWhileRevalidate,
          bypassCache: force,
        });

        setState({
          data,
          loading: false,
          error: null,
          isStale: false,
          lastFetch: new Date(),
        });
      } catch (error) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: error instanceof Error ? error : new Error('Unknown error'),
        }));
      }
    },
    [url, ttl, tags, persistent, staleWhileRevalidate]
  );

  const refetch = useCallback(() => {
    return fetchData(true);
  }, [fetchData]);

  const invalidate = useCallback(() => {
    if (url) {
      apiCache.invalidateByUrl(url);
      setState((prev) => ({ ...prev, isStale: true }));
    }
  }, [url]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto refetch setup
  useEffect(() => {
    if (!autoRefetch || !url) return;

    refetchTimerRef.current = setInterval(() => {
      fetchData();
    }, refetchInterval);

    return () => {
      if (refetchTimerRef.current) {
        clearInterval(refetchTimerRef.current);
      }
    };
  }, [autoRefetch, refetchInterval, fetchData, url]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (refetchTimerRef.current) {
        clearInterval(refetchTimerRef.current);
      }
    };
  }, []);

  return {
    ...state,
    refetch,
    invalidate,
  };
}

// Hook for mutating API data
export function useApiMutation<TData, TVariables = any>() {
  const [state, setState] = useState<{
    loading: boolean;
    error: Error | null;
    data: TData | null;
  }>({
    loading: false,
    error: null,
    data: null,
  });

  const mutate = useCallback(
    async (
      url: string,
      variables: TVariables,
      method: 'POST' | 'PUT' | 'DELETE' = 'POST',
      options: {
        invalidateTags?: string[];
        invalidateUrls?: string[];
      } = {}
    ) => {
      setState({ loading: true, error: null, data: null });

      try {
        let data: TData;

        switch (method) {
          case 'POST':
            data = await apiCache.post<TData, TVariables>(url, variables);
            break;
          case 'PUT':
            data = await apiCache.put<TData, TVariables>(url, variables);
            break;
          case 'DELETE':
            data = await apiCache.delete<TData>(url);
            break;
        }

        // Manual invalidation if needed
        if (options.invalidateTags) {
          options.invalidateTags.forEach((tag) => apiCache.invalidateByTag(tag));
        }

        if (options.invalidateUrls) {
          options.invalidateUrls.forEach((url) => apiCache.invalidateByUrl(url));
        }

        setState({ loading: false, error: null, data });
        return data;
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Unknown error');
        setState({ loading: false, error: err, data: null });
        throw err;
      }
    },
    []
  );

  const reset = useCallback(() => {
    setState({ loading: false, error: null, data: null });
  }, []);

  return {
    ...state,
    mutate,
    reset,
  };
}

// Hook for local cache operations
export function useLocalCache<T>(key: string, options: UseCacheOptions = {}) {
  const { persistent = false, ttl = 5 * 60 * 1000, tags = [] } = options;
  const cache = persistent ? persistentCache : memoryCache;

  const [value, setValue] = useState<T | null>(() => {
    return cache.get<T>(key);
  });

  const set = useCallback(
    (newValue: T) => {
      cache.set(key, newValue, { ttl, tags });
      setValue(newValue);
    },
    [key, ttl, tags, cache]
  );

  const remove = useCallback(() => {
    cache.delete(key);
    setValue(null);
  }, [key, cache]);

  const refresh = useCallback(() => {
    const freshValue = cache.get<T>(key);
    setValue(freshValue);
    return freshValue;
  }, [key, cache]);

  return {
    value,
    set,
    remove,
    refresh,
  };
}

// Hook for cache statistics
export function useCacheStats() {
  const [stats, setStats] = useState({
    memory: memoryCache.getStats(),
    persistent: persistentCache.getStats(),
    api: apiCache.getStats(),
  });

  const refresh = useCallback(() => {
    setStats({
      memory: memoryCache.getStats(),
      persistent: persistentCache.getStats(),
      api: apiCache.getStats(),
    });
  }, []);

  useEffect(() => {
    const interval = setInterval(refresh, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, [refresh]);

  const clearAll = useCallback(() => {
    memoryCache.clear();
    persistentCache.clear();
    apiCache.invalidateAll();
    refresh();
  }, [refresh]);

  const clearByTag = useCallback(
    (tag: string) => {
      memoryCache.invalidateByTag(tag);
      persistentCache.invalidateByTag(tag);
      apiCache.invalidateByTag(tag);
      refresh();
    },
    [refresh]
  );

  return {
    stats,
    refresh,
    clearAll,
    clearByTag,
  };
}

// Hook for prefetching data
export function usePrefetch() {
  const [prefetchQueue, setPrefetchQueue] = useState<string[]>([]);
  const [prefetching, setPrefetching] = useState(false);

  const addToPrefetchQueue = useCallback((urls: string | string[]) => {
    const urlArray = Array.isArray(urls) ? urls : [urls];
    setPrefetchQueue((prev) => [...prev, ...urlArray]);
  }, []);

  const prefetchAll = useCallback(async () => {
    if (prefetchQueue.length === 0 || prefetching) return;

    setPrefetching(true);

    try {
      await Promise.allSettled(
        prefetchQueue.map((url) => apiCache.prefetch(url, { priority: 'low' }))
      );
      setPrefetchQueue([]);
    } finally {
      setPrefetching(false);
    }
  }, [prefetchQueue, prefetching]);

  const prefetchCritical = useCallback(async () => {
    setPrefetching(true);
    try {
      await api.prefetchCriticalData();
    } finally {
      setPrefetching(false);
    }
  }, []);

  return {
    prefetchQueue,
    prefetching,
    addToPrefetchQueue,
    prefetchAll,
    prefetchCritical,
  };
}

// Hook for work orders with caching
export function useWorkOrders(params?: Record<string, any>) {
  return useApiCache('/api/work-orders', {
    tags: ['work-orders'],
    persistent: true,
    ttl: 10 * 60 * 1000, // 10 minutes
    autoRefetch: true,
    refetchInterval: 2 * 60 * 1000, // 2 minutes
  });
}

// Hook for single work order with caching
export function useWorkOrder(id: string | null) {
  return useApiCache(id ? `/api/work-orders/${id}` : null, {
    tags: ['work-orders', `work-order-${id}`],
    ttl: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for customers with caching
export function useCustomers() {
  return useApiCache('/api/customers', {
    tags: ['customers'],
    persistent: true,
    ttl: 15 * 60 * 1000, // 15 minutes
  });
}

// Hook for single customer with caching
export function useCustomer(id: string | null) {
  return useApiCache(id ? `/api/customers/${id}` : null, {
    tags: ['customers', `customer-${id}`],
    ttl: 10 * 60 * 1000, // 10 minutes
  });
}

// Hook for inventory with caching
export function useInventory() {
  return useApiCache('/api/inventory', {
    tags: ['inventory'],
    persistent: true,
    ttl: 5 * 60 * 1000, // 5 minutes
    autoRefetch: true,
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}
