'use client';

import { useState, useEffect, useCallback } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

interface PWAState {
  isInstalled: boolean;
  isInstallable: boolean;
  isOffline: boolean;
  isStandalone: boolean;
  installPrompt: BeforeInstallPromptEvent | null;
  swRegistration: ServiceWorkerRegistration | null;
  swUpdateAvailable: boolean;
}

export function usePWA() {
  const [pwaState, setPWAState] = useState<PWAState>({
    isInstalled: false,
    isInstallable: false,
    isOffline: false,
    isStandalone: false,
    installPrompt: null,
    swRegistration: null,
    swUpdateAvailable: false,
  });

  // Check if app is running in standalone mode
  const checkStandalone = useCallback(() => {
    const isStandalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone === true ||
      document.referrer.includes('android-app://');

    setPWAState((prev) => ({ ...prev, isStandalone }));
  }, []);

  // Check online/offline status
  const checkOnlineStatus = useCallback(() => {
    const isOffline = !navigator.onLine;
    setPWAState((prev) => ({ ...prev, isOffline }));
  }, []);

  // Register service worker
  const registerServiceWorker = useCallback(async () => {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');

        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                setPWAState((prev) => ({ ...prev, swUpdateAvailable: true }));
              }
            });
          }
        });

        setPWAState((prev) => ({ ...prev, swRegistration: registration }));
        console.log('Service Worker registered successfully');
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }, []);

  // Handle install prompt
  const handleInstallPrompt = useCallback((e: BeforeInstallPromptEvent) => {
    e.preventDefault();
    setPWAState((prev) => ({
      ...prev,
      installPrompt: e,
      isInstallable: true,
    }));
  }, []);

  // Install PWA
  const installPWA = useCallback(async () => {
    if (pwaState.installPrompt) {
      try {
        await pwaState.installPrompt.prompt();
        const { outcome } = await pwaState.installPrompt.userChoice;

        if (outcome === 'accepted') {
          setPWAState((prev) => ({
            ...prev,
            isInstalled: true,
            isInstallable: false,
            installPrompt: null,
          }));
        }
      } catch (error) {
        console.error('PWA installation failed:', error);
      }
    }
  }, [pwaState.installPrompt]);

  // Update service worker
  const updateServiceWorker = useCallback(() => {
    if (pwaState.swRegistration?.waiting) {
      pwaState.swRegistration.waiting.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  }, [pwaState.swRegistration]);

  // Get app version from service worker
  const getAppVersion = useCallback(async (): Promise<string> => {
    return new Promise((resolve) => {
      if (pwaState.swRegistration?.active) {
        const messageChannel = new MessageChannel();
        messageChannel.port1.onmessage = (event) => {
          resolve(event.data.version || 'unknown');
        };

        pwaState.swRegistration.active.postMessage({ type: 'GET_VERSION' }, [messageChannel.port2]);
      } else {
        resolve('unknown');
      }
    });
  }, [pwaState.swRegistration]);

  // Share data using Web Share API
  const shareData = useCallback(async (data: ShareData): Promise<boolean> => {
    if (navigator.share) {
      try {
        await navigator.share(data);
        return true;
      } catch (error) {
        console.error('Sharing failed:', error);
        return false;
      }
    } else {
      // Fallback to clipboard or other sharing method
      if (navigator.clipboard && data.text) {
        try {
          await navigator.clipboard.writeText(data.text);
          return true;
        } catch (error) {
          console.error('Clipboard write failed:', error);
          return false;
        }
      }
      return false;
    }
  }, []);

  // Check if device supports features
  const getDeviceCapabilities = useCallback(() => {
    return {
      geolocation: 'geolocation' in navigator,
      camera: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
      vibration: 'vibrate' in navigator,
      notification: 'Notification' in window,
      backgroundSync:
        'serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype,
      share: 'share' in navigator,
      clipboard: 'clipboard' in navigator,
      wakeLock: 'wakeLock' in navigator,
      deviceMotion: 'DeviceMotionEvent' in window,
      deviceOrientation: 'DeviceOrientationEvent' in window,
      battery: 'getBattery' in navigator,
    };
  }, []);

  // Request persistent storage
  const requestPersistentStorage = useCallback(async (): Promise<boolean> => {
    if ('storage' in navigator && 'persist' in navigator.storage) {
      try {
        const persistent = await navigator.storage.persist();
        console.log('Persistent storage granted:', persistent);
        return persistent;
      } catch (error) {
        console.error('Persistent storage request failed:', error);
        return false;
      }
    }
    return false;
  }, []);

  // Get storage usage
  const getStorageUsage = useCallback(async () => {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      try {
        const estimate = await navigator.storage.estimate();
        return {
          used: estimate.usage || 0,
          available: estimate.quota || 0,
          percentage: estimate.quota
            ? Math.round(((estimate.usage || 0) / estimate.quota) * 100)
            : 0,
        };
      } catch (error) {
        console.error('Storage estimate failed:', error);
        return { used: 0, available: 0, percentage: 0 };
      }
    }
    return { used: 0, available: 0, percentage: 0 };
  }, []);

  // Initialize PWA functionality
  useEffect(() => {
    checkStandalone();
    checkOnlineStatus();
    registerServiceWorker();
    requestPersistentStorage();

    // Event listeners
    window.addEventListener('beforeinstallprompt', handleInstallPrompt as EventListener);
    window.addEventListener('online', checkOnlineStatus);
    window.addEventListener('offline', checkOnlineStatus);

    // Check for app updates periodically
    const updateCheckInterval = setInterval(() => {
      if (pwaState.swRegistration) {
        pwaState.swRegistration.update();
      }
    }, 30000); // Check every 30 seconds

    return () => {
      window.removeEventListener('beforeinstallprompt', handleInstallPrompt as EventListener);
      window.removeEventListener('online', checkOnlineStatus);
      window.removeEventListener('offline', checkOnlineStatus);
      clearInterval(updateCheckInterval);
    };
  }, [checkStandalone, checkOnlineStatus, registerServiceWorker, handleInstallPrompt]);

  return {
    ...pwaState,
    installPWA,
    updateServiceWorker,
    getAppVersion,
    shareData,
    getDeviceCapabilities,
    requestPersistentStorage,
    getStorageUsage,
  };
}

// Hook for managing app installation banner
export function useInstallBanner() {
  const [showBanner, setShowBanner] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const { isInstallable, isStandalone, installPWA } = usePWA();

  useEffect(() => {
    // Check if banner was previously dismissed
    const dismissed = localStorage.getItem('pwa-banner-dismissed');
    if (dismissed) {
      const dismissedDate = new Date(dismissed);
      const now = new Date();
      const daysSinceDismissed = Math.floor(
        (now.getTime() - dismissedDate.getTime()) / (1000 * 60 * 60 * 24)
      );

      // Show banner again after 7 days
      if (daysSinceDismissed >= 7) {
        localStorage.removeItem('pwa-banner-dismissed');
        setBannerDismissed(false);
      } else {
        setBannerDismissed(true);
      }
    }

    // Show banner if app is installable, not standalone, and not dismissed
    setShowBanner(isInstallable && !isStandalone && !bannerDismissed);
  }, [isInstallable, isStandalone, bannerDismissed]);

  const dismissBanner = useCallback(() => {
    setShowBanner(false);
    setBannerDismissed(true);
    localStorage.setItem('pwa-banner-dismissed', new Date().toISOString());
  }, []);

  return {
    showBanner,
    dismissBanner,
    installPWA,
  };
}
