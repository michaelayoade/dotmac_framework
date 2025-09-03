import { useState, useEffect, useCallback } from 'react';
import { useApiClient, useAuth } from '@dotmac/headless';
import { crmDb } from '../database';
import type { Lead, LeadFilter, LeadMetrics, CustomerAccount } from '../../types';

interface UseLeadsOptions {
  autoSync?: boolean;
  syncInterval?: number;
  filter?: LeadFilter;
  pageSize?: number;
  assignedToMe?: boolean;
}

interface UseLeadsReturn {
  leads: Lead[];
  loading: boolean;
  error: string | null;
  metrics: LeadMetrics | null;
  totalCount: number;
  currentPage: number;

  // CRUD Operations
  createLead: (lead: Omit<Lead, 'id' | 'createdAt' | 'updatedAt'>) => Promise<Lead>;
  updateLead: (id: string, updates: Partial<Lead>) => Promise<void>;
  deleteLead: (id: string) => Promise<void>;

  // Lead Management
  assignLead: (leadId: string, userId: string) => Promise<void>;
  updateLeadStatus: (leadId: string, status: Lead['status']) => Promise<void>;
  updateLeadScore: (leadId: string, score: number) => Promise<void>;
  convertToCustomer: (
    leadId: string,
    customerData: Partial<CustomerAccount>
  ) => Promise<CustomerAccount>;

  // Lead Scoring
  calculateLeadScore: (lead: Lead) => number;
  getLeadScoreFactors: (lead: Lead) => { factor: string; score: number; weight: number }[];

  // Lead Nurturing
  scheduleFollowUp: (leadId: string, date: string, notes: string) => Promise<void>;
  addLeadNote: (leadId: string, note: string) => Promise<void>;
  setNextFollowUp: (leadId: string, date: string) => Promise<void>;

  // Search and Filter
  searchLeads: (query: string) => Promise<Lead[]>;
  filterLeads: (filter: LeadFilter) => Promise<void>;
  clearFilter: () => Promise<void>;
  getOverdueLeads: () => Promise<Lead[]>;
  getHighScoreLeads: (minScore?: number) => Promise<Lead[]>;

  // Pagination
  setPage: (page: number) => void;
  nextPage: () => void;
  previousPage: () => void;

  // Sync
  syncWithServer: () => Promise<void>;
  syncStatus: 'idle' | 'syncing' | 'error';
  lastSync: Date | null;

  // Analytics
  refreshMetrics: () => Promise<void>;
  getLeadsBySource: () => Promise<Record<string, number>>;
  getConversionFunnel: () => Promise<{ stage: string; count: number; conversionRate: number }[]>;

  // Bulk Operations
  bulkAssignLeads: (leadIds: string[], userId: string) => Promise<void>;
  bulkUpdateStatus: (leadIds: string[], status: Lead['status']) => Promise<void>;
  bulkDeleteLeads: (leadIds: string[]) => Promise<void>;
  exportLeads: (format: 'csv' | 'json') => Promise<string>;
}

