import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@dotmac/auth';
import type {
  CustomerJourney,
  UseJourneyOrchestrationReturn,
  JourneyTemplate,
  TouchpointRecord,
  HandoffRecord,
} from '../types';
import { JourneyOrchestrator } from '../orchestrator/JourneyOrchestrator';
import { HandoffSystem } from '../handoffs/HandoffSystem';

/**
 * Hook for journey orchestration management
 */
export function useJourneyOrchestration(): UseJourneyOrchestrationReturn {
  const { tenantId, user } = useAuth();
  const orchestratorRef = useRef<JourneyOrchestrator | null>(null);
  const handoffSystemRef = useRef<HandoffSystem | null>(null);

  // State
  const [journeys, setJourneys] = useState<CustomerJourney[]>([]);
  const [activeJourney, setActiveJourney] = useState<CustomerJourney | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize orchestrator
  useEffect(() => {
    if (!tenantId) return;

    try {
      orchestratorRef.current = new JourneyOrchestrator(tenantId, {
        autoProgressEnabled: true,
        persistenceEnabled: true,
      });

      handoffSystemRef.current = new HandoffSystem(tenantId);

      // Subscribe to journey changes
      const journeySubscription = orchestratorRef.current
        .subscribeToJourneys()
        .subscribe((updatedJourneys) => {
          setJourneys(updatedJourneys);
          setLoading(false);
        });

      const activeJourneySubscription = orchestratorRef.current
        .subscribeToActiveJourney()
        .subscribe((journey) => {
          setActiveJourney(journey);
        });

      const stateSubscription = orchestratorRef.current
        .subscribeToStateChanges()
        .subscribe((change) => {
          console.log('Journey state change:', change);
        });

      // Load initial journeys
      const initialJourneys = orchestratorRef.current.getJourneys();
      setJourneys(initialJourneys);
      setLoading(false);

      return () => {
        journeySubscription.unsubscribe();
        activeJourneySubscription.unsubscribe();
        stateSubscription.unsubscribe();
        orchestratorRef.current?.destroy();
        handoffSystemRef.current?.destroy();
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize orchestrator');
      setLoading(false);
    }
  }, [tenantId]);

  // Start new journey
  const startJourney = useCallback(
    async (templateId: string, context: Record<string, any> = {}): Promise<CustomerJourney> => {
      if (!orchestratorRef.current) {
        throw new Error('Orchestrator not initialized');
      }

      try {
        setError(null);
        const journey = await orchestratorRef.current.startJourney(
          templateId,
          { ...context, userId: user?.id },
          context.customerId,
          context.leadId
        );

        return journey;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to start journey';
        setError(errorMessage);
        throw new Error(errorMessage);
      }
    },
    [user?.id]
  );

  // Pause journey
  const pauseJourney = useCallback(async (journeyId: string): Promise<void> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    try {
      setError(null);
      await orchestratorRef.current.pauseJourney(journeyId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to pause journey';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Resume journey
  const resumeJourney = useCallback(async (journeyId: string): Promise<void> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    try {
      setError(null);
      await orchestratorRef.current.resumeJourney(journeyId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to resume journey';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Complete journey
  const completeJourney = useCallback(async (journeyId: string): Promise<void> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    try {
      setError(null);
      await orchestratorRef.current.completeJourney(journeyId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to complete journey';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Abandon journey
  const abandonJourney = useCallback(async (journeyId: string, reason?: string): Promise<void> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    try {
      setError(null);
      await orchestratorRef.current.abandonJourney(journeyId, reason);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to abandon journey';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Advance step
  const advanceStep = useCallback(async (journeyId: string, stepId?: string): Promise<void> => {
    if (!orchestratorRef.current) {
      throw new Error('Orchestrator not initialized');
    }

    try {
      setError(null);
      await orchestratorRef.current.advanceStep(journeyId, stepId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to advance step';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Skip step
  const skipStep = useCallback(
    async (journeyId: string, stepId: string, reason: string): Promise<void> => {
      if (!orchestratorRef.current) {
        throw new Error('Orchestrator not initialized');
      }

      try {
        setError(null);
        await orchestratorRef.current.skipStep(journeyId, stepId, reason);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to skip step';
        setError(errorMessage);
        throw new Error(errorMessage);
      }
    },
    []
  );

  // Retry step
  const retryStep = useCallback(
    async (journeyId: string, stepId: string): Promise<void> => {
      // This would retry a failed step by advancing again
      await advanceStep(journeyId, stepId);
    },
    [advanceStep]
  );

  // Update context
  const updateContext = useCallback(
    async (journeyId: string, updates: Record<string, any>): Promise<void> => {
      if (!orchestratorRef.current) {
        throw new Error('Orchestrator not initialized');
      }

      try {
        setError(null);
        await orchestratorRef.current.updateContext(journeyId, updates);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to update context';
        setError(errorMessage);
        throw new Error(errorMessage);
      }
    },
    []
  );

  // Add touchpoint
  const addTouchpoint = useCallback(
    async (
      journeyId: string,
      touchpoint: Omit<TouchpointRecord, 'id' | 'journeyId'>
    ): Promise<void> => {
      if (!orchestratorRef.current) {
        throw new Error('Orchestrator not initialized');
      }

      try {
        setError(null);
        await orchestratorRef.current.addTouchpoint(journeyId, {
          ...touchpoint,
          userId: touchpoint.userId || user?.id,
        });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to add touchpoint';
        setError(errorMessage);
        throw new Error(errorMessage);
      }
    },
    [user?.id]
  );

  // Initiate handoff
  const initiateHandoff = useCallback(
    async (
      journeyId: string,
      handoff: Omit<HandoffRecord, 'id' | 'journeyId'>
    ): Promise<HandoffRecord> => {
      if (!handoffSystemRef.current) {
        throw new Error('Handoff system not initialized');
      }

      try {
        setError(null);
        return await handoffSystemRef.current.createHandoff({
          ...handoff,
          journeyId,
        });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to initiate handoff';
        setError(errorMessage);
        throw new Error(errorMessage);
      }
    },
    []
  );

  // Complete handoff
  const completeHandoff = useCallback(
    async (handoffId: string, result: Record<string, any>): Promise<void> => {
      if (!handoffSystemRef.current) {
        throw new Error('Handoff system not initialized');
      }

      try {
        setError(null);
        await handoffSystemRef.current.processHandoff(handoffId);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to complete handoff';
        setError(errorMessage);
        throw new Error(errorMessage);
      }
    },
    []
  );

  // Search journeys
  const searchJourneys = useCallback(async (query: string): Promise<CustomerJourney[]> => {
    if (!orchestratorRef.current) {
      return [];
    }

    try {
      setError(null);
      return orchestratorRef.current.searchJourneys(query);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to search journeys');
      return [];
    }
  }, []);

  // Filter journeys
  const filterJourneys = useCallback(async (filters: Record<string, any>): Promise<void> => {
    if (!orchestratorRef.current) {
      return;
    }

    try {
      setError(null);
      const filteredJourneys = orchestratorRef.current.filterJourneys(filters);
      setJourneys(filteredJourneys);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to filter journeys');
    }
  }, []);

  // Subscribe to journey
  const subscribeToJourney = useCallback(
    (journeyId: string, callback: (journey: CustomerJourney) => void): (() => void) => {
      if (!orchestratorRef.current) {
        return () => {};
      }

      const subscription = orchestratorRef.current.subscribeToStateChanges().subscribe((change) => {
        if (change.journeyId === journeyId) {
          const journey = orchestratorRef.current?.getJourney(journeyId);
          if (journey) {
            callback(journey);
          }
        }
      });

      return () => subscription.unsubscribe();
    },
    []
  );

  return {
    // State
    journeys,
    activeJourney,
    loading,
    error,

    // Journey management
    startJourney,
    pauseJourney,
    resumeJourney,
    completeJourney,
    abandonJourney,

    // Step management
    advanceStep,
    skipStep,
    retryStep,

    // Context management
    updateContext,
    addTouchpoint,

    // Handoffs
    initiateHandoff,
    completeHandoff,

    // Search and filter
    searchJourneys,
    filterJourneys,

    // Real-time updates
    subscribeToJourney,
  };
}
