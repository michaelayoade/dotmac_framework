import { MobileOfflineOptions, MobileCacheOptions } from './offline/types';
import { PWAConfig } from './pwa/types';

export interface MobileConfig {
  /** Offline sync configuration */
  offline?: MobileOfflineOptions;
  /** Cache configuration */
  cache?: MobileCacheOptions;
  /** PWA configuration */
  pwa?: PWAConfig;
  /** Enable mobile optimizations */
  enableOptimizations?: boolean;
  /** Debug mode */
  debug?: boolean;
}

export interface MobileContextValue {
  /** Mobile configuration */
  config: MobileConfig;
  /** Is mobile device */
  isMobile: boolean;
  /** Is tablet device */
  isTablet: boolean;
  /** Is desktop device */
  isDesktop: boolean;
  /** Device orientation */
  orientation: 'portrait' | 'landscape';
  /** Screen size category */
  screenSize: 'small' | 'medium' | 'large';
  /** Touch support */
  hasTouch: boolean;
  /** Network information */
  network: {
    online: boolean;
    effectiveType?: string;
    downlink?: number;
    rtt?: number;
  };
  /** Battery information */
  battery?: {
    charging: boolean;
    level: number;
    chargingTime: number;
    dischargingTime: number;
  };
}

export interface DeviceInfo {
  /** User agent string */
  userAgent: string;
  /** Platform */
  platform: 'ios' | 'android' | 'desktop' | 'unknown';
  /** Is mobile device */
  isMobile: boolean;
  /** Is tablet */
  isTablet: boolean;
  /** Has touch support */
  hasTouch: boolean;
  /** Screen dimensions */
  screen: {
    width: number;
    height: number;
    ratio: number;
  };
  /** Viewport dimensions */
  viewport: {
    width: number;
    height: number;
  };
  /** Connection info */
  connection?: {
    effectiveType: string;
    downlink: number;
    rtt: number;
  };
}
