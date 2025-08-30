import { useState, useEffect } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  Item,
  AssetDetails,
  ItemType,
  MovementType
} from '../types';

export interface ProvisioningRequest {
  id?: string;
  customer_id: string;
  customer_name: string;
  service_address: string;
  service_type: string;
  equipment_requirements: EquipmentRequirement[];
  requested_date: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  technician_id?: string;
  technician_name?: string;
  status: 'pending' | 'allocated' | 'dispatched' | 'installed' | 'completed' | 'cancelled';
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface EquipmentRequirement {
  item_type: ItemType;
  item_category: string;
  manufacturer_preference?: string;
  model_preference?: string;
  quantity: number;
  specifications?: Record<string, any>;
  allocated_items?: AllocatedEquipment[];
}

export interface AllocatedEquipment {
  item_id: string;
  item_name: string;
  item_code: string;
  serial_number?: string;
  warehouse_id: string;
  warehouse_name: string;
  allocation_date: string;
  status: 'allocated' | 'dispatched' | 'installed' | 'returned';
}

export interface ProvisioningKit {
  id?: string;
  name: string;
  description?: string;
  service_type: string;
  equipment_list: EquipmentRequirement[];
  is_template: boolean;
  created_by?: string;
  created_at?: string;
}

export interface UseEquipmentProvisioningResult {
  provisioningRequests: ProvisioningRequest[];
  provisioningKits: ProvisioningKit[];
  loading: boolean;
  error: string | null;
  createProvisioningRequest: (request: Omit<ProvisioningRequest, 'id' | 'status' | 'created_at' | 'updated_at'>) => Promise<ProvisioningRequest>;
  updateProvisioningRequest: (id: string, updates: Partial<ProvisioningRequest>) => Promise<ProvisioningRequest>;
  allocateEquipment: (requestId: string, allocations: {
    requirement_index: number;
    item_id: string;
    warehouse_id: string;
    serial_number?: string;
  }[]) => Promise<void>;
  dispatchEquipment: (requestId: string, technicianId: string, technicianName: string) => Promise<void>;
  confirmInstallation: (requestId: string, installationNotes?: string) => Promise<void>;
  returnEquipment: (requestId: string, returnedItems: {
    item_id: string;
    condition: 'good' | 'damaged' | 'faulty';
    notes?: string;
  }[], returnWarehouseId: string) => Promise<void>;
  createProvisioningKit: (kit: Omit<ProvisioningKit, 'id' | 'created_at'>) => Promise<ProvisioningKit>;
  updateProvisioningKit: (id: string, updates: Partial<ProvisioningKit>) => Promise<ProvisioningKit>;
  deleteProvisioningKit: (id: string) => Promise<void>;
  getAvailableEquipment: (requirements: EquipmentRequirement[], preferredWarehouseId?: string) => Promise<{
    requirement_index: number;
    available_items: Array<{
      item: Item;
      available_quantity: number;
      warehouse_id: string;
      warehouse_name: string;
    }>;
  }[]>;
  getProvisioningAnalytics: () => Promise<{
    total_requests: number;
    pending_requests: number;
    completed_requests: number;
    equipment_utilization: Record<string, number>;
    technician_workload: Array<{
      technician_id: string;
      technician_name: string;
      active_requests: number;
    }>;
  }>;
  refreshRequests: () => Promise<void>;
}

export function useEquipmentProvisioning(): UseEquipmentProvisioningResult {
  const [provisioningRequests, setProvisioningRequests] = useState<ProvisioningRequest[]>([]);
  const [provisioningKits, setProvisioningKits] = useState<ProvisioningKit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const createProvisioningRequest = async (
    request: Omit<ProvisioningRequest, 'id' | 'status' | 'created_at' | 'updated_at'>
  ): Promise<ProvisioningRequest> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<ProvisioningRequest>('/api/inventory/provisioning/requests', {
        ...request,
        status: 'pending'
      });

      setProvisioningRequests(prev => [response, ...prev]);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create provisioning request';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updateProvisioningRequest = async (
    id: string,
    updates: Partial<ProvisioningRequest>
  ): Promise<ProvisioningRequest> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.put<ProvisioningRequest>(`/api/inventory/provisioning/requests/${id}`, updates);

