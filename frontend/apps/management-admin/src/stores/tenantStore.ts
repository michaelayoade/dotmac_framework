/**
 * Tenant Management Store
 * Handles all tenant-related state and operations
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Types
export interface Tenant {
  id: string;
  name: string;
  domain: string;
  status: 'active' | 'inactive' | 'suspended' | 'pending';
  plan: string;
  created_at: string;
  updated_at: string;
  users_count: number;
  subscription?: {
    id: string;
    plan: string;
    status: string;
    next_billing_date: string;
    amount: number;
  };
  settings?: {
    theme: string;
    features: string[];
    limits: {
      users: number;
      storage: number;
    };
  };
}

export interface TenantFilters {
  status?: string;
  plan?: string;
  search?: string;
  dateRange?: {
    from: string;
    to: string;
  };
}

export interface TenantPagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export interface TenantStore {
  // State
  tenants: Tenant[];
  selectedTenant: Tenant | null;
  filters: TenantFilters;
  pagination: TenantPagination;
  loading: {
    list: boolean;
    create: boolean;
    update: boolean;
    delete: boolean;
    details: boolean;
  };
  error: string | null;
  
  // List Management
  setTenants: (tenants: Tenant[]) => void;
  addTenant: (tenant: Tenant) => void;
  updateTenant: (id: string, updates: Partial<Tenant>) => void;
  removeTenant: (id: string) => void;
  
  // Selection
  setSelectedTenant: (tenant: Tenant | null) => void;
  
  // Filtering & Pagination
  setFilters: (filters: Partial<TenantFilters>) => void;
  clearFilters: () => void;
  setPagination: (pagination: Partial<TenantPagination>) => void;
  
  // Loading States
  setLoading: (key: keyof TenantStore['loading'], loading: boolean) => void;
  
  // Error Handling
  setError: (error: string | null) => void;
  
  // Utility
  reset: () => void;
  getTenantById: (id: string) => Tenant | undefined;
  getFilteredTenants: () => Tenant[];
}

const initialState = {
  tenants: [],
  selectedTenant: null,
  filters: {},
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  },
  loading: {
    list: false,
    create: false,
    update: false,
    delete: false,
    details: false,
  },
  error: null,
};

export const useTenantStore = create<TenantStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // List Management
      setTenants: (tenants) =>
        set((state) => ({
          tenants,
        })),

      addTenant: (tenant) =>
        set((state) => ({
          tenants: [tenant, ...state.tenants],
        })),

      updateTenant: (id, updates) =>
        set((state) => ({
          tenants: state.tenants.map((tenant) =>
            tenant.id === id ? { ...tenant, ...updates } : tenant
          ),
          selectedTenant: state.selectedTenant?.id === id 
            ? { ...state.selectedTenant, ...updates }
            : state.selectedTenant,
        })),

      removeTenant: (id) =>
        set((state) => ({
          tenants: state.tenants.filter((tenant) => tenant.id !== id),
          selectedTenant: state.selectedTenant?.id === id ? null : state.selectedTenant,
        })),

      // Selection
      setSelectedTenant: (tenant) =>
        set(() => ({
          selectedTenant: tenant,
        })),

      // Filtering & Pagination
      setFilters: (filters) =>
        set((state) => ({
          filters: { ...state.filters, ...filters },
          pagination: { ...state.pagination, page: 1 }, // Reset to first page
        })),

      clearFilters: () =>
        set((state) => ({
          filters: {},
          pagination: { ...state.pagination, page: 1 },
        })),

      setPagination: (pagination) =>
        set((state) => ({
          pagination: { ...state.pagination, ...pagination },
        })),

      // Loading States
      setLoading: (key, loading) =>
        set((state) => ({
          loading: {
            ...state.loading,
            [key]: loading,
          },
        })),

      // Error Handling
      setError: (error) =>
        set(() => ({
          error,
        })),

      // Utility
      reset: () =>
        set(() => ({
          ...initialState,
        })),

      getTenantById: (id) => {
        const { tenants } = get();
        return tenants.find((tenant) => tenant.id === id);
      },

      getFilteredTenants: () => {
        const { tenants, filters } = get();
        
        return tenants.filter((tenant) => {
          // Status filter
          if (filters.status && tenant.status !== filters.status) {
            return false;
          }
          
          // Plan filter
          if (filters.plan && tenant.plan !== filters.plan) {
            return false;
          }
          
          // Search filter
          if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            const searchableText = `${tenant.name} ${tenant.domain}`.toLowerCase();
            if (!searchableText.includes(searchLower)) {
              return false;
            }
          }
          
          // Date range filter
          if (filters.dateRange) {
            const createdDate = new Date(tenant.created_at);
            const fromDate = new Date(filters.dateRange.from);
            const toDate = new Date(filters.dateRange.to);
            
            if (createdDate < fromDate || createdDate > toDate) {
              return false;
            }
          }
          
          return true;
        });
      },
    }),
    {
      name: 'tenant-store',
    }
  )
);

// Selectors
export const useTenants = () => useTenantStore((state) => state.tenants);
export const useSelectedTenant = () => useTenantStore((state) => state.selectedTenant);
export const useTenantFilters = () => useTenantStore((state) => state.filters);
export const useTenantPagination = () => useTenantStore((state) => state.pagination);
export const useTenantLoading = () => useTenantStore((state) => state.loading);
export const useTenantError = () => useTenantStore((state) => state.error);
export const useFilteredTenants = () => useTenantStore((state) => state.getFilteredTenants());