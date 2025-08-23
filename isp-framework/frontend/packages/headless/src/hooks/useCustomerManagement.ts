/**
 * Customer Management Hook
 * Complete ISP customer lifecycle management
 */

import { useCallback, useState, useEffect } from 'react';
import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useStandardErrorHandler } from './useStandardErrorHandler';
import { useRealTimeSync } from './useRealTimeSync';
import { DateTimeUtils } from '../utils/dateTimeUtils';

export interface CustomerContact {
  id: string;
  type: 'primary' | 'billing' | 'technical' | 'emergency';
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  title?: string;
  department?: string;
  isPrimary: boolean;
  canReceiveBilling: boolean;
  canReceiveTechnical: boolean;
  canReceiveMarketing: boolean;
}

export interface CustomerAddress {
  id: string;
  type: 'service' | 'billing' | 'installation';
  street: string;
  street2?: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
  latitude?: number;
  longitude?: number;
  installationNotes?: string;
  accessInstructions?: string;
  isPrimary: boolean;
}

export interface CustomerService {
  id: string;
  customerId: string;
  serviceType: 'fiber' | 'cable' | 'dsl' | 'wireless' | 'dedicated';
  packageId: string;
  packageName: string;
  status: 'pending' | 'active' | 'suspended' | 'cancelled' | 'installing';
  bandwidth: {
    download: number;
    upload: number;
    unit: 'Mbps' | 'Gbps';
  };
  monthlyRate: number;
  installationFee?: number;
  activationDate?: string;
  suspensionDate?: string;
  cancellationDate?: string;
  serviceAddress: CustomerAddress;
  equipment: Array<{
    id: string;
    type: string;
    model: string;
    serialNumber: string;
    macAddress?: string;
    ipAddress?: string;
    installDate: string;
    status: 'active' | 'inactive' | 'faulty';
  }>;
  notes?: string;
}

export interface Customer {
  id: string;
  portalId: string;
  accountNumber: string;
  type: 'residential' | 'business' | 'enterprise';
  status: 'active' | 'suspended' | 'cancelled' | 'pending';
  creditScore?: number;
  creditLimit?: number;
  
  // Company info (for business customers)
  companyName?: string;
  taxId?: string;
  businessType?: string;
  
  // Contacts
  contacts: CustomerContact[];
  
  // Addresses
  addresses: CustomerAddress[];
  
  // Services
  services: CustomerService[];
  
  // Billing info
  billing: {
    preferredMethod: 'email' | 'mail' | 'portal';
    billingCycle: 'monthly' | 'quarterly' | 'annually';
    dueDay: number; // 1-28
    autoPayEnabled: boolean;
    paperlessBilling: boolean;
    currentBalance: number;
    creditBalance: number;
    lastPaymentDate?: string;
    lastPaymentAmount?: number;
  };
  
  // Metadata
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  assignedAccount?: string; // Account manager
  tags: string[];
  notes?: string;
  
  // Computed fields
  totalMonthlyRecurring?: number;
  nextBillDate?: string;
  daysPastDue?: number;
}

export interface CustomerFilters {
  status?: string[];
  type?: string[];
  serviceType?: string[];
  assignedAccount?: string;
  tags?: string[];
  search?: string;
  creditScoreMin?: number;
  creditScoreMax?: number;
  balanceMin?: number;
  balanceMax?: number;
  createdAfter?: string;
  createdBefore?: string;
}

export interface CustomerCreationData {
  type: Customer['type'];
  companyName?: string;
  taxId?: string;
  
  // Primary contact
  primaryContact: Omit<CustomerContact, 'id' | 'isPrimary' | 'type'>;
  
  // Service address
  serviceAddress: Omit<CustomerAddress, 'id' | 'isPrimary' | 'type'>;
  
  // Billing preferences
  billingPreferences: {
    method: Customer['billing']['preferredMethod'];
    cycle: Customer['billing']['billingCycle'];
    dueDay: number;
    autoPayEnabled: boolean;
    paperlessBilling: boolean;
  };
  
  // Initial service (optional)
  initialService?: {
    serviceType: CustomerService['serviceType'];
    packageId: string;
    preferredInstallationDate?: string;
    specialInstructions?: string;
  };
  
  // Metadata
  tags?: string[];
  notes?: string;
  assignedAccount?: string;
}

