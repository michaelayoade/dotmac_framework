import { useState, useEffect, useCallback } from 'react';
import { useApiClient, useAuth } from '@dotmac/headless';
import { crmDb } from '../database';
import type {
  CustomerAccount,
  CustomerFilter,
  CustomerMetrics,
  Address,
  ContactMethod,
  CustomField
} from '../../types';

interface UseCustomersOptions {
  autoSync?: boolean;
  syncInterval?: number;
  filter?: CustomerFilter;
  pageSize?: number;
}

interface UseCustomersReturn {
  customers: CustomerAccount[];
  loading: boolean;
  error: string | null;
  metrics: CustomerMetrics | null;
  totalCount: number;
  currentPage: number;

  // CRUD Operations
  createCustomer: (customer: Omit<CustomerAccount, 'id' | 'createdAt' | 'updatedAt'>) => Promise<CustomerAccount>;
  updateCustomer: (id: string, updates: Partial<CustomerAccount>) => Promise<void>;
  deleteCustomer: (id: string) => Promise<void>;

  // Customer Management
  activateCustomer: (id: string) => Promise<void>;
  suspendCustomer: (id: string, reason?: string) => Promise<void>;
  cancelCustomer: (id: string, reason?: string) => Promise<void>;

  // Contact Management
  addAddress: (customerId: string, address: Omit<Address, 'id'>) => Promise<void>;
  updateAddress: (customerId: string, addressId: string, updates: Partial<Address>) => Promise<void>;
  removeAddress: (customerId: string, addressId: string) => Promise<void>;
  setPrimaryAddress: (customerId: string, addressId: string) => Promise<void>;

  addContactMethod: (customerId: string, method: Omit<ContactMethod, 'id'>) => Promise<void>;
  updateContactMethod: (customerId: string, methodId: string, updates: Partial<ContactMethod>) => Promise<void>;
  removeContactMethod: (customerId: string, methodId: string) => Promise<void>;
  setPrimaryContactMethod: (customerId: string, methodId: string) => Promise<void>;

  // Custom Fields
  addCustomField: (customerId: string, field: Omit<CustomField, 'id'>) => Promise<void>;
  updateCustomField: (customerId: string, fieldId: string, value: any) => Promise<void>;
  removeCustomField: (customerId: string, fieldId: string) => Promise<void>;

  // Search and Filter
  searchCustomers: (query: string) => Promise<CustomerAccount[]>;
  filterCustomers: (filter: CustomerFilter) => Promise<void>;
  clearFilter: () => Promise<void>;

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
  getCustomerHistory: (customerId: string) => Promise<CustomerAccount[]>;

  // Bulk Operations
  bulkUpdateCustomers: (customerIds: string[], updates: Partial<CustomerAccount>) => Promise<void>;
  bulkDeleteCustomers: (customerIds: string[]) => Promise<void>;
  exportCustomers: (format: 'csv' | 'json') => Promise<string>;
}

