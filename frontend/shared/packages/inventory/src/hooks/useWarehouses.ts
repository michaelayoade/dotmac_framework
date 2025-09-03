import { useState, useEffect } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  Warehouse,
  WarehouseCreate,
  WarehouseUpdate,
  WarehouseFilter,
  WarehouseType,
} from '../types';

export interface UseWarehousesResult {
  warehouses: Warehouse[];
  loading: boolean;
  error: string | null;
  totalWarehouses: number;
  currentPage: number;
  pageSize: number;
  createWarehouse: (data: WarehouseCreate) => Promise<Warehouse>;
  updateWarehouse: (id: string, data: WarehouseUpdate) => Promise<Warehouse>;
  deleteWarehouse: (id: string) => Promise<void>;
  getWarehouse: (id: string) => Promise<Warehouse | null>;
  listWarehouses: (filters?: WarehouseFilter, page?: number, size?: number) => Promise<void>;
  setupStandardWarehouses: () => Promise<Warehouse[]>;
  refreshWarehouses: () => Promise<void>;
}

export function useWarehouses(): UseWarehousesResult {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalWarehouses, setTotalWarehouses] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [currentFilters, setCurrentFilters] = useState<WarehouseFilter>({});

  const apiClient = useApiClient();

  const createWarehouse = async (data: WarehouseCreate): Promise<Warehouse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<Warehouse>('/api/inventory/warehouses', data);

      setWarehouses((prev) => [response, ...prev]);
      setTotalWarehouses((prev) => prev + 1);

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create warehouse';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updateWarehouse = async (id: string, data: WarehouseUpdate): Promise<Warehouse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.put<Warehouse>(`/api/inventory/warehouses/${id}`, data);

      setWarehouses((prev) =>
        prev.map((warehouse) => (warehouse.id === id ? response : warehouse))
      );

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update warehouse';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const deleteWarehouse = async (id: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.delete(`/api/inventory/warehouses/${id}`);

      setWarehouses((prev) => prev.filter((warehouse) => warehouse.id !== id));
      setTotalWarehouses((prev) => prev - 1);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete warehouse';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getWarehouse = async (id: string): Promise<Warehouse | null> => {
    try {
      setError(null);
      const response = await apiClient.get<Warehouse>(`/api/inventory/warehouses/${id}`);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get warehouse';
      setError(errorMessage);
      return null;
    }
  };

  const listWarehouses = async (
    filters: WarehouseFilter = {},
    page: number = 1,
    size: number = 50
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.search) params.append('search', filters.search);
      if (filters.warehouse_type) {
        const types = Array.isArray(filters.warehouse_type)
          ? filters.warehouse_type
          : [filters.warehouse_type];
        types.forEach((type) => params.append('warehouse_type', type));
      }
      if (filters.city) params.append('city', filters.city);
      if (filters.country) params.append('country', filters.country);
      if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString());

      params.append('page', page.toString());
      params.append('size', size.toString());

      const response = await apiClient.get<{
        items: Warehouse[];
        total: number;
        page: number;
        size: number;
      }>(`/api/inventory/warehouses?${params.toString()}`);

      setWarehouses(response.items);
      setTotalWarehouses(response.total);
      setCurrentPage(page);
      setPageSize(size);
      setCurrentFilters(filters);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to list warehouses';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const setupStandardWarehouses = async (): Promise<Warehouse[]> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<Warehouse[]>(
        '/api/inventory/warehouses/setup-standard'
      );

      // Add new warehouses to the list
      setWarehouses((prev) => [...response, ...prev]);
      setTotalWarehouses((prev) => prev + response.length);

      return response;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to setup standard warehouses';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const refreshWarehouses = async (): Promise<void> => {
    await listWarehouses(currentFilters, currentPage, pageSize);
  };

  // Load initial data
  useEffect(() => {
    listWarehouses();
  }, []);

  return {
    warehouses,
    loading,
    error,
    totalWarehouses,
    currentPage,
    pageSize,
    createWarehouse,
    updateWarehouse,
    deleteWarehouse,
    getWarehouse,
    listWarehouses,
    setupStandardWarehouses,
    refreshWarehouses,
  };
}
