/**
 * Custom hook for optimized dashboard data management with caching and error handling
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { customerAPI } from '../lib/api/customerApi';

interface DashboardData {
  account: any;
  networkStatus: any;
  services: any[];
  billing: any;
  lastUpdated: string;
}

interface UseDashboardDataOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
  enableCaching?: boolean;
  cacheTimeout?: number;
}

export function useDashboardData(options: UseDashboardDataOptions = {}) {
  const {
    autoRefresh = false,
    refreshInterval = 60000, // 1 minute
    enableCaching = true,
    cacheTimeout = 300000, // 5 minutes
  } = options;

  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState<number>(0);

  const abortControllerRef = useRef<AbortController | null>(null);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const cacheRef = useRef<{ data: DashboardData; timestamp: number } | null>(null);

  // Check if cached data is still valid
  const isCacheValid = useMemo(() => {
    if (!enableCaching || !cacheRef.current) return false;
    const now = Date.now();
    return now - cacheRef.current.timestamp < cacheTimeout;
  }, [enableCaching, cacheTimeout]);

  const fetchData = useCallback(
    async (forceRefresh = false) => {
      // Use cached data if available and valid, unless force refresh
      if (!forceRefresh && isCacheValid && cacheRef.current) {
        setData(cacheRef.current.data);
        setIsLoading(false);
        setError(null);
        return cacheRef.current.data;
      }

      // Cancel previous request if still pending
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      try {
        setIsLoading(true);
        setError(null);

        const [dashboardData, notifications, insights] = await Promise.allSettled([
          customerAPI.getDashboardData({ signal: abortController.signal }),
          customerAPI.getServiceNotifications({ signal: abortController.signal }),
          customerAPI.getUsageInsights({ signal: abortController.signal }),
        ]);

        // Check if request was aborted
        if (abortController.signal.aborted) {
          return null;
        }

        let combinedData: DashboardData;

        if (dashboardData.status === 'fulfilled') {
          combinedData = {
            ...dashboardData.value,
            lastUpdated: new Date().toISOString(),
          };

          // Add notifications and insights if available
          if (notifications.status === 'fulfilled') {
            combinedData.notifications = notifications.value;
          }
          if (insights.status === 'fulfilled') {
            combinedData.insights = insights.value;
          }
        } else {
          throw new Error(dashboardData.reason?.message || 'Failed to fetch dashboard data');
        }

        // Update cache
        if (enableCaching) {
          cacheRef.current = {
            data: combinedData,
            timestamp: Date.now(),
          };
        }

        setData(combinedData);
        setLastFetch(Date.now());
        return combinedData;
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return null; // Request was cancelled
        }

        const errorMessage = err.message || 'Failed to load dashboard data';
        setError(errorMessage);
        console.error('Dashboard data fetch failed:', err);
        return null;
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [isCacheValid, enableCaching]
  );

  const refetch = useCallback(
    (forceRefresh = true) => {
      return fetchData(forceRefresh);
    },
    [fetchData]
  );

  // Auto-refresh functionality
  useEffect(() => {
    if (!autoRefresh) return;

    const setupAutoRefresh = () => {
      refreshTimeoutRef.current = setTimeout(() => {
        fetchData(false); // Don't force refresh for auto-refresh
        setupAutoRefresh(); // Schedule next refresh
      }, refreshInterval);
    };

    setupAutoRefresh();

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, fetchData]);

  // Initial data load
  useEffect(() => {
    fetchData(false);

    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [fetchData]);

  // Memoized derived state
  const derivedState = useMemo(() => {
    const isStale = lastFetch > 0 && Date.now() - lastFetch > cacheTimeout;
    const hasData = data !== null;

    return {
      hasData,
      isStale,
      isEmpty: hasData && (!data.services || data.services.length === 0),
      isUsingCache: isCacheValid && cacheRef.current !== null,
    };
  }, [data, lastFetch, cacheTimeout, isCacheValid]);

  // Optimized network status for quick access
  const networkStatus = useMemo(() => {
    if (!data?.networkStatus) return null;

    return {
      isOnline: data.networkStatus.connectionStatus === 'connected',
      speed: data.networkStatus.currentSpeed?.download || 0,
      uptime: data.networkStatus.uptime || 0,
      quality:
        data.networkStatus.currentSpeed?.download >= 50
          ? 'good'
          : data.networkStatus.currentSpeed?.download >= 25
            ? 'fair'
            : 'poor',
    };
  }, [data?.networkStatus]);

  // Billing summary for quick access
  const billingSummary = useMemo(() => {
    if (!data?.billing) return null;

    return {
      currentBalance: data.billing.balance || 0,
      dueDate: data.billing.nextDueDate,
      isOverdue: data.billing.isOverdue || false,
      autopayEnabled: data.billing.autopay?.enabled || false,
    };
  }, [data?.billing]);

  return {
    data,
    isLoading,
    error,
    lastFetch,
    refetch,
    networkStatus,
    billingSummary,
    ...derivedState,
  };
}

// Hook for real-time network status updates
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionType, setConnectionType] = useState<string>('unknown');

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Check connection type if supported
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      setConnectionType(connection.effectiveType || 'unknown');

      const handleConnectionChange = () => {
        setConnectionType(connection.effectiveType || 'unknown');
      };

      connection.addEventListener('change', handleConnectionChange);

      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
        connection.removeEventListener('change', handleConnectionChange);
      };
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return {
    isOnline,
    connectionType,
    isSlowConnection: ['slow-2g', '2g'].includes(connectionType),
  };
}
