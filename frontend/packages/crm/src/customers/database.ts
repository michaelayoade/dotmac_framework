import Dexie, { Table } from 'dexie';
import type {
  CustomerAccount,
  Lead,
  Communication,
  SupportTicket,
  CustomerFilter
} from '../types';

export class CRMDatabase extends Dexie {
  customers!: Table<CustomerAccount, string>;
  leads!: Table<Lead, string>;
  communications!: Table<Communication, string>;
  supportTickets!: Table<SupportTicket, string>;

  constructor() {
    super('CRMDatabase');

    this.version(1).stores({
      customers: 'id, tenantId, accountNumber, status, type, segment, displayName, createdAt, updatedAt, lastContactDate, syncStatus',
      leads: 'id, tenantId, status, source, priority, assignedTo, score, createdAt, updatedAt, lastContactDate, syncStatus',
      communications: 'id, tenantId, customerId, leadId, type, direction, timestamp, userId, syncStatus',
      supportTickets: 'id, tenantId, ticketNumber, customerId, status, priority, category, assignedTo, createdAt, updatedAt, syncStatus'
    });

    // Add hooks for audit trail
    this.customers.hook('creating', (primKey, obj, trans) => {
      obj.createdAt = obj.createdAt || new Date().toISOString();
      obj.updatedAt = new Date().toISOString();
      obj.syncStatus = obj.syncStatus || 'pending';
    });

    this.customers.hook('updating', (modifications, primKey, obj, trans) => {
      modifications.updatedAt = new Date().toISOString();
      if (modifications.syncStatus !== 'error') {
        modifications.syncStatus = 'pending';
      }
    });

    this.leads.hook('creating', (primKey, obj, trans) => {
      obj.createdAt = obj.createdAt || new Date().toISOString();
      obj.updatedAt = new Date().toISOString();
      obj.syncStatus = obj.syncStatus || 'pending';
    });

    this.leads.hook('updating', (modifications, primKey, obj, trans) => {
      modifications.updatedAt = new Date().toISOString();
      if (modifications.syncStatus !== 'error') {
        modifications.syncStatus = 'pending';
      }
    });

    this.communications.hook('creating', (primKey, obj, trans) => {
      obj.createdAt = obj.createdAt || new Date().toISOString();
      obj.syncStatus = obj.syncStatus || 'pending';
    });

    this.supportTickets.hook('creating', (primKey, obj, trans) => {
      obj.createdAt = obj.createdAt || new Date().toISOString();
      obj.updatedAt = new Date().toISOString();
      obj.syncStatus = obj.syncStatus || 'pending';
    });

    this.supportTickets.hook('updating', (modifications, primKey, obj, trans) => {
      modifications.updatedAt = new Date().toISOString();
      if (modifications.syncStatus !== 'error') {
        modifications.syncStatus = 'pending';
      }
    });
  }

  // ========================================
  // CUSTOMER QUERIES
  // ========================================

  async getCustomersByStatus(status: CustomerAccount['status'], tenantId: string): Promise<CustomerAccount[]> {
    return this.customers
      .where('[tenantId+status]')
      .equals([tenantId, status])
      .orderBy('displayName')
      .toArray();
  }

  async getCustomersBySegment(segment: CustomerAccount['segment'], tenantId: string): Promise<CustomerAccount[]> {
    return this.customers
      .where('[tenantId+segment]')
      .equals([tenantId, segment])
      .orderBy('displayName')
      .toArray();
  }

  async getCustomersByAccountManager(accountManagerId: string, tenantId: string): Promise<CustomerAccount[]> {
    return this.customers
      .where('tenantId')
      .equals(tenantId)
      .filter(customer => customer.accountManagerId === accountManagerId)
      .sortBy('displayName');
  }

  async getHighValueCustomers(tenantId: string, minRevenue = 1000): Promise<CustomerAccount[]> {
    return this.customers
      .where('tenantId')
      .equals(tenantId)
      .filter(customer => customer.monthlyRevenue >= minRevenue)
      .orderBy('monthlyRevenue')
      .reverse()
      .toArray();
  }

  async searchCustomers(query: string, tenantId: string): Promise<CustomerAccount[]> {
    const searchTerm = query.toLowerCase().trim();

    return this.customers
      .where('tenantId')
      .equals(tenantId)
      .filter(customer =>
        customer.displayName.toLowerCase().includes(searchTerm) ||
        customer.firstName.toLowerCase().includes(searchTerm) ||
        customer.lastName.toLowerCase().includes(searchTerm) ||
        customer.companyName?.toLowerCase().includes(searchTerm) ||
        customer.accountNumber.toLowerCase().includes(searchTerm) ||
        customer.contactMethods.some(method =>
          method.value.toLowerCase().includes(searchTerm)
        )
      )
      .toArray();
  }

