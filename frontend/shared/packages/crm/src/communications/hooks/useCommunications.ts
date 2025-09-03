import { useState, useEffect, useCallback } from 'react';
import { useApiClient, useAuth } from '@dotmac/headless';
import { crmDb } from '../database';
import type {
  Communication,
  CommunicationFilter,
  CommunicationMetrics,
  CommunicationType,
  CommunicationAttachment,
} from '../../types';

interface UseCommunicationsOptions {
  customerId?: string;
  leadId?: string;
  autoSync?: boolean;
  syncInterval?: number;
  pageSize?: number;
}

interface UseCommunicationsReturn {
  communications: Communication[];
  loading: boolean;
  error: string | null;
  metrics: CommunicationMetrics | null;
  totalCount: number;
  currentPage: number;

  // Communication Creation
  sendEmail: (params: {
    to: string[];
    cc?: string[];
    bcc?: string[];
    subject: string;
    content: string;
    attachments?: File[];
    templateId?: string;
  }) => Promise<Communication>;

  makeCall: (params: {
    phoneNumber: string;
    duration?: number;
    notes: string;
    outcome?: string;
  }) => Promise<Communication>;

  sendSMS: (params: { phoneNumber: string; message: string }) => Promise<Communication>;

  addNote: (params: {
    content: string;
    summary?: string;
    tags?: string[];
  }) => Promise<Communication>;

  scheduleMeeting: (params: {
    subject: string;
    startTime: string;
    endTime: string;
    attendees: string[];
    location?: string;
    description?: string;
  }) => Promise<Communication>;

  // Communication Management
  markAsRead: (communicationId: string) => Promise<void>;
  addReply: (communicationId: string, content: string) => Promise<Communication>;
  forwardCommunication: (
    communicationId: string,
    to: string[],
    note?: string
  ) => Promise<Communication>;
  archiveCommunication: (communicationId: string) => Promise<void>;

  // Attachments
  uploadAttachment: (communicationId: string, file: File) => Promise<CommunicationAttachment>;
  downloadAttachment: (attachmentId: string) => Promise<Blob>;
  removeAttachment: (communicationId: string, attachmentId: string) => Promise<void>;

  // Search and Filter
  searchCommunications: (query: string) => Promise<Communication[]>;
  filterCommunications: (filter: CommunicationFilter) => Promise<void>;
  clearFilter: () => Promise<void>;
  getCommunicationsByType: (type: CommunicationType) => Promise<Communication[]>;
  getRecentCommunications: (days?: number) => Promise<Communication[]>;

  // Analytics
  refreshMetrics: () => Promise<void>;
  getResponseTimes: () => Promise<{ avg: number; min: number; max: number }>;
  getSentimentAnalysis: () => Promise<{ positive: number; neutral: number; negative: number }>;
  getCommunicationTrends: (
    days?: number
  ) => Promise<{ date: string; count: number; type: CommunicationType }[]>;

  // Templates
  getEmailTemplates: () => Promise<
    { id: string; name: string; subject: string; content: string }[]
  >;
  renderTemplate: (
    templateId: string,
    variables: Record<string, string>
  ) => Promise<{ subject: string; content: string }>;

  // Pagination
  setPage: (page: number) => void;
  nextPage: () => void;
  previousPage: () => void;

  // Sync
  syncWithServer: () => Promise<void>;
  syncStatus: 'idle' | 'syncing' | 'error';
  lastSync: Date | null;

  // Bulk Operations
  bulkArchive: (communicationIds: string[]) => Promise<void>;
  bulkMarkAsRead: (communicationIds: string[]) => Promise<void>;
  bulkDelete: (communicationIds: string[]) => Promise<void>;
  exportCommunications: (format: 'csv' | 'json') => Promise<string>;
}