export function useLeads(options: UseLeadsOptions = {}): UseLeadsReturn {
  const {
    autoSync = true,
    syncInterval = 30000,
    filter: initialFilter,
    pageSize = 20,
    assignedToMe = false,
  } = options;

  const { user, tenantId } = useAuth();
  const apiClient = useApiClient();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<LeadMetrics | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [currentFilter, setCurrentFilter] = useState<LeadFilter | undefined>(
    assignedToMe && user?.id ? { ...initialFilter, assignedTo: [user.id] } : initialFilter
  );
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error'>('idle');
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // Load leads from local database
  const loadLocalLeads = useCallback(async () => {
    if (!tenantId) return;

    try {
      setLoading(true);
      setError(null);

      let leadsList: Lead[];

      if (currentFilter) {
        // Apply filters
        let query = crmDb.leads.where('tenantId').equals(tenantId);
        const results = await query.toArray();

        leadsList = results.filter((lead) => {
          if (currentFilter.status && !currentFilter.status.includes(lead.status)) return false;
          if (currentFilter.source && !currentFilter.source.includes(lead.source)) return false;
          if (currentFilter.priority && !currentFilter.priority.includes(lead.priority))
            return false;
          if (
            currentFilter.assignedTo &&
            lead.assignedTo &&
            !currentFilter.assignedTo.includes(lead.assignedTo)
          )
            return false;

          if (currentFilter.createdAfter && lead.createdAt < currentFilter.createdAfter)
            return false;
          if (currentFilter.createdBefore && lead.createdAt > currentFilter.createdBefore)
            return false;

          if (currentFilter.scoreMin && lead.score < currentFilter.scoreMin) return false;
          if (currentFilter.scoreMax && lead.score > currentFilter.scoreMax) return false;

          if (currentFilter.interestedServices && currentFilter.interestedServices.length > 0) {
            const hasMatchingService = currentFilter.interestedServices.some((service) =>
              lead.interestedServices.includes(service)
            );
            if (!hasMatchingService) return false;
          }

          if (currentFilter.search) {
            const searchTerm = currentFilter.search.toLowerCase();
            const searchableText = [
              lead.firstName,
              lead.lastName,
              lead.companyName,
              lead.email,
              lead.phone,
              lead.notes,
            ]
              .join(' ')
              .toLowerCase();

            if (!searchableText.includes(searchTerm)) return false;
          }

          return true;
        });
      } else if (assignedToMe && user?.id) {
        leadsList = await crmDb.getLeadsByAssignee(user.id, tenantId);
      } else {
        leadsList = await crmDb.leads
          .where('tenantId')
          .equals(tenantId)
          .orderBy('updatedAt')
          .reverse()
          .toArray();
      }

      setTotalCount(leadsList.length);

      // Apply pagination
      const startIndex = (currentPage - 1) * pageSize;
      const endIndex = startIndex + pageSize;
      const paginatedLeads = leadsList.slice(startIndex, endIndex);

      setLeads(paginatedLeads);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load leads');
      console.error('Failed to load leads:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, currentFilter, currentPage, pageSize, assignedToMe, user?.id]);

  // Sync with server
  const syncWithServer = useCallback(async () => {
    if (!tenantId || syncStatus === 'syncing') return;

    try {
      setSyncStatus('syncing');

      // Get pending sync items
      const { leads: pendingLeads } = await crmDb.getPendingSyncItems();

      // Sync pending leads
      for (const lead of pendingLeads) {
        try {
          if (lead.id.startsWith('temp_')) {
            // New lead - create on server
            const response = await apiClient.post('/crm/leads', lead);
            if (response.data?.lead) {
              await crmDb.leads.delete(lead.id);
              await crmDb.leads.add({
                ...response.data.lead,
                syncStatus: 'synced',
              });
            }
          } else {
            // Update existing lead
            await apiClient.put(`/crm/leads/${lead.id}`, lead);
            await crmDb.leads.update(lead.id, { syncStatus: 'synced' });
          }
        } catch (apiError) {
          console.error(`Failed to sync lead ${lead.id}:`, apiError);
          await crmDb.leads.update(lead.id, { syncStatus: 'error' });
        }
      }

      // Fetch latest leads from server
      const response = await apiClient.get('/crm/leads', {
        params: { tenantId },
      });

      if (response.data?.leads) {
        await crmDb.transaction('rw', crmDb.leads, async () => {
          const syncedLeads = await crmDb.leads
            .where('[tenantId+syncStatus]')
            .equals([tenantId, 'synced'])
            .toArray();

          const syncedIds = syncedLeads.map((l) => l.id);
          await crmDb.leads.where('id').anyOf(syncedIds).delete();

          const serverLeads = response.data.leads.map((l: Lead) => ({
            ...l,
            syncStatus: 'synced',
          }));

          await crmDb.leads.bulkAdd(serverLeads, { allKeys: true });
        });

        await loadLocalLeads();
      }

      setSyncStatus('idle');
      setLastSync(new Date());
      setError(null);
    } catch (err) {
      setSyncStatus('error');
      setError(err instanceof Error ? err.message : 'Sync failed');
      console.error('Lead sync failed:', err);
    }
  }, [tenantId, syncStatus, apiClient, loadLocalLeads]);

  // Create lead
  const createLead = useCallback(
    async (leadData: Omit<Lead, 'id' | 'createdAt' | 'updatedAt'>): Promise<Lead> => {
      if (!tenantId || !user?.id) throw new Error('Missing required information');

      const lead: Lead = {
        ...leadData,
        id: `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        tenantId,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: user.id,
        syncStatus: 'pending',
      };

      // Calculate initial lead score
      lead.score = calculateLeadScore(lead);

      try {
        await crmDb.leads.add(lead);
        await loadLocalLeads();

        if (autoSync) {
          syncWithServer();
        }

        return lead;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create lead');
        throw err;
      }
    },
    [tenantId, user?.id, loadLocalLeads, autoSync, syncWithServer]
  );

  // Update lead
  const updateLead = useCallback(
    async (id: string, updates: Partial<Lead>) => {
      try {
        const updatedData = {
          ...updates,
          updatedAt: new Date().toISOString(),
          syncStatus: 'pending' as const,
        };

        // Recalculate score if relevant fields changed
        if (updates.source || updates.interestedServices || updates.budget) {
          const currentLead = await crmDb.leads.get(id);
          if (currentLead) {
            const updatedLead = { ...currentLead, ...updatedData };
            updatedData.score = calculateLeadScore(updatedLead);
          }
        }

        await crmDb.leads.update(id, updatedData);
        await loadLocalLeads();

        if (autoSync) {
          syncWithServer();
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update lead');
        throw err;
      }
    },
    [loadLocalLeads, autoSync, syncWithServer]
  );

  // Delete lead
  const deleteLead = useCallback(
    async (id: string) => {
      try {
        await crmDb.leads.delete(id);
        await loadLocalLeads();

        if (!id.startsWith('temp_') && autoSync) {
          try {
            await apiClient.delete(`/crm/leads/${id}`);
          } catch (err) {
            console.error('Failed to delete lead on server:', err);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete lead');
        throw err;
      }
    },
    [loadLocalLeads, autoSync, apiClient]
  );

  // Assign lead
  const assignLead = useCallback(
    async (leadId: string, userId: string) => {
      await updateLead(leadId, {
        assignedTo: userId,
        assignedDate: new Date().toISOString(),
      });
    },
    [updateLead]
  );

  // Update lead status
  const updateLeadStatus = useCallback(
    async (leadId: string, status: Lead['status']) => {
      const updates: Partial<Lead> = { status };

      if (status === 'closed_won') {
        updates.convertedDate = new Date().toISOString();
      }

      await updateLead(leadId, updates);
    },
    [updateLead]
  );

  // Update lead score
  const updateLeadScore = useCallback(
    async (leadId: string, score: number) => {
      await updateLead(leadId, { score });
    },
    [updateLead]
  );

  // Convert to customer
  const convertToCustomer = useCallback(
    async (leadId: string, customerData: Partial<CustomerAccount>): Promise<CustomerAccount> => {
      if (!tenantId || !user?.id) throw new Error('Missing required information');

      const lead = await crmDb.leads.get(leadId);
      if (!lead) throw new Error('Lead not found');

      // Create customer from lead data
      const customer: CustomerAccount = {
        id: `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        accountNumber: `ACC_${Date.now()}`,
        status: 'active',
        type: lead.companyName ? 'business' : 'residential',
        segment: 'standard',
        firstName: lead.firstName,
        lastName: lead.lastName,
        companyName: lead.companyName,
        displayName: lead.companyName || `${lead.firstName} ${lead.lastName}`,
        addresses: lead.address.street1
          ? [
              {
                id: `addr_${Date.now()}`,
                type: 'service',
                street1: lead.address.street1!,
                street2: lead.address.street2,
                city: lead.address.city || '',
                state: lead.address.state || '',
                zipCode: lead.address.zipCode || '',
                country: lead.address.country || 'US',
                isPrimary: true,
              },
            ]
          : [],
        contactMethods: [
          {
            id: `contact_email_${Date.now()}`,
            type: 'email',
            value: lead.email,
            isPrimary: true,
            isVerified: false,
            preferences: {
              allowMarketing: true,
              allowSMS: false,
              allowCalls: true,
            },
          },
          ...(lead.phone
            ? [
                {
                  id: `contact_phone_${Date.now()}`,
                  type: 'phone' as const,
                  value: lead.phone,
                  isPrimary: true,
                  isVerified: false,
                  preferences: {
                    allowMarketing: true,
                    allowSMS: true,
                    allowCalls: true,
                  },
                },
              ]
            : []),
        ],
        activeServices: [],
        totalRevenue: 0,
        monthlyRevenue: 0,
        lifetimeValue: 0,
        outstandingBalance: 0,
        paymentTerms: 'net_30',
        billingCycle: 'monthly',
        communicationPreferences: {
          preferredMethod: 'email',
          language: 'en',
          timezone: 'UTC',
          marketingOptIn: true,
        },
        customFields: [],
        source: lead.source,
        referredBy: lead.notes.includes('referral') ? lead.notes : undefined,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        tenantId,
        syncStatus: 'pending',
        ...customerData,
      };

      try {
        // Create customer
        await crmDb.customers.add(customer);

        // Update lead to converted
        await updateLead(leadId, {
          status: 'closed_won',
          convertedToCustomerId: customer.id,
          convertedDate: new Date().toISOString(),
        });

        if (autoSync) {
          // Sync with server
          try {
            const response = await apiClient.post('/crm/customers', customer);
            if (response.data?.customer) {
              await crmDb.customers.delete(customer.id);
              await crmDb.customers.add({
                ...response.data.customer,
                syncStatus: 'synced',
              });

              // Update lead with actual customer ID
              await updateLead(leadId, {
                convertedToCustomerId: response.data.customer.id,
              });

              return response.data.customer;
            }
          } catch (err) {
            console.error('Failed to sync converted customer:', err);
          }
        }

        return customer;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to convert lead to customer');
        throw err;
      }
    },
    [tenantId, user?.id, updateLead, autoSync, apiClient]
  );

  // Calculate lead score
  const calculateLeadScore = useCallback((lead: Lead): number => {
    let score = 0;

    // Source scoring
    const sourceScores: Record<string, number> = {
      website: 20,
      referral: 30,
      advertising: 15,
      social_media: 10,
      cold_call: 5,
      trade_show: 25,
      partner: 35,
    };
    score += sourceScores[lead.source] || 0;

    // Budget scoring
    if (lead.budget) {
      if (lead.budget > 1000) score += 30;
      else if (lead.budget > 500) score += 20;
      else if (lead.budget > 100) score += 10;
    }

    // Company scoring
    if (lead.companyName) score += 15;

    // Interest scoring
    score += Math.min(lead.interestedServices.length * 10, 30);

    // Timeline scoring
    if (lead.timeline) {
      if (lead.timeline.includes('immediate')) score += 25;
      else if (lead.timeline.includes('month')) score += 15;
      else if (lead.timeline.includes('quarter')) score += 10;
    }

    // Contact information completeness
    if (lead.phone) score += 5;
    if (lead.address.street1) score += 5;

    return Math.min(Math.max(score, 0), 100);
  }, []);

  // Get lead score factors
  const getLeadScoreFactors = useCallback((lead: Lead) => {
    const factors = [];

    const sourceScores: Record<string, number> = {
      website: 20,
      referral: 30,
      advertising: 15,
      social_media: 10,
      cold_call: 5,
      trade_show: 25,
      partner: 35,
    };

    factors.push({
      factor: 'Lead Source',
      score: sourceScores[lead.source] || 0,
      weight: 0.3,
    });

    if (lead.budget) {
      let budgetScore = 0;
      if (lead.budget > 1000) budgetScore = 30;
      else if (lead.budget > 500) budgetScore = 20;
      else if (lead.budget > 100) budgetScore = 10;

      factors.push({
        factor: 'Budget',
        score: budgetScore,
        weight: 0.25,
      });
    }

    factors.push({
      factor: 'Company Type',
      score: lead.companyName ? 15 : 0,
      weight: 0.15,
    });

    factors.push({
      factor: 'Service Interest',
      score: Math.min(lead.interestedServices.length * 10, 30),
      weight: 0.2,
    });

    factors.push({
      factor: 'Contact Completeness',
      score: (lead.phone ? 5 : 0) + (lead.address.street1 ? 5 : 0),
      weight: 0.1,
    });

    return factors;
  }, []);

  // Schedule follow up
  const scheduleFollowUp = useCallback(
    async (leadId: string, date: string, notes: string) => {
      await updateLead(leadId, {
        nextFollowUpDate: date,
        notes: `${notes}\n\nFollow-up scheduled for ${date}`,
      });
    },
    [updateLead]
  );

  // Add lead note
  const addLeadNote = useCallback(
    async (leadId: string, note: string) => {
      const lead = await crmDb.leads.get(leadId);
      if (!lead) throw new Error('Lead not found');

      const timestamp = new Date().toISOString();
      const newNote = `[${timestamp}] ${note}`;
      const updatedNotes = lead.notes ? `${lead.notes}\n\n${newNote}` : newNote;

      await updateLead(leadId, { notes: updatedNotes });
    },
    [updateLead]
  );

  // Set next follow up
  const setNextFollowUp = useCallback(
    async (leadId: string, date: string) => {
      await updateLead(leadId, { nextFollowUpDate: date });
    },
    [updateLead]
  );

  // Search leads
  const searchLeads = useCallback(
    async (query: string): Promise<Lead[]> => {
      if (!tenantId) return [];

      const searchTerm = query.toLowerCase().trim();
      return crmDb.leads
        .where('tenantId')
        .equals(tenantId)
        .filter(
          (lead) =>
            lead.firstName.toLowerCase().includes(searchTerm) ||
            lead.lastName.toLowerCase().includes(searchTerm) ||
            lead.companyName?.toLowerCase().includes(searchTerm) ||
            lead.email.toLowerCase().includes(searchTerm) ||
            lead.phone?.toLowerCase().includes(searchTerm) ||
            lead.notes.toLowerCase().includes(searchTerm)
        )
        .toArray();
    },
    [tenantId]
  );

  // Filter leads
  const filterLeads = useCallback(
    async (filter: LeadFilter) => {
      setCurrentFilter(filter);
      setCurrentPage(1);
      await loadLocalLeads();
    },
    [loadLocalLeads]
  );

  // Clear filter
  const clearFilter = useCallback(async () => {
    setCurrentFilter(assignedToMe && user?.id ? { assignedTo: [user.id] } : undefined);
    setCurrentPage(1);
    await loadLocalLeads();
  }, [assignedToMe, user?.id, loadLocalLeads]);

  // Get overdue leads
  const getOverdueLeads = useCallback(async (): Promise<Lead[]> => {
    if (!tenantId) return [];
    return crmDb.getOverdueLeads(tenantId);
  }, [tenantId]);

  // Get high score leads
  const getHighScoreLeads = useCallback(
    async (minScore = 80): Promise<Lead[]> => {
      if (!tenantId) return [];
      return crmDb.getHighScoreLeads(tenantId, minScore);
    },
    [tenantId]
  );

  // Pagination
  const setPage = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const nextPage = useCallback(() => {
    const maxPage = Math.ceil(totalCount / pageSize);
    if (currentPage < maxPage) {
      setCurrentPage(currentPage + 1);
    }
  }, [currentPage, totalCount, pageSize]);

  const previousPage = useCallback(() => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  }, [currentPage]);

  // Refresh metrics
  const refreshMetrics = useCallback(async () => {
    if (!tenantId) return;

    try {
      const dbMetrics = await crmDb.getLeadMetrics(tenantId);

      const metrics: LeadMetrics = {
        totalLeads: dbMetrics.total,
        newLeads: dbMetrics.new,
        qualifiedLeads: dbMetrics.qualified,
        convertedLeads: dbMetrics.converted,
        conversionRate: dbMetrics.conversionRate,
        averageScore: dbMetrics.averageScore,
        leadsBySource: dbMetrics.bySource as any,
        leadsByStatus: dbMetrics.byStatus as any,
      };

      setMetrics(metrics);
    } catch (err) {
      console.error('Failed to refresh lead metrics:', err);
    }
  }, [tenantId]);

  // Get leads by source
  const getLeadsBySource = useCallback(async (): Promise<Record<string, number>> => {
    if (!tenantId) return {};

    const allLeads = await crmDb.leads.where('tenantId').equals(tenantId).toArray();

    const bySource: Record<string, number> = {};
    allLeads.forEach((lead) => {
      bySource[lead.source] = (bySource[lead.source] || 0) + 1;
    });

    return bySource;
  }, [tenantId]);

  // Get conversion funnel
  const getConversionFunnel = useCallback(async () => {
    if (!tenantId) return [];

    const allLeads = await crmDb.leads.where('tenantId').equals(tenantId).toArray();

    const statusCounts: Record<string, number> = {};
    allLeads.forEach((lead) => {
      statusCounts[lead.status] = (statusCounts[lead.status] || 0) + 1;
    });

    const funnelStages = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'closed_won'];

    let previousCount = allLeads.length;

    return funnelStages.map((stage) => {
      const count = statusCounts[stage] || 0;
      const conversionRate = previousCount > 0 ? (count / previousCount) * 100 : 0;
      previousCount = count;

      return {
        stage: stage.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        count,
        conversionRate,
      };
    });
  }, [tenantId]);

  // Bulk operations
  const bulkAssignLeads = useCallback(
    async (leadIds: string[], userId: string) => {
      try {
        const updatePromises = leadIds.map((id) => assignLead(id, userId));
        await Promise.all(updatePromises);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to bulk assign leads');
        throw err;
      }
    },
    [assignLead]
  );

  const bulkUpdateStatus = useCallback(
    async (leadIds: string[], status: Lead['status']) => {
      try {
        const updatePromises = leadIds.map((id) => updateLeadStatus(id, status));
        await Promise.all(updatePromises);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to bulk update lead status');
        throw err;
      }
    },
    [updateLeadStatus]
  );

  const bulkDeleteLeads = useCallback(
    async (leadIds: string[]) => {
      try {
        const deletePromises = leadIds.map((id) => deleteLead(id));
        await Promise.all(deletePromises);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to bulk delete leads');
        throw err;
      }
    },
    [deleteLead]
  );

  const exportLeads = useCallback(
    async (format: 'csv' | 'json'): Promise<string> => {
      if (!tenantId) throw new Error('No tenant ID available');

      const allLeads = await crmDb.leads.where('tenantId').equals(tenantId).toArray();

      if (format === 'json') {
        return JSON.stringify(allLeads, null, 2);
      } else {
        // CSV format
        if (allLeads.length === 0) return '';

        const headers = [
          'Name',
          'Company',
          'Email',
          'Phone',
          'Status',
          'Source',
          'Priority',
          'Score',
          'Budget',
          'Interested Services',
          'Assigned To',
          'Created Date',
        ];

        const rows = allLeads.map((lead) => [
          `${lead.firstName} ${lead.lastName}`,
          lead.companyName || '',
          lead.email,
          lead.phone || '',
          lead.status,
          lead.source,
          lead.priority,
          lead.score.toString(),
          lead.budget?.toString() || '',
          lead.interestedServices.join('; '),
          lead.assignedTo || '',
          lead.createdAt,
        ]);

        return [headers, ...rows]
          .map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(','))
          .join('\n');
      }
    },
    [tenantId]
  );

  // Initialize
  useEffect(() => {
    loadLocalLeads();
    refreshMetrics();
  }, [loadLocalLeads, refreshMetrics]);

  // Auto-sync interval
  useEffect(() => {
    if (!autoSync) return;

    const interval = setInterval(syncWithServer, syncInterval);
    return () => clearInterval(interval);
  }, [autoSync, syncInterval, syncWithServer]);

  // Reload when page changes
  useEffect(() => {
    loadLocalLeads();
  }, [currentPage, loadLocalLeads]);

  // Initial sync
  useEffect(() => {
    if (autoSync && tenantId) {
      syncWithServer();
    }
  }, [autoSync, tenantId, syncWithServer]);

  return {
    leads,
    loading,
    error,
    metrics,
    totalCount,
    currentPage,

    // CRUD Operations
    createLead,
    updateLead,
    deleteLead,

    // Lead Management
    assignLead,
    updateLeadStatus,
    updateLeadScore,
    convertToCustomer,

    // Lead Scoring
    calculateLeadScore,
    getLeadScoreFactors,

    // Lead Nurturing
    scheduleFollowUp,
    addLeadNote,
    setNextFollowUp,

    // Search and Filter
    searchLeads,
    filterLeads,
    clearFilter,
    getOverdueLeads,
    getHighScoreLeads,

    // Pagination
    setPage,
    nextPage,
    previousPage,

    // Sync
    syncWithServer,
    syncStatus,
    lastSync,

    // Analytics
    refreshMetrics,
    getLeadsBySource,
    getConversionFunnel,

    // Bulk Operations
    bulkAssignLeads,
    bulkUpdateStatus,
    bulkDeleteLeads,
    exportLeads,
  };
}
