import { useState, useEffect } from 'react';
import { useApiClient } from '@dotmac/headless';
import type { StockMovement, StockMovementCreate, MovementFilter, MovementType } from '../types';

export interface UseMovementsResult {
  movements: StockMovement[];
  loading: boolean;
  error: string | null;
  totalMovements: number;
  currentPage: number;
  pageSize: number;
  createMovement: (data: StockMovementCreate) => Promise<StockMovement>;
  getMovement: (id: string) => Promise<StockMovement | null>;
  listMovements: (filters?: MovementFilter, page?: number, size?: number) => Promise<void>;
  getMovementsByItem: (itemId: string, limit?: number) => Promise<StockMovement[]>;
  getMovementsByWarehouse: (warehouseId: string, limit?: number) => Promise<StockMovement[]>;
  getRecentMovements: (limit?: number) => Promise<StockMovement[]>;
  refreshMovements: () => Promise<void>;
}

export function useMovements(): UseMovementsResult {
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalMovements, setTotalMovements] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [currentFilters, setCurrentFilters] = useState<MovementFilter>({});

  const apiClient = useApiClient();

  const createMovement = async (data: StockMovementCreate): Promise<StockMovement> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<StockMovement>('/api/inventory/movements', data);

      setMovements((prev) => [response, ...prev]);
      setTotalMovements((prev) => prev + 1);

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create movement';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getMovement = async (id: string): Promise<StockMovement | null> => {
    try {
      setError(null);
      const response = await apiClient.get<StockMovement>(`/api/inventory/movements/${id}`);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get movement';
      setError(errorMessage);
      return null;
    }
  };

  const listMovements = async (
    filters: MovementFilter = {},
    page: number = 1,
    size: number = 50
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.item_id) params.append('item_id', filters.item_id);
      if (filters.warehouse_id) params.append('warehouse_id', filters.warehouse_id);
      if (filters.movement_type) {
        const types = Array.isArray(filters.movement_type)
          ? filters.movement_type
          : [filters.movement_type];
        types.forEach((type) => params.append('movement_type', type));
      }
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.reference_number) params.append('reference_number', filters.reference_number);
      if (filters.purchase_order_id) params.append('purchase_order_id', filters.purchase_order_id);
      if (filters.work_order_id) params.append('work_order_id', filters.work_order_id);
      if (filters.project_id) params.append('project_id', filters.project_id);

      params.append('page', page.toString());
      params.append('size', size.toString());

      const response = await apiClient.get<{
        items: StockMovement[];
        total: number;
        page: number;
        size: number;
      }>(`/api/inventory/movements?${params.toString()}`);

      setMovements(response.items);
      setTotalMovements(response.total);
      setCurrentPage(page);
      setPageSize(size);
      setCurrentFilters(filters);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to list movements';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getMovementsByItem = async (
    itemId: string,
    limit: number = 100
  ): Promise<StockMovement[]> => {
    try {
      setError(null);
      const response = await apiClient.get<StockMovement[]>(
        `/api/inventory/movements/by-item/${itemId}?limit=${limit}`
      );
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get movements by item';
      setError(errorMessage);
      return [];
    }
  };

  const getMovementsByWarehouse = async (
    warehouseId: string,
    limit: number = 100
  ): Promise<StockMovement[]> => {
    try {
      setError(null);
      const response = await apiClient.get<StockMovement[]>(
        `/api/inventory/movements/by-warehouse/${warehouseId}?limit=${limit}`
      );
      return response;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get movements by warehouse';
      setError(errorMessage);
      return [];
    }
  };

  const getRecentMovements = async (limit: number = 50): Promise<StockMovement[]> => {
    try {
      setError(null);
      const response = await apiClient.get<StockMovement[]>(
        `/api/inventory/movements/recent?limit=${limit}`
      );
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get recent movements';
      setError(errorMessage);
      return [];
    }
  };

  const refreshMovements = async (): Promise<void> => {
    await listMovements(currentFilters, currentPage, pageSize);
  };

  return {
    movements,
    loading,
    error,
    totalMovements,
    currentPage,
    pageSize,
    createMovement,
    getMovement,
    listMovements,
    getMovementsByItem,
    getMovementsByWarehouse,
    getRecentMovements,
    refreshMovements,
  };
}
