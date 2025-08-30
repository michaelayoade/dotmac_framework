import { useState, useCallback } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  ProjectTask,
  TaskCreate,
  TaskUpdate,
  TaskFilters,
  TaskStatus,
  UseTasksResult
} from '../types';

const API_ENDPOINTS = {
  TASKS: '/api/projects/tasks',
  TASK_STATUS: '/api/projects/tasks/status',
  TASK_ASSIGN: '/api/projects/tasks/assign',
  TASK_COMMENTS: '/api/projects/tasks/comments'
} as const;

export function useTasks(): UseTasksResult {
  const [tasks, setTasks] = useState<ProjectTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const createTask = useCallback(async (projectId: string, data: TaskCreate): Promise<ProjectTask> => {
    try {
      setError(null);

      const response = await apiClient.post<ProjectTask>(API_ENDPOINTS.TASKS, {
        ...data,
        project_id: projectId
      });

      // Add to local state
      setTasks(prev => [response.data, ...prev]);

      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create task';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const updateTask = useCallback(async (taskId: string, data: TaskUpdate): Promise<ProjectTask> => {
    try {
      setError(null);

      const response = await apiClient.put<ProjectTask>(`${API_ENDPOINTS.TASKS}/${taskId}`, data);

      // Update in local state
      setTasks(prev => prev.map(task =>
        task.id === taskId ? response.data : task
      ));

      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update task';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const deleteTask = useCallback(async (taskId: string): Promise<void> => {
    try {
      setError(null);

      await apiClient.delete(`${API_ENDPOINTS.TASKS}/${taskId}`);

      // Remove from local state
      setTasks(prev => prev.filter(task => task.id !== taskId));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete task';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const assignTask = useCallback(async (taskId: string, userId: string): Promise<void> => {
    try {
      setError(null);

      await apiClient.patch(`${API_ENDPOINTS.TASK_ASSIGN}/${taskId}`, {
        assigned_to: userId
      });

      // Update local state
      setTasks(prev => prev.map(task =>
        task.id === taskId
          ? { ...task, assigned_to: userId, updated_at: new Date().toISOString() }
          : task
      ));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to assign task';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const changeTaskStatus = useCallback(async (taskId: string, status: TaskStatus): Promise<void> => {
    try {
      setError(null);

      const updateData: Partial<TaskUpdate> = {
        task_status: status
      };

      // Set completion date if marking as done
      if (status === TaskStatus.DONE) {
        updateData.completed_date = new Date().toISOString();
      }

      await apiClient.patch(`${API_ENDPOINTS.TASK_STATUS}/${taskId}`, updateData);

      // Update local state
      setTasks(prev => prev.map(task =>
        task.id === taskId
          ? {
              ...task,
              task_status: status,
              completed_date: updateData.completed_date || task.completed_date,
              updated_at: new Date().toISOString()
            }
          : task
      ));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to change task status';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const addTaskComment = useCallback(async (taskId: string, comment: string): Promise<void> => {
    try {
      setError(null);

      await apiClient.post(`${API_ENDPOINTS.TASK_COMMENTS}/${taskId}`, {
        comment
      });

      // Note: In a real implementation, you might want to fetch updated task
      // with comments or manage comments separately
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to add comment';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const getTasksByProject = useCallback(async (
    projectId: string,
    filters?: TaskFilters
  ): Promise<ProjectTask[]> => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        project_id: projectId,
        ...filters
      };

      const response = await apiClient.get<{ tasks: ProjectTask[] }>(API_ENDPOINTS.TASKS, {
        params
      });

      setTasks(response.data.tasks);
      return response.data.tasks;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch tasks';
      setError(message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  const getTasksByUser = useCallback(async (
    userId: string,
    filters?: TaskFilters
  ): Promise<ProjectTask[]> => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        assigned_to: userId,
        ...filters
      };

      const response = await apiClient.get<{ tasks: ProjectTask[] }>(API_ENDPOINTS.TASKS, {
        params
      });

      return response.data.tasks;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch user tasks';
      setError(message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  const refreshTasks = useCallback(async (): Promise<void> => {
    // This would typically refresh the current view
    // For now, we'll just clear the error
    setError(null);
  }, []);

  return {
    tasks,
    loading,
    error,

    // Task management
    createTask,
    updateTask,
    deleteTask,

    // Task operations
    assignTask,
    changeTaskStatus,
    addTaskComment,

    // Filtering and search
    getTasksByProject,
    getTasksByUser,

    // Utilities
    refreshTasks
  };
}
