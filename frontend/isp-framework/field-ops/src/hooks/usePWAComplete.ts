/**
 * Complete PWA Hook
 * React hooks for comprehensive Progressive Web App functionality
 */

import { useState, useEffect, useCallback } from 'react';
import { pwaManager, PWACapabilities } from '../lib/pwa/pwa-manager';
import { pushManager, PushSubscriptionInfo } from '../lib/notifications/push-manager';
import { backgroundSyncManager } from '../lib/sync/background-sync';

interface PWAState {
  isOnline: boolean;
  isInstallable: boolean;
  isInstalled: boolean;
  capabilities: PWACapabilities;
  updateAvailable: boolean;
}

interface NotificationState {
  permission: NotificationPermission;
  subscription: PushSubscriptionInfo;
  isSupported: boolean;
}

interface SyncState {
  pending: number;
  inProgress: boolean;
  lastSync: Date | null;
}

export function usePWAComplete() {
  const [pwaState, setPwaState] = useState<PWAState>({
    isOnline: navigator.onLine,
    isInstallable: false,
    isInstalled: false,
    capabilities: pwaManager.getCapabilities(),
    updateAvailable: false,
  });

  const [notificationState, setNotificationState] = useState<NotificationState>({
    permission: 'default',
    subscription: pushManager.getSubscriptionInfo(),
    isSupported: pushManager.getSubscriptionInfo().isSupported,
  });

  const [syncState, setSyncState] = useState<SyncState>({
    pending: 0,
    inProgress: false,
    lastSync: null,
  });

  const [updateAvailable, setUpdateAvailable] = useState(false);

  // PWA State Management
  useEffect(() => {
    const updatePWAState = () => {
      setPwaState({
        isOnline: pwaManager.isOnlineMode(),
        isInstallable: pwaManager.canInstall(),
        isInstalled: pwaManager.getInstallabilityState() === 'installed',
        capabilities: pwaManager.getCapabilities(),
        updateAvailable,
      });
    };

    updatePWAState();

    // Network status listeners
    const handleOnline = () => updatePWAState();
    const handleOffline = () => updatePWAState();

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Install prompt listener
    const handleInstallPrompt = () => updatePWAState();
    window.addEventListener('beforeinstallprompt', handleInstallPrompt);
    window.addEventListener('appinstalled', handleInstallPrompt);

    // Service worker update listener
    if ('serviceWorker' in navigator) {
      const handleServiceWorkerUpdate = () => {
        setUpdateAvailable(true);
        updatePWAState();
      };

      navigator.serviceWorker.addEventListener('controllerchange', handleServiceWorkerUpdate);

      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
        window.removeEventListener('beforeinstallprompt', handleInstallPrompt);
        window.removeEventListener('appinstalled', handleInstallPrompt);
        navigator.serviceWorker.removeEventListener('controllerchange', handleServiceWorkerUpdate);
      };
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('beforeinstallprompt', handleInstallPrompt);
      window.removeEventListener('appinstalled', handleInstallPrompt);
    };
  }, [updateAvailable]);

  // Notification State Management
  useEffect(() => {
    const updateNotificationState = () => {
      setNotificationState({
        permission: 'Notification' in window ? Notification.permission : 'denied',
        subscription: pushManager.getSubscriptionInfo(),
        isSupported: pushManager.getSubscriptionInfo().isSupported,
      });
    };

    updateNotificationState();

    // Check for permission changes periodically
    const interval = setInterval(updateNotificationState, 5000);

    return () => {
      clearInterval(interval);
    };
  }, []);

  // Sync State Management
  useEffect(() => {
    const updateSyncState = () => {
      const status = backgroundSyncManager.getSyncStatus();
      setSyncState({
        pending: status.pending,
        inProgress: status.inProgress,
        lastSync:
          status.tasks.length > 0
            ? new Date(Math.max(...status.tasks.map((t) => t.lastAttempt || t.createdAt)))
            : null,
      });
    };

    updateSyncState();

    // Listen for sync events
    const handleSyncSuccess = () => updateSyncState();
    const handleSyncFailed = () => updateSyncState();

    window.addEventListener('sync-success', handleSyncSuccess);
    window.addEventListener('sync-failed', handleSyncFailed);

    const interval = setInterval(updateSyncState, 5000);

    return () => {
      window.removeEventListener('sync-success', handleSyncSuccess);
      window.removeEventListener('sync-failed', handleSyncFailed);
      clearInterval(interval);
    };
  }, []);

  // PWA Methods
  const install = useCallback(async (): Promise<boolean> => {
    try {
      return await pwaManager.promptInstall();
    } catch (error) {
      console.error('Installation failed:', error);
      return false;
    }
  }, []);

  const update = useCallback(async (): Promise<void> => {
    try {
      await pwaManager.skipWaiting();
      setUpdateAvailable(false);
    } catch (error) {
      console.error('Update failed:', error);
    }
  }, []);

  const clearCache = useCallback(async (): Promise<void> => {
    try {
      await pwaManager.clearCache();
    } catch (error) {
      console.error('Clear cache failed:', error);
    }
  }, []);

  const prefetchCritical = useCallback(async (): Promise<void> => {
    try {
      await pwaManager.prefetchCriticalData();
    } catch (error) {
      console.error('Prefetch failed:', error);
    }
  }, []);

  const share = useCallback(
    async (data: { title?: string; text?: string; url?: string }): Promise<boolean> => {
      if (!pwaManager.canShare()) {
        return false;
      }

      try {
        await pwaManager.share(data);
        return true;
      } catch (error) {
        console.error('Share failed:', error);
        return false;
      }
    },
    []
  );

  const requestPersistentStorage = useCallback(async (): Promise<boolean> => {
    try {
      return await pwaManager.requestPersistentStorage();
    } catch (error) {
      console.error('Persistent storage request failed:', error);
      return false;
    }
  }, []);

  const getStorageEstimate = useCallback(async (): Promise<StorageEstimate | null> => {
    try {
      return await pwaManager.getStorageEstimate();
    } catch (error) {
      console.error('Storage estimate failed:', error);
      return null;
    }
  }, []);

  // Notification Methods
  const requestNotificationPermission = useCallback(async (): Promise<NotificationPermission> => {
    try {
      const permission = await pushManager.requestPermission();
      setNotificationState((prev) => ({ ...prev, permission }));
      return permission;
    } catch (error) {
      console.error('Permission request failed:', error);
      throw error;
    }
  }, []);

  const subscribeToNotifications = useCallback(async (): Promise<boolean> => {
    try {
      await pushManager.subscribe();
      setNotificationState((prev) => ({
        ...prev,
        subscription: pushManager.getSubscriptionInfo(),
      }));
      return true;
    } catch (error) {
      console.error('Subscription failed:', error);
      return false;
    }
  }, []);

  const unsubscribeFromNotifications = useCallback(async (): Promise<boolean> => {
    try {
      const success = await pushManager.unsubscribe();
      if (success) {
        setNotificationState((prev) => ({
          ...prev,
          subscription: pushManager.getSubscriptionInfo(),
        }));
      }
      return success;
    } catch (error) {
      console.error('Unsubscription failed:', error);
      return false;
    }
  }, []);

  const sendTestNotification = useCallback(async (payload?: any): Promise<boolean> => {
    try {
      await pushManager.sendTestNotification(payload);
      return true;
    } catch (error) {
      console.error('Test notification failed:', error);
      return false;
    }
  }, []);

  // Sync Methods
  const queueSync = useCallback(
    async (
      endpoint: string,
      method: 'GET' | 'POST' | 'PUT' | 'DELETE',
      data?: any,
      options?: any
    ): Promise<string> => {
      const taskId = await backgroundSyncManager.queueSync(endpoint, method, data, options);

      setSyncState((prev) => ({
        ...prev,
        pending: backgroundSyncManager.getSyncStatus().pending,
      }));

      return taskId;
    },
    []
  );

  const cancelSync = useCallback((taskId: string): boolean => {
    const success = backgroundSyncManager.cancelSync(taskId);

    if (success) {
      setSyncState((prev) => ({
        ...prev,
        pending: backgroundSyncManager.getSyncStatus().pending,
      }));
    }

    return success;
  }, []);

  const triggerSync = useCallback(async (): Promise<void> => {
    try {
      await backgroundSyncManager.triggerSync();
    } catch (error) {
      console.error('Manual sync trigger failed:', error);
    }
  }, []);

  // Convenience Methods
  const syncWorkOrderUpdate = useCallback(
    async (workOrderId: string, data: any): Promise<string> => {
      return backgroundSyncManager.syncWorkOrderUpdate(workOrderId, data);
    },
    []
  );

  const syncInventoryUpdate = useCallback(async (itemId: string, data: any): Promise<string> => {
    return backgroundSyncManager.syncInventoryUpdate(itemId, data);
  }, []);

  const syncPhotoUpload = useCallback(
    async (workOrderId: string, photoData: FormData): Promise<string> => {
      return backgroundSyncManager.syncPhotoUpload(workOrderId, photoData);
    },
    []
  );

  const syncLocationUpdate = useCallback(async (locationData: any): Promise<string> => {
    return backgroundSyncManager.syncLocationUpdate(locationData);
  }, []);

  // Complete Setup Workflow
  const setupCompleteWorkflow = useCallback(async (): Promise<{
    success: boolean;
    permissions: {
      notifications: boolean;
      persistentStorage: boolean;
    };
    errors: string[];
  }> => {
    const errors: string[] = [];
    const permissions = {
      notifications: false,
      persistentStorage: false,
    };

    try {
      // Request notification permission
      const notificationPermission = await requestNotificationPermission();
      permissions.notifications = notificationPermission === 'granted';

      if (permissions.notifications) {
        // Subscribe to all notification types
        await pushManager.subscribeToWorkOrderNotifications();
        await pushManager.subscribeToInventoryAlerts();
        await pushManager.subscribeToSystemNotifications();
      } else {
        errors.push('Notification permission denied');
      }
    } catch (error) {
      errors.push(`Notification setup failed: ${error.message}`);
    }

    try {
      // Request persistent storage
      permissions.persistentStorage = await requestPersistentStorage();
      if (!permissions.persistentStorage) {
        errors.push('Persistent storage not granted');
      }
    } catch (error) {
      errors.push(`Storage setup failed: ${error.message}`);
    }

    try {
      // Prefetch critical data
      await prefetchCritical();
    } catch (error) {
      errors.push(`Prefetch failed: ${error.message}`);
    }

    const success = errors.length === 0;

    return {
      success,
      permissions,
      errors,
    };
  }, [requestNotificationPermission, requestPersistentStorage, prefetchCritical]);

  // Quick status check
  const getStatus = useCallback(() => {
    return {
      pwa: {
        installed: pwaState.isInstalled,
        installable: pwaState.isInstallable,
        online: pwaState.isOnline,
        updateAvailable: pwaState.updateAvailable,
      },
      notifications: {
        supported: notificationState.isSupported,
        permission: notificationState.permission,
        subscribed: notificationState.subscription.isSubscribed,
      },
      sync: {
        pending: syncState.pending,
        inProgress: syncState.inProgress,
        lastSync: syncState.lastSync,
      },
      capabilities: pwaState.capabilities,
    };
  }, [pwaState, notificationState, syncState]);

  return {
    // State
    pwa: pwaState,
    notifications: notificationState,
    sync: syncState,

    // PWA Methods
    install,
    update,
    clearCache,
    prefetchCritical,
    share,
    requestPersistentStorage,
    getStorageEstimate,

    // Notification Methods
    requestNotificationPermission,
    subscribeToNotifications,
    unsubscribeFromNotifications,
    sendTestNotification,

    // Sync Methods
    queueSync,
    cancelSync,
    triggerSync,
    syncWorkOrderUpdate,
    syncInventoryUpdate,
    syncPhotoUpload,
    syncLocationUpdate,

    // Utilities
    setupCompleteWorkflow,
    getStatus,
  };
}
