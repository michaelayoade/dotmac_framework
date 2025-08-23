/**
 * Data Persistence Hook
 * Handles offline data synchronization, conflict resolution, and persistence
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useStandardErrorHandler } from './useStandardErrorHandler';
import { useRealTimeSync } from './useRealTimeSync';

export interface DataOperation {
  id: string;
  type: 'create' | 'update' | 'delete';
  entity: string;
  entityId: string;
  data: any;
  timestamp: number;
  userId: string;
  tenantId: string;
  retries: number;
  maxRetries: number;
  lastError?: string;
  status: 'pending' | 'syncing' | 'completed' | 'failed';
}

export interface ConflictResolution {
  operationId: string;
  conflictType: 'version' | 'concurrent_edit' | 'delete_modified';
  serverData: any;
  localData: any;
  resolution: 'server' | 'client' | 'merge' | 'manual';
  resolvedData?: any;
}

export interface SyncStatus {
  isOnline: boolean;
  lastSync: number;
  pendingOperations: number;
  failedOperations: number;
  syncInProgress: boolean;
  conflictsToResolve: number;
}

export function useDataPersistence() {
  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { handleError, withErrorHandling } = useStandardErrorHandler({
    context: 'Data Persistence',
    enableRetry: true,
    maxRetries: 3
  });
  const { emit, subscribe, isConnected } = useRealTimeSync();

  const [pendingOperations, setPendingOperations] = useState<DataOperation[]>([]);
  const [conflicts, setConflicts] = useState<ConflictResolution[]>([]);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    isOnline: navigator.onLine,
    lastSync: 0,
    pendingOperations: 0,
    failedOperations: 0,
    syncInProgress: false,
    conflictsToResolve: 0
  });

  const syncIntervalRef = useRef<NodeJS.Timeout>();
  const operationQueueRef = useRef<Map<string, DataOperation>>(new Map());

  // Add operation to queue
  const queueOperation = useCallback((operation: Omit<DataOperation, 'id' | 'timestamp' | 'userId' | 'tenantId' | 'retries' | 'status'>): string => {
    if (!user?.id || !currentTenant?.tenant?.id) {
      throw new Error('User or tenant context not available');
    }

    const operationId = `${operation.type}_${operation.entity}_${operation.entityId}_${Date.now()}`;
    
    const fullOperation: DataOperation = {
      ...operation,
      id: operationId,
      timestamp: Date.now(),
      userId: user.id,
      tenantId: currentTenant.tenant.id,
      retries: 0,
      maxRetries: 3,
      status: 'pending'
    };

    operationQueueRef.current.set(operationId, fullOperation);
    setPendingOperations(prev => [...prev, fullOperation]);
    
    setSyncStatus(prev => ({
      ...prev,
      pendingOperations: prev.pendingOperations + 1
    }));

    // If online, try to sync immediately
    if (syncStatus.isOnline && isConnected) {
      processOperation(fullOperation);
    }

    return operationId;
  }, [user?.id, currentTenant?.tenant?.id, syncStatus.isOnline, isConnected]);

  // Process individual operation
  const processOperation = useCallback(async (operation: DataOperation): Promise<boolean> => {
    return withErrorHandling(async () => {
      setSyncStatus(prev => ({ ...prev, syncInProgress: true }));
      
      // Mark operation as syncing
      operationQueueRef.current.set(operation.id, { ...operation, status: 'syncing' });
      setPendingOperations(prev => prev.map(op => 
        op.id === operation.id ? { ...op, status: 'syncing' } : op
      ));

      const apiClient = getApiClient();
      let response;

      try {
        switch (operation.type) {
          case 'create':
            response = await apiClient.request(`/api/v1/${operation.entity}`, {
              method: 'POST',
              body: {
                ...operation.data,
                _operationId: operation.id,
                _clientTimestamp: operation.timestamp
              }
            });
            break;

          case 'update':
            response = await apiClient.request(`/api/v1/${operation.entity}/${operation.entityId}`, {
              method: 'PUT',
              body: {
                ...operation.data,
                _operationId: operation.id,
                _clientTimestamp: operation.timestamp
              }
            });
            break;

          case 'delete':
            response = await apiClient.request(`/api/v1/${operation.entity}/${operation.entityId}`, {
              method: 'DELETE',
              body: {
                _operationId: operation.id,
                _clientTimestamp: operation.timestamp
              }
            });
            break;

          default:
            throw new Error(`Unknown operation type: ${operation.type}`);
        }

        // Operation successful
        operationQueueRef.current.delete(operation.id);
        setPendingOperations(prev => prev.filter(op => op.id !== operation.id));
        
        setSyncStatus(prev => ({
          ...prev,
          pendingOperations: prev.pendingOperations - 1,
          lastSync: Date.now(),
          syncInProgress: false
        }));

        // Emit sync success event
        emit('data:sync_success', {
          operationId: operation.id,
          entity: operation.entity,
          entityId: operation.entityId,
          type: operation.type
        });

        return true;

      } catch (error: any) {
        // Handle conflicts
        if (error.status === 409) {
          const conflict: ConflictResolution = {
            operationId: operation.id,
            conflictType: error.data?.conflictType || 'concurrent_edit',
            serverData: error.data?.serverData,
            localData: operation.data,
            resolution: 'manual' // Default to manual resolution
          };

          setConflicts(prev => [...prev, conflict]);
          setSyncStatus(prev => ({
            ...prev,
            conflictsToResolve: prev.conflictsToResolve + 1,
            syncInProgress: false
          }));

          return false;
        }

        // Handle retryable errors
        const updatedOperation = {
          ...operation,
          retries: operation.retries + 1,
          lastError: error.message,
          status: operation.retries >= operation.maxRetries ? 'failed' : 'pending'
        } as DataOperation;

        operationQueueRef.current.set(operation.id, updatedOperation);
        setPendingOperations(prev => prev.map(op => 
          op.id === operation.id ? updatedOperation : op
        ));

        if (updatedOperation.status === 'failed') {
          setSyncStatus(prev => ({
            ...prev,
            failedOperations: prev.failedOperations + 1,
            syncInProgress: false
          }));
        }

        throw error;
      }
    }) || false;
  }, [withErrorHandling, emit]);

  // Sync all pending operations
  const syncPendingOperations = useCallback(async (): Promise<{ synced: number; failed: number; conflicts: number }> => {
    if (!syncStatus.isOnline || !isConnected) {
      return { synced: 0, failed: 0, conflicts: 0 };
    }

    const operations = Array.from(operationQueueRef.current.values())
      .filter(op => op.status === 'pending')
      .sort((a, b) => a.timestamp - b.timestamp); // Process in chronological order

    let synced = 0;
    let failed = 0;
    let conflicts = 0;

    for (const operation of operations) {
      try {
        const success = await processOperation(operation);
        if (success) {
          synced++;
        } else {
          conflicts++;
        }
      } catch (error) {
        failed++;
        handleError(error);
      }
    }

    return { synced, failed, conflicts };
  }, [syncStatus.isOnline, isConnected, processOperation, handleError]);

  // Resolve conflict
  const resolveConflict = useCallback(async (
    conflictId: string,
    resolution: ConflictResolution['resolution'],
    resolvedData?: any
  ): Promise<boolean> => {
    const conflict = conflicts.find(c => c.operationId === conflictId);
    if (!conflict) return false;

    const operation = operationQueueRef.current.get(conflictId);
    if (!operation) return false;

    let finalData: any;
    
    switch (resolution) {
      case 'server':
        finalData = conflict.serverData;
        break;
      case 'client':
        finalData = conflict.localData;
        break;
      case 'merge':
        finalData = mergeData(conflict.localData, conflict.serverData);
        break;
      case 'manual':
        finalData = resolvedData;
        break;
    }

    if (!finalData) {
      throw new Error('No resolved data provided for manual conflict resolution');
    }

    // Create new operation with resolved data
    const resolvedOperation: DataOperation = {
      ...operation,
      data: finalData,
      retries: 0,
      status: 'pending'
    };

    // Replace operation in queue
    operationQueueRef.current.set(conflictId, resolvedOperation);
    setPendingOperations(prev => prev.map(op => 
      op.id === conflictId ? resolvedOperation : op
    ));

    // Remove from conflicts
    setConflicts(prev => prev.filter(c => c.operationId !== conflictId));
    setSyncStatus(prev => ({
      ...prev,
      conflictsToResolve: prev.conflictsToResolve - 1
    }));

    // Try to process the resolved operation
    return await processOperation(resolvedOperation);
  }, [conflicts, processOperation]);

  // Clear failed operations
  const clearFailedOperations = useCallback(() => {
    const failedOps = Array.from(operationQueueRef.current.values())
      .filter(op => op.status === 'failed');

    failedOps.forEach(op => {
      operationQueueRef.current.delete(op.id);
    });

    setPendingOperations(prev => prev.filter(op => op.status !== 'failed'));
    setSyncStatus(prev => ({ ...prev, failedOperations: 0 }));
  }, []);

  // Retry failed operations
  const retryFailedOperations = useCallback(async (): Promise<void> => {
    const failedOps = Array.from(operationQueueRef.current.values())
      .filter(op => op.status === 'failed');

    for (const operation of failedOps) {
      const resetOperation = { ...operation, retries: 0, status: 'pending' as const };
      operationQueueRef.current.set(operation.id, resetOperation);
    }

    setPendingOperations(prev => prev.map(op => 
      op.status === 'failed' ? { ...op, retries: 0, status: 'pending' } : op
    ));

    setSyncStatus(prev => ({ ...prev, failedOperations: 0 }));

    await syncPendingOperations();
  }, [syncPendingOperations]);

  // Export data for backup
  const exportPendingData = useCallback((): string => {
    const exportData = {
      operations: Array.from(operationQueueRef.current.values()),
      conflicts,
      timestamp: Date.now(),
      version: '1.0'
    };

    return JSON.stringify(exportData, null, 2);
  }, [conflicts]);

  // Import data from backup
  const importPendingData = useCallback((importData: string): number => {
    try {
      const data = JSON.parse(importData);
      
      if (!data.operations || !Array.isArray(data.operations)) {
        throw new Error('Invalid import data format');
      }

      let importedCount = 0;
      
      for (const operation of data.operations) {
        if (!operationQueueRef.current.has(operation.id)) {
          operationQueueRef.current.set(operation.id, operation);
          importedCount++;
        }
      }

      if (data.conflicts && Array.isArray(data.conflicts)) {
        setConflicts(prev => [...prev, ...data.conflicts.filter(
          (conflict: ConflictResolution) => !prev.find(c => c.operationId === conflict.operationId)
        )]);
      }

      setPendingOperations(Array.from(operationQueueRef.current.values()));
      
      return importedCount;
    } catch (error) {
      handleError(error);
      return 0;
    }
  }, [handleError]);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setSyncStatus(prev => ({ ...prev, isOnline: true }));
      // Auto-sync when coming back online
      syncPendingOperations();
    };

    const handleOffline = () => {
      setSyncStatus(prev => ({ ...prev, isOnline: false }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [syncPendingOperations]);

  // Set up automatic sync interval
  useEffect(() => {
    if (syncStatus.isOnline && isConnected) {
      syncIntervalRef.current = setInterval(() => {
        if (operationQueueRef.current.size > 0) {
          syncPendingOperations();
        }
      }, 30000); // Sync every 30 seconds
    }

    return () => {
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
      }
    };
  }, [syncStatus.isOnline, isConnected, syncPendingOperations]);

  // Listen for real-time sync events
  useEffect(() => {
    return subscribe('data:*', (event) => {
      if (event.type === 'data:invalidate') {
        // Server indicates data has changed, trigger sync
        syncPendingOperations();
      }
    });
  }, [subscribe, syncPendingOperations]);

  return {
    // State
    pendingOperations,
    conflicts,
    syncStatus,

    // Operations
    queueOperation,
    syncPendingOperations,
    resolveConflict,
    clearFailedOperations,
    retryFailedOperations,

    // Utilities
    exportPendingData,
    importPendingData,

    // Computed values
    hasPendingChanges: pendingOperations.length > 0,
    hasConflicts: conflicts.length > 0,
    canSync: syncStatus.isOnline && isConnected && !syncStatus.syncInProgress,
  };
}

// Helper function to merge conflicting data
function mergeData(localData: any, serverData: any): any {
  if (!localData || !serverData) {
    return serverData || localData;
  }

  if (typeof localData !== 'object' || typeof serverData !== 'object') {
    return serverData; // Prefer server for primitive values
  }

  const merged = { ...serverData };

  // Simple merge strategy: prefer local changes for specific fields
  const localOnlyFields = ['notes', 'tags', 'metadata'];
  
  for (const field of localOnlyFields) {
    if (localData[field] !== undefined) {
      merged[field] = localData[field];
    }
  }

  // For arrays, merge unique values
  Object.keys(localData).forEach(key => {
    if (Array.isArray(localData[key]) && Array.isArray(serverData[key])) {
      merged[key] = [...new Set([...serverData[key], ...localData[key]])];
    }
  });

  return merged;
}

export type { DataOperation, ConflictResolution, SyncStatus };