      setProvisioningRequests(prev =>
        prev.map(request => request.id === id ? response : request)
      );

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update provisioning request';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const allocateEquipment = async (
    requestId: string,
    allocations: {
      requirement_index: number;
      item_id: string;
      warehouse_id: string;
      serial_number?: string;
    }[]
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/provisioning/requests/${requestId}/allocate`, {
        allocations
      });

      // Update request status
      setProvisioningRequests(prev =>
        prev.map(request =>
          request.id === requestId
            ? { ...request, status: 'allocated' as const }
            : request
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to allocate equipment';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const dispatchEquipment = async (
    requestId: string,
    technicianId: string,
    technicianName: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/provisioning/requests/${requestId}/dispatch`, {
        technician_id: technicianId,
        technician_name: technicianName,
        dispatch_date: new Date().toISOString()
      });

      // Update request status and technician info
      setProvisioningRequests(prev =>
        prev.map(request =>
          request.id === requestId
            ? {
                ...request,
                status: 'dispatched' as const,
                technician_id: technicianId,
                technician_name: technicianName
              }
            : request
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to dispatch equipment';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const confirmInstallation = async (
    requestId: string,
    installationNotes?: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/provisioning/requests/${requestId}/install`, {
        installation_date: new Date().toISOString(),
        installation_notes: installationNotes
      });

      // Update request status
      setProvisioningRequests(prev =>
        prev.map(request =>
          request.id === requestId
            ? { ...request, status: 'installed' as const }
            : request
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to confirm installation';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const returnEquipment = async (
    requestId: string,
    returnedItems: {
      item_id: string;
      condition: 'good' | 'damaged' | 'faulty';
      notes?: string;
    }[],
    returnWarehouseId: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/provisioning/requests/${requestId}/return`, {
        returned_items: returnedItems,
        return_warehouse_id: returnWarehouseId,
        return_date: new Date().toISOString()
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to return equipment';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const createProvisioningKit = async (
    kit: Omit<ProvisioningKit, 'id' | 'created_at'>
  ): Promise<ProvisioningKit> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post<ProvisioningKit>('/api/inventory/provisioning/kits', kit);

      setProvisioningKits(prev => [response, ...prev]);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create provisioning kit';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updateProvisioningKit = async (
    id: string,
    updates: Partial<ProvisioningKit>
  ): Promise<ProvisioningKit> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.put<ProvisioningKit>(`/api/inventory/provisioning/kits/${id}`, updates);

      setProvisioningKits(prev =>
        prev.map(kit => kit.id === id ? response : kit)
      );

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update provisioning kit';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const deleteProvisioningKit = async (id: string): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.delete(`/api/inventory/provisioning/kits/${id}`);

      setProvisioningKits(prev => prev.filter(kit => kit.id !== id));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete provisioning kit';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getAvailableEquipment = async (
    requirements: EquipmentRequirement[],
    preferredWarehouseId?: string
  ) => {
    try {
      setError(null);
      const response = await apiClient.post<{
        requirement_index: number;
        available_items: Array<{
          item: Item;
          available_quantity: number;
          warehouse_id: string;
          warehouse_name: string;
        }>;
      }[]>('/api/inventory/provisioning/available-equipment', {
        requirements,
        preferred_warehouse_id: preferredWarehouseId
      });

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get available equipment';
      setError(errorMessage);
      return [];
    }
  };

  const getProvisioningAnalytics = async () => {
    try {
      setError(null);
      const response = await apiClient.get<{
        total_requests: number;
        pending_requests: number;
        completed_requests: number;
        equipment_utilization: Record<string, number>;
        technician_workload: Array<{
          technician_id: string;
          technician_name: string;
          active_requests: number;
        }>;
      }>('/api/inventory/provisioning/analytics');

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get provisioning analytics';
      setError(errorMessage);
      return {
        total_requests: 0,
        pending_requests: 0,
        completed_requests: 0,
        equipment_utilization: {},
        technician_workload: []
      };
    }
  };

  const refreshRequests = async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const [requestsResponse, kitsResponse] = await Promise.all([
        apiClient.get<ProvisioningRequest[]>('/api/inventory/provisioning/requests'),
        apiClient.get<ProvisioningKit[]>('/api/inventory/provisioning/kits')
      ]);

      setProvisioningRequests(requestsResponse);
      setProvisioningKits(kitsResponse);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to refresh provisioning data';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Load initial data
  useEffect(() => {
    refreshRequests();
  }, []);

  return {
    provisioningRequests,
    provisioningKits,
    loading,
    error,
    createProvisioningRequest,
    updateProvisioningRequest,
    allocateEquipment,
    dispatchEquipment,
    confirmInstallation,
    returnEquipment,
    createProvisioningKit,
    updateProvisioningKit,
    deleteProvisioningKit,
    getAvailableEquipment,
    getProvisioningAnalytics,
    refreshRequests
  };
}
