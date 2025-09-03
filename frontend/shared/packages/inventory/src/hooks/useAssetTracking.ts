import { useState, useEffect } from 'react';
import { useApiClient } from '@dotmac/headless';
import type { Item, StockItem, StockMovement, ItemStatus, MovementType } from '../types';

export interface AssetLocation {
  warehouse_id: string;
  warehouse_name: string;
  bin_location?: string;
  zone?: string;
  aisle?: string;
  shelf?: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
}

export interface AssetHistory {
  movement: StockMovement;
  previous_location?: AssetLocation;
  current_location?: AssetLocation;
  technician?: string;
  customer_info?: {
    customer_id: string;
    customer_name: string;
    service_address: string;
  };
}

export interface AssetDetails extends Item {
  current_location?: AssetLocation;
  current_status: ItemStatus;
  serial_number?: string;
  installation_date?: string;
  last_maintenance_date?: string;
  next_maintenance_due?: string;
  warranty_expiry?: string;
  assigned_to?: {
    technician_id: string;
    technician_name: string;
    assignment_date: string;
  };
  customer_deployment?: {
    customer_id: string;
    customer_name: string;
    service_address: string;
    installation_date: string;
  };
}

export interface UseAssetTrackingResult {
  assets: AssetDetails[];
  loading: boolean;
  error: string | null;
  getAssetDetails: (assetId: string) => Promise<AssetDetails | null>;
  getAssetHistory: (assetId: string) => Promise<AssetHistory[]>;
  trackAssetMovement: (
    assetId: string,
    newLocation: AssetLocation,
    reason?: string
  ) => Promise<void>;
  assignAssetToTechnician: (
    assetId: string,
    technicianId: string,
    technicianName: string
  ) => Promise<void>;
  deployAssetToCustomer: (
    assetId: string,
    customerInfo: {
      customer_id: string;
      customer_name: string;
      service_address: string;
    }
  ) => Promise<void>;
  markAssetForMaintenance: (
    assetId: string,
    maintenanceType: string,
    notes?: string
  ) => Promise<void>;
  updateAssetStatus: (assetId: string, status: ItemStatus, reason?: string) => Promise<void>;
  searchAssetsBySerial: (serialNumber: string) => Promise<AssetDetails[]>;
  getAssetsByLocation: (warehouseId: string, zone?: string) => Promise<AssetDetails[]>;
  getAssetsByTechnician: (technicianId: string) => Promise<AssetDetails[]>;
  getCustomerAssets: (customerId: string) => Promise<AssetDetails[]>;
  getMaintenanceDue: (daysAhead?: number) => Promise<AssetDetails[]>;
}

