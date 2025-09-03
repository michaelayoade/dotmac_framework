/**
 * Performance-optimized Service Overview Section with memoization
 */
import { StatusCard } from '../../ui/StatusCard';
import { Activity, TrendingUp, Wifi, Globe } from 'lucide-react';
import React, { memo, useMemo } from 'react';

interface NetworkStatus {
  connectionStatus: string;
  currentSpeed: {
    download: number;
    upload: number;
  };
  uptime: number;
  latency: number;
}

interface ServiceOverviewProps {
  networkStatus: NetworkStatus;
  dataUsage: {
    current: number;
    limit: number;
  };
  onRefreshStatus?: () => void;
  onViewDetails?: () => void;
  loading?: boolean;
}

// Memoized component to prevent unnecessary re-renders
export const ServiceOverviewSectionOptimized = memo<ServiceOverviewProps>(
  function ServiceOverviewSection({
    networkStatus,
    dataUsage,
    onRefreshStatus,
    onViewDetails,
    loading = false,
  }) {
    // Memoize status calculations to avoid recalculating on every render
    const connectionStatus = useMemo(() => {
      switch (networkStatus.connectionStatus) {
        case 'connected':
          return 'success' as const;
        case 'disconnected':
          return 'error' as const;
        case 'limited':
          return 'warning' as const;
        default:
          return 'neutral' as const;
      }
    }, [networkStatus.connectionStatus]);

    const speedStatus = useMemo(() => {
      const speed = networkStatus.currentSpeed.download;
      if (speed >= 100) return 'success' as const;
      if (speed >= 50) return 'neutral' as const;
      if (speed >= 25) return 'warning' as const;
      return 'error' as const;
    }, [networkStatus.currentSpeed.download]);

    const usageStatus = useMemo(() => {
      const percentage = (dataUsage.current / dataUsage.limit) * 100;
      if (percentage >= 90) return 'error' as const;
      if (percentage >= 75) return 'warning' as const;
      return 'neutral' as const;
    }, [dataUsage.current, dataUsage.limit]);

    const uptimeStatus = useMemo(() => {
      if (networkStatus.uptime >= 99.5) return 'success' as const;
      if (networkStatus.uptime >= 98) return 'neutral' as const;
      return 'warning' as const;
    }, [networkStatus.uptime]);

    // Memoize formatted values to prevent string concatenation on every render
    const formattedValues = useMemo(
      () => ({
        usageDisplay: `${dataUsage.current}/${dataUsage.limit}`,
        uptimeDisplay: `${networkStatus.uptime}%`,
      }),
      [dataUsage.current, dataUsage.limit, networkStatus.uptime]
    );

    // Memoize action objects to prevent recreation
    const refreshAction = useMemo(
      () =>
        onRefreshStatus
          ? {
              label: 'Refresh',
              onClick: onRefreshStatus,
            }
          : undefined,
      [onRefreshStatus]
    );

    const viewDetailsAction = useMemo(
      () =>
        onViewDetails
          ? {
              label: 'View Details',
              onClick: onViewDetails,
            }
          : undefined,
      [onViewDetails]
    );

    return (
      <div className='grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4'>
        <StatusCard
          title='Connection Status'
          value={networkStatus.connectionStatus}
          icon={Wifi}
          status={connectionStatus}
          action={refreshAction}
          loading={loading}
        />

        <StatusCard
          title='Current Speed'
          value={networkStatus.currentSpeed.download}
          subtitle='Mbps'
          icon={TrendingUp}
          status={speedStatus}
          action={viewDetailsAction}
          loading={loading}
        />

        <StatusCard
          title='Data Usage'
          value={formattedValues.usageDisplay}
          subtitle='GB'
          icon={Globe}
          status={usageStatus}
          loading={loading}
        />

        <StatusCard
          title='Network Uptime'
          value={formattedValues.uptimeDisplay}
          icon={Activity}
          status={uptimeStatus}
          loading={loading}
        />
      </div>
    );
  },
  (prevProps, nextProps) => {
    // Custom equality check for better performance
    return (
      prevProps.loading === nextProps.loading &&
      prevProps.networkStatus.connectionStatus === nextProps.networkStatus.connectionStatus &&
      prevProps.networkStatus.currentSpeed.download ===
        nextProps.networkStatus.currentSpeed.download &&
      prevProps.networkStatus.uptime === nextProps.networkStatus.uptime &&
      prevProps.dataUsage.current === nextProps.dataUsage.current &&
      prevProps.dataUsage.limit === nextProps.dataUsage.limit &&
      prevProps.onRefreshStatus === nextProps.onRefreshStatus &&
      prevProps.onViewDetails === nextProps.onViewDetails
    );
  }
);
