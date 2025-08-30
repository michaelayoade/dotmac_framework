import { useState, useEffect, useCallback } from 'react';
import { useApiClient } from '@dotmac/headless';
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectFilters,
  ProjectAnalytics,
  ProjectStatus,
  ProjectType,
  UseProjectsResult
} from '../types';

const API_ENDPOINTS = {
  PROJECTS: '/api/projects',
  PROJECT_ANALYTICS: '/api/projects/analytics',
  PROJECT_STATUS: '/api/projects/status',
  PROJECT_ASSIGN: '/api/projects/assign'
} as const;

export function useProjects(): UseProjectsResult {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useApiClient();

  const createProject = useCallback(async (data: ProjectCreate): Promise<Project> => {
    try {
      setError(null);

      const response = await apiClient.post<Project>(API_ENDPOINTS.PROJECTS, data);

      // Add to local state
      setProjects(prev => [response.data, ...prev]);

      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create project';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const updateProject = useCallback(async (projectId: string, data: ProjectUpdate): Promise<Project> => {
    try {
      setError(null);

      const response = await apiClient.put<Project>(`${API_ENDPOINTS.PROJECTS}/${projectId}`, data);

      // Update in local state
      setProjects(prev => prev.map(project =>
        project.id === projectId ? response.data : project
      ));

      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update project';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const deleteProject = useCallback(async (projectId: string): Promise<void> => {
    try {
      setError(null);

      await apiClient.delete(`${API_ENDPOINTS.PROJECTS}/${projectId}`);

      // Remove from local state
      setProjects(prev => prev.filter(project => project.id !== projectId));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete project';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const getProject = useCallback(async (projectId: string): Promise<Project | null> => {
    try {
      const response = await apiClient.get<Project>(`${API_ENDPOINTS.PROJECTS}/${projectId}`);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch project';
      setError(message);
      return null;
    }
  }, [apiClient]);

  const listProjects = useCallback(async (
    filters?: ProjectFilters,
    page = 1,
    pageSize = 20
  ): Promise<{ projects: Project[]; total: number }> => {
    try {
      setLoading(true);
      setError(null);

      const params = {
        page,
        page_size: pageSize,
        ...filters
      };

      const response = await apiClient.get<{ projects: Project[]; total: number; page: number; page_size: number }>(
        API_ENDPOINTS.PROJECTS,
        { params }
      );

      // Update local state for first page
      if (page === 1) {
        setProjects(response.data.projects);
      }

      return {
        projects: response.data.projects,
        total: response.data.total
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch projects';
      setError(message);
      return { projects: [], total: 0 };
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  const searchProjects = useCallback(async (query: string): Promise<Project[]> => {
    try {
      setError(null);

      const response = await apiClient.get<{ projects: Project[] }>(API_ENDPOINTS.PROJECTS, {
        params: { search: query }
      });

      return response.data.projects;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to search projects';
      setError(message);
      return [];
    }
  }, [apiClient]);

  const changeProjectStatus = useCallback(async (projectId: string, status: ProjectStatus): Promise<void> => {
    try {
      setError(null);

      await apiClient.patch(`${API_ENDPOINTS.PROJECT_STATUS}/${projectId}`, { status });

      // Update local state
      setProjects(prev => prev.map(project =>
        project.id === projectId
          ? { ...project, project_status: status, updated_at: new Date().toISOString() }
          : project
      ));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to change project status';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const assignProjectManager = useCallback(async (projectId: string, managerId: string): Promise<void> => {
    try {
      setError(null);

      await apiClient.patch(`${API_ENDPOINTS.PROJECT_ASSIGN}/${projectId}`, {
        project_manager: managerId
      });

      // Update local state
      setProjects(prev => prev.map(project =>
        project.id === projectId
          ? { ...project, project_manager: managerId, updated_at: new Date().toISOString() }
          : project
      ));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to assign project manager';
      setError(message);
      throw new Error(message);
    }
  }, [apiClient]);

  const getProjectAnalytics = useCallback(async (filters?: ProjectFilters): Promise<ProjectAnalytics> => {
    try {
      const response = await apiClient.get<ProjectAnalytics>(API_ENDPOINTS.PROJECT_ANALYTICS, {
        params: filters
      });

      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch project analytics';
      throw new Error(message);
    }
  }, [apiClient]);

  const refreshProjects = useCallback(async (): Promise<void> => {
    await listProjects();
  }, [listProjects]);

  const getProjectTypes = useCallback((): ProjectType[] => {
    return Object.values(ProjectType);
  }, []);

  const getProjectStatuses = useCallback((): ProjectStatus[] => {
    return Object.values(ProjectStatus);
  }, []);

  // Initial load
  useEffect(() => {
    listProjects();
  }, []);

  return {
    projects,
    loading,
    error,

    // CRUD operations
    createProject,
    updateProject,
    deleteProject,
    getProject,

    // Listing and filtering
    listProjects,
    searchProjects,

    // Project management
    changeProjectStatus,
    assignProjectManager,

    // Analytics
    getProjectAnalytics,

    // Utilities
    refreshProjects,
    getProjectTypes,
    getProjectStatuses
  };
}
