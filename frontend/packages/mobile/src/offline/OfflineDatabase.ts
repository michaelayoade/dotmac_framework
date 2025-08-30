import Dexie, { Table } from 'dexie';
import { MobileOfflineEntry, StorageQuota, CacheStatistics } from './types';

export interface CacheRecord {
  id?: number;
  key: string;
  data: any;
  timestamp: number;
  ttl: number;
  tenantId: string;
  size: number;
  accessed: number;
  etag?: string;
  version?: number;
}

export interface QueueRecord extends MobileOfflineEntry {
  id?: number;
}

export interface AssetRecord {
  id?: number;
  url: string;
  data: Blob;
  type: string;
  size: number;
  timestamp: number;
  tenantId: string;
  accessed: number;
}

export class OfflineDatabase extends Dexie {
  cache!: Table<CacheRecord>;
  queue!: Table<QueueRecord>;
  assets!: Table<AssetRecord>;

  constructor() {
    super('DotMacMobileDB');

    this.version(1).stores({
      cache: '++id, key, tenantId, timestamp, accessed',
      queue: '++id, tenantId, priority, timestamp, status',
      assets: '++id, url, tenantId, timestamp, accessed'
    });

    this.cache.hook('creating', (primKey, obj, trans) => {
      obj.accessed = Date.now();
    });

    this.cache.hook('reading', (obj) => {
      this.cache.update(obj.id!, { accessed: Date.now() });
      return obj;
    });
  }

  async getStorageQuota(): Promise<StorageQuota> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      const quota = estimate.quota || 0;
      const used = estimate.usage || 0;
      const available = quota - used;
      const usage = quota > 0 ? (used / quota) * 100 : 0;

      return { used, available, quota, usage };
    }

    // Fallback estimation
    const cacheSize = await this.getCacheSize();
    const estimatedQuota = 50 * 1024 * 1024; // 50MB default
    return {
      used: cacheSize,
      available: estimatedQuota - cacheSize,
      quota: estimatedQuota,
      usage: (cacheSize / estimatedQuota) * 100
    };
  }

  async getCacheSize(): Promise<number> {
    const [cacheRecords, assetRecords] = await Promise.all([
      this.cache.toArray(),
      this.assets.toArray()
    ]);

    const cacheSize = cacheRecords.reduce((total, record) => total + (record.size || 0), 0);
    const assetSize = assetRecords.reduce((total, record) => total + record.size, 0);

    return cacheSize + assetSize;
  }

  async getCacheStatistics(): Promise<CacheStatistics> {
    const records = await this.cache.toArray();

    if (records.length === 0) {
      return {
        totalEntries: 0,
        totalSize: 0,
        hitRate: 0,
        missRate: 0
      };
    }

    const totalSize = records.reduce((total, record) => total + (record.size || 0), 0);
    const timestamps = records.map(r => r.timestamp);

    return {
      totalEntries: records.length,
      totalSize,
      hitRate: 0, // Would need tracking for actual hit rate
      missRate: 0,
      oldestEntry: Math.min(...timestamps),
      newestEntry: Math.max(...timestamps)
    };
  }

  async cleanupExpiredCache(): Promise<number> {
    const now = Date.now();
    const expiredRecords = await this.cache
      .where('timestamp')
      .below(now)
      .and(record => now > record.timestamp + record.ttl)
      .toArray();

    if (expiredRecords.length > 0) {
      await this.cache.bulkDelete(expiredRecords.map(r => r.id!));
    }

    return expiredRecords.length;
  }

  async cleanupOldAssets(maxAge: number = 7 * 24 * 60 * 60 * 1000): Promise<number> {
    const cutoff = Date.now() - maxAge;
    const oldAssets = await this.assets
      .where('accessed')
      .below(cutoff)
      .toArray();

    if (oldAssets.length > 0) {
      await this.assets.bulkDelete(oldAssets.map(a => a.id!));
    }

    return oldAssets.length;
  }

  async optimizeStorage(targetSize: number): Promise<void> {
    const currentSize = await this.getCacheSize();

    if (currentSize <= targetSize) {
      return;
    }

    // Remove least recently accessed items first
    const cacheRecords = await this.cache.orderBy('accessed').toArray();
    const assetRecords = await this.assets.orderBy('accessed').toArray();

    let freedSize = 0;
    const toDelete: { cache: number[], assets: number[] } = { cache: [], assets: [] };

    // Delete cache records first
    for (const record of cacheRecords) {
      if (freedSize >= (currentSize - targetSize)) break;
      toDelete.cache.push(record.id!);
      freedSize += record.size || 0;
    }

    // Delete assets if needed
    for (const asset of assetRecords) {
      if (freedSize >= (currentSize - targetSize)) break;
      toDelete.assets.push(asset.id!);
      freedSize += asset.size;
    }

    if (toDelete.cache.length > 0) {
      await this.cache.bulkDelete(toDelete.cache);
    }
    if (toDelete.assets.length > 0) {
      await this.assets.bulkDelete(toDelete.assets);
    }
  }

  async clearTenantData(tenantId: string): Promise<void> {
    await Promise.all([
      this.cache.where('tenantId').equals(tenantId).delete(),
      this.queue.where('tenantId').equals(tenantId).delete(),
      this.assets.where('tenantId').equals(tenantId).delete()
    ]);
  }

  async exportData(): Promise<string> {
    const [cache, queue, assets] = await Promise.all([
      this.cache.toArray(),
      this.queue.toArray(),
      this.assets.toArray()
    ]);

    return JSON.stringify({
      version: 1,
      timestamp: Date.now(),
      cache: cache.map(r => ({ ...r, data: typeof r.data === 'object' ? JSON.stringify(r.data) : r.data })),
      queue,
      assets: assets.map(a => ({ ...a, data: null })) // Exclude blob data
    }, null, 2);
  }

  async getQueueByPriority(tenantId?: string): Promise<QueueRecord[]> {
    let query = this.queue.orderBy('priority').reverse();

    if (tenantId) {
      return query.and(record => record.tenantId === tenantId).toArray();
    }

    return query.toArray();
  }

  async updateQueueStatus(id: number, status: string, error?: string): Promise<void> {
    await this.queue.update(id, {
      status,
      error,
      retryCount: status === 'failed' ? undefined : 0
    });
  }
}
