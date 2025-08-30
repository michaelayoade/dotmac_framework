import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { MobileConfig, MobileContextValue, DeviceInfo } from './types';

const MobileContext = createContext<MobileContextValue | undefined>(undefined);

interface MobileProviderProps {
  children: ReactNode;
  config?: MobileConfig;
}

export function MobileProvider({ children, config = {} }: MobileProviderProps) {
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo | null>(null);
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('portrait');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [battery, setBattery] = useState<MobileContextValue['battery']>();

  // Detect device info
  useEffect(() => {
    const detectDevice = (): DeviceInfo => {
      const userAgent = navigator.userAgent.toLowerCase();

      // Platform detection
      let platform: DeviceInfo['platform'] = 'unknown';
      if (/iphone|ipad|ipod/.test(userAgent)) {
        platform = 'ios';
      } else if (/android/.test(userAgent)) {
        platform = 'android';
      } else if (/windows|mac|linux/.test(userAgent)) {
        platform = 'desktop';
      }

      // Device type detection
      const isMobile = /iphone|ipod|android.*mobile/.test(userAgent) ||
        (window.innerWidth <= 768);
      const isTablet = /ipad|android(?!.*mobile)/.test(userAgent) ||
        (window.innerWidth > 768 && window.innerWidth <= 1024);

      // Touch support
      const hasTouch = 'ontouchstart' in window ||
        navigator.maxTouchPoints > 0 ||
        (navigator as any).msMaxTouchPoints > 0;

      // Screen info
      const screen = {
        width: window.screen.width,
        height: window.screen.height,
        ratio: window.devicePixelRatio || 1
      };

      // Viewport info
      const viewport = {
        width: window.innerWidth,
        height: window.innerHeight
      };

      // Connection info (if available)
      let connection: DeviceInfo['connection'];
      if ('connection' in navigator) {
        const conn = (navigator as any).connection;
        connection = {
          effectiveType: conn.effectiveType,
          downlink: conn.downlink,
          rtt: conn.rtt
        };
      }

      return {
        userAgent: navigator.userAgent,
        platform,
        isMobile,
        isTablet,
        hasTouch,
        screen,
        viewport,
        connection
      };
    };

    setDeviceInfo(detectDevice());
  }, []);

  // Handle orientation changes
  useEffect(() => {
    const updateOrientation = () => {
      setOrientation(window.innerHeight > window.innerWidth ? 'portrait' : 'landscape');
    };

    window.addEventListener('resize', updateOrientation);
    window.addEventListener('orientationchange', updateOrientation);
    updateOrientation();

    return () => {
      window.removeEventListener('resize', updateOrientation);
      window.removeEventListener('orientationchange', updateOrientation);
    };
  }, []);

  // Handle online/offline
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

  // Battery API
  useEffect(() => {
    const updateBattery = async () => {
      if ('getBattery' in navigator) {
        try {
          const battery = await (navigator as any).getBattery();

          const updateBatteryInfo = () => {
            setBattery({
              charging: battery.charging,
              level: Math.round(battery.level * 100),
              chargingTime: battery.chargingTime,
              dischargingTime: battery.dischargingTime
            });
          };

          updateBatteryInfo();

          battery.addEventListener('chargingchange', updateBatteryInfo);
          battery.addEventListener('levelchange', updateBatteryInfo);

          return () => {
            battery.removeEventListener('chargingchange', updateBatteryInfo);
            battery.removeEventListener('levelchange', updateBatteryInfo);
          };
        } catch (error) {
          console.warn('Battery API not available:', error);
        }
      }
    };

    updateBattery();
  }, []);

  // Apply mobile optimizations
  useEffect(() => {
    if (config.enableOptimizations !== false && deviceInfo?.isMobile) {
      // Prevent zoom on inputs
      const viewport = document.querySelector('meta[name="viewport"]');
      if (viewport) {
        viewport.setAttribute('content',
          'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover'
        );
      }

      // Add mobile CSS classes
      document.body.classList.add('mobile-optimized');

      if (deviceInfo.platform) {
        document.body.classList.add(`platform-${deviceInfo.platform}`);
      }

      // Prevent overscroll bounce
      document.body.style.overscrollBehavior = 'contain';

      return () => {
        document.body.classList.remove('mobile-optimized', `platform-${deviceInfo.platform}`);
      };
    }
  }, [config.enableOptimizations, deviceInfo]);

  if (!deviceInfo) {
    return null; // Loading
  }

  const screenSize = deviceInfo.isMobile ? 'small' :
    deviceInfo.isTablet ? 'medium' : 'large';

  const network = {
    online: isOnline,
    effectiveType: deviceInfo.connection?.effectiveType,
    downlink: deviceInfo.connection?.downlink,
    rtt: deviceInfo.connection?.rtt
  };

  const contextValue: MobileContextValue = {
    config,
    isMobile: deviceInfo.isMobile,
    isTablet: deviceInfo.isTablet,
    isDesktop: !deviceInfo.isMobile && !deviceInfo.isTablet,
    orientation,
    screenSize,
    hasTouch: deviceInfo.hasTouch,
    network,
    battery
  };

  return (
    <MobileContext.Provider value={contextValue}>
      {children}
    </MobileContext.Provider>
  );
}

export function useMobileContext(): MobileContextValue {
  const context = useContext(MobileContext);
  if (!context) {
    throw new Error('useMobileContext must be used within a MobileProvider');
  }
  return context;
}
