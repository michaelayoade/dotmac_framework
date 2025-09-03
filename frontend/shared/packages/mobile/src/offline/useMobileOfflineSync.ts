import { useCallback, useEffect, useState, useRef } from 'react';
import { useOfflineSync } from '@dotmac/headless';
import { useAuth } from '@dotmac/headless/auth';
import { useTenantStore } from '@dotmac/headless/stores';
import { OfflineDatabase } from './OfflineDatabase';
import { OfflineNotificationManager } from './OfflineNotificationManager';
import { MobileOfflineOptions, MobileOfflineEntry, OfflineSyncResult, StorageQuota } from './types';

export function useMobileOfflineSync(options: MobileOfflineOptions = {}) {
  const {
    backgroundSync = true,
    notifications = true,
    storageQuota = 50, // MB
    autoCleanup = true,
    cacheDays = 7,
    compression = true,
  } = options;

  const { user } = useAuth();
  const { currentTenant } = useTenantStore();
  const baseSync = useOfflineSync({
    enableOffline: true,
    enableCache: true,
    syncOnReconnect: true,
  });

  const [db] = useState(() => new OfflineDatabase());
  const [notificationManager] = useState(() =>
    notifications ? new OfflineNotificationManager() : null
  );
  const [storageInfo, setStorageInfo] = useState<StorageQuota | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<OfflineSyncResult | null>(null);

  const cleanupTimeoutRef = useRef<NodeJS.Timeout>();
  const visibilityChangeRef = useRef<() => void>();

  // Update storage info periodically
  const updateStorageInfo = useCallback(async () => {
    try {
      const quota = await db.getStorageQuota();
      setStorageInfo(quota);

      // Auto cleanup if over quota
      if (autoCleanup && quota.usage > 80) {
        const targetSize = storageQuota * 1024 * 1024 * 0.7; // 70% of quota
        await db.optimizeStorage(targetSize);

        const newQuota = await db.getStorageQuota();
        setStorageInfo(newQuota);

        notificationManager?.showNotification(
          'Storage Optimized',
          'Cleared old data to free up space',
          'info'
        );
      }
    } catch (error) {
      console.warn('Failed to update storage info:', error);
    }
  }, [db, autoCleanup, storageQuota, notificationManager]);

  // Enhanced queue operation with mobile-specific metadata
  const queueMobileOperation = useCallback(
    async (
      operation: 'create' | 'update' | 'delete',
      resource: string,
      data: unknown,
      options: {
        priority?: number;
        estimatedSize?: number;
        maxRetries?: number;
      } = {}
    ) => {
      if (!user || !currentTenant?.tenant) return;

      const { priority = 3, estimatedSize = JSON.stringify(data).length, maxRetries = 3 } = options;

      // Get device info
      let deviceInfo: MobileOfflineEntry['deviceInfo'] = {
        userAgent: navigator.userAgent,
        online: navigator.onLine,
      };

      // Add battery info if available
      if ('getBattery' in navigator) {
        try {
          const battery = await (navigator as any).getBattery();
          deviceInfo.batteryLevel = Math.round(battery.level * 100);
        } catch (error) {
          // Battery API not available or blocked
        }
      }

      // Add connection info if available
      if ('connection' in navigator) {
        const conn = (navigator as any).connection;
        deviceInfo.connectionType = conn.effectiveType || conn.type;
      }

      // Get location if available (for field operations)
      let location: MobileOfflineEntry['location'];
      if ('geolocation' in navigator && resource.includes('field')) {
        try {
          const position = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              timeout: 5000,
              maximumAge: 300000, // 5 minutes
            });
          });

          location = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          };
        } catch (error) {
          // Location not available
        }
      }

      const entry: Omit<MobileOfflineEntry, 'id' | 'timestamp' | 'retryCount' | 'status'> = {
        operation,
        resource,
        data,
        tenantId: currentTenant.tenant.id,
        userId: user.id,
        maxRetries,
        priority,
        estimatedSize,
        location,
        deviceInfo,
      };

      // Store in IndexedDB
      await db.queue.add({
        ...entry,
        timestamp: Date.now(),
        retryCount: 0,
        status: 'pending',
      });

      // Also use base sync for immediate processing if online
      if (navigator.onLine) {
        baseSync.queueOperation(operation, resource, data, maxRetries);
      }

      await updateStorageInfo();
    },
    [user, currentTenant?.tenant, db.queue, baseSync, updateStorageInfo]
  );

  // Enhanced sync with mobile optimizations
  const syncMobileOperations = useCallback(async (): Promise<OfflineSyncResult> => {
    if (!navigator.onLine || isSyncing || !currentTenant?.tenant?.id) {
      return {
        success: false,
        synced: 0,
        failed: 0,
        errors: ['Offline or already syncing'],
        duration: 0,
      };
    }

    setIsSyncing(true);
    const startTime = Date.now();
    let synced = 0;
    let failed = 0;
    const errors: string[] = [];

    try {
      // Get prioritized queue
      const queue = await db.getQueueByPriority(currentTenant.tenant.id);
      const pendingEntries = queue.filter(
        (entry) => entry.status === 'pending' || entry.status === 'failed'
      );

      if (pendingEntries.length === 0) {
        return {
          success: true,
          synced: 0,
          failed: 0,
          errors: [],
          duration: Date.now() - startTime,
        };
      }

      notificationManager?.showNotification(
        'Sync Started',
        `Syncing ${pendingEntries.length} operations...`,
        'info'
      );

      // Process by priority (highest first)
      for (const entry of pendingEntries) {
        try {
          await db.updateQueueStatus(entry.id!, 'syncing');

          // Simulate API call (replace with actual API)
          await new Promise((resolve) => setTimeout(resolve, 100));

          // Remove from queue on success
          await db.queue.delete(entry.id!);
          synced++;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          const retryCount = (entry.retryCount || 0) + 1;

          if (retryCount >= entry.maxRetries) {
            await db.updateQueueStatus(entry.id!, 'failed', errorMessage);
            failed++;
            errors.push(`${entry.resource}: ${errorMessage}`);
          } else {
            await db.queue.update(entry.id!, {
              status: 'pending',
              retryCount,
              error: errorMessage,
            });
          }
        }
      }

      const result: OfflineSyncResult = {
        success: failed === 0,
        synced,
        failed,
        errors,
        duration: Date.now() - startTime,
      };

      setLastSyncResult(result);

      // Show completion notification
      if (synced > 0 || failed > 0) {
        notificationManager?.showNotification(
          'Sync Complete',
          `Synced: ${synced}, Failed: ${failed}`,
          result.success ? 'success' : 'warning'
        );
      }

      return result;
    } catch (error) {
      const result: OfflineSyncResult = {
        success: false,
        synced,
        failed,
        errors: [...errors, error instanceof Error ? error.message : 'Sync failed'],
        duration: Date.now() - startTime,
      };

      setLastSyncResult(result);
      return result;
    } finally {
      setIsSyncing(false);
      await updateStorageInfo();
    }
  }, [isSyncing, currentTenant?.tenant?.id, db, notificationManager, updateStorageInfo]);

  // Auto cleanup
  const performCleanup = useCallback(async () => {
    if (!autoCleanup) return;

    try {
      const expiredCount = await db.cleanupExpiredCache();
      const oldAssetsCount = await db.cleanupOldAssets(cacheDays * 24 * 60 * 60 * 1000);

      if (expiredCount > 0 || oldAssetsCount > 0) {
        console.log(
          `Cleaned up ${expiredCount} expired cache entries and ${oldAssetsCount} old assets`
        );
        await updateStorageInfo();
      }
    } catch (error) {
      console.warn('Cleanup failed:', error);
    }
  }, [autoCleanup, cacheDays, db, updateStorageInfo]);

  // Background sync on visibility change
  useEffect(() => {
    if (!backgroundSync) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        // Delayed sync to allow app to fully resume
        setTimeout(() => {
          syncMobileOperations();
        }, 1000);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    visibilityChangeRef.current = handleVisibilityChange;

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [backgroundSync, syncMobileOperations]);

  // Periodic cleanup
  useEffect(() => {
    if (autoCleanup) {
      cleanupTimeoutRef.current = setInterval(performCleanup, 60 * 60 * 1000); // Every hour

      return () => {
        if (cleanupTimeoutRef.current) {
          clearInterval(cleanupTimeoutRef.current);
        }
      };
    }
  }, [autoCleanup, performCleanup]);

  // Initial setup
  useEffect(() => {
    updateStorageInfo();
    performCleanup();
  }, [updateStorageInfo, performCleanup]);

  return {
    // Base sync functionality
    ...baseSync,

    // Mobile-specific functionality
    queueMobileOperation,
    syncMobileOperations,

    // Mobile state
    isSyncing,
    lastSyncResult,
    storageInfo,

    // Database access
    db,

    // Utilities
    updateStorageInfo,
    performCleanup,

    // Config
    isBackgroundSyncEnabled: backgroundSync,
    isNotificationsEnabled: notifications,
    isCompressionEnabled: compression,
  };
}