  async filterCustomers(filter: CustomerFilter, tenantId: string): Promise<CustomerAccount[]> {
    let query = this.customers.where('tenantId').equals(tenantId);

    const results = await query.toArray();

    return results.filter(customer => {
      if (filter.status && !filter.status.includes(customer.status)) return false;
      if (filter.type && !filter.type.includes(customer.type)) return false;
      if (filter.segment && !filter.segment.includes(customer.segment)) return false;
      if (filter.accountManager && customer.accountManagerId &&
          !filter.accountManager.includes(customer.accountManagerId)) return false;
      if (filter.salesRep && customer.salesRepId &&
          !filter.salesRep.includes(customer.salesRepId)) return false;

      if (filter.createdAfter && customer.createdAt < filter.createdAfter) return false;
      if (filter.createdBefore && customer.createdAt > filter.createdBefore) return false;

      if (filter.lastContactAfter && customer.lastContactDate &&
          customer.lastContactDate < filter.lastContactAfter) return false;
      if (filter.lastContactBefore && customer.lastContactDate &&
          customer.lastContactDate > filter.lastContactBefore) return false;

      if (filter.revenueMin && customer.monthlyRevenue < filter.revenueMin) return false;
      if (filter.revenueMax && customer.monthlyRevenue > filter.revenueMax) return false;

      if (filter.search) {
        const searchTerm = filter.search.toLowerCase();
        const searchableText = [
          customer.displayName,
          customer.firstName,
          customer.lastName,
          customer.companyName,
          customer.accountNumber,
          ...customer.contactMethods.map(m => m.value)
        ].join(' ').toLowerCase();

        if (!searchableText.includes(searchTerm)) return false;
      }

      return true;
    });
  }

  // ========================================
  // LEAD QUERIES
  // ========================================

  async getLeadsByStatus(status: Lead['status'], tenantId: string): Promise<Lead[]> {
    return this.leads
      .where('[tenantId+status]')
      .equals([tenantId, status])
      .orderBy('updatedAt')
      .reverse()
      .toArray();
  }

  async getLeadsByAssignee(assignedTo: string, tenantId: string): Promise<Lead[]> {
    return this.leads
      .where('tenantId')
      .equals(tenantId)
      .filter(lead => lead.assignedTo === assignedTo)
      .sortBy('priority');
  }

  async getHighScoreLeads(tenantId: string, minScore = 80): Promise<Lead[]> {
    return this.leads
      .where('tenantId')
      .equals(tenantId)
      .filter(lead => lead.score >= minScore)
      .orderBy('score')
      .reverse()
      .toArray();
  }

  async getOverdueLeads(tenantId: string): Promise<Lead[]> {
    const now = new Date().toISOString();

    return this.leads
      .where('tenantId')
      .equals(tenantId)
      .filter(lead =>
        lead.nextFollowUpDate &&
        lead.nextFollowUpDate < now &&
        !['closed_won', 'closed_lost'].includes(lead.status)
      )
      .toArray();
  }

  // ========================================
  // COMMUNICATION QUERIES
  // ========================================

  async getCommunicationsByCustomer(customerId: string, tenantId: string): Promise<Communication[]> {
    return this.communications
      .where('[tenantId+customerId]')
      .equals([tenantId, customerId])
      .orderBy('timestamp')
      .reverse()
      .toArray();
  }

  async getCommunicationsByLead(leadId: string, tenantId: string): Promise<Communication[]> {
    return this.communications
      .where('tenantId')
      .equals(tenantId)
      .filter(comm => comm.leadId === leadId)
      .sortBy('timestamp')
      .then(results => results.reverse());
  }

  async getRecentCommunications(tenantId: string, days = 7): Promise<Communication[]> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    const cutoffISO = cutoffDate.toISOString();

