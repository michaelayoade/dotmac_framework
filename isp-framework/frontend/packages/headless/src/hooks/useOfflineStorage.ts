/**
 * Offline Storage Hook
 * Manages local data storage, indexedDB operations, and offline capabilities
 */

import { useCallback, useEffect, useState } from 'react';
import { useStandardErrorHandler } from './useStandardErrorHandler';

// IndexedDB configuration
const DB_NAME = 'ISPFrameworkDB';
const DB_VERSION = 1;

interface StorageSchema {
  customers: 'id';
  devices: 'id';
  invoices: 'id';
  tickets: 'id';
  incidents: 'id';
  operations: 'id';
  cache: 'key';
}

export interface StorageItem<T = any> {
  id: string;
  data: T;
  timestamp: number;
  version: number;
  synced: boolean;
  tenantId: string;
  userId?: string;
}

export interface CacheItem {
  key: string;
  data: any;
  expiresAt: number;
  tags: string[];
}

export interface StorageStats {
  totalItems: number;
  unsyncedItems: number;
  storageUsed: number;
  storageQuota: number;
  lastSync: number;
  dbVersion: number;
}

export function useOfflineStorage() {
  const { handleError, withErrorHandling } = useStandardErrorHandler({
    context: 'Offline Storage',
    enableRetry: true,
    maxRetries: 2
  });

  const [dbReady, setDbReady] = useState(false);
  const [storageStats, setStorageStats] = useState<StorageStats>({
    totalItems: 0,
    unsyncedItems: 0,
    storageUsed: 0,
    storageQuota: 0,
    lastSync: 0,
    dbVersion: 0
  });

  // Initialize IndexedDB
  const initDB = useCallback(async (): Promise<IDBDatabase> => {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        reject(new Error('Failed to open database'));
      };

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Create object stores
        const storeConfigs = [
          { name: 'customers', keyPath: 'id', indices: ['tenantId', 'timestamp'] },
          { name: 'devices', keyPath: 'id', indices: ['tenantId', 'timestamp'] },
          { name: 'invoices', keyPath: 'id', indices: ['tenantId', 'timestamp', 'customerId'] },
          { name: 'tickets', keyPath: 'id', indices: ['tenantId', 'timestamp', 'customerId'] },
          { name: 'incidents', keyPath: 'id', indices: ['tenantId', 'timestamp'] },
          { name: 'operations', keyPath: 'id', indices: ['tenantId', 'timestamp', 'synced'] },
          { name: 'cache', keyPath: 'key', indices: ['expiresAt', 'tags'] },
        ];

        storeConfigs.forEach(config => {
          if (!db.objectStoreNames.contains(config.name)) {
            const store = db.createObjectStore(config.name, { keyPath: config.keyPath });
            
            config.indices.forEach(index => {
              store.createIndex(index, index, { unique: false });
            });
          }
        });
      };
    });
  }, []);

  // Store data in IndexedDB
  const store = useCallback(async <T>(
    storeName: keyof StorageSchema,
    item: StorageItem<T>
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      
      await new Promise<void>((resolve, reject) => {
        const request = store.put(item);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });

      return true;
    }) || false;
  }, [initDB, withErrorHandling]);

  // Retrieve data from IndexedDB
  const retrieve = useCallback(async <T>(
    storeName: keyof StorageSchema,
    id: string
  ): Promise<StorageItem<T> | null> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      
      return new Promise<StorageItem<T> | null>((resolve, reject) => {
        const request = store.get(id);
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });
    });
  }, [initDB, withErrorHandling]);

  // Query data with filters
  const query = useCallback(async <T>(
    storeName: keyof StorageSchema,
    filters: {
      tenantId?: string;
      userId?: string;
      synced?: boolean;
      timestampFrom?: number;
      timestampTo?: number;
    } = {},
    limit = 100
  ): Promise<StorageItem<T>[]> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      
      let results: StorageItem<T>[] = [];
      
      return new Promise<StorageItem<T>[]>((resolve, reject) => {
        const request = store.openCursor();
        
        request.onsuccess = (event) => {
          const cursor = (event.target as IDBRequest).result;
          
          if (cursor && results.length < limit) {
            const item = cursor.value as StorageItem<T>;
            
            // Apply filters
            const matchesFilters = (
              (!filters.tenantId || item.tenantId === filters.tenantId) &&
              (!filters.userId || item.userId === filters.userId) &&
              (filters.synced === undefined || item.synced === filters.synced) &&
              (!filters.timestampFrom || item.timestamp >= filters.timestampFrom) &&
              (!filters.timestampTo || item.timestamp <= filters.timestampTo)
            );
            
            if (matchesFilters) {
              results.push(item);
            }
            
            cursor.continue();
          } else {
            resolve(results);
          }
        };
        
        request.onerror = () => reject(request.error);
      });
    }) || [];
  }, [initDB, withErrorHandling]);

  // Delete data
  const remove = useCallback(async (
    storeName: keyof StorageSchema,
    id: string
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      
      await new Promise<void>((resolve, reject) => {
        const request = store.delete(id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });

      return true;
    }) || false;
  }, [initDB, withErrorHandling]);

  // Batch operations
  const batchStore = useCallback(async <T>(
    storeName: keyof StorageSchema,
    items: StorageItem<T>[]
  ): Promise<{ success: number; failed: number }> => {
    let success = 0;
    let failed = 0;

    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      
      const promises = items.map(item => 
        new Promise<void>((resolve) => {
          const request = store.put(item);
          request.onsuccess = () => {
            success++;
            resolve();
          };
          request.onerror = () => {
            failed++;
            resolve();
          };
        })
      );

      await Promise.all(promises);
      return { success, failed };
    }) || { success: 0, failed: items.length };
  }, [initDB, withErrorHandling]);

  // Cache operations
  const setCache = useCallback(async (
    key: string,
    data: any,
    ttl = 3600000, // 1 hour default
    tags: string[] = []
  ): Promise<boolean> => {
    const cacheItem: CacheItem = {
      key,
      data,
      expiresAt: Date.now() + ttl,
      tags
    };

    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      
      await new Promise<void>((resolve, reject) => {
        const request = store.put(cacheItem);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });

      return true;
    }) || false;
  }, [initDB, withErrorHandling]);

  // Get from cache
  const getCache = useCallback(async <T = any>(key: string): Promise<T | null> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction(['cache'], 'readonly');
      const store = transaction.objectStore('cache');
      
      const cacheItem = await new Promise<CacheItem | null>((resolve, reject) => {
        const request = store.get(key);
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });

      if (!cacheItem) return null;
      
      // Check expiry
      if (cacheItem.expiresAt < Date.now()) {
        // Remove expired item
        remove('cache', key);
        return null;
      }

      return cacheItem.data as T;
    });
  }, [initDB, withErrorHandling, remove]);

  // Clear expired cache
  const clearExpiredCache = useCallback(async (): Promise<number> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      const index = store.index('expiresAt');
      
      let deletedCount = 0;
      const now = Date.now();
      
      return new Promise<number>((resolve, reject) => {
        const request = index.openCursor(IDBKeyRange.upperBound(now));
        
        request.onsuccess = (event) => {
          const cursor = (event.target as IDBRequest).result;
          
          if (cursor) {
            cursor.delete();
            deletedCount++;
            cursor.continue();
          } else {
            resolve(deletedCount);
          }
        };
        
        request.onerror = () => reject(request.error);
      });
    }) || 0;
  }, [initDB, withErrorHandling]);

  // Clear cache by tags
  const clearCacheByTags = useCallback(async (tags: string[]): Promise<number> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      const transaction = db.transaction(['cache'], 'readwrite');
      const store = transaction.objectStore('cache');
      
      let deletedCount = 0;
      
      return new Promise<number>((resolve, reject) => {
        const request = store.openCursor();
        
        request.onsuccess = (event) => {
          const cursor = (event.target as IDBRequest).result;
          
          if (cursor) {
            const item = cursor.value as CacheItem;
            
            // Check if any of the item's tags match the tags to clear
            const hasMatchingTag = item.tags.some(tag => tags.includes(tag));
            
            if (hasMatchingTag) {
              cursor.delete();
              deletedCount++;
            }
            
            cursor.continue();
          } else {
            resolve(deletedCount);
          }
        };
        
        request.onerror = () => reject(request.error);
      });
    }) || 0;
  }, [initDB, withErrorHandling]);

  // Get storage statistics
  const getStorageStats = useCallback(async (): Promise<StorageStats> => {
    return withErrorHandling(async () => {
      const db = await initDB();
      
      // Get storage estimate
      let storageEstimate = { usage: 0, quota: 0 };
      if ('storage' in navigator && 'estimate' in navigator.storage) {
        storageEstimate = await navigator.storage.estimate();
      }
      
      // Count items
      let totalItems = 0;
      let unsyncedItems = 0;
      
      const storeNames: (keyof StorageSchema)[] = ['customers', 'devices', 'invoices', 'tickets', 'incidents', 'operations'];
      
      for (const storeName of storeNames) {
        const transaction = db.transaction([storeName], 'readonly');
        const store = transaction.objectStore(storeName);
        
        const count = await new Promise<number>((resolve) => {
          const request = store.count();
          request.onsuccess = () => resolve(request.result);
          request.onerror = () => resolve(0);
        });
        
        totalItems += count;
        
        // Count unsynced items
        if (storeName === 'operations') {
          const unsyncedIndex = store.index('synced');
          const unsyncedCount = await new Promise<number>((resolve) => {
            const request = unsyncedIndex.count(IDBKeyRange.only(false));
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => resolve(0);
          });
          
          unsyncedItems += unsyncedCount;
        }
      }
      
      const stats: StorageStats = {
        totalItems,
        unsyncedItems,
        storageUsed: storageEstimate.usage || 0,
        storageQuota: storageEstimate.quota || 0,
        lastSync: parseInt(localStorage.getItem('lastSync') || '0'),
        dbVersion: DB_VERSION
      };
      
      setStorageStats(stats);
      return stats;
    }) || storageStats;
  }, [initDB, withErrorHandling, storageStats]);

  // Clear all data
  const clearAllData = useCallback(async (): Promise<boolean> => {
    return withErrorHandling(async () => {
      // Close existing connections
      const db = await initDB();
      db.close();
      
      // Delete the database
      return new Promise<boolean>((resolve, reject) => {
        const deleteRequest = indexedDB.deleteDatabase(DB_NAME);
        deleteRequest.onsuccess = () => resolve(true);
        deleteRequest.onerror = () => reject(deleteRequest.error);
      });
    }) || false;
  }, [initDB, withErrorHandling]);

  // Initialize database on mount
  useEffect(() => {
    const init = async () => {
      try {
        await initDB();
        setDbReady(true);
        await getStorageStats();
      } catch (error) {
        handleError(error);
      }
    };

    init();
  }, [initDB, getStorageStats, handleError]);

  // Periodic cleanup of expired cache
  useEffect(() => {
    if (dbReady) {
      const cleanupInterval = setInterval(() => {
        clearExpiredCache();
      }, 300000); // Clean up every 5 minutes

      return () => clearInterval(cleanupInterval);
    }
  }, [dbReady, clearExpiredCache]);

  return {
    // State
    dbReady,
    storageStats,

    // Data operations
    store,
    retrieve,
    query,
    remove,
    batchStore,

    // Cache operations
    setCache,
    getCache,
    clearExpiredCache,
    clearCacheByTags,

    // Utilities
    getStorageStats,
    clearAllData,

    // Computed values
    isStorageAvailable: 'indexedDB' in window,
    storageUsagePercentage: storageStats.storageQuota > 0 
      ? (storageStats.storageUsed / storageStats.storageQuota) * 100 
      : 0,
  };
}

export type { StorageItem, CacheItem, StorageStats };