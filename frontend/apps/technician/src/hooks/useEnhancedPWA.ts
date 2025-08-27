/**
 * Enhanced PWA Hook for Technician Portal
 * Advanced offline capabilities, background sync, and native features
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  offlineDB,
  WorkOrder,
  Photo,
  TechnicianLocation,
  OfflineAction,
} from '../lib/enhanced-offline-db';
import { SecureTokenManager } from '../lib/auth/secure-token-manager';

interface PWACapabilities {
  isInstallable: boolean;
  isInstalled: boolean;
  isOffline: boolean;
  hasCamera: boolean;
  hasGeolocation: boolean;
  hasBluetooth: boolean;
  hasNfc: boolean;
  supportsPush: boolean;
  supportsBackgroundSync: boolean;
  supportsBadge: boolean;
}

interface SyncStatus {
  isOnline: boolean;
  isSyncing: boolean;
  lastSyncTime: string | null;
  pendingActions: number;
  syncError: string | null;
}

interface GeolocationData {
  latitude: number;
  longitude: number;
  accuracy: number;
  heading?: number;
  speed?: number;
  timestamp: number;
}

interface UseEnhancedPWAReturn {
  // PWA state
  capabilities: PWACapabilities;
  syncStatus: SyncStatus;
  installPrompt: Event | null;

  // Actions
  installApp: () => Promise<void>;
  requestPermissions: () => Promise<void>;
  syncData: () => Promise<void>;

  // Camera functionality
  capturePhoto: (options?: CaptureOptions) => Promise<Blob>;

  // Geolocation
  getCurrentLocation: () => Promise<GeolocationData>;
  startLocationTracking: (interval?: number) => void;
  stopLocationTracking: () => void;

  // Offline work orders
  getOfflineWorkOrders: () => Promise<WorkOrder[]>;
  updateWorkOrderOffline: (workOrder: WorkOrder) => Promise<void>;
  completeWorkOrderOffline: (id: string, data: CompletionData) => Promise<void>;

  // Background operations
  queueBackgroundSync: (action: OfflineAction) => Promise<void>;
  getPendingActions: () => Promise<OfflineAction[]>;

  // Device features
  vibrate: (pattern: number | number[]) => void;
  setBadge: (count: number) => Promise<void>;
  clearBadge: () => Promise<void>;
}

interface CaptureOptions {
  quality?: number;
  width?: number;
  height?: number;
  facing?: 'user' | 'environment';
}

interface CompletionData {
  completion_notes: string;
  signature?: string;
  photos: Photo[];
}

export function useEnhancedPWA(): UseEnhancedPWAReturn {
  const [capabilities, setCapabilities] = useState<PWACapabilities>({
    isInstallable: false,
    isInstalled: false,
    isOffline: !navigator.onLine,
    hasCamera: false,
    hasGeolocation: false,
    hasBluetooth: false,
    hasNfc: false,
    supportsPush: false,
    supportsBackgroundSync: false,
    supportsBadge: false,
  });

  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    isOnline: navigator.onLine,
    isSyncing: false,
    lastSyncTime: null,
    pendingActions: 0,
    syncError: null,
  });

  const [installPrompt, setInstallPrompt] = useState<Event | null>(null);

  const locationWatchId = useRef<number | null>(null);
  const syncIntervalId = useRef<NodeJS.Timeout | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Initialize PWA capabilities detection
  useEffect(() => {
    const detectCapabilities = async () => {
      const newCapabilities: PWACapabilities = {
        isInstallable: false,
        isInstalled: window.matchMedia('(display-mode: standalone)').matches,
        isOffline: !navigator.onLine,
        hasCamera: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
        hasGeolocation: 'geolocation' in navigator,
        hasBluetooth: 'bluetooth' in navigator,
        hasNfc: 'nfc' in navigator,
        supportsPush: 'serviceWorker' in navigator && 'PushManager' in window,
        supportsBackgroundSync:
          'serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype,
        supportsBadge: 'setAppBadge' in navigator,
      };

      setCapabilities(newCapabilities);
    };

    detectCapabilities();

    // Listen for install prompt
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e);
      setCapabilities((prev) => ({ ...prev, isInstallable: true }));
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Listen for network status changes
    const handleOnline = () => {
      setCapabilities((prev) => ({ ...prev, isOffline: false }));
      setSyncStatus((prev) => ({ ...prev, isOnline: true }));
      // Auto-sync when coming back online
      syncData();
    };

    const handleOffline = () => {
      setCapabilities((prev) => ({ ...prev, isOffline: true }));
      setSyncStatus((prev) => ({ ...prev, isOnline: false }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initialize offline database
    offlineDB.init().catch(console.error);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Initialize sync status
  useEffect(() => {
    const loadSyncStatus = async () => {
      try {
        await offlineDB.init();
        const pendingActions = await offlineDB.getPendingActions();
        const lastSyncTime = await offlineDB.getSyncMetadata('lastSyncTime');

        setSyncStatus((prev) => ({
          ...prev,
          pendingActions: pendingActions.length,
          lastSyncTime: lastSyncTime || null,
        }));
      } catch (error) {
        console.error('Failed to load sync status:', error);
      }
    };

    loadSyncStatus();
  }, []);

  // Install PWA
  const installApp = useCallback(async () => {
    if (!installPrompt) return;

    try {
      const promptEvent = installPrompt as any;
      const result = await promptEvent.prompt();

      if (result.outcome === 'accepted') {
        setCapabilities((prev) => ({ ...prev, isInstalled: true, isInstallable: false }));
        setInstallPrompt(null);
      }
    } catch (error) {
      console.error('Failed to install app:', error);
    }
  }, [installPrompt]);

  // Request necessary permissions
  const requestPermissions = useCallback(async () => {
    const permissions = [];

    // Camera permission
    if (capabilities.hasCamera) {
      try {
        await navigator.mediaDevices.getUserMedia({ video: true });
        permissions.push('camera');
      } catch (error) {
        console.warn('Camera permission denied:', error);
      }
    }

    // Geolocation permission
    if (capabilities.hasGeolocation) {
      try {
        await new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject);
        });
        permissions.push('geolocation');
      } catch (error) {
        console.warn('Geolocation permission denied:', error);
      }
    }

    // Push notification permission
    if (capabilities.supportsPush) {
      try {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          permissions.push('notifications');
        }
      } catch (error) {
        console.warn('Notification permission denied:', error);
      }
    }

    return permissions;
  }, [capabilities]);

  // Sync data with server
  const syncData = useCallback(async () => {
    if (!navigator.onLine) return;

    setSyncStatus((prev) => ({ ...prev, isSyncing: true, syncError: null }));

    try {
      const pendingActions = await offlineDB.getPendingActions();
      let successfulSyncs = 0;

      for (const action of pendingActions) {
        try {
          // Execute sync action based on type
          switch (action.type) {
            case 'UPDATE_WORK_ORDER':
              await syncWorkOrder(action.data);
              break;
            case 'UPLOAD_PHOTO':
              await syncPhoto(action.data);
              break;
            case 'UPDATE_LOCATION':
              await syncLocation(action.data);
              break;
            case 'COMPLETE_WORK_ORDER':
              await syncWorkOrderCompletion(action.data);
              break;
          }

          await offlineDB.removeOfflineAction(action.id);
          successfulSyncs++;
        } catch (error) {
          console.error(`Failed to sync action ${action.id}:`, error);

          // Increment retry count
          action.retry_count++;
          if (action.retry_count >= action.max_retries) {
            await offlineDB.removeOfflineAction(action.id);
          } else {
            await offlineDB.queueOfflineAction(action);
          }
        }
      }

      // Update sync metadata
      const now = new Date().toISOString();
      await offlineDB.setSyncMetadata('lastSyncTime', now);

      // Update sync status
      const remainingActions = await offlineDB.getPendingActions();
      setSyncStatus((prev) => ({
        ...prev,
        isSyncing: false,
        lastSyncTime: now,
        pendingActions: remainingActions.length,
        syncError: null,
      }));
    } catch (error) {
      setSyncStatus((prev) => ({
        ...prev,
        isSyncing: false,
        syncError: error instanceof Error ? error.message : 'Sync failed',
      }));
    }
  }, []);

  // Camera functionality
  const capturePhoto = useCallback(
    async (options: CaptureOptions = {}): Promise<Blob> => {
      if (!capabilities.hasCamera) {
        throw new Error('Camera not available');
      }

      const { quality = 0.8, width = 1920, height = 1080, facing = 'environment' } = options;

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: width },
            height: { ideal: height },
            facingMode: facing,
          },
        });

        // Create video element if not exists
        if (!videoRef.current) {
          videoRef.current = document.createElement('video');
          videoRef.current.autoplay = true;
          videoRef.current.playsInline = true;
        }

        videoRef.current.srcObject = stream;
        await videoRef.current.play();

        // Create canvas for capture
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d')!;

        // Capture frame
        ctx.drawImage(videoRef.current, 0, 0, width, height);

        // Stop stream
        stream.getTracks().forEach((track) => track.stop());

        // Convert to blob
        return new Promise((resolve) => {
          canvas.toBlob(
            (blob) => {
              resolve(blob!);
            },
            'image/jpeg',
            quality
          );
        });
      } catch (error) {
        throw new Error(`Camera capture failed: ${error}`);
      }
    },
    [capabilities.hasCamera]
  );

  // Geolocation functionality
  const getCurrentLocation = useCallback(async (): Promise<GeolocationData> => {
    if (!capabilities.hasGeolocation) {
      throw new Error('Geolocation not available');
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            heading: position.coords.heading || undefined,
            speed: position.coords.speed || undefined,
            timestamp: position.timestamp,
          });
        },
        reject,
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000, // 1 minute
        }
      );
    });
  }, [capabilities.hasGeolocation]);

  // Start location tracking
  const startLocationTracking = useCallback(
    (interval: number = 30000) => {
      if (!capabilities.hasGeolocation || locationWatchId.current) return;

      locationWatchId.current = navigator.geolocation.watchPosition(
        async (position) => {
          const location: TechnicianLocation = {
            id: `loc_${Date.now()}_${Math.random().toString(36).slice(2)}`,
            technician_id: 'current_technician', // Should come from auth context
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            heading: position.coords.heading || undefined,
            speed: position.coords.speed || undefined,
            timestamp: new Date(position.timestamp).toISOString(),
            sync_status: 'PENDING',
          };

          try {
            await offlineDB.saveLocation(location);
          } catch (error) {
            console.error('Failed to save location:', error);
          }
        },
        (error) => {
          console.error('Location tracking error:', error);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: interval,
        }
      );
    },
    [capabilities.hasGeolocation]
  );

  // Stop location tracking
  const stopLocationTracking = useCallback(() => {
    if (locationWatchId.current) {
      navigator.geolocation.clearWatch(locationWatchId.current);
      locationWatchId.current = null;
    }
  }, []);

  // Offline work orders
  const getOfflineWorkOrders = useCallback(async (): Promise<WorkOrder[]> => {
    return await offlineDB.getWorkOrders();
  }, []);

  const updateWorkOrderOffline = useCallback(async (workOrder: WorkOrder): Promise<void> => {
    await offlineDB.saveWorkOrder(workOrder);

    // Queue for sync
    await offlineDB.queueOfflineAction({
      id: `update_${workOrder.id}_${Date.now()}`,
      type: 'UPDATE_WORK_ORDER',
      data: workOrder,
      timestamp: new Date().toISOString(),
      retry_count: 0,
      max_retries: 3,
    });
  }, []);

  const completeWorkOrderOffline = useCallback(
    async (id: string, data: CompletionData): Promise<void> => {
      await offlineDB.completeWorkOrder(id, data);

      // Update pending actions count
      const pendingActions = await offlineDB.getPendingActions();
      setSyncStatus((prev) => ({ ...prev, pendingActions: pendingActions.length }));
    },
    []
  );

  // Background sync queue
  const queueBackgroundSync = useCallback(async (action: OfflineAction): Promise<void> => {
    await offlineDB.queueOfflineAction(action);

    // Update pending actions count
    const pendingActions = await offlineDB.getPendingActions();
    setSyncStatus((prev) => ({ ...prev, pendingActions: pendingActions.length }));
  }, []);

  const getPendingActions = useCallback(async (): Promise<OfflineAction[]> => {
    return await offlineDB.getPendingActions();
  }, []);

  // Device features
  const vibrate = useCallback((pattern: number | number[]) => {
    if ('vibrate' in navigator) {
      navigator.vibrate(pattern);
    }
  }, []);

  const setBadge = useCallback(async (count: number): Promise<void> => {
    if ('setAppBadge' in navigator) {
      try {
        await (navigator as any).setAppBadge(count);
      } catch (error) {
        console.warn('Failed to set app badge:', error);
      }
    }
  }, []);

  const clearBadge = useCallback(async (): Promise<void> => {
    if ('clearAppBadge' in navigator) {
      try {
        await (navigator as any).clearAppBadge();
      } catch (error) {
        console.warn('Failed to clear app badge:', error);
      }
    }
  }, []);

  // Auto-sync on regular intervals when online
  useEffect(() => {
    if (capabilities.isOffline) return;

    syncIntervalId.current = setInterval(
      () => {
        if (navigator.onLine && syncStatus.pendingActions > 0) {
          syncData();
        }
      },
      2 * 60 * 1000
    ); // Every 2 minutes

    return () => {
      if (syncIntervalId.current) {
        clearInterval(syncIntervalId.current);
      }
    };
  }, [capabilities.isOffline, syncStatus.pendingActions, syncData]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopLocationTracking();
      if (syncIntervalId.current) {
        clearInterval(syncIntervalId.current);
      }
    };
  }, [stopLocationTracking]);

  return {
    capabilities,
    syncStatus,
    installPrompt,
    installApp,
    requestPermissions,
    syncData,
    capturePhoto,
    getCurrentLocation,
    startLocationTracking,
    stopLocationTracking,
    getOfflineWorkOrders,
    updateWorkOrderOffline,
    completeWorkOrderOffline,
    queueBackgroundSync,
    getPendingActions,
    vibrate,
    setBadge,
    clearBadge,
  };
}

// Utility functions for sync operations
async function syncWorkOrder(workOrder: WorkOrder): Promise<void> {
  // SECURITY: Use cookie-only authentication - no tokens
  const response = await fetch(`/api/v1/field-ops/work-orders/${workOrder.id}`, {
    method: 'PUT',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workOrder),
  });

  if (!response.ok) {
    throw new Error(`Failed to sync work order: ${response.statusText}`);
  }
}

async function syncPhoto(photo: Photo): Promise<void> {
  const formData = new FormData();
  formData.append('photo', photo.blob, photo.filename);
  formData.append('work_order_id', photo.work_order_id);
  formData.append('category', photo.category);
  formData.append('description', photo.description || '');

  // SECURITY: Use cookie-only authentication - no tokens
  const response = await fetch('/api/v1/field-ops/photos/upload', {
    method: 'POST',
    credentials: 'include',
    headers: {
      // No Authorization header needed - cookies handle auth
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to sync photo: ${response.statusText}`);
  }
}

async function syncLocation(location: TechnicianLocation): Promise<void> {
  // SECURITY: Use cookie-only authentication - no tokens
  const response = await fetch('/api/v1/field-ops/technicians/location', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(location),
  });

  if (!response.ok) {
    throw new Error(`Failed to sync location: ${response.statusText}`);
  }
}

async function syncWorkOrderCompletion(data: any): Promise<void> {
  const token = await SecureTokenManager.getToken();
  const response = await fetch(`/api/v1/field-ops/work-orders/${data.work_order_id}/complete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to sync work order completion: ${response.statusText}`);
  }
}
