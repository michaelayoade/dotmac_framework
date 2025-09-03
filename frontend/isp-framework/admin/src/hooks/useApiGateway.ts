/**
 * React Hooks for API Gateway Integration
 * Provides React integration for the unified API gateway
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { apiGateway, ApiGateway } from '../lib/api-gateway';
import { ApiResponse, RequestConfig } from '../lib/api-client';
import { monitoring } from '../lib/monitoring';

// Hook for basic API gateway operations
export function useApiGateway() {
  const [isHealthy, setIsHealthy] = useState(true);
  const [services, setServices] = useState<any[]>([]);

  useEffect(() => {
    // Monitor gateway health
    const checkHealth = () => {
      const status = apiGateway.getGatewayStatus();
      setIsHealthy(status.healthyServices === status.totalServices);
      setServices(status.services);
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }, []);

  const request = useCallback(
    async <T = any>(
      endpoint: string,
      options?: RequestConfig & { method?: string; data?: any }
    ): Promise<ApiResponse<T>> => {
      return apiGateway.request<T>(endpoint, options);
    },
    []
  );

  const get = useCallback(
    async <T = any>(endpoint: string, options?: RequestConfig): Promise<ApiResponse<T>> => {
      return apiGateway.get<T>(endpoint, options);
    },
    []
  );

  const post = useCallback(
    async <T = any>(
      endpoint: string,
      data?: any,
      options?: RequestConfig
    ): Promise<ApiResponse<T>> => {
      return apiGateway.post<T>(endpoint, data, options);
    },
    []
  );

  const put = useCallback(
    async <T = any>(
      endpoint: string,
      data?: any,
      options?: RequestConfig
    ): Promise<ApiResponse<T>> => {
      return apiGateway.put<T>(endpoint, data, options);
    },
    []
  );

  const del = useCallback(
    async <T = any>(endpoint: string, options?: RequestConfig): Promise<ApiResponse<T>> => {
      return apiGateway.delete<T>(endpoint, options);
    },
    []
  );

  const patch = useCallback(
    async <T = any>(
      endpoint: string,
      data?: any,
      options?: RequestConfig
    ): Promise<ApiResponse<T>> => {
      return apiGateway.patch<T>(endpoint, data, options);
    },
    []
  );

  return {
    // Gateway status
    isHealthy,
    services,

    // HTTP methods
    request,
    get,
    post,
    put,
    delete: del,
    patch,

    // Utility
    getStatus: () => apiGateway.getGatewayStatus(),
  };
}

// Hook for API requests with loading states
export function useApiRequest<T = any>(
  endpoint?: string,
  options?: RequestConfig & { method?: string; data?: any },
  deps: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { request } = useApiGateway();

  const execute = useCallback(
    async (
      customEndpoint?: string,
      customOptions?: RequestConfig & { method?: string; data?: any }
    ): Promise<T | null> => {
      const finalEndpoint = customEndpoint || endpoint;
      const finalOptions = customOptions || options;

      if (!finalEndpoint) {
        return null;
      }

      setLoading(true);
      setError(null);

      try {
        monitoring.recordInteraction({
          event: 'api_request_started',
          target: finalEndpoint,
          metadata: {
            method: finalOptions?.method || 'GET',
          },
        });

        const response = await request<T>(finalEndpoint, finalOptions);

        if (response.success) {
          setData(response.data);

          monitoring.recordBusinessMetric({
            metric: 'api_request_success',
            value: 1,
            dimensions: {
              endpoint: finalEndpoint,
              method: finalOptions?.method || 'GET',
            },
          });

          return response.data;
        } else {
          const errorMessage = response.error || 'Request failed';
          setError(errorMessage);

          monitoring.recordBusinessMetric({
            metric: 'api_request_error',
            value: 1,
            dimensions: {
              endpoint: finalEndpoint,
              error_type: 'api_error',
            },
          });

          return null;
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);

        monitoring.recordError({
          error: err instanceof Error ? err : new Error(String(err)),
          context: 'useApiRequest',
          metadata: {
            endpoint: finalEndpoint,
            options: finalOptions,
          },
        });

        return null;
      } finally {
        setLoading(false);
      }
    },
    [endpoint, options, request]
  );

  // Auto-execute on mount if endpoint is provided
  useEffect(() => {
    if (endpoint) {
      execute();
    }
  }, [execute, ...deps]);

  return {
    data,
    loading,
    error,
    execute,
    refetch: () => execute(),
  };
}

// Hook for paginated API requests
export function usePaginatedApi<T = any>(
  endpoint: string,
  options: RequestConfig & {
    pageSize?: number;
    initialPage?: number;
  } = {}
) {
  const [items, setItems] = useState<T[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(options.initialPage || 1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { get } = useApiGateway();

  const pageSize = options.pageSize || 20;

  const fetchPage = useCallback(
    async (page: number) => {
      setLoading(true);
      setError(null);

      try {
        const response = await get<{
          items: T[];
          totalItems: number;
          totalPages: number;
          currentPage: number;
        }>(`${endpoint}?page=${page}&pageSize=${pageSize}`, options);

        if (response.success && response.data) {
          setItems(response.data.items);
          setTotalItems(response.data.totalItems);
          setCurrentPage(page);
        } else {
          setError(response.error || 'Failed to fetch data');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    },
    [endpoint, pageSize, get, options]
  );

  useEffect(() => {
    fetchPage(currentPage);
  }, [fetchPage]);

  const goToPage = useCallback(
    (page: number) => {
      fetchPage(page);
    },
    [fetchPage]
  );

  const nextPage = useCallback(() => {
    const totalPages = Math.ceil(totalItems / pageSize);
    if (currentPage < totalPages) {
      goToPage(currentPage + 1);
    }
  }, [currentPage, totalItems, pageSize, goToPage]);

  const prevPage = useCallback(() => {
    if (currentPage > 1) {
      goToPage(currentPage - 1);
    }
  }, [currentPage, goToPage]);

  return {
    items,
    totalItems,
    currentPage,
    pageSize,
    loading,
    error,
    totalPages: Math.ceil(totalItems / pageSize),
    hasNextPage: currentPage < Math.ceil(totalItems / pageSize),
    hasPrevPage: currentPage > 1,
    goToPage,
    nextPage,
    prevPage,
    refetch: () => fetchPage(currentPage),
  };
}

// Hook for real-time API subscriptions
export function useApiSubscription<T = any>(
  endpoint: string,
  options: {
    interval?: number;
    enabled?: boolean;
    onData?: (data: T) => void;
    onError?: (error: string) => void;
  } = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number | null>(null);
  const { get } = useApiGateway();

  const interval = options.interval || 5000; // 5 seconds default
  const enabled = options.enabled !== false;

  useEffect(() => {
    if (!enabled) {
      return;
    }

    let intervalId: NodeJS.Timeout;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await get<T>(endpoint);

        if (response.success) {
          setData(response.data);
          setLastUpdate(Date.now());
          options.onData?.(response.data);
        } else {
          const errorMessage = response.error || 'Subscription failed';
          setError(errorMessage);
          options.onError?.(errorMessage);
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);
        options.onError?.(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchData();

    // Set up polling
    intervalId = setInterval(fetchData, interval);

    return () => {
      clearInterval(intervalId);
    };
  }, [endpoint, interval, enabled, get, options]);

  const pause = useCallback(() => {
    // This would typically control the enabled state
    // For now, we'll just record the interaction
    monitoring.recordInteraction({
      event: 'api_subscription_paused',
      target: endpoint,
    });
  }, [endpoint]);

  const resume = useCallback(() => {
    monitoring.recordInteraction({
      event: 'api_subscription_resumed',
      target: endpoint,
    });
  }, [endpoint]);

  return {
    data,
    loading,
    error,
    lastUpdate,
    pause,
    resume,
  };
}

// Hook for batch API requests
export function useBatchApi() {
  const [requests, setRequests] = useState<
    Array<{
      id: string;
      endpoint: string;
      options?: RequestConfig & { method?: string; data?: any };
      status: 'pending' | 'loading' | 'success' | 'error';
      data?: any;
      error?: string;
    }>
  >([]);

  const { request } = useApiGateway();

  const addRequest = useCallback(
    (id: string, endpoint: string, options?: RequestConfig & { method?: string; data?: any }) => {
      setRequests((prev) => [
        ...prev,
        {
          id,
          endpoint,
          options,
          status: 'pending',
        },
      ]);
    },
    []
  );

  const executeAll = useCallback(async () => {
    const pendingRequests = requests.filter((req) => req.status === 'pending');

    // Update all to loading
    setRequests((prev) =>
      prev.map((req) => (req.status === 'pending' ? { ...req, status: 'loading' as const } : req))
    );

    // Execute all requests in parallel
    const results = await Promise.allSettled(
      pendingRequests.map(async (req) => {
        try {
          const response = await request(req.endpoint, req.options);
          return { id: req.id, success: true, data: response.data, error: response.error };
        } catch (error) {
          return {
            id: req.id,
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      })
    );

    // Update results
    setRequests((prev) =>
      prev.map((req) => {
        const result = results.find((r) => r.status === 'fulfilled' && r.value.id === req.id);

        if (result && result.status === 'fulfilled') {
          const { value } = result;
          return {
            ...req,
            status: value.success ? ('success' as const) : ('error' as const),
            data: value.data,
            error: value.error,
          };
        }

        return req;
      })
    );
  }, [requests, request]);

  const clearRequests = useCallback(() => {
    setRequests([]);
  }, []);

  const removeRequest = useCallback((id: string) => {
    setRequests((prev) => prev.filter((req) => req.id !== id));
  }, []);

  return {
    requests,
    addRequest,
    executeAll,
    clearRequests,
    removeRequest,
    isLoading: requests.some((req) => req.status === 'loading'),
    completedCount: requests.filter((req) => req.status === 'success').length,
    errorCount: requests.filter((req) => req.status === 'error').length,
  };
}
