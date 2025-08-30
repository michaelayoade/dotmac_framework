import { OfflineEntry } from '@dotmac/headless';

export interface MobileOfflineOptions {
  /** Enable background sync when app comes to foreground */
  backgroundSync?: boolean;
  /** Enable push notifications for sync status */
  notifications?: boolean;
  /** Maximum storage quota (in MB) */
  storageQuota?: number;
  /** Enable automatic cleanup of old cached data */
  autoCleanup?: boolean;
  /** Days to keep cached data */
  cacheDays?: number;
  /** Enable data compression */
  compression?: boolean;
}

export interface MobileCacheOptions {
  /** Use IndexedDB instead of localStorage */
  useIndexedDB?: boolean;
  /** Enable image/asset caching */
  cacheAssets?: boolean;
  /** Maximum cache size in MB */
  maxCacheSize?: number;
  /** Prefetch strategy */
  prefetchStrategy?: 'aggressive' | 'conservative' | 'minimal';
}

export interface OfflineSyncResult {
  success: boolean;
  synced: number;
  failed: number;
  errors: string[];
  duration: number;
}

export interface MobileOfflineEntry extends OfflineEntry {
  /** Priority for mobile sync (1-5, 5 = highest) */
  priority: number;
  /** Size in bytes for bandwidth optimization */
  estimatedSize: number;
  /** Location where operation was queued */
  location?: {
    latitude: number;
    longitude: number;
    accuracy?: number;
  };
  /** Device info when queued */
  deviceInfo?: {
    userAgent: string;
    online: boolean;
    batteryLevel?: number;
    connectionType?: string;
  };
}

export interface StorageQuota {
  used: number;
  available: number;
  quota: number;
  usage: number; // percentage
}

export interface CacheStatistics {
  totalEntries: number;
  totalSize: number;
  hitRate: number;
  missRate: number;
  oldestEntry?: number;
  newestEntry?: number;
}