    return this.communications
      .where('tenantId')
      .equals(tenantId)
      .filter(comm => comm.timestamp >= cutoffISO)
      .orderBy('timestamp')
      .reverse()
      .toArray();
  }

  // ========================================
  // SUPPORT TICKET QUERIES
  // ========================================

  async getTicketsByCustomer(customerId: string, tenantId: string): Promise<SupportTicket[]> {
    return this.supportTickets
      .where('[tenantId+customerId]')
      .equals([tenantId, customerId])
      .orderBy('createdAt')
      .reverse()
      .toArray();
  }

  async getTicketsByAssignee(assignedTo: string, tenantId: string): Promise<SupportTicket[]> {
    return this.supportTickets
      .where('tenantId')
      .equals(tenantId)
      .filter(ticket => ticket.assignedTo === assignedTo)
      .sortBy('priority');
  }

  async getOpenTickets(tenantId: string): Promise<SupportTicket[]> {
    return this.supportTickets
      .where('tenantId')
      .equals(tenantId)
      .filter(ticket => ['open', 'in_progress'].includes(ticket.status))
      .orderBy('priority')
      .toArray();
  }

  async getOverdueSLATickets(tenantId: string): Promise<SupportTicket[]> {
    return this.supportTickets
      .where('tenantId')
      .equals(tenantId)
      .filter(ticket => ticket.slaBreached)
      .toArray();
  }

  // ========================================
  // ANALYTICS QUERIES
  // ========================================

  async getCustomerMetrics(tenantId: string): Promise<{
    total: number;
    active: number;
    new: number;
    churned: number;
    byStatus: Record<string, number>;
    bySegment: Record<string, number>;
    totalRevenue: number;
    averageRevenue: number;
  }> {
    const customers = await this.customers
      .where('tenantId')
      .equals(tenantId)
      .toArray();

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoISO = thirtyDaysAgo.toISOString();

    const metrics = {
      total: customers.length,
      active: customers.filter(c => c.status === 'active').length,
      new: customers.filter(c => c.createdAt >= thirtyDaysAgoISO).length,
      churned: customers.filter(c => c.status === 'churned').length,
      byStatus: {} as Record<string, number>,
      bySegment: {} as Record<string, number>,
      totalRevenue: 0,
      averageRevenue: 0
    };

    customers.forEach(customer => {
      // Count by status
      metrics.byStatus[customer.status] = (metrics.byStatus[customer.status] || 0) + 1;

      // Count by segment
      metrics.bySegment[customer.segment] = (metrics.bySegment[customer.segment] || 0) + 1;

      // Sum revenue
      metrics.totalRevenue += customer.monthlyRevenue;
    });

    metrics.averageRevenue = customers.length > 0 ? metrics.totalRevenue / customers.length : 0;

    return metrics;
  }

  async getLeadMetrics(tenantId: string): Promise<{
    total: number;
    new: number;
    qualified: number;
    converted: number;
    conversionRate: number;
    byStatus: Record<string, number>;
    bySource: Record<string, number>;
    averageScore: number;
  }> {
    const leads = await this.leads
      .where('tenantId')
      .equals(tenantId)
      .toArray();

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoISO = thirtyDaysAgo.toISOString();

    const metrics = {
      total: leads.length,
      new: leads.filter(l => l.createdAt >= thirtyDaysAgoISO).length,
      qualified: leads.filter(l => l.status === 'qualified').length,
      converted: leads.filter(l => l.status === 'closed_won').length,
      conversionRate: 0,
      byStatus: {} as Record<string, number>,
      bySource: {} as Record<string, number>,
      averageScore: 0
    };

    metrics.conversionRate = leads.length > 0 ? (metrics.converted / leads.length) * 100 : 0;

    let totalScore = 0;
    leads.forEach(lead => {
      metrics.byStatus[lead.status] = (metrics.byStatus[lead.status] || 0) + 1;
      metrics.bySource[lead.source] = (metrics.bySource[lead.source] || 0) + 1;
      totalScore += lead.score;
    });

    metrics.averageScore = leads.length > 0 ? totalScore / leads.length : 0;

    return metrics;
  }

  // ========================================
  // SYNC OPERATIONS
  // ========================================

  async getPendingSyncItems(): Promise<{
    customers: CustomerAccount[];
    leads: Lead[];
    communications: Communication[];
    supportTickets: SupportTicket[];
  }> {
    const [customers, leads, communications, supportTickets] = await Promise.all([
      this.customers.where('syncStatus').equals('pending').toArray(),
      this.leads.where('syncStatus').equals('pending').toArray(),
      this.communications.where('syncStatus').equals('pending').toArray(),
      this.supportTickets.where('syncStatus').equals('pending').toArray()
    ]);

    return { customers, leads, communications, supportTickets };
  }

  async markAsSynced(tableName: string, ids: string[]): Promise<void> {
    const table = this[tableName as keyof CRMDatabase] as Table;
    if (table) {
      await table.where('id').anyOf(ids).modify({ syncStatus: 'synced' });
    }
  }

  async markAsSyncError(tableName: string, ids: string[]): Promise<void> {
    const table = this[tableName as keyof CRMDatabase] as Table;
    if (table) {
      await table.where('id').anyOf(ids).modify({ syncStatus: 'error' });
    }
  }

  // ========================================
  // DATA CLEANUP
  // ========================================

  async cleanupOldData(daysOld = 90): Promise<{
    communicationsDeleted: number;
    completedTicketsDeleted: number;
  }> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysOld);
    const cutoffISO = cutoffDate.toISOString();

    // Cleanup old communications
    const oldCommunications = await this.communications
      .where('timestamp')
      .below(cutoffISO)
      .toArray();

    const oldTickets = await this.supportTickets
      .where('updatedAt')
      .below(cutoffISO)
      .filter(ticket => ['resolved', 'closed'].includes(ticket.status))
      .toArray();

    if (oldCommunications.length > 0) {
      await this.communications.bulkDelete(oldCommunications.map(c => c.id));
    }

    if (oldTickets.length > 0) {
      await this.supportTickets.bulkDelete(oldTickets.map(t => t.id));
    }

    return {
      communicationsDeleted: oldCommunications.length,
      completedTicketsDeleted: oldTickets.length
    };
  }
}

// Singleton instance
export const crmDb = new CRMDatabase();
