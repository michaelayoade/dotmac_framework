/**
 * Real-time Sync Hook
 * React hook for managing real-time synchronization with optimistic updates
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { SyncManager, SyncOperation } from '../lib/realtime/sync-manager';

interface UseSyncOptions {
  websocketUrl: string;
  syncInterval?: number;
  maxRetries?: number;
  conflictResolutionStrategy?: 'CLIENT_WINS' | 'SERVER_WINS' | 'MERGE';
  autoConnect?: boolean;
}

interface SyncState {
  isConnected: boolean;
  connectionState: string;
  pendingOperations: number;
  conflicts: number;
  lastSyncTime: Date | null;
  error: string | null;
}

export function useRealtimeSync(options: UseSyncOptions) {
  const {
    websocketUrl,
    syncInterval = 30000,
    maxRetries = 3,
    conflictResolutionStrategy = 'MERGE',
    autoConnect = true,
  } = options;

  const syncManagerRef = useRef<SyncManager | null>(null);
  const [syncState, setSyncState] = useState<SyncState>({
    isConnected: false,
    connectionState: 'CLOSED',
    pendingOperations: 0,
    conflicts: 0,
    lastSyncTime: null,
    error: null,
  });

  const [isInitializing, setIsInitializing] = useState(false);

  // Initialize sync manager
  useEffect(() => {
    if (!autoConnect || syncManagerRef.current) return;

    const initializeSync = async () => {
      setIsInitializing(true);

      try {
        const syncManager = new SyncManager({
          websocketUrl,
          syncInterval,
          maxRetries,
          conflictResolutionStrategy,
        });

        await syncManager.initialize();
        syncManagerRef.current = syncManager;

        setSyncState((prev) => ({
          ...prev,
          isConnected: syncManager.isConnected,
          connectionState: syncManager.connectionState,
          pendingOperations: syncManager.pendingOperationsCount,
          conflicts: syncManager.conflictCount,
          lastSyncTime: new Date(),
          error: null,
        }));
      } catch (error) {
        console.error('Failed to initialize sync manager:', error);
        setSyncState((prev) => ({
          ...prev,
          error: error instanceof Error ? error.message : 'Failed to initialize sync',
        }));
      } finally {
        setIsInitializing(false);
      }
    };

    initializeSync();

    return () => {
      if (syncManagerRef.current) {
        syncManagerRef.current.disconnect();
        syncManagerRef.current = null;
      }
    };
  }, [websocketUrl, syncInterval, maxRetries, conflictResolutionStrategy, autoConnect]);

  // Update sync state periodically
  useEffect(() => {
    const interval = setInterval(() => {
      if (syncManagerRef.current) {
        setSyncState((prev) => ({
          ...prev,
          isConnected: syncManagerRef.current!.isConnected,
          connectionState: syncManagerRef.current!.connectionState,
          pendingOperations: syncManagerRef.current!.pendingOperationsCount,
          conflicts: syncManagerRef.current!.conflictCount,
        }));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const createEntity = useCallback(
    async (entity: 'WORK_ORDER' | 'CUSTOMER' | 'INVENTORY', data: any): Promise<string | null> => {
      if (!syncManagerRef.current) {
        setSyncState((prev) => ({ ...prev, error: 'Sync manager not initialized' }));
        return null;
      }

      try {
        const operationId = await syncManagerRef.current.createOptimisticUpdate(entity, data);
        setSyncState((prev) => ({
          ...prev,
          pendingOperations: syncManagerRef.current!.pendingOperationsCount,
          error: null,
        }));
        return operationId;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to create entity';
        setSyncState((prev) => ({ ...prev, error: errorMessage }));
        return null;
      }
    },
    []
  );

  const updateEntity = useCallback(
    async (
      entity: 'WORK_ORDER' | 'CUSTOMER' | 'INVENTORY',
      id: string,
      data: any
    ): Promise<string | null> => {
      if (!syncManagerRef.current) {
        setSyncState((prev) => ({ ...prev, error: 'Sync manager not initialized' }));
        return null;
      }

      try {
        const operationId = await syncManagerRef.current.updateOptimistically(entity, id, data);
        setSyncState((prev) => ({
          ...prev,
          pendingOperations: syncManagerRef.current!.pendingOperationsCount,
          error: null,
        }));
        return operationId;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to update entity';
        setSyncState((prev) => ({ ...prev, error: errorMessage }));
        return null;
      }
    },
    []
  );

  const deleteEntity = useCallback(
    async (entity: 'WORK_ORDER' | 'CUSTOMER' | 'INVENTORY', id: string): Promise<string | null> => {
      if (!syncManagerRef.current) {
        setSyncState((prev) => ({ ...prev, error: 'Sync manager not initialized' }));
        return null;
      }

      try {
        const operationId = await syncManagerRef.current.deleteOptimistically(entity, id);
        setSyncState((prev) => ({
          ...prev,
          pendingOperations: syncManagerRef.current!.pendingOperationsCount,
          error: null,
        }));
        return operationId;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to delete entity';
        setSyncState((prev) => ({ ...prev, error: errorMessage }));
        return null;
      }
    },
    []
  );

  const getConflicts = useCallback(async (): Promise<SyncOperation[]> => {
    if (!syncManagerRef.current) {
      return [];
    }

    try {
      return await syncManagerRef.current.getConflicts();
    } catch (error) {
      console.error('Failed to get conflicts:', error);
      return [];
    }
  }, []);

  const resolveConflict = useCallback(
    async (
      operationId: string,
      strategy: 'CLIENT_WINS' | 'SERVER_WINS' | 'MERGE',
      resolvedData?: any
    ): Promise<boolean> => {
      if (!syncManagerRef.current) {
        setSyncState((prev) => ({ ...prev, error: 'Sync manager not initialized' }));
        return false;
      }

      try {
        await syncManagerRef.current.resolveConflictManually(operationId, {
          strategy,
          resolvedData,
        });

        setSyncState((prev) => ({
          ...prev,
          conflicts: syncManagerRef.current!.conflictCount,
          error: null,
        }));

        return true;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to resolve conflict';
        setSyncState((prev) => ({ ...prev, error: errorMessage }));
        return false;
      }
    },
    []
  );

  const connect = useCallback(async (): Promise<boolean> => {
    if (!syncManagerRef.current) {
      return false;
    }

    try {
      await syncManagerRef.current.initialize();
      setSyncState((prev) => ({
        ...prev,
        isConnected: syncManagerRef.current!.isConnected,
        connectionState: syncManagerRef.current!.connectionState,
        error: null,
      }));
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to connect';
      setSyncState((prev) => ({ ...prev, error: errorMessage }));
      return false;
    }
  }, []);

  const disconnect = useCallback(async (): Promise<void> => {
    if (syncManagerRef.current) {
      await syncManagerRef.current.disconnect();
      setSyncState((prev) => ({
        ...prev,
        isConnected: false,
        connectionState: 'CLOSED',
      }));
    }
  }, []);

  const clearError = useCallback(() => {
    setSyncState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    // State
    ...syncState,
    isInitializing,

    // Operations
    createEntity,
    updateEntity,
    deleteEntity,

    // Conflict Resolution
    getConflicts,
    resolveConflict,

    // Connection Management
    connect,
    disconnect,

    // Utilities
    clearError,
  };
}
