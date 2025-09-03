import { useState, useEffect } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  PurchaseOrder,
  PurchaseOrderCreate,
  PurchaseOrderUpdate,
  PurchaseOrderLine,
  PurchaseOrderLineCreate,
  PurchaseOrderFilter,
  PurchaseOrderStatus,
} from '../types';

export interface UsePurchaseOrdersResult {
  purchaseOrders: PurchaseOrder[];
  loading: boolean;
  error: string | null;
  totalOrders: number;
  currentPage: number;
  pageSize: number;
  createPurchaseOrder: (
    data: PurchaseOrderCreate,
    lineItems: PurchaseOrderLineCreate[]
  ) => Promise<PurchaseOrder>;
  updatePurchaseOrder: (id: string, data: PurchaseOrderUpdate) => Promise<PurchaseOrder>;
  deletePurchaseOrder: (id: string) => Promise<void>;
  getPurchaseOrder: (id: string) => Promise<PurchaseOrder | null>;
  listPurchaseOrders: (
    filters?: PurchaseOrderFilter,
    page?: number,
    size?: number
  ) => Promise<void>;
  approvePurchaseOrder: (id: string) => Promise<PurchaseOrder>;
  sendToVendor: (id: string, vendorEmail?: string) => Promise<void>;
  receiveItems: (
    poId: string,
    receipts: {
      line_id: string;
      quantity_received: number;
      unit_cost?: number;
      condition?: string;
      notes?: string;
    }[]
  ) => Promise<void>;
  createReorderPurchaseOrders: (defaultWarehouseId: string) => Promise<PurchaseOrder[]>;
  refreshPurchaseOrders: () => Promise<void>;
}

export function usePurchaseOrders(): UsePurchaseOrdersResult {
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalOrders, setTotalOrders] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [currentFilters, setCurrentFilters] = useState<PurchaseOrderFilter>({});

  const apiClient = useApiClient();

  const createPurchaseOrder = async (
    data: PurchaseOrderCreate,
    lineItems: PurchaseOrderLineCreate[]
  ): Promise<PurchaseOrder> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<PurchaseOrder>('/api/inventory/purchase-orders', {
        ...data,
        line_items: lineItems,
      });

      setPurchaseOrders((prev) => [response, ...prev]);
      setTotalOrders((prev) => prev + 1);

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create purchase order';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updatePurchaseOrder = async (
    id: string,
    data: PurchaseOrderUpdate
  ): Promise<PurchaseOrder> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.put<PurchaseOrder>(
        `/api/inventory/purchase-orders/${id}`,
        data
      );

      setPurchaseOrders((prev) => prev.map((po) => (po.id === id ? response : po)));

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update purchase order';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const deletePurchaseOrder = async (id: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.delete(`/api/inventory/purchase-orders/${id}`);

      setPurchaseOrders((prev) => prev.filter((po) => po.id !== id));
      setTotalOrders((prev) => prev - 1);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete purchase order';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getPurchaseOrder = async (id: string): Promise<PurchaseOrder | null> => {
    try {
      setError(null);
      const response = await apiClient.get<PurchaseOrder>(`/api/inventory/purchase-orders/${id}`);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get purchase order';
      setError(errorMessage);
      return null;
    }
  };

  const listPurchaseOrders = async (
    filters: PurchaseOrderFilter = {},
    page: number = 1,
    size: number = 50
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (filters.vendor_id) params.append('vendor_id', filters.vendor_id);
      if (filters.po_status) {
        const statuses = Array.isArray(filters.po_status) ? filters.po_status : [filters.po_status];
        statuses.forEach((status) => params.append('po_status', status));
      }
      if (filters.order_date_from) params.append('order_date_from', filters.order_date_from);
      if (filters.order_date_to) params.append('order_date_to', filters.order_date_to);
      if (filters.required_date_from)
        params.append('required_date_from', filters.required_date_from);
      if (filters.required_date_to) params.append('required_date_to', filters.required_date_to);
      if (filters.search) params.append('search', filters.search);

      params.append('page', page.toString());
      params.append('size', size.toString());

      const response = await apiClient.get<{
        items: PurchaseOrder[];
        total: number;
        page: number;
        size: number;
      }>(`/api/inventory/purchase-orders?${params.toString()}`);

      setPurchaseOrders(response.items);
      setTotalOrders(response.total);
      setCurrentPage(page);
      setPageSize(size);
      setCurrentFilters(filters);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to list purchase orders';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const approvePurchaseOrder = async (id: string): Promise<PurchaseOrder> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<PurchaseOrder>(
        `/api/inventory/purchase-orders/${id}/approve`,
        {
          approval_date: new Date().toISOString(),
        }
      );

      setPurchaseOrders((prev) => prev.map((po) => (po.id === id ? response : po)));

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to approve purchase order';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const sendToVendor = async (id: string, vendorEmail?: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/purchase-orders/${id}/send-to-vendor`, {
        vendor_email: vendorEmail,
        sent_date: new Date().toISOString(),
      });

      // Update PO status
      setPurchaseOrders((prev) =>
        prev.map((po) =>
          po.id === id ? { ...po, po_status: PurchaseOrderStatus.SENT_TO_VENDOR } : po
        )
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to send purchase order to vendor';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const receiveItems = async (
    poId: string,
    receipts: {
      line_id: string;
      quantity_received: number;
      unit_cost?: number;
      condition?: string;
      notes?: string;
    }[]
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/purchase-orders/${poId}/receive`, {
        receipts: receipts,
        received_date: new Date().toISOString(),
      });

      // Refresh the purchase order to get updated quantities and status
      const updatedPO = await getPurchaseOrder(poId);
      if (updatedPO) {
        setPurchaseOrders((prev) => prev.map((po) => (po.id === poId ? updatedPO : po)));
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to receive items';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const createReorderPurchaseOrders = async (
    defaultWarehouseId: string
  ): Promise<PurchaseOrder[]> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<PurchaseOrder[]>(
        '/api/inventory/purchase-orders/create-reorders',
        {
          default_warehouse_id: defaultWarehouseId,
        }
      );

      // Add new POs to the list
      setPurchaseOrders((prev) => [...response, ...prev]);
      setTotalOrders((prev) => prev + response.length);

      return response;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create reorder purchase orders';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const refreshPurchaseOrders = async (): Promise<void> => {
    await listPurchaseOrders(currentFilters, currentPage, pageSize);
  };

  // Load initial data
  useEffect(() => {
    listPurchaseOrders();
  }, []);

  return {
    purchaseOrders,
    loading,
    error,
    totalOrders,
    currentPage,
    pageSize,
    createPurchaseOrder,
    updatePurchaseOrder,
    deletePurchaseOrder,
    getPurchaseOrder,
    listPurchaseOrders,
    approvePurchaseOrder,
    sendToVendor,
    receiveItems,
    createReorderPurchaseOrders,
    refreshPurchaseOrders,
  };
}