export function useAssetTracking(): UseAssetTrackingResult {
  const [assets, setAssets] = useState<AssetDetails[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const getAssetDetails = async (assetId: string): Promise<AssetDetails | null> => {
    try {
      setError(null);
      const response = await apiClient.get<AssetDetails>(`/api/inventory/assets/${assetId}`);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get asset details';
      setError(errorMessage);
      return null;
    }
  };

  const getAssetHistory = async (assetId: string): Promise<AssetHistory[]> => {
    try {
      setError(null);
      const response = await apiClient.get<AssetHistory[]>(
        `/api/inventory/assets/${assetId}/history`
      );
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get asset history';
      setError(errorMessage);
      return [];
    }
  };

  const trackAssetMovement = async (
    assetId: string,
    newLocation: AssetLocation,
    reason?: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/assets/${assetId}/move`, {
        warehouse_id: newLocation.warehouse_id,
        bin_location: newLocation.bin_location,
        zone: newLocation.zone,
        aisle: newLocation.aisle,
        shelf: newLocation.shelf,
        coordinates: newLocation.coordinates,
        reason_description: reason || 'Asset relocation',
      });

      // Update the asset in our local state if it exists
      setAssets((prev) =>
        prev.map((asset) =>
          asset.id === assetId ? { ...asset, current_location: newLocation } : asset
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to track asset movement';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const assignAssetToTechnician = async (
    assetId: string,
    technicianId: string,
    technicianName: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/assets/${assetId}/assign-technician`, {
        technician_id: technicianId,
        technician_name: technicianName,
        assignment_date: new Date().toISOString(),
      });

      // Update local state
      setAssets((prev) =>
        prev.map((asset) =>
          asset.id === assetId
            ? {
                ...asset,
                assigned_to: {
                  technician_id: technicianId,
                  technician_name: technicianName,
                  assignment_date: new Date().toISOString(),
                },
                current_status: ItemStatus.ALLOCATED,
              }
            : asset
        )
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to assign asset to technician';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const deployAssetToCustomer = async (
    assetId: string,
    customerInfo: {
      customer_id: string;
      customer_name: string;
      service_address: string;
    }
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/assets/${assetId}/deploy-customer`, {
        ...customerInfo,
        installation_date: new Date().toISOString(),
      });

      // Update local state
      setAssets((prev) =>
        prev.map((asset) =>
          asset.id === assetId
            ? {
                ...asset,
                customer_deployment: {
                  ...customerInfo,
                  installation_date: new Date().toISOString(),
                },
                current_status: ItemStatus.IN_USE,
                installation_date: new Date().toISOString(),
              }
            : asset
        )
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to deploy asset to customer';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const markAssetForMaintenance = async (
    assetId: string,
    maintenanceType: string,
    notes?: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.post(`/api/inventory/assets/${assetId}/maintenance`, {
        maintenance_type: maintenanceType,
        scheduled_date: new Date().toISOString(),
        notes: notes,
      });

      // Update local state
      setAssets((prev) =>
        prev.map((asset) =>
          asset.id === assetId
            ? {
                ...asset,
                current_status: ItemStatus.IN_REPAIR,
                last_maintenance_date: new Date().toISOString(),
              }
            : asset
        )
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to mark asset for maintenance';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const updateAssetStatus = async (
    assetId: string,
    status: ItemStatus,
    reason?: string
  ): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      await apiClient.put(`/api/inventory/assets/${assetId}/status`, {
        status: status,
        reason: reason,
        updated_date: new Date().toISOString(),
      });

      // Update local state
      setAssets((prev) =>
        prev.map((asset) => (asset.id === assetId ? { ...asset, current_status: status } : asset))
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update asset status';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const searchAssetsBySerial = async (serialNumber: string): Promise<AssetDetails[]> => {
    try {
      setError(null);
      const response = await apiClient.get<AssetDetails[]>(
        `/api/inventory/assets/search?serial_number=${encodeURIComponent(serialNumber)}`
      );
      return response;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to search assets by serial number';
      setError(errorMessage);
      return [];
    }
  };

  const getAssetsByLocation = async (
    warehouseId: string,
    zone?: string
  ): Promise<AssetDetails[]> => {
    try {
      setError(null);
      const params = new URLSearchParams({ warehouse_id: warehouseId });
      if (zone) params.append('zone', zone);

      const response = await apiClient.get<AssetDetails[]>(
        `/api/inventory/assets/by-location?${params.toString()}`
      );
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get assets by location';
      setError(errorMessage);
      return [];
    }
  };

  const getAssetsByTechnician = async (technicianId: string): Promise<AssetDetails[]> => {
    try {
      setError(null);
      const response = await apiClient.get<AssetDetails[]>(
        `/api/inventory/assets/by-technician/${technicianId}`
      );
      return response;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get assets by technician';
      setError(errorMessage);
      return [];
    }
  };

  const getCustomerAssets = async (customerId: string): Promise<AssetDetails[]> => {
    try {
      setError(null);
      const response = await apiClient.get<AssetDetails[]>(
        `/api/inventory/assets/by-customer/${customerId}`
      );
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get customer assets';
      setError(errorMessage);
      return [];
    }
  };

  const getMaintenanceDue = async (daysAhead: number = 30): Promise<AssetDetails[]> => {
    try {
      setError(null);
      const response = await apiClient.get<AssetDetails[]>(
        `/api/inventory/assets/maintenance-due?days_ahead=${daysAhead}`
      );
      return response;
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to get maintenance due assets';
      setError(errorMessage);
      return [];
    }
  };

  return {
    assets,
    loading,
    error,
    getAssetDetails,
    getAssetHistory,
    trackAssetMovement,
    assignAssetToTechnician,
    deployAssetToCustomer,
    markAssetForMaintenance,
    updateAssetStatus,
    searchAssetsBySerial,
    getAssetsByLocation,
    getAssetsByTechnician,
    getCustomerAssets,
    getMaintenanceDue,
  };
}
