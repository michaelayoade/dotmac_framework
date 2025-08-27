/**
 * Service Worker Provider
 * Handles service worker registration and PWA functionality
 */

'use client';

import React, { createContext, type ReactNode, useContext, useEffect, useState } from 'react';
import {
  networkMonitor,
  pwaInstaller,
  registerServiceWorker,
  showUpdateNotification,
} from '../../lib/utils/serviceWorker';

interface ServiceWorkerContextType {
  isInstallable: boolean;
  isInstalled: boolean;
  isOnline: boolean;
  installApp: () => Promise<void>;
  registration: ServiceWorkerRegistration | null;
}

const ServiceWorkerContext = createContext<ServiceWorkerContextType>({
  isInstallable: false,
  isInstalled: false,
  isOnline: true,
  installApp: async () => {},
  registration: null,
});

export const useServiceWorker = () => {
  return useContext(ServiceWorkerContext);
};

interface ServiceWorkerProviderProps {
  children: ReactNode;
}

export function ServiceWorkerProvider({ children }: ServiceWorkerProviderProps) {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);
  const [isInstallable, setIsInstallable] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    // Initialize network status
    setIsOnline(networkMonitor.isOnline());

    // Monitor network changes
    const cleanup = networkMonitor.onStatusChange(setIsOnline);

    // Register service worker
    if (process.env.NODE_ENV === 'production') {
      registerServiceWorker({
        onSuccess: reg => {
          setRegistration(reg);
          // Service Worker registered successfully
        },
        onUpdate: reg => {
          setRegistration(reg);
          showUpdateNotification(reg);
        },
        onError: error => {
          console.error('Service Worker registration failed:', error);
        },
      });
    }

    // Monitor PWA installation status
    const checkInstallStatus = () => {
      const installStatus = pwaInstaller.getInstallationStatus();
      setIsInstallable(installStatus === 'available');
      setIsInstalled(installStatus === 'installed');
    };

    checkInstallStatus();

    // Check periodically for changes
    const interval = setInterval(checkInstallStatus, 5000);

    return () => {
      cleanup();
      clearInterval(interval);
    };
  }, []);

  const installApp = async () => {
    try {
      const result = await pwaInstaller.promptInstall();
      if (result.outcome === 'accepted') {
        setIsInstalled(true);
        setIsInstallable(false);
      }
    } catch (error) {
      console.error('Failed to install app:', error);
    }
  };

  const contextValue: ServiceWorkerContextType = {
    isInstallable,
    isInstalled,
    isOnline,
    installApp,
    registration,
  };

  return (
    <ServiceWorkerContext.Provider value={contextValue}>
      {children}
      {/* PWA Install Banner */}
      {isInstallable && !isInstalled && <PWAInstallBanner onInstall={installApp} />}
    </ServiceWorkerContext.Provider>
  );
}

// PWA Install Banner Component
interface PWAInstallBannerProps {
  onInstall: () => Promise<void>;
}

function PWAInstallBanner({ onInstall }: PWAInstallBannerProps) {
  const [isDismissed, setIsDismissed] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);

  useEffect(() => {
    // Check if user has dismissed the banner before
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    if (dismissed === 'true') {
      setIsDismissed(true);
    }
  }, []);

  const handleInstall = async () => {
    setIsInstalling(true);
    try {
      await onInstall();
      setIsDismissed(true);
    } catch (error) {
      console.error('Installation failed:', error);
    } finally {
      setIsInstalling(false);
    }
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    localStorage.setItem('pwa-install-dismissed', 'true');
  };

  if (isDismissed) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-sm z-50">
      <div className="bg-blue-600 text-white rounded-lg shadow-lg p-4">
        <div className="flex items-start">
          <div className="flex-1">
            <h3 className="font-semibold text-sm mb-1">Install DotMac Portal</h3>
            <p className="text-xs text-blue-100 mb-3">
              Get quick access to your services, even when offline
            </p>
            <div className="flex space-x-2">
              <button
                onClick={handleInstall}
                disabled={isInstalling}
                className="px-3 py-1 bg-white text-blue-600 rounded text-xs font-medium hover:bg-blue-50 disabled:opacity-50"
              >
                {isInstalling ? 'Installing...' : 'Install'}
              </button>
              <button
                onClick={handleDismiss}
                className="px-3 py-1 text-blue-100 hover:text-white text-xs"
              >
                Not now
              </button>
            </div>
          </div>
          <button onClick={handleDismiss} className="ml-2 text-blue-200 hover:text-white">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
