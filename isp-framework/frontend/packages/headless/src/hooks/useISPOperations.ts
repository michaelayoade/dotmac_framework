/**
 * ISP-specific business operations hooks
 * Provides specialized functionality for telecommunications operations
 */

import { useCallback, useState, useEffect } from 'react';
import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useStandardErrorHandler } from './useStandardErrorHandler';
import { useRealTimeSync } from './useRealTimeSync';

// Service provisioning types
export interface ServiceProvisionRequest {
  customerId: string;
  serviceType: 'fiber' | 'cable' | 'dsl' | 'wireless' | 'dedicated';
  packageId: string;
  installationAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    unit?: string;
  };
  bandwidth: {
    download: number; // Mbps
    upload: number; // Mbps
  };
  preferredInstallationDate?: string;
  specialInstructions?: string;
}

export interface ServiceProvisionStatus {
  requestId: string;
  status: 'pending' | 'approved' | 'scheduled' | 'installing' | 'active' | 'failed' | 'cancelled';
  progress: number;
  estimatedCompletionDate?: string;
  assignedTechnician?: {
    id: string;
    name: string;
    phone: string;
  };
  networkDetails?: {
    ipAddress?: string;
    vlan?: number;
    port?: string;
    equipment?: Array<{
      type: string;
      model: string;
      serialNumber: string;
    }>;
  };
}

// Network monitoring types
export interface NetworkDevice {
  id: string;
  name: string;
  type: 'router' | 'switch' | 'modem' | 'access_point' | 'olt' | 'onu';
  ipAddress: string;
  location: string;
  status: 'online' | 'offline' | 'warning' | 'critical';
  lastSeen: string;
  uptime: number;
  metrics: {
    cpuUsage: number;
    memoryUsage: number;
    temperature?: number;
    powerLevel?: number;
    rxPower?: number;
    txPower?: number;
  };
  ports?: Array<{
    id: string;
    name: string;
    status: 'up' | 'down' | 'disabled';
    utilization: number;
    errors: number;
  }>;
}

export interface NetworkOutage {
  id: string;
  title: string;
  description: string;
  severity: 'minor' | 'major' | 'critical';
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved';
  startTime: string;
  estimatedResolution?: string;
  affectedServices: string[];
  affectedAreas: string[];
  customerCount: number;
  updates: Array<{
    timestamp: string;
    message: string;
    author: string;
  }>;
}

// Customer support types
export interface SupportTicket {
  id: string;
  customerId: string;
  subject: string;
  description: string;
  category: 'technical' | 'billing' | 'service' | 'sales' | 'complaint';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  status: 'open' | 'pending' | 'resolved' | 'closed';
  assignedTo?: string;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  attachments?: Array<{
    id: string;
    filename: string;
    url: string;
    size: number;
  }>;
}

