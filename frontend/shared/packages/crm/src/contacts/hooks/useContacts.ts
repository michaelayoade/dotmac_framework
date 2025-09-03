import { useState, useEffect, useCallback } from 'react';
import { useApiClient, useAuth } from '@dotmac/headless';
import { crmDb } from '../database';
import type { ContactMethod, CustomerAccount, Communication, CommunicationType } from '../../types';

interface ContactActivity {
  type: 'communication' | 'update' | 'service_change';
  timestamp: string;
  description: string;
  userId: string;
  userName: string;
}

interface UseContactsOptions {
  customerId?: string;
  autoSync?: boolean;
}

interface UseContactsReturn {
  // Contact Information
  contactMethods: ContactMethod[];
  primaryEmail: ContactMethod | null;
  primaryPhone: ContactMethod | null;
  loading: boolean;
  error: string | null;

  // Contact Management
  addContactMethod: (method: Omit<ContactMethod, 'id'>) => Promise<void>;
  updateContactMethod: (methodId: string, updates: Partial<ContactMethod>) => Promise<void>;
  removeContactMethod: (methodId: string) => Promise<void>;
  setPrimaryContact: (methodId: string, type: 'email' | 'phone') => Promise<void>;

  // Communication History
  recentCommunications: Communication[];
  sendEmail: (to: string, subject: string, content: string) => Promise<void>;
  makeCall: (phone: string, notes?: string) => Promise<void>;
  sendSMS: (phone: string, message: string) => Promise<void>;
  addNote: (content: string) => Promise<void>;

  // Contact Preferences
  updatePreferences: (methodId: string, preferences: ContactMethod['preferences']) => Promise<void>;
  checkDoNotContact: (type: 'email' | 'phone' | 'sms') => boolean;

  // Contact Validation
  validateEmail: (email: string) => Promise<boolean>;
  validatePhone: (phone: string) => Promise<boolean>;

  // Activity History
  contactActivity: ContactActivity[];
  refreshActivity: () => Promise<void>;

  // Quick Actions
  sendQuickEmail: (templateId: string, variables?: Record<string, string>) => Promise<void>;
  scheduleFollowUp: (date: string, notes: string) => Promise<void>;
}

