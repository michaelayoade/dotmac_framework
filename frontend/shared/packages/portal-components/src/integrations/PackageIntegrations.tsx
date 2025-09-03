'use client';

import { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';

// Package imports
import { NetworkProvider, useNetworkStore } from '@dotmac/network';
import { AssetsProvider, useAssetsStore } from '@dotmac/assets';
import { JourneyProvider, useJourneyOrchestration } from '@dotmac/journey-orchestration';

/**
 * Package Integration Provider
 * Provides all package contexts to portal applications
 */
interface PackageIntegrationsProps {
  children: ReactNode;
  tenantId?: string;
  enableNetwork?: boolean;
  enableAssets?: boolean;
  enableJourneys?: boolean;
}

export function PackageIntegrations({
  children,
  tenantId,
  enableNetwork = true,
  enableAssets = true,
  enableJourneys = true,
}: PackageIntegrationsProps) {
  let content = children;

  // Wrap with Journey Orchestration (outermost for event coordination)
  if (enableJourneys) {
    content = (
      <JourneyProvider
        tenantId={tenantId}
        config={{
          enableRealTimeUpdates: true,
          enableAnalytics: true,
          autoStartJourneys: true,
          debugMode: process.env.NODE_ENV === 'development',
        }}
      >
        {content}
      </JourneyProvider>
    );
  }

  // Wrap with Assets Management
  if (enableAssets) {
    content = (
      <AssetsProvider
        tenantId={tenantId}
        config={{
          enableRealTimeSync: true,
          enableMaintenanceAlerts: true,
          enableLifecycleTracking: true,
          autoCalculateDepreciation: true,
        }}
      >
        {content}
      </AssetsProvider>
    );
  }

  // Wrap with Network Management
  if (enableNetwork) {
    content = (
      <NetworkProvider
        tenantId={tenantId}
        config={{
          enableRealTimeMonitoring: true,
          enableSNMPPolling: true,
          enableTopologyUpdates: true,
          pollingInterval: 30000, // 30 seconds
        }}
      >
        {content}
      </NetworkProvider>
    );
  }

  return <>{content}</>;
}

/**
 * Package Integration Dashboard Widgets
 */
export function NetworkStatusWidget() {
  const { devices, topology } = useNetworkStore();
  const { data: networkHealth } = useQuery({
    queryKey: ['network-health'],
    queryFn: () => ({
      totalDevices: devices.length,
      activeDevices: devices.filter((d) => d.status === 'active').length,
      alerts: devices.filter((d) => d.alerts?.length > 0).length,
      topologyHealth: topology ? 'healthy' : 'unknown',
    }),
    refetchInterval: 30000,
  });

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-2'>Network Status</h3>
      <div className='grid grid-cols-2 gap-4'>
        <div>
          <p className='text-2xl font-bold text-green-600'>{networkHealth?.activeDevices || 0}</p>
          <p className='text-sm text-gray-600'>Active Devices</p>
        </div>
        <div>
          <p className='text-2xl font-bold text-red-600'>{networkHealth?.alerts || 0}</p>
          <p className='text-sm text-gray-600'>Alerts</p>
        </div>
      </div>
    </div>
  );
}

export function AssetsOverviewWidget() {
  const { assets, maintenanceSchedule } = useAssetsStore();
  const { data: assetsOverview } = useQuery({
    queryKey: ['assets-overview'],
    queryFn: () => ({
      totalAssets: assets.length,
      maintenanceDue: maintenanceSchedule.filter(
        (m) => new Date(m.scheduledDate) <= new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
      ).length,
      criticalAssets: assets.filter((a) => a.status === 'critical').length,
    }),
    refetchInterval: 60000,
  });

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-2'>Assets Overview</h3>
      <div className='grid grid-cols-3 gap-2'>
        <div>
          <p className='text-xl font-bold text-blue-600'>{assetsOverview?.totalAssets || 0}</p>
          <p className='text-xs text-gray-600'>Total Assets</p>
        </div>
        <div>
          <p className='text-xl font-bold text-orange-600'>{assetsOverview?.maintenanceDue || 0}</p>
          <p className='text-xs text-gray-600'>Due Soon</p>
        </div>
        <div>
          <p className='text-xl font-bold text-red-600'>{assetsOverview?.criticalAssets || 0}</p>
          <p className='text-xs text-gray-600'>Critical</p>
        </div>
      </div>
    </div>
  );
}

export function JourneyMetricsWidget() {
  const { getActiveJourneys, getConversionMetrics } = useJourneyOrchestration();
  const { data: journeyMetrics } = useQuery({
    queryKey: ['journey-metrics'],
    queryFn: async () => {
      const activeJourneys = await getActiveJourneys();
      const conversionMetrics = await getConversionMetrics({ period: '7d' });

      return {
        activeJourneys: activeJourneys.length,
        completedToday: conversionMetrics.completedJourneys || 0,
        conversionRate: conversionMetrics.conversionRate || 0,
      };
    },
    refetchInterval: 60000,
  });

  return (
    <div className='bg-white p-4 rounded-lg shadow'>
      <h3 className='text-lg font-semibold mb-2'>Customer Journeys</h3>
      <div className='grid grid-cols-3 gap-2'>
        <div>
          <p className='text-xl font-bold text-purple-600'>{journeyMetrics?.activeJourneys || 0}</p>
          <p className='text-xs text-gray-600'>Active</p>
        </div>
        <div>
          <p className='text-xl font-bold text-green-600'>{journeyMetrics?.completedToday || 0}</p>
          <p className='text-xs text-gray-600'>Completed</p>
        </div>
        <div>
          <p className='text-xl font-bold text-blue-600'>
            {journeyMetrics?.conversionRate?.toFixed(1) || 0}%
          </p>
          <p className='text-xs text-gray-600'>Conv. Rate</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Combined Dashboard Widgets Grid
 */
export function PackageDashboardWidgets({ layout = 'grid' }: { layout?: 'grid' | 'row' }) {
  const gridClass =
    layout === 'grid'
      ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
      : 'flex flex-col md:flex-row gap-4';

  return (
    <div className={gridClass}>
      <NetworkStatusWidget />
      <AssetsOverviewWidget />
      <JourneyMetricsWidget />
    </div>
  );
}

/**
 * Hook for package integration status
 */
export function usePackageIntegrationStatus() {
  const { data: integrationStatus } = useQuery({
    queryKey: ['package-integration-status'],
    queryFn: async () => {
      // Check if packages are properly integrated
      try {
        const networkStatus = useNetworkStore.getState();
        const assetsStatus = useAssetsStore.getState();
        const journeyStatus = useJourneyOrchestration();

        return {
          network: { connected: true, devices: networkStatus.devices.length },
          assets: { connected: true, assets: assetsStatus.assets.length },
          journeys: { connected: true, active: 0 }, // This would be properly implemented
        };
      } catch (error) {
        return {
          network: { connected: false, error: error.message },
          assets: { connected: false, error: error.message },
          journeys: { connected: false, error: error.message },
        };
      }
    },
    staleTime: 30000,
  });

  return integrationStatus;
}
