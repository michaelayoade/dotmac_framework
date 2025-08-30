import React from 'react';
import { FieldOpsProvider } from '../components/FieldOpsProvider';
import { useWorkOrders } from '../work-orders';
import { useGPSTracking } from '../gps';
import { useWorkflow } from '../workflows';
import type { WorkOrder } from '../types';

interface TechnicianPortalIntegrationProps {
  children: React.ReactNode;
  technicianId: string;
  workOrderId?: string;
  config?: {
    enableGPS?: boolean;
    enableOfflineMode?: boolean;
    autoStartWorkflows?: boolean;
  };
}

/**
 * Integration component that provides field operations functionality to the technician portal
 * This component handles the setup and configuration needed for technician workflows
 */
export function TechnicianPortalIntegration({
  children,
  technicianId,
  workOrderId,
  config = {}
}: TechnicianPortalIntegrationProps) {
  const {
    enableGPS = true,
    enableOfflineMode = true,
    autoStartWorkflows = false
  } = config;

  const fieldOpsConfig = {
    gpsSettings: {
      enabled: enableGPS,
      accuracy: 'high' as const,
      updateInterval: 5000,
      backgroundTracking: true,
      geoFenceRadius: 100,
      maxLocationAge: 60000
    },
    offlineMode: enableOfflineMode,
    autoSync: true,
    syncInterval: 30000,
    workflowValidation: true
  };

  return (
    <FieldOpsProvider config={fieldOpsConfig}>
      <TechnicianPortalFeatures
        technicianId={technicianId}
        workOrderId={workOrderId}
        autoStartWorkflows={autoStartWorkflows}
      >
        {children}
      </TechnicianPortalFeatures>
    </FieldOpsProvider>
  );
}

interface TechnicianPortalFeaturesProps {
  children: React.ReactNode;
  technicianId: string;
  workOrderId?: string;
  autoStartWorkflows: boolean;
}

function TechnicianPortalFeatures({
  children,
  technicianId,
  workOrderId,
  autoStartWorkflows
}: TechnicianPortalFeaturesProps) {
  // Initialize work orders management
  const workOrders = useWorkOrders({
    autoSync: true,
    technicianId
  });

  // Initialize GPS tracking
  const gpsTracking = useGPSTracking({
    autoStart: false, // Start manually when work order begins
    workOrderId
  });

  // Initialize workflow if work order is provided
  const workflow = useWorkflow({
    workOrderId: workOrderId || '',
    autoSave: true
  });

  // Auto-start GPS tracking when work order starts
  React.useEffect(() => {
    if (workOrderId && gpsTracking.permissionStatus?.granted) {
      const activeWorkOrder = workOrders.workOrders.find(
        wo => wo.id === workOrderId && wo.status === 'in_progress'
      );

      if (activeWorkOrder && !gpsTracking.isTracking) {
        gpsTracking.startTracking();
      }
    }
  }, [workOrderId, gpsTracking, workOrders.workOrders]);

  // Auto-start workflows if enabled
  React.useEffect(() => {
    if (autoStartWorkflows && workflow.workflow && workflow.workflow.status === 'not_started') {
      workflow.startWorkflow();
    }
  }, [autoStartWorkflows, workflow]);

  // Setup geofences for work orders
  React.useEffect(() => {
    workOrders.workOrders.forEach(workOrder => {
      if (workOrder.location.coordinates[0] !== 0 && workOrder.location.coordinates[1] !== 0) {
        const geoFence = {
          id: `wo_${workOrder.id}`,
          name: workOrder.title,
          center: {
            latitude: workOrder.location.coordinates[0],
            longitude: workOrder.location.coordinates[1],
            accuracy: 10
          },
          radius: workOrder.location.geoFence?.radius || 100,
          type: 'work_site' as const,
          workOrderId: workOrder.id
        };

        gpsTracking.addGeoFence(geoFence);
      }
    });
  }, [workOrders.workOrders, gpsTracking]);

  // Setup event handlers for GPS events
  React.useEffect(() => {
    const unsubscribeEnter = gpsTracking.onGeoFenceEnter((event) => {
      console.log('Arrived at work site:', event);

      // Auto-update work order status to "on_site"
      if (event.workOrderId) {
        workOrders.updateStatus(event.workOrderId, 'on_site');
      }

      // Show notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Arrived at Work Site', {
          body: 'You have arrived at the work site. Ready to begin work?',
          icon: '/favicon.ico'
        });
      }
    });

    const unsubscribeExit = gpsTracking.onGeoFenceExit((event) => {
      console.log('Left work site:', event);

      // Show notification if work is not complete
      if (event.workOrderId) {
        const workOrder = workOrders.workOrders.find(wo => wo.id === event.workOrderId);
        if (workOrder && workOrder.status !== 'completed') {
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Left Work Site', {
              body: 'Work order is not yet complete. Did you finish the job?',
              icon: '/favicon.ico'
            });
          }
        }
      }
    });

    return () => {
      unsubscribeEnter();
      unsubscribeExit();
    };
  }, [gpsTracking, workOrders]);

  return <>{children}</>;
}

/**
 * Hook to access field operations functionality in technician portal
 */
export function useFieldOperations() {
  const workOrders = useWorkOrders();
  const gpsTracking = useGPSTracking();

  return {
    workOrders,
    gpsTracking,

    // Quick actions
    startWork: async (workOrderId: string) => {
      await workOrders.updateStatus(workOrderId, 'in_progress');
      if (gpsTracking.permissionStatus?.granted) {
        await gpsTracking.startTracking();
      }
    },

    completeWork: async (workOrderId: string) => {
      await workOrders.completeWorkOrder(workOrderId);
      gpsTracking.stopTracking();
    },

    // Location utilities
    getCurrentLocation: gpsTracking.getCurrentLocation,
    calculateDistanceToWorkSite: (workOrder: WorkOrder) => {
      if (!gpsTracking.currentLocation ||
          workOrder.location.coordinates[0] === 0 ||
          workOrder.location.coordinates[1] === 0) {
        return null;
      }

      return gpsTracking.calculateDistance(
        gpsTracking.currentLocation,
        {
          latitude: workOrder.location.coordinates[0],
          longitude: workOrder.location.coordinates[1],
          accuracy: 0
        }
      );
    },

    // Status checks
    isOnSite: (workOrderId: string) => {
      return gpsTracking.geoFences.some(gf =>
        gf.workOrderId === workOrderId &&
        gpsTracking.currentLocation &&
        gpsTracking.calculateDistance(gpsTracking.currentLocation, gf.center) <= gf.radius
      );
    }
  };
}
