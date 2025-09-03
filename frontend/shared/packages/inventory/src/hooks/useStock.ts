import { useState, useEffect } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  StockItem,
  StockAdjustment,
  StockReservation,
  ItemStatus,
  ItemCondition,
} from '../types';

export interface StockLevel {
  warehouse_id: string;
  warehouse_name: string;
  item_id: string;
  item_name: string;
  item_code: string;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
  min_quantity: number;
  max_quantity?: number;
  reorder_point: number;
  status: 'healthy' | 'low' | 'critical' | 'overstock';
  last_movement_date?: string;
}

export interface UseStockResult {
  stockLevels: StockLevel[];
  loading: boolean;
  error: string | null;
  getStockLevels: (warehouseId?: string) => Promise<void>;
  getItemStock: (itemId: string) => Promise<StockItem[]>;
  adjustStock: (adjustment: StockAdjustment) => Promise<void>;
  reserveStock: (reservation: StockReservation) => Promise<void>;
  releaseReservation: (reservationId: string) => Promise<void>;
  transferStock: (params: {
    item_id: string;
    from_warehouse_id: string;
    to_warehouse_id: string;
    quantity: number;
    reason: string;
  }) => Promise<void>;
  performStockCount: (params: {
    warehouse_id: string;
    item_selections?: string[];
    count_type: 'full' | 'cycle' | 'spot';
  }) => Promise<string>; // Returns count_id
  updateStockLocation: (
    stockItemId: string,
    location: {
      bin_location?: string;
      zone?: string;
      aisle?: string;
      shelf?: string;
    }
  ) => Promise<void>;
  getLowStockAlerts: () => Promise<StockLevel[]>;
  getOverstockItems: () => Promise<StockLevel[]>;
  refreshStock: () => Promise<void>;
}

export function useStock(): UseStockResult {
  const [stockLevels, setStockLevels] = useState<StockLevel[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const getStockLevels = async (warehouseId?: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const params = warehouseId ? `?warehouse_id=${warehouseId}` : '';
      const response = await apiClient.get<StockLevel[]>(`/api/inventory/stock/levels${params}`);

      setStockLevels(response);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get stock levels';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getItemStock = async (itemId: string): Promise<StockItem[]> => {
    try {
      setError(null);
      const response = await apiClient.get<StockItem[]>(`/api/inventory/stock/items/${itemId}`);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get item stock';
      setError(errorMessage);
      return [];
    }
  };

  const adjustStock = async (adjustment: StockAdjustment): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post('/api/inventory/stock/adjust', adjustment);

      // Refresh stock levels after adjustment
      await getStockLevels();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to adjust stock';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const reserveStock = async (reservation: StockReservation): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post('/api/inventory/stock/reserve', reservation);

      // Update local stock levels
      setStockLevels((prev) =>
        prev.map((stock) =>
          stock.item_id === reservation.item_id && stock.warehouse_id === reservation.warehouse_id
            ? {
                ...stock,
                reserved_quantity: stock.reserved_quantity + reservation.quantity,
                available_quantity: stock.available_quantity - reservation.quantity,
              }
            : stock
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reserve stock';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const releaseReservation = async (reservationId: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.delete(`/api/inventory/stock/reservations/${reservationId}`);

      // Refresh stock levels after releasing reservation
      await getStockLevels();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to release reservation';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const transferStock = async (params: {
    item_id: string;
    from_warehouse_id: string;
    to_warehouse_id: string;
    quantity: number;
    reason: string;
  }): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post('/api/inventory/stock/transfer', params);

      // Update local stock levels
      setStockLevels((prev) =>
        prev.map((stock) => {
          if (stock.item_id === params.item_id) {
            if (stock.warehouse_id === params.from_warehouse_id) {
              return {
                ...stock,
                quantity: stock.quantity - params.quantity,
                available_quantity: stock.available_quantity - params.quantity,
              };
            } else if (stock.warehouse_id === params.to_warehouse_id) {
              return {
                ...stock,
                quantity: stock.quantity + params.quantity,
                available_quantity: stock.available_quantity + params.quantity,
              };
            }
          }
          return stock;
        })
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to transfer stock';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const performStockCount = async (params: {
    warehouse_id: string;
    item_selections?: string[];
    count_type: 'full' | 'cycle' | 'spot';
  }): Promise<string> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<{ count_id: string }>(
        '/api/inventory/stock/count/create',
        params
      );
      return response.count_id;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create stock count';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updateStockLocation = async (
    stockItemId: string,
    location: {
      bin_location?: string;
      zone?: string;
      aisle?: string;
      shelf?: string;
    }
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.put(`/api/inventory/stock/items/${stockItemId}/location`, location);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update stock location';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getLowStockAlerts = async (): Promise<StockLevel[]> => {
    try {
      setError(null);
      const response = await apiClient.get<StockLevel[]>('/api/inventory/stock/alerts/low-stock');
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get low stock alerts';
      setError(errorMessage);
      return [];
    }
  };

  const getOverstockItems = async (): Promise<StockLevel[]> => {
    try {
      setError(null);
      const response = await apiClient.get<StockLevel[]>('/api/inventory/stock/alerts/overstock');
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get overstock items';
      setError(errorMessage);
      return [];
    }
  };

  const refreshStock = async (): Promise<void> => {
    await getStockLevels();
  };

  // Load initial data
  useEffect(() => {
    getStockLevels();
  }, []);

  return {
    stockLevels,
    loading,
    error,
    getStockLevels,
    getItemStock,
    adjustStock,
    reserveStock,
    releaseReservation,
    transferStock,
    performStockCount,
    updateStockLocation,
    getLowStockAlerts,
    getOverstockItems,
    refreshStock,
  };
}