export function useCustomerManagement() {
  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { handleError, withErrorHandling } = useStandardErrorHandler({
    context: 'Customer Management',
    enableRetry: true,
    maxRetries: 2
  });
  const { emit, subscribe } = useRealTimeSync();

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [filters, setFilters] = useState<CustomerFilters>({});

  // Load customers with pagination and filtering
  const loadCustomers = useCallback(async (
    page = 1,
    limit = 50,
    customerFilters: CustomerFilters = {}
  ): Promise<void> => {
    if (!currentTenant?.tenant?.id) return;

    return withErrorHandling(async () => {
      setIsLoading(true);
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/customers', {
        method: 'GET',
        params: {
          page,
          limit,
          tenantId: currentTenant.tenant.id,
          ...customerFilters
        }
      });

      const { customers: customerData, total, pagination } = response.data;
      
      // Enhance customers with computed fields
      const enhancedCustomers = customerData.map((customer: Customer) => ({
        ...customer,
        totalMonthlyRecurring: customer.services
          .filter(s => s.status === 'active')
          .reduce((sum, s) => sum + s.monthlyRate, 0),
        nextBillDate: calculateNextBillDate(customer),
        daysPastDue: calculateDaysPastDue(customer)
      }));

      if (page === 1) {
        setCustomers(enhancedCustomers);
      } else {
        setCustomers(prev => [...prev, ...enhancedCustomers]);
      }
      
      setTotalCount(total);
      setFilters(customerFilters);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Create new customer
  const createCustomer = useCallback(async (customerData: CustomerCreationData): Promise<string | null> => {
    if (!currentTenant?.tenant?.id || !user?.id) return null;

    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/customers', {
        method: 'POST',
        body: {
          ...customerData,
          tenantId: currentTenant.tenant.id,
          createdBy: user.id
        }
      });

      const newCustomer = response.data.customer;
      
      // Add to local state
      setCustomers(prev => [newCustomer, ...prev]);
      setTotalCount(prev => prev + 1);
      
      // Emit real-time event
      emit('customer:created', { customerId: newCustomer.id, tenantId: currentTenant.tenant.id });
      
      return newCustomer.id;
    });
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Get customer details
  const getCustomer = useCallback(async (customerId: string): Promise<Customer | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request(`/api/v1/customers/${customerId}`);
      
      const customer = {
        ...response.data.customer,
        totalMonthlyRecurring: response.data.customer.services
          .filter((s: CustomerService) => s.status === 'active')
          .reduce((sum: number, s: CustomerService) => sum + s.monthlyRate, 0),
        nextBillDate: calculateNextBillDate(response.data.customer),
        daysPastDue: calculateDaysPastDue(response.data.customer)
      };
      
      setSelectedCustomer(customer);
      return customer;
    });
  }, [withErrorHandling]);

  // Update customer
  const updateCustomer = useCallback(async (
    customerId: string,
    updates: Partial<Customer>
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/customers/${customerId}`, {
        method: 'PUT',
        body: {
          ...updates,
          updatedBy: user?.id
        }
      });

      // Update local state
      setCustomers(prev => prev.map(customer =>
        customer.id === customerId
          ? { ...customer, ...updates, updatedAt: new Date().toISOString() }
          : customer
      ));

      if (selectedCustomer?.id === customerId) {
        setSelectedCustomer(prev => prev ? { ...prev, ...updates } : null);
      }

      emit('customer:updated', { customerId, updates });
      return true;
    }) || false;
  }, [user?.id, selectedCustomer?.id, withErrorHandling, emit]);

  // Suspend customer
  const suspendCustomer = useCallback(async (
    customerId: string,
    reason: string,
    suspendServices = true
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/customers/${customerId}/suspend`, {
        method: 'POST',
        body: {
          reason,
          suspendServices,
          suspendedBy: user?.id
        }
      });

      // Update local state
      const suspensionDate = new Date().toISOString();
      setCustomers(prev => prev.map(customer =>
        customer.id === customerId
          ? { 
              ...customer, 
              status: 'suspended',
              services: suspendServices ? customer.services.map(service => ({
                ...service,
                status: service.status === 'active' ? 'suspended' : service.status,
                suspensionDate: service.status === 'active' ? suspensionDate : service.suspensionDate
              })) : customer.services
            }
          : customer
      ));

      emit('customer:suspended', { customerId, reason, suspendServices });
      return true;
    }) || false;
  }, [user?.id, withErrorHandling, emit]);

  // Restore customer
  const restoreCustomer = useCallback(async (customerId: string): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/customers/${customerId}/restore`, {
        method: 'POST',
        body: {
          restoredBy: user?.id
        }
      });

      // Update local state
      setCustomers(prev => prev.map(customer =>
        customer.id === customerId
          ? { 
              ...customer, 
              status: 'active',
              services: customer.services.map(service => ({
                ...service,
                status: service.status === 'suspended' ? 'active' : service.status,
                suspensionDate: service.status === 'suspended' ? undefined : service.suspensionDate
              }))
            }
          : customer
      ));

      emit('customer:restored', { customerId });
      return true;
    }) || false;
  }, [user?.id, withErrorHandling, emit]);

  // Add service to customer
  const addService = useCallback(async (
    customerId: string,
    serviceData: {
      serviceType: CustomerService['serviceType'];
      packageId: string;
      serviceAddressId: string;
      preferredInstallationDate?: string;
      specialInstructions?: string;
    }
  ): Promise<string | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request(`/api/v1/customers/${customerId}/services`, {
        method: 'POST',
        body: {
          ...serviceData,
          requestedBy: user?.id
        }
      });

      const newService = response.data.service;
      
      // Update local state
      setCustomers(prev => prev.map(customer =>
        customer.id === customerId
          ? { ...customer, services: [...customer.services, newService] }
          : customer
      ));

      emit('service:requested', { customerId, serviceId: newService.id });
      return newService.id;
    });
  }, [user?.id, withErrorHandling, emit]);

  // Customer search with advanced filters
  const searchCustomers = useCallback(async (
    searchTerm: string,
    searchFilters: CustomerFilters = {}
  ): Promise<Customer[]> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/customers/search', {
        method: 'POST',
        body: {
          query: searchTerm,
          filters: searchFilters,
          tenantId: currentTenant?.tenant?.id,
          limit: 100
        }
      });

      return response.data.customers || [];
    }) || [];
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Get customer analytics
  const getCustomerAnalytics = useCallback(async (customerId: string) => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request(`/api/v1/customers/${customerId}/analytics`);
      
      return response.data.analytics;
    });
  }, [withErrorHandling]);

  // Real-time customer updates
  useEffect(() => {
    return subscribe('customer:*', (event) => {
      switch (event.type) {
        case 'customer:updated':
          if (event.data && typeof event.data === 'object') {
            const { customerId, updates } = event.data as any;
            setCustomers(prev => prev.map(customer =>
              customer.id === customerId ? { ...customer, ...updates } : customer
            ));
          }
          break;
        case 'customer:service_updated':
          if (event.data && typeof event.data === 'object') {
            const { customerId, serviceId, updates } = event.data as any;
            setCustomers(prev => prev.map(customer =>
              customer.id === customerId
                ? {
                    ...customer,
                    services: customer.services.map(service =>
                      service.id === serviceId ? { ...service, ...updates } : service
                    )
                  }
                : customer
            ));
          }
          break;
      }
    });
  }, [subscribe]);

  // Load initial customers
  useEffect(() => {
    if (currentTenant?.tenant?.id) {
      loadCustomers();
    }
  }, [currentTenant?.tenant?.id, loadCustomers]);

  return {
    // State
    customers,
    selectedCustomer,
    isLoading,
    totalCount,
    filters,

    // Actions
    loadCustomers,
    createCustomer,
    getCustomer,
    updateCustomer,
    suspendCustomer,
    restoreCustomer,
    addService,
    searchCustomers,
    getCustomerAnalytics,
    setSelectedCustomer,
    
    // Computed values
    activeCustomers: customers.filter(c => c.status === 'active'),
    suspendedCustomers: customers.filter(c => c.status === 'suspended'),
    businessCustomers: customers.filter(c => c.type === 'business' || c.type === 'enterprise'),
    residentialCustomers: customers.filter(c => c.type === 'residential'),
    
    // Utilities
    refreshCustomers: () => loadCustomers(1, 50, filters),
  };
}

// Helper functions
function calculateNextBillDate(customer: Customer): string | undefined {
  if (!customer.billing) return undefined;
  
  const { billingCycle, dueDay } = customer.billing;
  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();
  
  let nextBillDate = new Date(currentYear, currentMonth, dueDay);
  
  // If due day has passed this month, move to next billing cycle
  if (nextBillDate <= now) {
    switch (billingCycle) {
      case 'monthly':
        nextBillDate.setMonth(nextBillDate.getMonth() + 1);
        break;
      case 'quarterly':
        nextBillDate.setMonth(nextBillDate.getMonth() + 3);
        break;
      case 'annually':
        nextBillDate.setFullYear(nextBillDate.getFullYear() + 1);
        break;
    }
  }
  
  return DateTimeUtils.format(nextBillDate, 'YYYY-MM-DD');
}

function calculateDaysPastDue(customer: Customer): number | undefined {
  if (!customer.billing || customer.billing.currentBalance <= 0) return undefined;
  
  const nextBillDate = calculateNextBillDate(customer);
  if (!nextBillDate) return undefined;
  
  const dueDate = DateTimeUtils.parseDate(nextBillDate);
  if (!dueDate) return undefined;
  
  const now = new Date();
  const diffTime = now.getTime() - dueDate.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  return diffDays > 0 ? diffDays : undefined;
}

export type { Customer, CustomerService, CustomerContact, CustomerAddress, CustomerFilters, CustomerCreationData };