import Dexie, { Table } from 'dexie';
import type { WorkOrder, WorkOrderSyncPayload } from '../types';

export class WorkOrderDatabase extends Dexie {
  workOrders!: Table<WorkOrder, string>;
  syncQueue!: Table<WorkOrderSyncPayload, string>;

  constructor() {
    super('FieldOpsDatabase');

    this.version(1).stores({
      workOrders: 'id, tenantId, technicianId, status, priority, scheduledDate, lastModified',
      syncQueue: '++id, workOrderId, syncType, priority, timestamp'
    });

    // Add hooks for audit trail
    this.workOrders.hook('creating', (primKey, obj, trans) => {
      obj.createdAt = obj.createdAt || new Date().toISOString();
      obj.lastModified = new Date().toISOString();
    });

    this.workOrders.hook('updating', (modifications, primKey, obj, trans) => {
      modifications.lastModified = new Date().toISOString();
    });
  }

  // Advanced queries for work order management
  async getWorkOrdersByStatus(status: WorkOrder['status'], tenantId: string): Promise<WorkOrder[]> {
    return this.workOrders
      .where('[tenantId+status]')
      .equals([tenantId, status])
      .orderBy('scheduledDate')
      .toArray();
  }

  async getWorkOrdersByTechnician(technicianId: string, tenantId: string): Promise<WorkOrder[]> {
    return this.workOrders
      .where('[tenantId+technicianId]')
      .equals([tenantId, technicianId])
      .orderBy('scheduledDate')
      .toArray();
  }

  async getWorkOrdersInDateRange(startDate: string, endDate: string, tenantId: string): Promise<WorkOrder[]> {
    return this.workOrders
      .where('tenantId')
      .equals(tenantId)
      .filter(wo => wo.scheduledDate >= startDate && wo.scheduledDate <= endDate)
      .orderBy('scheduledDate')
      .toArray();
  }

  async getHighPriorityWorkOrders(tenantId: string): Promise<WorkOrder[]> {
    return this.workOrders
      .where('tenantId')
      .equals(tenantId)
      .filter(wo => wo.priority === 'urgent' || wo.priority === 'emergency')
      .orderBy('scheduledDate')
      .toArray();
  }

  async searchWorkOrders(query: string, tenantId: string): Promise<WorkOrder[]> {
    const searchTerm = query.toLowerCase().trim();

    return this.workOrders
      .where('tenantId')
      .equals(tenantId)
      .filter(wo =>
        wo.title.toLowerCase().includes(searchTerm) ||
        wo.description.toLowerCase().includes(searchTerm) ||
        wo.customer.name.toLowerCase().includes(searchTerm) ||
        wo.location.address.toLowerCase().includes(searchTerm) ||
        wo.id.toLowerCase().includes(searchTerm)
      )
      .toArray();
  }

  // Sync queue management
  async addToSyncQueue(workOrder: Partial<WorkOrder>, syncType: 'create' | 'update' | 'complete', priority = 1): Promise<void> {
    await this.syncQueue.add({
      workOrder,
      syncType,
      priority,
      timestamp: new Date().toISOString()
    } as WorkOrderSyncPayload);
  }

  async getSyncQueue(): Promise<WorkOrderSyncPayload[]> {
    return this.syncQueue
      .orderBy('priority')
      .reverse() // Higher priority first
      .toArray();
  }

  async clearSyncQueue(): Promise<void> {
    await this.syncQueue.clear();
  }

  // Bulk operations for efficiency
  async bulkUpdateWorkOrders(updates: Array<{ id: string; changes: Partial<WorkOrder> }>): Promise<void> {
    await this.transaction('rw', this.workOrders, async () => {
      for (const update of updates) {
        await this.workOrders.update(update.id, {
          ...update.changes,
          lastModified: new Date().toISOString()
        });
      }
    });
  }

  // Analytics and metrics
  async getWorkOrderMetrics(tenantId: string, technicianId?: string): Promise<{
    total: number;
    completed: number;
    pending: number;
    overdue: number;
    byStatus: Record<string, number>;
    byPriority: Record<string, number>;
  }> {
    let query = this.workOrders.where('tenantId').equals(tenantId);

    if (technicianId) {
      query = query.filter(wo => wo.technicianId === technicianId);
    }

    const workOrders = await query.toArray();
    const now = new Date().toISOString();

    const metrics = {
      total: workOrders.length,
      completed: 0,
      pending: 0,
      overdue: 0,
      byStatus: {} as Record<string, number>,
      byPriority: {} as Record<string, number>
    };

    workOrders.forEach(wo => {
      // Count by status
      metrics.byStatus[wo.status] = (metrics.byStatus[wo.status] || 0) + 1;

      // Count by priority
      metrics.byPriority[wo.priority] = (metrics.byPriority[wo.priority] || 0) + 1;

      // Count specific categories
      if (wo.status === 'completed') {
        metrics.completed++;
      } else {
        metrics.pending++;

        // Check if overdue
        if (wo.scheduledDate < now && !['completed', 'cancelled'].includes(wo.status)) {
          metrics.overdue++;
        }
      }
    });

    return metrics;
  }

  // Data cleanup and maintenance
  async cleanupOldWorkOrders(daysOld = 30): Promise<number> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysOld);
    const cutoffISO = cutoffDate.toISOString();

    const oldWorkOrders = await this.workOrders
      .where('lastModified')
      .below(cutoffISO)
      .filter(wo => wo.status === 'completed' || wo.status === 'cancelled')
      .toArray();

    if (oldWorkOrders.length > 0) {
      await this.workOrders.bulkDelete(oldWorkOrders.map(wo => wo.id));
    }

    return oldWorkOrders.length;
  }
}

// Singleton instance
export const workOrderDb = new WorkOrderDatabase();