export function useCustomers(options: UseCustomersOptions = {}): UseCustomersReturn {
  const {
    autoSync = true,
    syncInterval = 30000,
    filter: initialFilter,
    pageSize = 20
  } = options;

  const { user, tenantId } = useAuth();
  const apiClient = useApiClient();

  const [customers, setCustomers] = useState<CustomerAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<CustomerMetrics | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [currentFilter, setCurrentFilter] = useState<CustomerFilter | undefined>(initialFilter);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error'>('idle');
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // Load customers from local database
  const loadLocalCustomers = useCallback(async () => {
    if (!tenantId) return;

    try {
      setLoading(true);
      setError(null);

      let customerList: CustomerAccount[];

      if (currentFilter) {
        customerList = await crmDb.filterCustomers(currentFilter, tenantId);
      } else {
        customerList = await crmDb.customers
          .where('tenantId')
          .equals(tenantId)
          .orderBy('displayName')
          .toArray();
      }

      setTotalCount(customerList.length);

      // Apply pagination
      const startIndex = (currentPage - 1) * pageSize;
      const endIndex = startIndex + pageSize;
      const paginatedCustomers = customerList.slice(startIndex, endIndex);

      setCustomers(paginatedCustomers);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load customers');
      console.error('Failed to load customers:', err);
    } finally {
      setLoading(false);
    }
  }, [tenantId, currentFilter, currentPage, pageSize]);

  // Sync with server
  const syncWithServer = useCallback(async () => {
    if (!tenantId || syncStatus === 'syncing') return;

    try {
      setSyncStatus('syncing');

      // Get pending sync items
      const { customers: pendingCustomers } = await crmDb.getPendingSyncItems();

      // Sync pending customers
      for (const customer of pendingCustomers) {
        try {
          if (customer.id.startsWith('temp_')) {
            // New customer - create on server
            const response = await apiClient.post('/crm/customers', customer);
            if (response.data?.customer) {
              // Update local record with server ID
              await crmDb.customers.delete(customer.id);
              await crmDb.customers.add({
                ...response.data.customer,
                syncStatus: 'synced'
              });
            }
          } else {
            // Update existing customer
            await apiClient.put(`/crm/customers/${customer.id}`, customer);
            await crmDb.customers.update(customer.id, { syncStatus: 'synced' });
          }
        } catch (apiError) {
          console.error(`Failed to sync customer ${customer.id}:`, apiError);
          await crmDb.customers.update(customer.id, { syncStatus: 'error' });
        }
      }

      // Fetch latest customers from server
      const response = await apiClient.get('/crm/customers', {
        params: { tenantId }
      });

      if (response.data?.customers) {
        // Update local database
        await crmDb.transaction('rw', crmDb.customers, async () => {
          // Only update customers that are synced (not pending local changes)
          const syncedCustomers = await crmDb.customers
            .where('[tenantId+syncStatus]')
            .equals([tenantId, 'synced'])
            .toArray();

          const syncedIds = syncedCustomers.map(c => c.id);
          await crmDb.customers.where('id').anyOf(syncedIds).delete();

          const serverCustomers = response.data.customers.map((c: CustomerAccount) => ({
            ...c,
            syncStatus: 'synced'
          }));

          await crmDb.customers.bulkAdd(serverCustomers, { allKeys: true });
        });

        await loadLocalCustomers();
      }

      setSyncStatus('idle');
      setLastSync(new Date());
      setError(null);

    } catch (err) {
      setSyncStatus('error');
      setError(err instanceof Error ? err.message : 'Sync failed');
      console.error('Sync failed:', err);
    }
  }, [tenantId, syncStatus, apiClient, loadLocalCustomers]);

  // Create customer
  const createCustomer = useCallback(async (customerData: Omit<CustomerAccount, 'id' | 'createdAt' | 'updatedAt'>): Promise<CustomerAccount> => {
    if (!tenantId) throw new Error('No tenant ID available');

    const customer: CustomerAccount = {
      ...customerData,
      id: `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      tenantId,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      syncStatus: 'pending'
    };

    try {
      await crmDb.customers.add(customer);
      await loadLocalCustomers();

      if (autoSync) {
        syncWithServer();
      }

      return customer;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create customer');
      throw err;
    }
  }, [tenantId, loadLocalCustomers, autoSync, syncWithServer]);

  // Update customer
  const updateCustomer = useCallback(async (id: string, updates: Partial<CustomerAccount>) => {
    try {
      const updatedData = {
        ...updates,
        updatedAt: new Date().toISOString(),
        syncStatus: 'pending' as const
      };

      await crmDb.customers.update(id, updatedData);
      await loadLocalCustomers();

      if (autoSync) {
        syncWithServer();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update customer');
      throw err;
    }
  }, [loadLocalCustomers, autoSync, syncWithServer]);

  // Delete customer
  const deleteCustomer = useCallback(async (id: string) => {
    try {
      await crmDb.customers.delete(id);
      await loadLocalCustomers();

      // If it was a server customer, mark for deletion sync
      if (!id.startsWith('temp_') && autoSync) {
        try {
          await apiClient.delete(`/crm/customers/${id}`);
        } catch (err) {
          console.error('Failed to delete customer on server:', err);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete customer');
      throw err;
    }
  }, [loadLocalCustomers, autoSync, apiClient]);

  // Customer status management
  const activateCustomer = useCallback(async (id: string) => {
    await updateCustomer(id, {
      status: 'active',
      updatedAt: new Date().toISOString()
    });
  }, [updateCustomer]);

  const suspendCustomer = useCallback(async (id: string, reason?: string) => {
    await updateCustomer(id, {
      status: 'suspended',
      updatedAt: new Date().toISOString()
      // Note: In a full implementation, you'd store the reason in a notes/history field
    });
  }, [updateCustomer]);

  const cancelCustomer = useCallback(async (id: string, reason?: string) => {
    await updateCustomer(id, {
      status: 'cancelled',
      updatedAt: new Date().toISOString()
      // Note: In a full implementation, you'd store the reason in a notes/history field
    });
  }, [updateCustomer]);

  // Address management
  const addAddress = useCallback(async (customerId: string, address: Omit<Address, 'id'>) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const newAddress: Address = {
      ...address,
      id: `addr_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };

    const updatedAddresses = [...customer.addresses, newAddress];
    await updateCustomer(customerId, { addresses: updatedAddresses });
  }, [updateCustomer]);

  const updateAddress = useCallback(async (customerId: string, addressId: string, updates: Partial<Address>) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedAddresses = customer.addresses.map(addr =>
      addr.id === addressId ? { ...addr, ...updates } : addr
    );

    await updateCustomer(customerId, { addresses: updatedAddresses });
  }, [updateCustomer]);

  const removeAddress = useCallback(async (customerId: string, addressId: string) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedAddresses = customer.addresses.filter(addr => addr.id !== addressId);
    await updateCustomer(customerId, { addresses: updatedAddresses });
  }, [updateCustomer]);

  const setPrimaryAddress = useCallback(async (customerId: string, addressId: string) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedAddresses = customer.addresses.map(addr => ({
      ...addr,
      isPrimary: addr.id === addressId
    }));

    await updateCustomer(customerId, { addresses: updatedAddresses });
  }, [updateCustomer]);

  // Contact method management
  const addContactMethod = useCallback(async (customerId: string, method: Omit<ContactMethod, 'id'>) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const newMethod: ContactMethod = {
      ...method,
      id: `contact_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };

    const updatedMethods = [...customer.contactMethods, newMethod];
    await updateCustomer(customerId, { contactMethods: updatedMethods });
  }, [updateCustomer]);

  const updateContactMethod = useCallback(async (customerId: string, methodId: string, updates: Partial<ContactMethod>) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedMethods = customer.contactMethods.map(method =>
      method.id === methodId ? { ...method, ...updates } : method
    );

    await updateCustomer(customerId, { contactMethods: updatedMethods });
  }, [updateCustomer]);

  const removeContactMethod = useCallback(async (customerId: string, methodId: string) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedMethods = customer.contactMethods.filter(method => method.id !== methodId);
    await updateCustomer(customerId, { contactMethods: updatedMethods });
  }, [updateCustomer]);

  const setPrimaryContactMethod = useCallback(async (customerId: string, methodId: string) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedMethods = customer.contactMethods.map(method => ({
      ...method,
      isPrimary: method.id === methodId
    }));

    await updateCustomer(customerId, { contactMethods: updatedMethods });
  }, [updateCustomer]);

  // Custom field management
  const addCustomField = useCallback(async (customerId: string, field: Omit<CustomField, 'id'>) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const newField: CustomField = {
      ...field,
      id: `field_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };

    const updatedFields = [...customer.customFields, newField];
    await updateCustomer(customerId, { customFields: updatedFields });
  }, [updateCustomer]);

  const updateCustomField = useCallback(async (customerId: string, fieldId: string, value: any) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedFields = customer.customFields.map(field =>
      field.id === fieldId ? { ...field, value } : field
    );

    await updateCustomer(customerId, { customFields: updatedFields });
  }, [updateCustomer]);

  const removeCustomField = useCallback(async (customerId: string, fieldId: string) => {
    const customer = await crmDb.customers.get(customerId);
    if (!customer) throw new Error('Customer not found');

    const updatedFields = customer.customFields.filter(field => field.id !== fieldId);
    await updateCustomer(customerId, { customFields: updatedFields });
  }, [updateCustomer]);

  // Search and filter
  const searchCustomers = useCallback(async (query: string): Promise<CustomerAccount[]> => {
    if (!tenantId) return [];
    return crmDb.searchCustomers(query, tenantId);
  }, [tenantId]);

  const filterCustomers = useCallback(async (filter: CustomerFilter) => {
    setCurrentFilter(filter);
    setCurrentPage(1); // Reset to first page when filtering
    await loadLocalCustomers();
  }, [loadLocalCustomers]);

  const clearFilter = useCallback(async () => {
    setCurrentFilter(undefined);
    setCurrentPage(1);
    await loadLocalCustomers();
  }, [loadLocalCustomers]);

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

  // Analytics
  const refreshMetrics = useCallback(async () => {
    if (!tenantId) return;

    try {
      const dbMetrics = await crmDb.getCustomerMetrics(tenantId);

      const metrics: CustomerMetrics = {
        totalCustomers: dbMetrics.total,
        activeCustomers: dbMetrics.active,
        newCustomers: dbMetrics.new,
        churnedCustomers: dbMetrics.churned,
        churnRate: dbMetrics.total > 0 ? (dbMetrics.churned / dbMetrics.total) * 100 : 0,
        lifetimeValue: dbMetrics.averageRevenue * 24, // Rough estimate: 2 years
        averageRevenue: dbMetrics.averageRevenue,
        customersBySegment: dbMetrics.bySegment as any,
        customersByStatus: dbMetrics.byStatus as any
      };

      setMetrics(metrics);
    } catch (err) {
      console.error('Failed to refresh metrics:', err);
    }
  }, [tenantId]);

  const getCustomerHistory = useCallback(async (customerId: string): Promise<CustomerAccount[]> => {
    // In a full implementation, this would fetch historical versions from the server
    const customer = await crmDb.customers.get(customerId);
    return customer ? [customer] : [];
  }, []);

  // Bulk operations
  const bulkUpdateCustomers = useCallback(async (customerIds: string[], updates: Partial<CustomerAccount>) => {
    try {
      const updatePromises = customerIds.map(id => updateCustomer(id, updates));
      await Promise.all(updatePromises);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to bulk update customers');
      throw err;
    }
  }, [updateCustomer]);

  const bulkDeleteCustomers = useCallback(async (customerIds: string[]) => {
    try {
      const deletePromises = customerIds.map(id => deleteCustomer(id));
      await Promise.all(deletePromises);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to bulk delete customers');
      throw err;
    }
  }, [deleteCustomer]);

  const exportCustomers = useCallback(async (format: 'csv' | 'json'): Promise<string> => {
    if (!tenantId) throw new Error('No tenant ID available');

    const allCustomers = await crmDb.customers
      .where('tenantId')
      .equals(tenantId)
      .toArray();

    if (format === 'json') {
      return JSON.stringify(allCustomers, null, 2);
    } else {
      // CSV format
      if (allCustomers.length === 0) return '';

      const headers = [
        'Account Number', 'Name', 'Company', 'Status', 'Type', 'Segment',
        'Email', 'Phone', 'Monthly Revenue', 'Created Date'
      ];

      const rows = allCustomers.map(customer => [
        customer.accountNumber,
        customer.displayName,
        customer.companyName || '',
        customer.status,
        customer.type,
        customer.segment,
        customer.contactMethods.find(m => m.type === 'email')?.value || '',
        customer.contactMethods.find(m => m.type === 'phone')?.value || '',
        customer.monthlyRevenue.toString(),
        customer.createdAt
      ]);

      return [headers, ...rows].map(row =>
        row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')
      ).join('\n');
    }
  }, [tenantId]);

  // Initialize
  useEffect(() => {
    loadLocalCustomers();
    refreshMetrics();
  }, [loadLocalCustomers, refreshMetrics]);

  // Auto-sync interval
  useEffect(() => {
    if (!autoSync) return;

    const interval = setInterval(syncWithServer, syncInterval);
    return () => clearInterval(interval);
  }, [autoSync, syncInterval, syncWithServer]);

  // Reload when page changes
  useEffect(() => {
    loadLocalCustomers();
  }, [currentPage, loadLocalCustomers]);

  // Initial sync
  useEffect(() => {
    if (autoSync && tenantId) {
      syncWithServer();
    }
  }, [autoSync, tenantId, syncWithServer]);

  return {
    customers,
    loading,
    error,
    metrics,
    totalCount,
    currentPage,

    // CRUD Operations
    createCustomer,
    updateCustomer,
    deleteCustomer,

    // Customer Management
    activateCustomer,
    suspendCustomer,
    cancelCustomer,

    // Contact Management
    addAddress,
    updateAddress,
    removeAddress,
    setPrimaryAddress,
    addContactMethod,
    updateContactMethod,
    removeContactMethod,
    setPrimaryContactMethod,

    // Custom Fields
    addCustomField,
    updateCustomField,
    removeCustomField,

    // Search and Filter
    searchCustomers,
    filterCustomers,
    clearFilter,

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
    getCustomerHistory,

    // Bulk Operations
    bulkUpdateCustomers,
    bulkDeleteCustomers,
    exportCustomers
  };
}
