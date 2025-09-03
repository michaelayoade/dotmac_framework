import { useState, useEffect, useCallback, useRef } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  TimeEntry,
  TimeEntryCreate,
  TimeTrackingAnalytics,
  UseTimeTrackingResult,
} from '../types';

const API_ENDPOINTS = {
  TIME_ENTRIES: '/api/projects/time-entries',
  TIME_ANALYTICS: '/api/projects/time-entries/analytics',
  TIMER_START: '/api/projects/time-entries/timer/start',
  TIMER_STOP: '/api/projects/time-entries/timer/stop',
} as const;

export function useTimeTracking(): UseTimeTrackingResult {
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [currentEntry, setCurrentEntry] = useState<TimeEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentDuration, setCurrentDuration] = useState(0);

  const timerInterval = useRef<NodeJS.Timeout | null>(null);
  const apiClient = useApiClient();

  const isTimerRunning = currentEntry !== null && !currentEntry.end_time;

  // Update current duration when timer is running
  useEffect(() => {
    if (isTimerRunning && currentEntry) {
      if (timerInterval.current) {
        clearInterval(timerInterval.current);
      }

      timerInterval.current = setInterval(() => {
        const startTime = new Date(currentEntry.start_time).getTime();
        const now = Date.now();
        const durationMs = now - startTime;
        setCurrentDuration(Math.floor(durationMs / 1000)); // Duration in seconds
      }, 1000);

      return () => {
        if (timerInterval.current) {
          clearInterval(timerInterval.current);
        }
      };
    } else {
      if (timerInterval.current) {
        clearInterval(timerInterval.current);
      }
      setCurrentDuration(0);
    }
  }, [isTimerRunning, currentEntry]);

  const startTimer = useCallback(
    async (projectId: string, taskId?: string, description?: string): Promise<TimeEntry> => {
      try {
        setError(null);

        // Stop any existing timer first
        if (currentEntry && !currentEntry.end_time) {
          await stopTimer();
        }

        const response = await apiClient.post<TimeEntry>(API_ENDPOINTS.TIMER_START, {
          project_id: projectId,
          task_id: taskId,
          description: description || 'Working on project',
          activity_type: 'development',
          billable: true,
        });

        setCurrentEntry(response.data);
        return response.data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to start timer';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient, currentEntry]
  );

  const stopTimer = useCallback(async (): Promise<TimeEntry> => {
    try {
      setError(null);

      if (!currentEntry || currentEntry.end_time) {
        throw new Error('No active timer to stop');
      }

      const response = await apiClient.post<TimeEntry>(
        `${API_ENDPOINTS.TIMER_STOP}/${currentEntry.id}`
      );

      // Add to time entries list
      setTimeEntries((prev) => [response.data, ...prev]);
      setCurrentEntry(null);
      setCurrentDuration(0);

      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to stop timer';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient, currentEntry]);

  const createTimeEntry = useCallback(
    async (data: TimeEntryCreate): Promise<TimeEntry> => {
      try {
        setError(null);

        // Calculate duration if not provided
        if (!data.duration_minutes && data.start_time && data.end_time) {
          const startTime = new Date(data.start_time).getTime();
          const endTime = new Date(data.end_time).getTime();
          const durationMs = endTime - startTime;
          data.duration_minutes = Math.floor(durationMs / (1000 * 60));
        }

        const response = await apiClient.post<TimeEntry>(API_ENDPOINTS.TIME_ENTRIES, data);

        // Add to local state
        setTimeEntries((prev) => [response.data, ...prev]);

        return response.data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create time entry';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient]
  );

  const updateTimeEntry = useCallback(
    async (entryId: string, data: Partial<TimeEntryCreate>): Promise<TimeEntry> => {
      try {
        setError(null);

        // Recalculate duration if times are updated
        if (data.start_time || data.end_time) {
          const entry = timeEntries.find((e) => e.id === entryId);
          if (entry) {
            const startTime = new Date(data.start_time || entry.start_time).getTime();
            const endTime = new Date(data.end_time || entry.end_time || Date.now()).getTime();
            const durationMs = endTime - startTime;
            data.duration_minutes = Math.floor(durationMs / (1000 * 60));
          }
        }

        const response = await apiClient.put<TimeEntry>(
          `${API_ENDPOINTS.TIME_ENTRIES}/${entryId}`,
          data
        );

        // Update in local state
        setTimeEntries((prev) =>
          prev.map((entry) => (entry.id === entryId ? response.data : entry))
        );

        return response.data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update time entry';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient, timeEntries]
  );

  const deleteTimeEntry = useCallback(
    async (entryId: string): Promise<void> => {
      try {
        setError(null);

        await apiClient.delete(`${API_ENDPOINTS.TIME_ENTRIES}/${entryId}`);

        // Remove from local state
        setTimeEntries((prev) => prev.filter((entry) => entry.id !== entryId));
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete time entry';
        setError(message);
        throw new Error(message);
      }
    },
    [apiClient]
  );

  const getTimeTrackingAnalytics = useCallback(
    async (filters?: {
      projectId?: string;
      userId?: string;
      dateRange?: [string, string];
    }): Promise<TimeTrackingAnalytics> => {
      try {
        const params: Record<string, any> = {};

        if (filters?.projectId) params.project_id = filters.projectId;
        if (filters?.userId) params.user_id = filters.userId;
        if (filters?.dateRange) {
          params.start_date = filters.dateRange[0];
          params.end_date = filters.dateRange[1];
        }

        const response = await apiClient.get<TimeTrackingAnalytics>(API_ENDPOINTS.TIME_ANALYTICS, {
          params,
        });

        return response.data;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Failed to fetch time tracking analytics';
        throw new Error(message);
      }
    },
    [apiClient]
  );

  const refreshTimeEntries = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.get<{ time_entries: TimeEntry[] }>(
        API_ENDPOINTS.TIME_ENTRIES
      );
      setTimeEntries(response.data.time_entries);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to refresh time entries';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  // Load initial data
  useEffect(() => {
    refreshTimeEntries();

    // Check for any active timer on load
    const checkActiveTimer = async () => {
      try {
        const response = await apiClient.get<{ active_timer: TimeEntry | null }>(
          '/api/projects/timer/status'
        );
        if (response.data.active_timer) {
          setCurrentEntry(response.data.active_timer);
        }
      } catch (err) {
        // Silently fail - no active timer
      }
    };

    checkActiveTimer();
  }, [apiClient, refreshTimeEntries]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerInterval.current) {
        clearInterval(timerInterval.current);
      }
    };
  }, []);

  return {
    timeEntries,
    loading,
    error,
    currentEntry,

    // Time tracking
    startTimer,
    stopTimer,
    createTimeEntry,
    updateTimeEntry,
    deleteTimeEntry,

    // Analytics
    getTimeTrackingAnalytics,

    // Utilities
    isTimerRunning,
    currentDuration,
    refreshTimeEntries,
  };
}