export function useCommunications(options: UseCommunicationsOptions = {}): UseCommunicationsReturn {
  const { customerId, leadId, autoSync = true, syncInterval = 30000, pageSize = 20 } = options;

  const { user, tenantId } = useAuth();
  const apiClient = useApiClient();

  const [communications, setCommunications] = useState<Communication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<CommunicationMetrics | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [currentFilter, setCurrentFilter] = useState<CommunicationFilter | undefined>();
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error'>('idle');
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // Load communications from local database
  const loadLocalCommunications = useCallback(async () => {
    if (!tenantId) return;

    try {
      setLoading(true);
      setError(null);

      let communicationsList: Communication[];

      if (customerId) {
        communicationsList = await crmDb.getCommunicationsByCustomer(customerId, tenantId);
      } else if (leadId) {
        communicationsList = await crmDb.getCommunicationsByLead(leadId, tenantId);
      } else if (currentFilter) {
        // Apply filters
        let query = crmDb.communications.where('tenantId').equals(tenantId);
        const results = await query.toArray();

        communicationsList = results.filter((comm) => {
          if (currentFilter.type && !currentFilter.type.includes(comm.type)) return false;
          if (currentFilter.direction && !currentFilter.direction.includes(comm.direction))
            return false;
          if (currentFilter.customerId && comm.customerId !== currentFilter.customerId)
            return false;
          if (currentFilter.leadId && comm.leadId !== currentFilter.leadId) return false;
          if (currentFilter.userId && comm.userId !== currentFilter.userId) return false;

          if (currentFilter.dateAfter && comm.timestamp < currentFilter.dateAfter) return false;
          if (currentFilter.dateBefore && comm.timestamp > currentFilter.dateBefore) return false;

          if (currentFilter.sentiment && !currentFilter.sentiment.includes(comm.sentiment!))
            return false;

          if (currentFilter.topics && currentFilter.topics.length > 0) {
            const hasMatchingTopic = currentFilter.topics.some((topic) =>
              comm.topics.includes(topic)
            );
            if (!hasMatchingTopic) return false;
          }

          if (currentFilter.search) {
            const searchTerm = currentFilter.search.toLowerCase();
            const searchableText = [
              comm.subject,
              comm.content,
              comm.summary,
              comm.fromAddress,
              ...comm.toAddresses,
              ...comm.topics,
              ...comm.tags,
            ]
              .join(' ')
              .toLowerCase();

            if (!searchableText.includes(searchTerm)) return false;
          }

          return true;
        });
      } else {
        communicationsList = await crmDb.communications
          .where('tenantId')
          .equals(tenantId)
          .orderBy('timestamp')
          .reverse()
          .toArray();
      }

      setTotalCount(communicationsList.length);

      // Apply pagination
      const startIndex = (currentPage - 1) * pageSize;
      const endIndex = startIndex + pageSize;
      const paginatedCommunications = communicationsList.slice(startIndex, endIndex);

      setCommunications(paginatedCommunications);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load communications');
      console.error('Failed to load communications:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, customerId, leadId, currentFilter, currentPage, pageSize]);

  // Sync with server
  const syncWithServer = useCallback(async () => {
    if (!tenantId || syncStatus === 'syncing') return;

    try {
      setSyncStatus('syncing');

      // Get pending sync items
      const { communications: pendingCommunications } = await crmDb.getPendingSyncItems();

      // Sync pending communications
      for (const comm of pendingCommunications) {
        try {
          if (comm.id.startsWith('temp_') || comm.id.startsWith('comm_')) {
            // New communication - create on server
            const response = await apiClient.post('/crm/communications', comm);
            if (response.data?.communication) {
              await crmDb.communications.delete(comm.id);
              await crmDb.communications.add({
                ...response.data.communication,
                syncStatus: 'synced',
              });
            }
          } else {
            // Update existing communication
            await apiClient.put(`/crm/communications/${comm.id}`, comm);
            await crmDb.communications.update(comm.id, { syncStatus: 'synced' });
          }
        } catch (apiError) {
          console.error(`Failed to sync communication ${comm.id}:`, apiError);
          await crmDb.communications.update(comm.id, { syncStatus: 'error' });
        }
      }

      // Fetch latest communications from server
      const response = await apiClient.get('/crm/communications', {
        params: {
          tenantId,
          customerId,
          leadId,
        },
      });

      if (response.data?.communications) {
        await crmDb.transaction('rw', crmDb.communications, async () => {
          // Only update communications that are synced
          const syncedComms = await crmDb.communications
            .where('[tenantId+syncStatus]')
            .equals([tenantId, 'synced'])
            .toArray();

          const syncedIds = syncedComms.map((c) => c.id);
          await crmDb.communications.where('id').anyOf(syncedIds).delete();

          const serverCommunications = response.data.communications.map((c: Communication) => ({
            ...c,
            syncStatus: 'synced',
          }));

          await crmDb.communications.bulkAdd(serverCommunications, { allKeys: true });
        });

        await loadLocalCommunications();
      }

      setSyncStatus('idle');
      setLastSync(new Date());
      setError(null);
    } catch (err) {
      setSyncStatus('error');
      setError(err instanceof Error ? err.message : 'Sync failed');
      console.error('Communication sync failed:', err);
    }
  }, [tenantId, syncStatus, apiClient, loadLocalCommunications, customerId, leadId]);

  // Send email
  const sendEmail = useCallback(
    async (params: {
      to: string[];
      cc?: string[];
      bcc?: string[];
      subject: string;
      content: string;
      attachments?: File[];
      templateId?: string;
    }): Promise<Communication> => {
      if (!user?.id || !tenantId) throw new Error('Missing required information');

      const communication: Communication = {
        id: `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'email',
        direction: 'outbound',
        customerId,
        leadId,
        subject: params.subject,
        content: params.content,
        summary: params.subject,
        fromAddress: user.email || 'noreply@example.com',
        toAddresses: params.to,
        ccAddresses: params.cc || [],
        bccAddresses: params.bcc || [],
        timestamp: new Date().toISOString(),
        status: 'sent',
        attachments: [], // Will be populated after file uploads
        sentiment: 'neutral',
        topics: [],
        tags: [],
        userId: user.id,
        userName: user.name || 'Unknown User',
        createdAt: new Date().toISOString(),
        tenantId,
        syncStatus: 'pending',
      };

      try {
        // Upload attachments if any
        if (params.attachments && params.attachments.length > 0) {
          for (const file of params.attachments) {
            const attachment = await uploadAttachment(communication.id, file);
            communication.attachments.push(attachment);
          }
        }

        await crmDb.communications.add(communication);

        // Update customer/lead last contact date
        if (customerId) {
          await crmDb.customers.update(customerId, {
            lastContactDate: new Date().toISOString(),
            syncStatus: 'pending',
          });
        }

        await loadLocalCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/email', communication);
            await crmDb.communications.update(communication.id, { syncStatus: 'synced' });
          } catch (err) {
            await crmDb.communications.update(communication.id, {
              syncStatus: 'error',
              status: 'failed',
            });
            throw err;
          }
        }

        return communication;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send email');
        throw err;
      }
    },
    [user, tenantId, customerId, leadId, loadLocalCommunications, autoSync, apiClient]
  );

  // Make call
  const makeCall = useCallback(
    async (params: {
      phoneNumber: string;
      duration?: number;
      notes: string;
      outcome?: string;
    }): Promise<Communication> => {
      if (!user?.id || !tenantId) throw new Error('Missing required information');

      const communication: Communication = {
        id: `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'phone_call',
        direction: 'outbound',
        customerId,
        leadId,
        subject: 'Phone Call',
        content: params.notes,
        summary: `Called ${params.phoneNumber} - ${params.outcome || 'Call completed'}`,
        fromAddress: user.phone || 'system',
        toAddresses: [params.phoneNumber],
        timestamp: new Date().toISOString(),
        duration: params.duration,
        status: 'sent',
        attachments: [],
        sentiment: 'neutral',
        topics: params.outcome ? [params.outcome] : [],
        tags: ['call'],
        userId: user.id,
        userName: user.name || 'Unknown User',
        createdAt: new Date().toISOString(),
        tenantId,
        syncStatus: 'pending',
      };

      try {
        await crmDb.communications.add(communication);

        if (customerId) {
          await crmDb.customers.update(customerId, {
            lastContactDate: new Date().toISOString(),
            syncStatus: 'pending',
          });
        }

        await loadLocalCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/call', communication);
            await crmDb.communications.update(communication.id, { syncStatus: 'synced' });
          } catch (err) {
            console.error('Failed to sync call record:', err);
          }
        }

        return communication;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to record call');
        throw err;
      }
    },
    [user, tenantId, customerId, leadId, loadLocalCommunications, autoSync, apiClient]
  );

  // Send SMS
  const sendSMS = useCallback(
    async (params: { phoneNumber: string; message: string }): Promise<Communication> => {
      if (!user?.id || !tenantId) throw new Error('Missing required information');

      const communication: Communication = {
        id: `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'sms',
        direction: 'outbound',
        customerId,
        leadId,
        subject: 'SMS Message',
        content: params.message,
        summary: `SMS to ${params.phoneNumber}`,
        fromAddress: 'system',
        toAddresses: [params.phoneNumber],
        timestamp: new Date().toISOString(),
        status: 'sent',
        attachments: [],
        sentiment: 'neutral',
        topics: [],
        tags: ['sms'],
        userId: user.id,
        userName: user.name || 'Unknown User',
        createdAt: new Date().toISOString(),
        tenantId,
        syncStatus: 'pending',
      };

      try {
        await crmDb.communications.add(communication);

        if (customerId) {
          await crmDb.customers.update(customerId, {
            lastContactDate: new Date().toISOString(),
            syncStatus: 'pending',
          });
        }

        await loadLocalCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/sms', communication);
            await crmDb.communications.update(communication.id, { syncStatus: 'synced' });
          } catch (err) {
            await crmDb.communications.update(communication.id, {
              syncStatus: 'error',
              status: 'failed',
            });
            throw err;
          }
        }

        return communication;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send SMS');
        throw err;
      }
    },
    [user, tenantId, customerId, leadId, loadLocalCommunications, autoSync, apiClient]
  );

  // Add note
  const addNote = useCallback(
    async (params: {
      content: string;
      summary?: string;
      tags?: string[];
    }): Promise<Communication> => {
      if (!user?.id || !tenantId) throw new Error('Missing required information');

      const communication: Communication = {
        id: `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'note',
        direction: 'outbound',
        customerId,
        leadId,
        subject: 'Note',
        content: params.content,
        summary:
          params.summary ||
          params.content.substring(0, 100) + (params.content.length > 100 ? '...' : ''),
        fromAddress: user.id,
        toAddresses: [],
        timestamp: new Date().toISOString(),
        status: 'sent',
        attachments: [],
        sentiment: 'neutral',
        topics: [],
        tags: params.tags || ['note'],
        userId: user.id,
        userName: user.name || 'Unknown User',
        createdAt: new Date().toISOString(),
        tenantId,
        syncStatus: 'pending',
      };

      try {
        await crmDb.communications.add(communication);
        await loadLocalCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/note', communication);
            await crmDb.communications.update(communication.id, { syncStatus: 'synced' });
          } catch (err) {
            console.error('Failed to sync note:', err);
          }
        }

        return communication;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to add note');
        throw err;
      }
    },
    [user, tenantId, customerId, leadId, loadLocalCommunications, autoSync, apiClient]
  );

  // Schedule meeting
  const scheduleMeeting = useCallback(
    async (params: {
      subject: string;
      startTime: string;
      endTime: string;
      attendees: string[];
      location?: string;
      description?: string;
    }): Promise<Communication> => {
      if (!user?.id || !tenantId) throw new Error('Missing required information');

      const duration = Math.round(
        (new Date(params.endTime).getTime() - new Date(params.startTime).getTime()) / 1000
      );

      const communication: Communication = {
        id: `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        type: 'meeting',
        direction: 'outbound',
        customerId,
        leadId,
        subject: params.subject,
        content: params.description || `Meeting scheduled: ${params.subject}`,
        summary: `Meeting: ${params.subject} at ${params.location || 'TBD'}`,
        fromAddress: user.email || user.id,
        toAddresses: params.attendees,
        timestamp: params.startTime,
        duration,
        status: 'sent',
        attachments: [],
        sentiment: 'neutral',
        topics: ['meeting'],
        tags: ['scheduled', 'meeting'],
        userId: user.id,
        userName: user.name || 'Unknown User',
        createdAt: new Date().toISOString(),
        tenantId,
        syncStatus: 'pending',
      };

      try {
        await crmDb.communications.add(communication);
        await loadLocalCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/meeting', communication);
            await crmDb.communications.update(communication.id, { syncStatus: 'synced' });
          } catch (err) {
            console.error('Failed to sync meeting:', err);
          }
        }

        return communication;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to schedule meeting');
        throw err;
      }
    },
    [user, tenantId, customerId, leadId, loadLocalCommunications, autoSync, apiClient]
  );

  // Mark as read
  const markAsRead = useCallback(
    async (communicationId: string) => {
      await crmDb.communications.update(communicationId, {
        status: 'read',
        readAt: new Date().toISOString(),
        syncStatus: 'pending',
      });

      await loadLocalCommunications();

      if (autoSync) {
        try {
          await apiClient.put(`/crm/communications/${communicationId}/read`);
          await crmDb.communications.update(communicationId, { syncStatus: 'synced' });
        } catch (err) {
          console.error('Failed to sync read status:', err);
        }
      }
    },
    [loadLocalCommunications, autoSync, apiClient]
  );

  // Add reply
  const addReply = useCallback(
    async (communicationId: string, content: string): Promise<Communication> => {
      const originalComm = await crmDb.communications.get(communicationId);
      if (!originalComm) throw new Error('Original communication not found');

      return sendEmail({
        to: [originalComm.fromAddress],
        subject: `Re: ${originalComm.subject}`,
        content,
      });
    },
    [sendEmail]
  );

  // Upload attachment
  const uploadAttachment = useCallback(
    async (communicationId: string, file: File): Promise<CommunicationAttachment> => {
      const attachment: CommunicationAttachment = {
        id: `att_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        fileName: file.name,
        fileSize: file.size,
        mimeType: file.type,
        url: URL.createObjectURL(file), // Temporary local URL
        thumbnailUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      };

      if (autoSync) {
        try {
          // Upload file to server
          const formData = new FormData();
          formData.append('file', file);
          formData.append('communicationId', communicationId);

          const response = await apiClient.post('/crm/communications/attachments', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });

          if (response.data?.attachment) {
            return response.data.attachment;
          }
        } catch (err) {
          console.error('Failed to upload attachment:', err);
        }
      }

      return attachment;
    },
    [autoSync, apiClient]
  );

  // Download attachment
  const downloadAttachment = useCallback(
    async (attachmentId: string): Promise<Blob> => {
      try {
        const response = await apiClient.get(`/crm/attachments/${attachmentId}/download`, {
          responseType: 'blob',
        });
        return response.data;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to download attachment');
        throw err;
      }
    },
    [apiClient]
  );

  // Search communications
  const searchCommunications = useCallback(
    async (query: string): Promise<Communication[]> => {
      if (!tenantId) return [];

      const searchTerm = query.toLowerCase().trim();
      return crmDb.communications
        .where('tenantId')
        .equals(tenantId)
        .filter(
          (comm) =>
            comm.subject.toLowerCase().includes(searchTerm) ||
            comm.content.toLowerCase().includes(searchTerm) ||
            comm.summary?.toLowerCase().includes(searchTerm) ||
            comm.fromAddress.toLowerCase().includes(searchTerm) ||
            comm.toAddresses.some((addr) => addr.toLowerCase().includes(searchTerm)) ||
            comm.topics.some((topic) => topic.toLowerCase().includes(searchTerm)) ||
            comm.tags.some((tag) => tag.toLowerCase().includes(searchTerm))
        )
        .toArray();
    },
    [tenantId]
  );

  // Filter communications
  const filterCommunications = useCallback(
    async (filter: CommunicationFilter) => {
      setCurrentFilter(filter);
      setCurrentPage(1);
      await loadLocalCommunications();
    },
    [loadLocalCommunications]
  );

  // Clear filter
  const clearFilter = useCallback(async () => {
    setCurrentFilter(undefined);
    setCurrentPage(1);
    await loadLocalCommunications();
  }, [loadLocalCommunications]);

  // Get communications by type
  const getCommunicationsByType = useCallback(
    async (type: CommunicationType): Promise<Communication[]> => {
      if (!tenantId) return [];

      return crmDb.communications
        .where('[tenantId+type]')
        .equals([tenantId, type])
        .orderBy('timestamp')
        .reverse()
        .toArray();
    },
    [tenantId]
  );

  // Get recent communications
  const getRecentCommunications = useCallback(
    async (days = 7): Promise<Communication[]> => {
      if (!tenantId) return [];
      return crmDb.getRecentCommunications(tenantId, days);
    },
    [tenantId]
  );

  // Refresh metrics
  const refreshMetrics = useCallback(async () => {
    if (!tenantId) return;

    try {
      const allCommunications = await crmDb.communications
        .where('tenantId')
        .equals(tenantId)
        .toArray();

      const totalCommunications = allCommunications.length;
      const emailCommunications = allCommunications.filter((c) => c.type === 'email');
      const sentEmails = emailCommunications.filter((c) => c.direction === 'outbound');
      const repliedEmails = emailCommunications.filter((c) => c.repliedAt);

      const responseRate =
        sentEmails.length > 0 ? (repliedEmails.length / sentEmails.length) * 100 : 0;

      // Calculate average response time (in hours)
      const responseTimes = repliedEmails
        .map((c) =>
          c.repliedAt && c.timestamp
            ? (new Date(c.repliedAt).getTime() - new Date(c.timestamp).getTime()) / (1000 * 60 * 60)
            : 0
        )
        .filter((time) => time > 0);

      const averageResponseTime =
        responseTimes.length > 0
          ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
          : 0;

      // Communication by type
      const communicationsByType: Record<CommunicationType, number> = {
        email: 0,
        phone_call: 0,
        sms: 0,
        meeting: 0,
        note: 0,
        support_ticket: 0,
        chat: 0,
      };

      allCommunications.forEach((comm) => {
        communicationsByType[comm.type] = (communicationsByType[comm.type] || 0) + 1;
      });

      // Sentiment analysis
      const sentimentCounts = { positive: 0, neutral: 0, negative: 0 };
      allCommunications.forEach((comm) => {
        if (comm.sentiment) {
          sentimentCounts[comm.sentiment]++;
        }
      });

      const metrics: CommunicationMetrics = {
        totalCommunications,
        responseRate,
        averageResponseTime,
        communicationsByType,
        sentimentAnalysis: sentimentCounts,
      };

      setMetrics(metrics);
    } catch (err) {
      console.error('Failed to refresh communication metrics:', err);
    }
  }, [tenantId]);

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

  // Bulk operations
  const bulkArchive = useCallback(
    async (communicationIds: string[]) => {
      try {
        const updatePromises = communicationIds.map((id) =>
          crmDb.communications.update(id, {
            tags: ['archived'],
            syncStatus: 'pending' as const,
          })
        );
        await Promise.all(updatePromises);
        await loadLocalCommunications();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to bulk archive communications');
        throw err;
      }
    },
    [loadLocalCommunications]
  );

  const bulkMarkAsRead = useCallback(
    async (communicationIds: string[]) => {
      try {
        const updatePromises = communicationIds.map((id) =>
          crmDb.communications.update(id, {
            status: 'read',
            readAt: new Date().toISOString(),
            syncStatus: 'pending' as const,
          })
        );
        await Promise.all(updatePromises);
        await loadLocalCommunications();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to bulk mark as read');
        throw err;
      }
    },
    [loadLocalCommunications]
  );

  const exportCommunications = useCallback(
    async (format: 'csv' | 'json'): Promise<string> => {
      if (!tenantId) throw new Error('No tenant ID available');

      const allCommunications = await crmDb.communications
        .where('tenantId')
        .equals(tenantId)
        .toArray();

      if (format === 'json') {
        return JSON.stringify(allCommunications, null, 2);
      } else {
        // CSV format
        if (allCommunications.length === 0) return '';

        const headers = [
          'Date',
          'Type',
          'Direction',
          'Subject',
          'From',
          'To',
          'Status',
          'Duration',
          'User',
          'Customer ID',
          'Lead ID',
        ];

        const rows = allCommunications.map((comm) => [
          comm.timestamp,
          comm.type,
          comm.direction,
          comm.subject,
          comm.fromAddress,
          comm.toAddresses.join('; '),
          comm.status,
          comm.duration?.toString() || '',
          comm.userName,
          comm.customerId || '',
          comm.leadId || '',
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
    loadLocalCommunications();
    refreshMetrics();
  }, [loadLocalCommunications, refreshMetrics]);

  // Auto-sync interval
  useEffect(() => {
    if (!autoSync) return;

    const interval = setInterval(syncWithServer, syncInterval);
    return () => clearInterval(interval);
  }, [autoSync, syncInterval, syncWithServer]);

  // Reload when page changes
  useEffect(() => {
    loadLocalCommunications();
  }, [currentPage, loadLocalCommunications]);

  // Initial sync
  useEffect(() => {
    if (autoSync && tenantId) {
      syncWithServer();
    }
  }, [autoSync, tenantId, syncWithServer]);

  return {
    communications,
    loading,
    error,
    metrics,
    totalCount,
    currentPage,

    // Communication Creation
    sendEmail,
    makeCall,
    sendSMS,
    addNote,
    scheduleMeeting,

    // Communication Management
    markAsRead,
    addReply,
    forwardCommunication: async () => {
      throw new Error('Not implemented');
    }, // Simplified for brevity
    archiveCommunication: async (id) => bulkArchive([id]),

    // Attachments
    uploadAttachment,
    downloadAttachment,
    removeAttachment: async () => {
      throw new Error('Not implemented');
    }, // Simplified for brevity

    // Search and Filter
    searchCommunications,
    filterCommunications,
    clearFilter,
    getCommunicationsByType,
    getRecentCommunications,

    // Analytics
    refreshMetrics,
    getResponseTimes: async () => ({ avg: 0, min: 0, max: 0 }), // Simplified for brevity
    getSentimentAnalysis: async () =>
      metrics?.sentimentAnalysis || { positive: 0, neutral: 0, negative: 0 },
    getCommunicationTrends: async () => [], // Simplified for brevity

    // Templates
    getEmailTemplates: async () => [], // Simplified for brevity
    renderTemplate: async () => ({ subject: '', content: '' }), // Simplified for brevity

    // Pagination
    setPage,
    nextPage,
    previousPage,

    // Sync
    syncWithServer,
    syncStatus,
    lastSync,

    // Bulk Operations
    bulkArchive,
    bulkMarkAsRead,
    bulkDelete: async () => {
      throw new Error('Not implemented');
    }, // Simplified for brevity
    exportCommunications,
  };
}
