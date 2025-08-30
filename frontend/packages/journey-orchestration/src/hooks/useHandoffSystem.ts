import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@dotmac/auth';
import type { HandoffRecord, UseHandoffSystemReturn } from '../types';
import { HandoffSystem } from '../handoffs/HandoffSystem';
import { JourneyEventBus } from '../events/EventBus';

/**
 * Hook for handoff system management
 */
export function useHandoffSystem(): UseHandoffSystemReturn {
  const { tenantId, user } = useAuth();
  const handoffSystemRef = useRef<HandoffSystem | null>(null);
  const eventBusRef = useRef<JourneyEventBus | null>(null);

  // State
  const [activeHandoffs, setActiveHandoffs] = useState<HandoffRecord[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<HandoffRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize handoff system
  useEffect(() => {
    if (!tenantId) return;

    try {
      handoffSystemRef.current = new HandoffSystem(tenantId);
      eventBusRef.current = JourneyEventBus.getInstance(tenantId);

      // Set up event listeners for handoff updates
      const unsubscribeHandoffStarted = eventBusRef.current.onEventType('handoff:started', () => {
        refreshHandoffs();
      });

      const unsubscribeHandoffCompleted = eventBusRef.current.onEventType('handoff:completed', () => {
        refreshHandoffs();
      });

      // Load initial handoffs
      refreshHandoffs();

      return () => {
        unsubscribeHandoffStarted();
        unsubscribeHandoffCompleted();
        handoffSystemRef.current?.destroy();
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize handoff system');
      setLoading(false);
    }
  }, [tenantId]);

  // Refresh handoffs data
  const refreshHandoffs = useCallback((): void => {
    if (!handoffSystemRef.current) return;

    try {
      setLoading(true);
      setError(null);

      const active = handoffSystemRef.current.getActiveHandoffs();
      const pending = handoffSystemRef.current.getPendingApprovals();

      setActiveHandoffs(active);
      setPendingApprovals(pending);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh handoffs');
    } finally {
      setLoading(false);
    }
  }, []);

  // Create handoff
  const createHandoff = useCallback(async (handoffData: Omit<HandoffRecord, 'id'>): Promise<HandoffRecord> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      const handoff = await handoffSystemRef.current.createHandoff({
        ...handoffData,
        assignedTo: handoffData.assignedTo || user?.id
      });

      refreshHandoffs();
      return handoff;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create handoff';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [user?.id, refreshHandoffs]);

  // Process handoff
  const processHandoff = useCallback(async (handoffId: string): Promise<void> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      await handoffSystemRef.current.processHandoff(handoffId);
      refreshHandoffs();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to process handoff';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [refreshHandoffs]);

  // Approve handoff
  const approveHandoff = useCallback(async (handoffId: string, notes?: string): Promise<void> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      await handoffSystemRef.current.approveHandoff(handoffId, notes);
      refreshHandoffs();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to approve handoff';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [refreshHandoffs]);

  // Reject handoff
  const rejectHandoff = useCallback(async (handoffId: string, reason: string): Promise<void> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      await handoffSystemRef.current.rejectHandoff(handoffId, reason);
      refreshHandoffs();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reject handoff';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [refreshHandoffs]);

  // Bulk process handoffs
  const bulkProcessHandoffs = useCallback(async (handoffIds: string[]): Promise<void> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      await handoffSystemRef.current.bulkProcessHandoffs(handoffIds);
      refreshHandoffs();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to bulk process handoffs';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [refreshHandoffs]);

  // Get handoff status
  const getHandoffStatus = useCallback(async (handoffId: string): Promise<HandoffRecord> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      const activeHandoff = activeHandoffs.find(h => h.id === handoffId);
      if (activeHandoff) {
        return activeHandoff;
      }

      // If not in active handoffs, it might be completed or failed
      throw new Error(`Handoff ${handoffId} not found in active handoffs`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get handoff status';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [activeHandoffs]);

  // Get failed handoffs
  const getFailedHandoffs = useCallback(async (): Promise<HandoffRecord[]> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      return handoffSystemRef.current.getFailedHandoffs();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get failed handoffs';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Retry failed handoffs
  const retryFailedHandoffs = useCallback(async (handoffIds: string[]): Promise<void> => {
    if (!handoffSystemRef.current) {
      throw new Error('Handoff system not initialized');
    }

    try {
      setError(null);
      await handoffSystemRef.current.retryFailedHandoffs(handoffIds);
      refreshHandoffs();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to retry handoffs';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [refreshHandoffs]);

  // Auto-refresh handoffs periodically
  useEffect(() => {
    if (!tenantId) return;

    const interval = setInterval(refreshHandoffs, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [tenantId, refreshHandoffs]);

  return {
    // State
    activeHandoffs,
    pendingApprovals,
    loading,
    error,

    // Handoff management
    createHandoff,
    processHandoff,
    approveHandoff,
    rejectHandoff,

    // Bulk operations
    bulkProcessHandoffs,

    // Monitoring
    getHandoffStatus,
    getFailedHandoffs,
    retryFailedHandoffs
  };
}
