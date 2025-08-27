'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { db, type SyncQueue } from '../lib/offline-db';
import { advancedSyncManager } from '../lib/sync/advanced-sync-manager';
import { usePWA } from './usePWA';

export type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';

interface SyncState {
  status: SyncStatus;
  progress: number;
  totalItems: number;
  currentItem: number;
  lastSync: Date | null;
  pendingItems: number;
  error: string | null;
}

interface SyncResult {
  success: boolean;
  synced: number;
  failed: number;
  errors: string[];
}

export function useOfflineSync() {
  const { isOffline } = usePWA();
  const [syncState, setSyncState] = useState<SyncState>({
    status: 'idle',
    progress: 0,
    totalItems: 0,
    currentItem: 0,
    lastSync: null,
    pendingItems: 0,
    error: null,
  });

  const syncInProgressRef = useRef(false);
  const syncIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // API base URL
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Update pending items count
  const updatePendingCount = useCallback(async () => {
    try {
      const metrics = advancedSyncManager.getSyncMetrics();
      setSyncState((prev) => ({ ...prev, pendingItems: metrics.pendingItems }));
    } catch (error) {
      console.error('Failed to update pending count:', error);
    }
  }, []);

  // Sync a single item
  const syncItem = useCallback(
    async (item: SyncQueue): Promise<boolean> => {
      try {
        let url = '';
        let method = 'POST';
        let body: any = item.data;

        // Determine API endpoint and method based on item type and action
        switch (item.type) {
          case 'work_order':
            switch (item.action) {
              case 'create':
                url = `${API_BASE}/api/work-orders`;
                method = 'POST';
                break;
              case 'update':
                url = `${API_BASE}/api/work-orders/${item.data.id}`;
                method = 'PUT';
                break;
              case 'delete':
                url = `${API_BASE}/api/work-orders/${item.data.id}`;
                method = 'DELETE';
                body = undefined;
                break;
            }
            break;

          case 'inventory':
            switch (item.action) {
              case 'update':
                url = `${API_BASE}/api/inventory/${item.data.id}`;
                method = 'PUT';
                break;
            }
            break;

          case 'customer':
            switch (item.action) {
              case 'update':
                url = `${API_BASE}/api/customers/${item.data.id}`;
                method = 'PUT';
                break;
            }
            break;

          case 'photo':
            url = `${API_BASE}/api/photos/upload`;
            method = 'POST';
            // Convert to FormData for photo uploads
            const formData = new FormData();
            formData.append('workOrderId', item.data.workOrderId);
            formData.append('photo', item.data.photoBlob);
            if (item.data.metadata) {
              formData.append('metadata', JSON.stringify(item.data.metadata));
            }
            body = formData;
            break;
        }

        if (!url) {
          throw new Error(`Unsupported sync item: ${item.type}:${item.action}`);
        }

        // Make API request
        const headers: HeadersInit = {};
        if (body && !(body instanceof FormData)) {
          headers['Content-Type'] = 'application/json';
          body = JSON.stringify(body);
        }

        // Authentication handled by secure cookies - no token needed
        // The advanced sync manager handles authentication automatically

        const response = await fetch(url, {
          method,
          headers,
          body,
        });

        if (!response.ok) {
          throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        // Update local database with server response if needed
        if (
          method !== 'DELETE' &&
          (item.type === 'work_order' || item.type === 'customer' || item.type === 'inventory')
        ) {
          const serverData = await response.json();

          // Update local record to mark as synced
          switch (item.type) {
            case 'work_order':
              await db.workOrders.update(item.data.id, {
                syncStatus: 'synced',
                ...serverData,
              });
              break;
            case 'customer':
              await db.customers.update(item.data.id, {
                syncStatus: 'synced',
                ...serverData,
              });
              break;
            case 'inventory':
              await db.inventory.update(item.data.id, {
                syncStatus: 'synced',
                ...serverData,
              });
              break;
          }
        }

        return true;
      } catch (error) {
        console.error('Failed to sync item:', item.id, error);
        return false;
      }
    },
    [API_BASE]
  );

  // Sync all pending items
  const syncPendingItems = useCallback(async (): Promise<SyncResult> => {
    if (syncInProgressRef.current || isOffline) {
      return {
        success: false,
        synced: 0,
        failed: 0,
        errors: ['Sync already in progress or offline'],
      };
    }

    syncInProgressRef.current = true;
    setSyncState((prev) => ({
      ...prev,
      status: 'syncing',
      progress: 0,
      error: null,
    }));

    const result: SyncResult = {
      success: true,
      synced: 0,
      failed: 0,
      errors: [],
    };

    try {
      // Use the advanced sync manager to process the queue
      await advancedSyncManager.processSyncQueue();
      
      const metrics = advancedSyncManager.getSyncMetrics();
      
      setSyncState((prev) => ({
        ...prev,
        totalItems: metrics.totalItems,
        currentItem: metrics.totalItems - metrics.pendingItems,
        progress: metrics.totalItems === 0 ? 100 : Math.round(((metrics.totalItems - metrics.pendingItems) / metrics.totalItems) * 100),
      }));
      
      result.synced = metrics.totalItems - metrics.pendingItems - metrics.errorItems;
      result.failed = metrics.errorItems;
      
      if (metrics.conflictItems > 0) {
        result.errors.push(`${metrics.conflictItems} items have conflicts requiring manual resolution`);
      }

      // Update settings with last sync time
      await db.settings.update('default', {
        lastSync: new Date().toISOString(),
      });

      setSyncState((prev) => ({
        ...prev,
        status: result.failed > 0 ? 'error' : 'success',
        lastSync: new Date(),
        progress: 100,
        error: result.failed > 0 ? `${result.failed} items failed to sync` : null,
      }));
    } catch (error) {
      console.error('Sync failed:', error);
      result.success = false;
      result.errors.push(`Sync error: ${error}`);

      setSyncState((prev) => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
    } finally {
      syncInProgressRef.current = false;
      await updatePendingCount();
    }

    return result;
  }, [isOffline, syncItem, updatePendingCount]);

  // Force sync (manual sync)
  const forceSync = useCallback(async (): Promise<SyncResult> => {
    console.log('Force sync initiated');
    return await syncPendingItems();
  }, [syncPendingItems]);

  // Download fresh data from server
  const downloadFreshData = useCallback(async (): Promise<boolean> => {
    if (isOffline) {
      console.log('Cannot download data while offline');
      return false;
    }

    try {
      setSyncState((prev) => ({
        ...prev,
        status: 'syncing',
        progress: 0,
      }));

      // Get technician ID from profile
      const profile = await db.profile.orderBy('id').first();
      if (!profile) {
        throw new Error('No technician profile found');
      }

      // Authentication handled by secure cookies - no token needed
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      // Download work orders
      setSyncState((prev) => ({ ...prev, progress: 25 }));
      const workOrdersResponse = await fetch(
        `${API_BASE}/api/technicians/${profile.id}/work-orders`,
        { headers }
      );
      if (workOrdersResponse.ok) {
        const workOrders = await workOrdersResponse.json();
        await db.transaction('rw', db.workOrders, async () => {
          for (const workOrder of workOrders) {
            await db.workOrders.put({ ...workOrder, syncStatus: 'synced' });
          }
        });
      }

      // Download customers
      setSyncState((prev) => ({ ...prev, progress: 50 }));
      const customersResponse = await fetch(`${API_BASE}/api/technicians/${profile.id}/customers`, {
        headers,
      });
      if (customersResponse.ok) {
        const customers = await customersResponse.json();
        await db.transaction('rw', db.customers, async () => {
          for (const customer of customers) {
            await db.customers.put({ ...customer, syncStatus: 'synced' });
          }
        });
      }

      // Download inventory
      setSyncState((prev) => ({ ...prev, progress: 75 }));
      const inventoryResponse = await fetch(`${API_BASE}/api/inventory`, { headers });
      if (inventoryResponse.ok) {
        const inventory = await inventoryResponse.json();
        await db.transaction('rw', db.inventory, async () => {
          for (const item of inventory) {
            await db.inventory.put({ ...item, syncStatus: 'synced' });
          }
        });
      }

      // Update last sync time
      await db.settings.update('default', {
        lastSync: new Date().toISOString(),
      });

      setSyncState((prev) => ({
        ...prev,
        status: 'success',
        progress: 100,
        lastSync: new Date(),
      }));

      return true;
    } catch (error) {
      console.error('Failed to download fresh data:', error);
      setSyncState((prev) => ({
        ...prev,
        status: 'error',
        error: error instanceof Error ? error.message : 'Download failed',
      }));
      return false;
    }
  }, [isOffline, API_BASE]);

  // Auto sync on network reconnection
  useEffect(() => {
    if (!isOffline && syncState.pendingItems > 0) {
      const autoSyncDelay = setTimeout(() => {
        console.log('Auto-syncing after network reconnection');
        syncPendingItems();
      }, 2000); // Wait 2 seconds after reconnection

      return () => clearTimeout(autoSyncDelay);
    }
  }, [isOffline, syncState.pendingItems, syncPendingItems]);

  // Periodic auto sync
  useEffect(() => {
    const startAutoSync = async () => {
      const settings = await db.settings.get('default');
      if (settings?.autoSync && !isOffline) {
        const interval = (settings.syncInterval || 5) * 60 * 1000; // Convert minutes to ms

        syncIntervalRef.current = setInterval(() => {
          if (!syncInProgressRef.current && !isOffline) {
            console.log('Auto-sync triggered');
            syncPendingItems();
          }
        }, interval);
      }
    };

    startAutoSync();

    return () => {
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
      }
    };
  }, [isOffline, syncPendingItems]);

  // Initialize pending count
  useEffect(() => {
    updatePendingCount();
  }, [updatePendingCount]);

  return {
    syncState,
    syncPendingItems,
    forceSync,
    downloadFreshData,
    updatePendingCount,
  };
}
