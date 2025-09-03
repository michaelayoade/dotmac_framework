import { useEffect, useState, useCallback } from 'react';
import { PWAManager } from './PWAManager';
import { PWAConfig, PWACapabilities, NotificationPayload, PushSubscriptionData } from './types';

let pwaManagerInstance: PWAManager | null = null;

export function usePWA(config?: PWAConfig) {
  const [pwaManager] = useState(() => {
    if (!pwaManagerInstance) {
      pwaManagerInstance = new PWAManager(config);
    }
    return pwaManagerInstance;
  });

  const [capabilities, setCapabilities] = useState<PWACapabilities | null>(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [canInstall, setCanInstall] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  // Initialize and get capabilities
  useEffect(() => {
    const initializePWA = async () => {
      // Wait a bit for PWA manager to initialize
      setTimeout(() => {
        const caps = pwaManager.getCapabilities();
        setCapabilities(caps);
        setIsInstalled(caps?.isPWA || false);
      }, 100);
    };

    initializePWA();
  }, [pwaManager]);

  // Handle online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Handle install prompt
  useEffect(() => {
    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setCanInstall(true);
    };

    const handleAppInstalled = () => {
      setCanInstall(false);
      setIsInstalled(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  // Handle service worker updates
  useEffect(() => {
    const handleSWMessage = (event: MessageEvent) => {
      if (event.data?.type === 'SW_UPDATE_AVAILABLE') {
        setUpdateAvailable(true);
      }
    };

    navigator.serviceWorker?.addEventListener('message', handleSWMessage);

    return () => {
      navigator.serviceWorker?.removeEventListener('message', handleSWMessage);
    };
  }, []);

  // Install app
  const installApp = useCallback(async (): Promise<boolean> => {
    if (!canInstall) return false;

    const result = await pwaManager.showInstallPrompt();
    if (result) {
      setCanInstall(false);
      setIsInstalled(true);
    }
    return result;
  }, [canInstall, pwaManager]);

  // Update app
  const updateApp = useCallback(async (): Promise<void> => {
    await pwaManager.updateApp();
    setUpdateAvailable(false);
    window.location.reload();
  }, [pwaManager]);

  // Show notification
  const showNotification = useCallback(
    async (payload: NotificationPayload): Promise<void> => {
      await pwaManager.showNotification(payload);
    },
    [pwaManager]
  );

  // Request push subscription
  const requestPushSubscription = useCallback(async (): Promise<PushSubscriptionData | null> => {
    return await pwaManager.requestPushSubscription();
  }, [pwaManager]);

  // Share content
  const shareContent = useCallback(
    async (data: { title?: string; text?: string; url?: string }): Promise<boolean> => {
      return await pwaManager.share(data);
    },
    [pwaManager]
  );

  // Clear app cache
  const clearCache = useCallback(async (): Promise<void> => {
    await pwaManager.clearCache();
  }, [pwaManager]);

  return {
    // Status
    capabilities,
    isOnline,
    canInstall,
    isInstalled,
    updateAvailable,
    isStandalone: capabilities?.isStandalone || false,
    platform: capabilities?.platform || 'unknown',

    // Actions
    installApp,
    updateApp,
    showNotification,
    requestPushSubscription,
    shareContent,
    clearCache,

    // Manager instance
    pwaManager,
  };
}
