import { useState, useEffect } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  Item,
  ItemCreate,
  ItemUpdate,
  ItemFilter,
  ItemStockSummary
} from '../types';

export interface UseInventoryResult {
  items: Item[];
  loading: boolean;
  error: string | null;
  totalItems: number;
  currentPage: number;
  pageSize: number;
  createItem: (data: ItemCreate) => Promise<Item>;
  updateItem: (id: string, data: ItemUpdate) => Promise<Item>;
  deleteItem: (id: string) => Promise<void>;
  getItem: (id: string) => Promise<Item | null>;
  getItemWithStock: (id: string) => Promise<{ item: Item; stock_summary: ItemStockSummary } | null>;
  listItems: (filters?: ItemFilter, page?: number, size?: number) => Promise<void>;
  searchItems: (query: string) => Promise<void>;
  getLowStockItems: () => Promise<Array<{
    item: Item;
    current_stock: number;
    reorder_point: number;
    reorder_quantity: number;
    shortage: number;
  }>>;
  refreshItems: () => Promise<void>;
}

export function useInventory(): UseInventoryResult {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [currentFilters, setCurrentFilters] = useState<ItemFilter>({});

  const apiClient = useApiClient();

  const createItem = async (data: ItemCreate): Promise<Item> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<Item>('/api/inventory/items', data);

      // Add new item to the list
      setItems(prev => [response, ...prev]);
      setTotalItems(prev => prev + 1);

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create item';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updateItem = async (id: string, data: ItemUpdate): Promise<Item> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.put<Item>(`/api/inventory/items/${id}`, data);

      // Update item in the list
      setItems(prev =>
        prev.map(item => item.id === id ? response : item)
      );

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update item';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const deleteItem = async (id: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.delete(`/api/inventory/items/${id}`);

      // Remove item from the list
      setItems(prev => prev.filter(item => item.id !== id));
      setTotalItems(prev => prev - 1);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete item';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getItem = async (id: string): Promise<Item | null> => {
    try {
      setError(null);
      const response = await apiClient.get<Item>(`/api/inventory/items/${id}`);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get item';
      setError(errorMessage);
      return null;
    }
  };

  const getItemWithStock = async (id: string) => {
    try {
      setError(null);
      const response = await apiClient.get<{ item: Item; stock_summary: ItemStockSummary }>(`/api/inventory/items/${id}/stock-summary`);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get item with stock';
      setError(errorMessage);
      return null;
    }
  };

  const listItems = async (filters: ItemFilter = {}, page: number = 1, size: number = 50): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.search) params.append('search', filters.search);
      if (filters.item_type) {
        const types = Array.isArray(filters.item_type) ? filters.item_type : [filters.item_type];
        types.forEach(type => params.append('item_type', type));
      }
      if (filters.category) {
        const categories = Array.isArray(filters.category) ? filters.category : [filters.category];
        categories.forEach(cat => params.append('category', cat));
      }
      if (filters.manufacturer) {
        const manufacturers = Array.isArray(filters.manufacturer) ? filters.manufacturer : [filters.manufacturer];
        manufacturers.forEach(mfg => params.append('manufacturer', mfg));
      }
      if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString());
      if (filters.is_discontinued !== undefined) params.append('is_discontinued', filters.is_discontinued.toString());
      if (filters.low_stock) params.append('low_stock', 'true');

      params.append('page', page.toString());
      params.append('size', size.toString());

      const response = await apiClient.get<{
        items: Item[];
        total: number;
        page: number;
        size: number;
      }>(`/api/inventory/items?${params.toString()}`);

      setItems(response.items);
      setTotalItems(response.total);
      setCurrentPage(page);
      setPageSize(size);
      setCurrentFilters(filters);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to list items';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const searchItems = async (query: string): Promise<void> => {
    await listItems({ ...currentFilters, search: query }, 1, pageSize);
  };

  const getLowStockItems = async () => {
    try {
      setError(null);
      const response = await apiClient.get<Array<{
        item: Item;
        current_stock: number;
        reorder_point: number;
        reorder_quantity: number;
        shortage: number;
      }>>('/api/inventory/items/low-stock');
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get low stock items';
      setError(errorMessage);
      return [];
    }
  };

  const refreshItems = async (): Promise<void> => {
    await listItems(currentFilters, currentPage, pageSize);
  };

  // Load initial data
  useEffect(() => {
    listItems();
  }, []);

  return {
    items,
    loading,
    error,
    totalItems,
    currentPage,
    pageSize,
    createItem,
    updateItem,
    deleteItem,
    getItem,
    getItemWithStock,
    listItems,
    searchItems,
    getLowStockItems,
    refreshItems
  };
}
