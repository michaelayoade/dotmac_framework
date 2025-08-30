import { useState, useEffect, useCallback } from 'react';
import { useApiClient, useAuth } from '@dotmac/headless';
import { workOrderDb } from '../database';
import type { WorkOrder, WorkOrderFilter, WorkOrderMetrics } from '../../types';

interface UseWorkOrdersOptions {
  autoSync?: boolean;
  syncInterval?: number;
  technicianId?: string;
}

interface UseWorkOrdersReturn {
  workOrders: WorkOrder[];
  loading: boolean;
  error: string | null;
  metrics: WorkOrderMetrics | null;

  // Actions
  createWorkOrder: (workOrder: Omit<WorkOrder, 'id' | 'createdAt' | 'lastModified'>) => Promise<void>;
  updateWorkOrder: (id: string, updates: Partial<WorkOrder>) => Promise<void>;
  deleteWorkOrder: (id: string) => Promise<void>;
  completeWorkOrder: (id: string) => Promise<void>;

  // Status management
  updateStatus: (id: string, status: WorkOrder['status']) => Promise<void>;
  startWorkOrder: (id: string) => Promise<void>;

  // Filtering and search
  filterWorkOrders: (filter: WorkOrderFilter) => Promise<WorkOrder[]>;
  searchWorkOrders: (query: string) => Promise<WorkOrder[]>;

  // Sync operations
  syncWithServer: () => Promise<void>;
  syncStatus: 'idle' | 'syncing' | 'error';
  lastSync: Date | null;

  // Metrics
  refreshMetrics: () => Promise<void>;
}