export function useServiceProvisioning() {
  const { currentTenant } = useTenantStore();
  const { handleError } = useStandardErrorHandler({ context: 'Service Provisioning' });
  const { emit, subscribe } = useRealTimeSync();
  
  const [provisioningStatus, setProvisioningStatus] = useState<Map<string, ServiceProvisionStatus>>(new Map());
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Submit service provision request
  const provisionService = useCallback(async (request: ServiceProvisionRequest): Promise<string | null> => {
    if (!currentTenant?.tenant?.id) {
      handleError(new Error('No tenant context available'));
      return null;
    }

    setIsSubmitting(true);
    try {
      const apiClient = getApiClient();
      const response = await apiClient.request('/api/v1/services/provision', {
        method: 'POST',
        body: {
          ...request,
          tenantId: currentTenant.tenant.id
        }
      });

      const requestId = response.data.requestId;
      
      // Initialize status tracking
      setProvisioningStatus(prev => new Map(prev).set(requestId, {
        requestId,
        status: 'pending',
        progress: 0
      }));

      // Emit real-time event
      emit('service:provision_requested', { requestId, customerId: request.customerId });

      return requestId;
    } catch (error) {
      handleError(error);
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, [currentTenant?.tenant?.id, handleError, emit]);

  // Get provisioning status
  const getProvisioningStatus = useCallback(async (requestId: string): Promise<ServiceProvisionStatus | null> => {
    try {
      const apiClient = getApiClient();
      const response = await apiClient.request(`/api/v1/services/provision/${requestId}/status`);
      
      const status = response.data;
      setProvisioningStatus(prev => new Map(prev).set(requestId, status));
      
      return status;
    } catch (error) {
      handleError(error);
      return null;
    }
  }, [handleError]);

  // Real-time provisioning updates
  useEffect(() => {
    return subscribe('service:*', (event) => {
      if (event.type === 'service:provision_updated' && event.data) {
        const { requestId, status } = event.data as any;
        if (requestId && status) {
          setProvisioningStatus(prev => new Map(prev).set(requestId, status));
        }
      }
    });
  }, [subscribe]);

  return {
    provisionService,
    getProvisioningStatus,
    provisioningStatus,
    isSubmitting
  };
}

export function useNetworkMonitoring() {
  const { currentTenant } = useTenantStore();
  const { handleError } = useStandardErrorHandler({ context: 'Network Monitoring' });
  const { subscribe } = useRealTimeSync();
  
  const [devices, setDevices] = useState<NetworkDevice[]>([]);
  const [outages, setOutages] = useState<NetworkOutage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Load network devices
  const loadDevices = useCallback(async () => {
    if (!currentTenant?.tenant?.id) return;

    setIsLoading(true);
    try {
      const apiClient = getApiClient();
      const response = await apiClient.request('/api/v1/network/devices');
      setDevices(response.data.devices || []);
    } catch (error) {
      handleError(error);
    } finally {
      setIsLoading(false);
    }
  }, [currentTenant?.tenant?.id, handleError]);

  // Load network outages
  const loadOutages = useCallback(async () => {
    if (!currentTenant?.tenant?.id) return;

    try {
      const apiClient = getApiClient();
      const response = await apiClient.request('/api/v1/network/outages');
      setOutages(response.data.outages || []);
    } catch (error) {
      handleError(error);
    }
  }, [currentTenant?.tenant?.id, handleError]);

  // Get device details
  const getDeviceDetails = useCallback(async (deviceId: string): Promise<NetworkDevice | null> => {
    try {
      const apiClient = getApiClient();
      const response = await apiClient.request(`/api/v1/network/devices/${deviceId}`);
      return response.data.device;
    } catch (error) {
      handleError(error);
      return null;
    }
  }, [handleError]);

  // Real-time device updates
  useEffect(() => {
    return subscribe('network:*', (event) => {
      if (event.type === 'network:device:status') {
        const deviceUpdate = event.data as any;
        setDevices(prev => prev.map(device => 
          device.id === deviceUpdate.deviceId 
            ? { ...device, ...deviceUpdate.updates }
            : device
        ));
      } else if (event.type === 'network:outage') {
        loadOutages();
      }
    });
  }, [subscribe, loadOutages]);

  // Load initial data
  useEffect(() => {
    loadDevices();
    loadOutages();
  }, [loadDevices, loadOutages]);

  return {
    devices,
    outages,
    isLoading,
    loadDevices,
    loadOutages,
    getDeviceDetails,
    // Computed values
    onlineDevices: devices.filter(d => d.status === 'online'),
    offlineDevices: devices.filter(d => d.status === 'offline'),
    criticalDevices: devices.filter(d => d.status === 'critical'),
    activeOutages: outages.filter(o => o.status !== 'resolved')
  };
}

export function useSupportTickets() {
  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { handleError } = useStandardErrorHandler({ context: 'Support Tickets' });
  const { emit, subscribe } = useRealTimeSync();
  
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Load support tickets
  const loadTickets = useCallback(async (filters?: {
    status?: string;
    priority?: string;
    category?: string;
    assignedTo?: string;
  }) => {
    if (!currentTenant?.tenant?.id) return;

    setIsLoading(true);
    try {
      const apiClient = getApiClient();
      const queryParams = new URLSearchParams(filters || {}).toString();
      const response = await apiClient.request(`/api/v1/support/tickets?${queryParams}`);
      setTickets(response.data.tickets || []);
    } catch (error) {
      handleError(error);
    } finally {
      setIsLoading(false);
    }
  }, [currentTenant?.tenant?.id, handleError]);

  // Create support ticket
  const createTicket = useCallback(async (ticketData: Omit<SupportTicket, 'id' | 'createdAt' | 'updatedAt'>): Promise<string | null> => {
    if (!user || !currentTenant?.tenant?.id) return null;

    try {
      const apiClient = getApiClient();
      const response = await apiClient.request('/api/v1/support/tickets', {
        method: 'POST',
        body: {
          ...ticketData,
          tenantId: currentTenant.tenant.id
        }
      });

      const ticketId = response.data.ticketId;
      emit('support:ticket_created', { ticketId, customerId: ticketData.customerId });
      
      // Reload tickets to show the new one
      loadTickets();
      
      return ticketId;
    } catch (error) {
      handleError(error);
      return null;
    }
  }, [user, currentTenant?.tenant?.id, handleError, emit, loadTickets]);

  // Update ticket status
  const updateTicketStatus = useCallback(async (ticketId: string, status: SupportTicket['status'], comment?: string): Promise<boolean> => {
    try {
      const apiClient = getApiClient();
      await apiClient.request(`/api/v1/support/tickets/${ticketId}/status`, {
        method: 'PUT',
        body: { status, comment }
      });

      // Update local state
      setTickets(prev => prev.map(ticket =>
        ticket.id === ticketId
          ? { ...ticket, status, updatedAt: new Date().toISOString() }
          : ticket
      ));

      emit('support:ticket_updated', { ticketId, status });
      return true;
    } catch (error) {
      handleError(error);
      return false;
    }
  }, [handleError, emit]);

  // Real-time ticket updates
  useEffect(() => {
    return subscribe('support:*', (event) => {
      if (event.type === 'support:ticket_created' || event.type === 'support:ticket_updated') {
        loadTickets();
      }
    });
  }, [subscribe, loadTickets]);

  // Load initial tickets
  useEffect(() => {
    loadTickets();
  }, [loadTickets]);

  return {
    tickets,
    isLoading,
    loadTickets,
    createTicket,
    updateTicketStatus,
    // Computed values
    openTickets: tickets.filter(t => t.status === 'open'),
    urgentTickets: tickets.filter(t => t.priority === 'urgent'),
    myTickets: tickets.filter(t => t.assignedTo === user?.id),
    unassignedTickets: tickets.filter(t => !t.assignedTo)
  };
}

// Billing-specific ISP operations
export function useBillingOperations() {
  const { currentTenant } = useTenantStore();
  const { handleError } = useStandardErrorHandler({ context: 'Billing Operations' });
  
  // Generate usage-based invoice
  const generateUsageInvoice = useCallback(async (customerId: string, period: { start: string; end: string }) => {
    try {
      const apiClient = getApiClient();
      const response = await apiClient.request('/api/v1/billing/generate-usage-invoice', {
        method: 'POST',
        body: {
          customerId,
          period,
          tenantId: currentTenant?.tenant?.id
        }
      });
      return response.data.invoiceId;
    } catch (error) {
      handleError(error);
      return null;
    }
  }, [currentTenant?.tenant?.id, handleError]);

  // Process service suspension
  const suspendService = useCallback(async (customerId: string, reason: string) => {
    try {
      const apiClient = getApiClient();
      await apiClient.request(`/api/v1/services/customers/${customerId}/suspend`, {
        method: 'POST',
        body: { reason }
      });
      return true;
    } catch (error) {
      handleError(error);
      return false;
    }
  }, [handleError]);

  // Restore suspended service
  const restoreService = useCallback(async (customerId: string) => {
    try {
      const apiClient = getApiClient();
      await apiClient.request(`/api/v1/services/customers/${customerId}/restore`, {
        method: 'POST'
      });
      return true;
    } catch (error) {
      handleError(error);
      return false;
    }
  }, [handleError]);

  return {
    generateUsageInvoice,
    suspendService,
    restoreService
  };
}