export function useContacts(options: UseContactsOptions = {}): UseContactsReturn {
  const { customerId, autoSync = true } = options;
  const { user, tenantId } = useAuth();
  const apiClient = useApiClient();

  const [contactMethods, setContactMethods] = useState<ContactMethod[]>([]);
  const [recentCommunications, setRecentCommunications] = useState<Communication[]>([]);
  const [contactActivity, setContactActivity] = useState<ContactActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load contact methods
  const loadContactMethods = useCallback(async () => {
    if (!customerId || !tenantId) {
      setContactMethods([]);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const customer = await crmDb.customers.get(customerId);
      if (customer) {
        setContactMethods(customer.contactMethods || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load contact methods');
      console.error('Failed to load contact methods:', err);
    } finally {
      setLoading(false);
    }
  }, [customerId, tenantId]);

  // Load communication history
  const loadCommunications = useCallback(async () => {
    if (!customerId || !tenantId) return;

    try {
      const communications = await crmDb.getCommunicationsByCustomer(customerId, tenantId);
      setRecentCommunications(communications.slice(0, 20)); // Last 20 communications
    } catch (err) {
      console.error('Failed to load communications:', err);
    }
  }, [customerId, tenantId]);

  // Add contact method
  const addContactMethod = useCallback(
    async (method: Omit<ContactMethod, 'id'>) => {
      if (!customerId) throw new Error('No customer selected');

      const customer = await crmDb.customers.get(customerId);
      if (!customer) throw new Error('Customer not found');

      const newMethod: ContactMethod = {
        ...method,
        id: `contact_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      };

      // If this is the first method of its type, make it primary
      const existingMethodsOfType = customer.contactMethods.filter((m) => m.type === method.type);
      if (existingMethodsOfType.length === 0) {
        newMethod.isPrimary = true;
      }

      const updatedMethods = [...customer.contactMethods, newMethod];

      await crmDb.customers.update(customerId, {
        contactMethods: updatedMethods,
        updatedAt: new Date().toISOString(),
        syncStatus: 'pending',
      });

      await loadContactMethods();

      if (autoSync) {
        // Sync with server
        try {
          await apiClient.put(`/crm/customers/${customerId}`, {
            contactMethods: updatedMethods,
          });
          await crmDb.customers.update(customerId, { syncStatus: 'synced' });
        } catch (err) {
          console.error('Failed to sync contact method:', err);
        }
      }
    },
    [customerId, loadContactMethods, autoSync, apiClient]
  );

  // Update contact method
  const updateContactMethod = useCallback(
    async (methodId: string, updates: Partial<ContactMethod>) => {
      if (!customerId) throw new Error('No customer selected');

      const customer = await crmDb.customers.get(customerId);
      if (!customer) throw new Error('Customer not found');

      const updatedMethods = customer.contactMethods.map((method) =>
        method.id === methodId ? { ...method, ...updates } : method
      );

      await crmDb.customers.update(customerId, {
        contactMethods: updatedMethods,
        updatedAt: new Date().toISOString(),
        syncStatus: 'pending',
      });

      await loadContactMethods();

      if (autoSync) {
        try {
          await apiClient.put(`/crm/customers/${customerId}`, {
            contactMethods: updatedMethods,
          });
          await crmDb.customers.update(customerId, { syncStatus: 'synced' });
        } catch (err) {
          console.error('Failed to sync contact method update:', err);
        }
      }
    },
    [customerId, loadContactMethods, autoSync, apiClient]
  );

  // Remove contact method
  const removeContactMethod = useCallback(
    async (methodId: string) => {
      if (!customerId) throw new Error('No customer selected');

      const customer = await crmDb.customers.get(customerId);
      if (!customer) throw new Error('Customer not found');

      const methodToRemove = customer.contactMethods.find((m) => m.id === methodId);
      if (!methodToRemove) return;

      let updatedMethods = customer.contactMethods.filter((method) => method.id !== methodId);

      // If we removed a primary method, make another method of the same type primary
      if (methodToRemove.isPrimary) {
        const sameTypeMethods = updatedMethods.filter((m) => m.type === methodToRemove.type);
        if (sameTypeMethods.length > 0) {
          sameTypeMethods[0].isPrimary = true;
          updatedMethods = updatedMethods.map((method) =>
            method.id === sameTypeMethods[0].id ? { ...method, isPrimary: true } : method
          );
        }
      }

      await crmDb.customers.update(customerId, {
        contactMethods: updatedMethods,
        updatedAt: new Date().toISOString(),
        syncStatus: 'pending',
      });

      await loadContactMethods();

      if (autoSync) {
        try {
          await apiClient.put(`/crm/customers/${customerId}`, {
            contactMethods: updatedMethods,
          });
          await crmDb.customers.update(customerId, { syncStatus: 'synced' });
        } catch (err) {
          console.error('Failed to sync contact method removal:', err);
        }
      }
    },
    [customerId, loadContactMethods, autoSync, apiClient]
  );

  // Set primary contact
  const setPrimaryContact = useCallback(
    async (methodId: string, type: 'email' | 'phone') => {
      if (!customerId) throw new Error('No customer selected');

      const customer = await crmDb.customers.get(customerId);
      if (!customer) throw new Error('Customer not found');

      const updatedMethods = customer.contactMethods.map((method) => ({
        ...method,
        isPrimary:
          method.id === methodId &&
          (method.type === type || (type === 'phone' && ['phone', 'mobile'].includes(method.type))),
      }));

      await crmDb.customers.update(customerId, {
        contactMethods: updatedMethods,
        updatedAt: new Date().toISOString(),
        syncStatus: 'pending',
      });

      await loadContactMethods();

      if (autoSync) {
        try {
          await apiClient.put(`/crm/customers/${customerId}`, {
            contactMethods: updatedMethods,
          });
          await crmDb.customers.update(customerId, { syncStatus: 'synced' });
        } catch (err) {
          console.error('Failed to sync primary contact change:', err);
        }
      }
    },
    [customerId, loadContactMethods, autoSync, apiClient]
  );

  // Send email
  const sendEmail = useCallback(
    async (to: string, subject: string, content: string) => {
      if (!customerId || !user?.id) throw new Error('Missing required information');

      try {
        const communication: Omit<Communication, 'id' | 'createdAt'> = {
          type: 'email',
          direction: 'outbound',
          customerId,
          subject,
          content,
          summary: subject,
          fromAddress: user.email || 'noreply@example.com',
          toAddresses: [to],
          timestamp: new Date().toISOString(),
          status: 'sent',
          attachments: [],
          sentiment: 'neutral',
          topics: [],
          tags: [],
          userId: user.id,
          userName: user.name || 'Unknown User',
          tenantId: tenantId!,
          syncStatus: 'pending',
        };

        const commId = `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await crmDb.communications.add({
          ...communication,
          id: commId,
          createdAt: communication.timestamp,
        });

        // Update customer last contact date
        await crmDb.customers.update(customerId, {
          lastContactDate: new Date().toISOString(),
          syncStatus: 'pending',
        });

        await loadCommunications();

        if (autoSync) {
          // Send email via API
          try {
            await apiClient.post('/crm/communications/email', communication);
            await crmDb.communications.update(commId, { syncStatus: 'synced' });
          } catch (err) {
            await crmDb.communications.update(commId, {
              syncStatus: 'error',
              status: 'failed',
            });
            throw err;
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send email');
        throw err;
      }
    },
    [customerId, user, tenantId, loadCommunications, autoSync, apiClient]
  );

  // Make call
  const makeCall = useCallback(
    async (phone: string, notes?: string) => {
      if (!customerId || !user?.id) throw new Error('Missing required information');

      try {
        const communication: Omit<Communication, 'id' | 'createdAt'> = {
          type: 'phone_call',
          direction: 'outbound',
          customerId,
          subject: 'Phone Call',
          content: notes || 'Phone call made',
          summary: `Called ${phone}`,
          fromAddress: user.phone || 'system',
          toAddresses: [phone],
          timestamp: new Date().toISOString(),
          status: 'sent',
          attachments: [],
          sentiment: 'neutral',
          topics: [],
          tags: [],
          userId: user.id,
          userName: user.name || 'Unknown User',
          tenantId: tenantId!,
          syncStatus: 'pending',
        };

        const commId = `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await crmDb.communications.add({
          ...communication,
          id: commId,
          createdAt: communication.timestamp,
        });

        // Update customer last contact date
        await crmDb.customers.update(customerId, {
          lastContactDate: new Date().toISOString(),
          syncStatus: 'pending',
        });

        await loadCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/call', communication);
            await crmDb.communications.update(commId, { syncStatus: 'synced' });
          } catch (err) {
            console.error('Failed to sync call record:', err);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to record call');
        throw err;
      }
    },
    [customerId, user, tenantId, loadCommunications, autoSync, apiClient]
  );

  // Send SMS
  const sendSMS = useCallback(
    async (phone: string, message: string) => {
      if (!customerId || !user?.id) throw new Error('Missing required information');

      try {
        const communication: Omit<Communication, 'id' | 'createdAt'> = {
          type: 'sms',
          direction: 'outbound',
          customerId,
          subject: 'SMS Message',
          content: message,
          summary: `SMS to ${phone}`,
          fromAddress: 'system',
          toAddresses: [phone],
          timestamp: new Date().toISOString(),
          status: 'sent',
          attachments: [],
          sentiment: 'neutral',
          topics: [],
          tags: [],
          userId: user.id,
          userName: user.name || 'Unknown User',
          tenantId: tenantId!,
          syncStatus: 'pending',
        };

        const commId = `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await crmDb.communications.add({
          ...communication,
          id: commId,
          createdAt: communication.timestamp,
        });

        // Update customer last contact date
        await crmDb.customers.update(customerId, {
          lastContactDate: new Date().toISOString(),
          syncStatus: 'pending',
        });

        await loadCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/sms', communication);
            await crmDb.communications.update(commId, { syncStatus: 'synced' });
          } catch (err) {
            await crmDb.communications.update(commId, {
              syncStatus: 'error',
              status: 'failed',
            });
            throw err;
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send SMS');
        throw err;
      }
    },
    [customerId, user, tenantId, loadCommunications, autoSync, apiClient]
  );

  // Add note
  const addNote = useCallback(
    async (content: string) => {
      if (!customerId || !user?.id) throw new Error('Missing required information');

      try {
        const communication: Omit<Communication, 'id' | 'createdAt'> = {
          type: 'note',
          direction: 'outbound',
          customerId,
          subject: 'Note',
          content,
          summary: content.substring(0, 100) + (content.length > 100 ? '...' : ''),
          fromAddress: user.id,
          toAddresses: [],
          timestamp: new Date().toISOString(),
          status: 'sent',
          attachments: [],
          sentiment: 'neutral',
          topics: [],
          tags: [],
          userId: user.id,
          userName: user.name || 'Unknown User',
          tenantId: tenantId!,
          syncStatus: 'pending',
        };

        const commId = `comm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await crmDb.communications.add({
          ...communication,
          id: commId,
          createdAt: communication.timestamp,
        });

        await loadCommunications();

        if (autoSync) {
          try {
            await apiClient.post('/crm/communications/note', communication);
            await crmDb.communications.update(commId, { syncStatus: 'synced' });
          } catch (err) {
            console.error('Failed to sync note:', err);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to add note');
        throw err;
      }
    },
    [customerId, user, tenantId, loadCommunications, autoSync, apiClient]
  );

  // Update preferences
  const updatePreferences = useCallback(
    async (methodId: string, preferences: ContactMethod['preferences']) => {
      await updateContactMethod(methodId, { preferences });
    },
    [updateContactMethod]
  );

  // Check do not contact
  const checkDoNotContact = useCallback(
    (type: 'email' | 'phone' | 'sms'): boolean => {
      const relevantMethods = contactMethods.filter((method) => {
        if (type === 'email') return method.type === 'email';
        if (type === 'phone') return ['phone', 'mobile'].includes(method.type);
        if (type === 'sms') return ['phone', 'mobile'].includes(method.type);
        return false;
      });

      return relevantMethods.some((method) => {
        if (type === 'email') return !method.preferences.allowMarketing;
        if (type === 'phone') return !method.preferences.allowCalls;
        if (type === 'sms') return !method.preferences.allowSMS;
        return false;
      });
    },
    [contactMethods]
  );

  // Validate email
  const validateEmail = useCallback(
    async (email: string): Promise<boolean> => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) return false;

      // In a full implementation, you might call an email validation service
      try {
        const response = await apiClient.post('/crm/validate/email', { email });
        return response.data?.isValid || false;
      } catch (err) {
        console.warn('Email validation service unavailable, using basic validation');
        return emailRegex.test(email);
      }
    },
    [apiClient]
  );

  // Validate phone
  const validatePhone = useCallback(
    async (phone: string): Promise<boolean> => {
      const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
      const cleanPhone = phone.replace(/[\s\-\(\)]/g, '');

      if (!phoneRegex.test(cleanPhone)) return false;

      try {
        const response = await apiClient.post('/crm/validate/phone', { phone: cleanPhone });
        return response.data?.isValid || false;
      } catch (err) {
        console.warn('Phone validation service unavailable, using basic validation');
        return phoneRegex.test(cleanPhone);
      }
    },
    [apiClient]
  );

  // Load activity history
  const refreshActivity = useCallback(async () => {
    if (!customerId || !tenantId) return;

    try {
      // Get recent communications
      const communications = await crmDb.getCommunicationsByCustomer(customerId, tenantId);

      const activity: ContactActivity[] = communications.map((comm) => ({
        type: 'communication' as const,
        timestamp: comm.timestamp,
        description: `${comm.type} - ${comm.subject}`,
        userId: comm.userId,
        userName: comm.userName,
      }));

      // Sort by timestamp descending
      activity.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

      setContactActivity(activity.slice(0, 50)); // Last 50 activities
    } catch (err) {
      console.error('Failed to refresh activity:', err);
    }
  }, [customerId, tenantId]);

  // Quick email
  const sendQuickEmail = useCallback(
    async (templateId: string, variables: Record<string, string> = {}) => {
      if (!customerId) throw new Error('No customer selected');

      const primaryEmailMethod = contactMethods.find((m) => m.type === 'email' && m.isPrimary);
      if (!primaryEmailMethod) throw new Error('No primary email found');

      try {
        const response = await apiClient.post('/crm/templates/render', {
          templateId,
          variables,
          customerId,
        });

        const { subject, content } = response.data;
        await sendEmail(primaryEmailMethod.value, subject, content);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to send quick email');
        throw err;
      }
    },
    [customerId, contactMethods, sendEmail, apiClient]
  );

  // Schedule follow up
  const scheduleFollowUp = useCallback(
    async (date: string, notes: string) => {
      if (!customerId || !user?.id) throw new Error('Missing required information');

      try {
        await apiClient.post('/crm/followups', {
          customerId,
          scheduledDate: date,
          notes,
          userId: user.id,
          tenantId,
        });

        // Add a note about the scheduled follow-up
        await addNote(`Follow-up scheduled for ${date}: ${notes}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to schedule follow-up');
        throw err;
      }
    },
    [customerId, user, tenantId, addNote, apiClient]
  );

  // Derived values
  const primaryEmail = contactMethods.find((m) => m.type === 'email' && m.isPrimary) || null;
  const primaryPhone =
    contactMethods.find((m) => ['phone', 'mobile'].includes(m.type) && m.isPrimary) || null;

  // Initialize
  useEffect(() => {
    loadContactMethods();
    loadCommunications();
    refreshActivity();
  }, [loadContactMethods, loadCommunications, refreshActivity]);

  return {
    // Contact Information
    contactMethods,
    primaryEmail,
    primaryPhone,
    loading,
    error,

    // Contact Management
    addContactMethod,
    updateContactMethod,
    removeContactMethod,
    setPrimaryContact,

    // Communication History
    recentCommunications,
    sendEmail,
    makeCall,
    sendSMS,
    addNote,

    // Contact Preferences
    updatePreferences,
    checkDoNotContact,

    // Contact Validation
    validateEmail,
    validatePhone,

    // Activity History
    contactActivity,
    refreshActivity,

    // Quick Actions
    sendQuickEmail,
    scheduleFollowUp,
  };
}