export function useWorkOrders(options: UseWorkOrdersOptions = {}): UseWorkOrdersReturn {
  const { autoSync = true, syncInterval = 30000, technicianId } = options;
  const { user, tenantId } = useAuth();
  const apiClient = useApiClient();

  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<WorkOrderMetrics | null>(null);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error'>('idle');
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // Load work orders from local database
  const loadLocalWorkOrders = useCallback(async () => {
    if (!tenantId) return;

    try {
      setLoading(true);
      setError(null);

      let orders: WorkOrder[];
      if (technicianId || user?.id) {
        orders = await workOrderDb.getWorkOrdersByTechnician(
          technicianId || user!.id,
          tenantId
        );
      } else {
        orders = await workOrderDb.workOrders
          .where('tenantId')
          .equals(tenantId)
          .orderBy('scheduledDate')
          .toArray();
      }

      setWorkOrders(orders);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load work orders');
      console.error('Failed to load work orders:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, technicianId, user?.id]);

  // Sync with server
  const syncWithServer = useCallback(async () => {
    if (!tenantId || syncStatus === 'syncing') return;

    try {
      setSyncStatus('syncing');

      // Get pending sync queue
      const syncQueue = await workOrderDb.getSyncQueue();

      // Process sync queue
      for (const item of syncQueue) {
        try {
          switch (item.syncType) {
            case 'create':
              await apiClient.post('/field-ops/work-orders', item.workOrder);
              break;
            case 'update':
              await apiClient.put(`/field-ops/work-orders/${item.workOrder.id}`, item.workOrder);
              break;
            case 'complete':
              await apiClient.post(`/field-ops/work-orders/${item.workOrder.id}/complete`, item.workOrder);
              break;
          }
        } catch (apiError) {
          console.error(`Failed to sync work order ${item.workOrder.id}:`, apiError);
          // Keep item in queue for retry
          continue;
        }
      }

      // Fetch latest work orders from server
      const response = await apiClient.get('/field-ops/work-orders', {
        params: {
          tenantId,
          technicianId: technicianId || user?.id
        }
      });

      if (response.data?.workOrders) {
        // Update local database
        await workOrderDb.transaction('rw', workOrderDb.workOrders, async () => {
          await workOrderDb.workOrders.clear();
          await workOrderDb.workOrders.bulkAdd(response.data.workOrders);
        });

        // Clear successful sync items
        await workOrderDb.clearSyncQueue();

        // Refresh local data
        await loadLocalWorkOrders();
      }

      setSyncStatus('idle');
      setLastSync(new Date());
      setError(null);

    } catch (err) {
      setSyncStatus('error');
      setError(err instanceof Error ? err.message : 'Sync failed');
      console.error('Sync failed:', err);
    }
  }, [tenantId, technicianId, user?.id, syncStatus, apiClient, loadLocalWorkOrders]);

  // Create work order
  const createWorkOrder = useCallback(async (workOrderData: Omit<WorkOrder, 'id' | 'createdAt' | 'lastModified'>) => {
    if (!tenantId) return;

    const workOrder: WorkOrder = {
      ...workOrderData,
      id: `wo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      tenantId,
      createdAt: new Date().toISOString(),
      lastModified: new Date().toISOString(),
      syncStatus: 'pending'
    };

    try {
      await workOrderDb.workOrders.add(workOrder);
      await workOrderDb.addToSyncQueue(workOrder, 'create', 5);
      await loadLocalWorkOrders();

      if (autoSync) {
        syncWithServer();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create work order');
      throw err;
    }
  }, [tenantId, loadLocalWorkOrders, autoSync, syncWithServer]);

  // Update work order
  const updateWorkOrder = useCallback(async (id: string, updates: Partial<WorkOrder>) => {
    try {
      const updatedData = {
        ...updates,
        lastModified: new Date().toISOString(),
        syncStatus: 'pending' as const
      };

      await workOrderDb.workOrders.update(id, updatedData);

      // Add to sync queue
      const workOrder = await workOrderDb.workOrders.get(id);
      if (workOrder) {
        await workOrderDb.addToSyncQueue(workOrder, 'update', 3);
      }

      await loadLocalWorkOrders();

      if (autoSync) {
        syncWithServer();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update work order');
      throw err;
    }
  }, [loadLocalWorkOrders, autoSync, syncWithServer]);

  // Update status with timeline tracking
  const updateStatus = useCallback(async (id: string, status: WorkOrder['status']) => {
    try {
      const workOrder = await workOrderDb.workOrders.get(id);
      if (!workOrder) throw new Error('Work order not found');

      const timelineEvent = {
        id: `event_${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: 'status_change' as const,
        description: `Status changed from ${workOrder.status} to ${status}`,
        author: user?.name || 'System',
        data: { oldStatus: workOrder.status, newStatus: status }
      };

      const updates: Partial<WorkOrder> = {
        status,
        timeline: [...(workOrder.timeline || []), timelineEvent],
        lastModified: new Date().toISOString(),
        syncStatus: 'pending'
      };

      // Add completion timestamp if completing
      if (status === 'completed') {
        updates.completedAt = new Date().toISOString();
        updates.progress = 100;
      }

      await updateWorkOrder(id, updates);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
      throw err;
    }
  }, [user?.name, updateWorkOrder]);

  // Start work order
  const startWorkOrder = useCallback(async (id: string) => {
    await updateStatus(id, 'in_progress');
  }, [updateStatus]);

  // Complete work order
  const completeWorkOrder = useCallback(async (id: string) => {
    const workOrder = await workOrderDb.workOrders.get(id);
    if (!workOrder) throw new Error('Work order not found');

    // Add to high priority sync queue for completion
    await workOrderDb.addToSyncQueue(workOrder, 'complete', 10);
    await updateStatus(id, 'completed');
  }, [updateStatus]);

  // Delete work order
  const deleteWorkOrder = useCallback(async (id: string) => {
    try {
      await workOrderDb.workOrders.delete(id);
      await loadLocalWorkOrders();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete work order');
      throw err;
    }
  }, [loadLocalWorkOrders]);

  // Filter work orders
  const filterWorkOrders = useCallback(async (filter: WorkOrderFilter): Promise<WorkOrder[]> => {
    if (!tenantId) return [];

    let query = workOrderDb.workOrders.where('tenantId').equals(tenantId);

    // Apply filters
    const results = await query.toArray();

    return results.filter(wo => {
      if (filter.status && !filter.status.includes(wo.status)) return false;
      if (filter.priority && !filter.priority.includes(wo.priority)) return false;
      if (filter.type && !filter.type.includes(wo.type)) return false;
      if (filter.technicianId && wo.technicianId !== filter.technicianId) return false;

      if (filter.dateRange) {
        if (wo.scheduledDate < filter.dateRange.start || wo.scheduledDate > filter.dateRange.end) {
          return false;
        }
      }

      return true;
    });
  }, [tenantId]);

  // Search work orders
  const searchWorkOrders = useCallback(async (query: string): Promise<WorkOrder[]> => {
    if (!tenantId) return [];
    return workOrderDb.searchWorkOrders(query, tenantId);
  }, [tenantId]);

  // Refresh metrics
  const refreshMetrics = useCallback(async () => {
    if (!tenantId) return;

    try {
      const dbMetrics = await workOrderDb.getWorkOrderMetrics(
        tenantId,
        technicianId || user?.id
      );

      // Convert to expected format
      const metrics: WorkOrderMetrics = {
        total: dbMetrics.total,
        completed: dbMetrics.completed,
        pending: dbMetrics.pending,
        overdue: dbMetrics.overdue,
        averageCompletionTime: 0, // TODO: Calculate from timeline data
        customerSatisfaction: 0 // TODO: Implement rating system
      };

      setMetrics(metrics);
    } catch (err) {
      console.error('Failed to refresh metrics:', err);
    }
  }, [tenantId, technicianId, user?.id]);

  // Initialize
  useEffect(() => {
    loadLocalWorkOrders();
    refreshMetrics();
  }, [loadLocalWorkOrders, refreshMetrics]);

  // Auto-sync interval
  useEffect(() => {
    if (!autoSync) return;

    const interval = setInterval(syncWithServer, syncInterval);
    return () => clearInterval(interval);
  }, [autoSync, syncInterval, syncWithServer]);

  // Initial sync
  useEffect(() => {
    if (autoSync && tenantId) {
      syncWithServer();
    }
  }, [autoSync, tenantId, syncWithServer]);

  return {
    workOrders,
    loading,
    error,
    metrics,

    // Actions
    createWorkOrder,
    updateWorkOrder,
    deleteWorkOrder,
    completeWorkOrder,

    // Status management
    updateStatus,
    startWorkOrder,

    // Filtering and search
    filterWorkOrders,
    searchWorkOrders,

    // Sync operations
    syncWithServer,
    syncStatus,
    lastSync,

    // Metrics
    refreshMetrics
  };
}
