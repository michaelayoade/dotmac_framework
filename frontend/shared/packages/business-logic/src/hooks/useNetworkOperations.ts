/**
 * React Hook for Network Service Operations
 * Provides network diagnostics, provisioning, and monitoring functionality
 */

import { useCallback } from 'react';
import { useBusinessLogic } from './useBusinessLogic';
import type {
  DiagnosticsResult,
  ServiceRequest,
  WorkOrder,
  ProvisioningResult,
  ServiceHealthReport,
  PortalContext,
} from '../types';

interface UseNetworkOperationsProps {
  portalType: PortalContext['portalType'];
  userId: string;
  permissions: string[];
  tenantId?: string;
}

interface ServiceProvisioningConfig {
  customerId: string;
  serviceType: 'fiber' | 'cable' | 'dsl' | 'wireless' | 'satellite';
  bandwidthMbps: {
    download: number;
    upload: number;
  };
  staticIPs?: string[];
  vlanId?: number;
  equipmentIds: string[];
  installationAddress: {
    street: string;
    city: string;
    state: string;
    zip: string;
    unit?: string;
  };
}

interface MaintenanceWindowParams {
  customerId?: string;
  serviceIds?: string[];
  type: 'scheduled' | 'emergency' | 'preventive';
  scheduledStart: Date;
  estimatedDurationHours: number;
  description: string;
  impact: 'none' | 'minimal' | 'moderate' | 'severe';
}

export function useNetworkOperations(props: UseNetworkOperationsProps) {
  const { network: networkEngine } = useBusinessLogic(props);

  const diagnoseConnection = useCallback(
    async (customerId: string): Promise<DiagnosticsResult> => {
      return networkEngine.diagnoseConnection(customerId);
    },
    [networkEngine]
  );

  const scheduleInstallation = useCallback(
    async (customerId: string, serviceDetails: ServiceRequest): Promise<WorkOrder> => {
      return networkEngine.scheduleInstallation(customerId, serviceDetails);
    },
    [networkEngine]
  );

  const provisionService = useCallback(
    async (
      customerId: string,
      serviceConfig: ServiceProvisioningConfig
    ): Promise<ProvisioningResult> => {
      return networkEngine.provisionService(customerId, serviceConfig);
    },
    [networkEngine]
  );

  const monitorServiceHealth = useCallback(
    async (customerId: string): Promise<ServiceHealthReport> => {
      return networkEngine.monitorServiceHealth(customerId);
    },
    [networkEngine]
  );

  const scheduleMaintenanceWindow = useCallback(
    async (params: MaintenanceWindowParams) => {
      return networkEngine.scheduleMaintenanceWindow(params);
    },
    [networkEngine]
  );

  return {
    diagnoseConnection,
    scheduleInstallation,
    provisionService,
    monitorServiceHealth,
    scheduleMaintenanceWindow,
  };
}
