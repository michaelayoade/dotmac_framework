import React, { useState, useMemo } from 'react';
import { Button, Input, Card } from '@dotmac/primitives';
import {
  Search,
  Filter,
  Plus,
  Calendar,
  User,
  Clock,
  CheckCircle,
  AlertTriangle,
  FolderOpen,
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { useProjects } from '../hooks';
import type {
  ProjectListProps,
  ProjectFilters,
  ProjectStatus,
  ProjectType,
  ProjectPriority,
} from '../types';

export const ProjectList: React.FC<ProjectListProps> = ({
  filters: initialFilters,
  showFilters = true,
  showActions = true,
  allowBulkOperations = false,
  onProjectSelect,
}) => {
  const { projects, loading, error, listProjects, getProjectTypes, getProjectStatuses } =
    useProjects();

  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<ProjectFilters>(initialFilters || {});
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(new Set());

  const projectTypes = getProjectTypes();
  const projectStatuses = getProjectStatuses();

  // Filter projects based on current filters and search
  const filteredProjects = useMemo(() => {
    let filtered = projects;

    // Apply search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (project) =>
          project.project_name.toLowerCase().includes(query) ||
          project.description?.toLowerCase().includes(query) ||
          project.project_number.toLowerCase().includes(query) ||
          project.client_name?.toLowerCase().includes(query)
      );
    }

    // Apply filters
    if (filters.project_status && filters.project_status.length > 0) {
      filtered = filtered.filter((p) => filters.project_status!.includes(p.project_status));
    }

    if (filters.project_type && filters.project_type.length > 0) {
      filtered = filtered.filter((p) => filters.project_type!.includes(p.project_type));
    }

    if (filters.priority && filters.priority.length > 0) {
      filtered = filtered.filter((p) => filters.priority!.includes(p.priority));
    }

    if (filters.project_manager) {
      filtered = filtered.filter((p) => p.project_manager === filters.project_manager);
    }

    if (filters.overdue_only) {
      const now = new Date();
      filtered = filtered.filter(
        (p) =>
          p.planned_end_date &&
          new Date(p.planned_end_date) < now &&
          !['completed', 'cancelled'].includes(p.project_status)
      );
    }

    return filtered;
  }, [projects, searchQuery, filters]);

  const handleFilterChange = (key: keyof ProjectFilters, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
  };

  const clearFilters = () => {
    setFilters({});
    setSearchQuery('');
  };

  const handleProjectSelect = (projectId: string, selected: boolean) => {
    const newSelection = new Set(selectedProjects);
    if (selected) {
      newSelection.add(projectId);
    } else {
      newSelection.delete(projectId);
    }
    setSelectedProjects(newSelection);
  };

  const selectAll = () => {
    if (selectedProjects.size === filteredProjects.length) {
      setSelectedProjects(new Set());
    } else {
      setSelectedProjects(new Set(filteredProjects.map((p) => p.id)));
    }
  };

  const getStatusIcon = (status: ProjectStatus) => {
    const statusIcons = {
      planning: <Clock className='h-4 w-4 text-gray-500' />,
      approved: <CheckCircle className='h-4 w-4 text-blue-500' />,
      scheduled: <Calendar className='h-4 w-4 text-purple-500' />,
      in_progress: <Clock className='h-4 w-4 text-yellow-500' />,
      on_hold: <AlertTriangle className='h-4 w-4 text-orange-500' />,
      testing: <CheckCircle className='h-4 w-4 text-blue-500' />,
      completed: <CheckCircle className='h-4 w-4 text-green-500' />,
      cancelled: <AlertTriangle className='h-4 w-4 text-red-500' />,
      failed: <AlertTriangle className='h-4 w-4 text-red-500' />,
    };

    return statusIcons[status] || <Clock className='h-4 w-4 text-gray-500' />;
  };

  const getStatusBadgeClass = (status: ProjectStatus) => {
    const statusClasses = {
      planning: 'bg-gray-100 text-gray-800',
      approved: 'bg-blue-100 text-blue-800',
      scheduled: 'bg-purple-100 text-purple-800',
      in_progress: 'bg-yellow-100 text-yellow-800',
      on_hold: 'bg-orange-100 text-orange-800',
      testing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      failed: 'bg-red-100 text-red-800',
    };

    return `px-2 py-1 text-xs font-medium rounded-full ${statusClasses[status] || 'bg-gray-100 text-gray-800'}`;
  };

  const getPriorityBadgeClass = (priority: ProjectPriority) => {
    const priorityClasses = {
      low: 'bg-gray-100 text-gray-800',
      medium: 'bg-blue-100 text-blue-800',
      high: 'bg-yellow-100 text-yellow-800',
      urgent: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800',
    };

    return `px-2 py-1 text-xs font-medium rounded-full ${priorityClasses[priority]}`;
  };

  if (error) {
    return (
      <Card className='border-red-200 bg-red-50 p-4'>
        <div className='flex items-center gap-2'>
          <AlertTriangle className='h-5 w-5 text-red-600' />
          <div>
            <h3 className='font-semibold text-red-800'>Error Loading Projects</h3>
            <p className='text-red-600'>{error}</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className='project-list space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-xl font-bold'>Projects</h2>
          <p className='text-gray-600'>
            {filteredProjects.length} of {projects.length} projects
          </p>
        </div>

        {showActions && (
          <div className='flex items-center gap-2'>
            <Button>
              <Plus className='h-4 w-4' />
              New Project
            </Button>
          </div>
        )}
      </div>

      {/* Search and Filters */}
      <div className='space-y-4'>
        <div className='flex gap-4'>
          <div className='flex-1 relative'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400' />
            <Input
              placeholder='Search projects...'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className='pl-10'
            />
          </div>

          {showFilters && (
            <Button variant='outline' onClick={() => setShowFiltersPanel(!showFiltersPanel)}>
              <Filter className='h-4 w-4' />
              Filters
            </Button>
          )}
        </div>

        {showFiltersPanel && (
          <Card className='p-4'>
            <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
              <div>
                <label className='block text-sm font-medium mb-2'>Status</label>
                <select
                  multiple
                  value={filters.project_status || []}
                  onChange={(e) =>
                    handleFilterChange(
                      'project_status',
                      Array.from(e.target.selectedOptions, (option) => option.value)
                    )
                  }
                  className='w-full p-2 border border-gray-300 rounded-md h-32'
                >
                  {projectStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status.replace('_', ' ').toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium mb-2'>Type</label>
                <select
                  multiple
                  value={filters.project_type || []}
                  onChange={(e) =>
                    handleFilterChange(
                      'project_type',
                      Array.from(e.target.selectedOptions, (option) => option.value)
                    )
                  }
                  className='w-full p-2 border border-gray-300 rounded-md h-32'
                >
                  {projectTypes.map((type) => (
                    <option key={type} value={type}>
                      {type.replace('_', ' ').toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium mb-2'>Priority</label>
                <select
                  multiple
                  value={filters.priority || []}
                  onChange={(e) =>
                    handleFilterChange(
                      'priority',
                      Array.from(e.target.selectedOptions, (option) => option.value)
                    )
                  }
                  className='w-full p-2 border border-gray-300 rounded-md h-32'
                >
                  {['low', 'medium', 'high', 'urgent', 'critical'].map((priority) => (
                    <option key={priority} value={priority}>
                      {priority.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div className='space-y-3'>
                <div>
                  <label className='flex items-center'>
                    <input
                      type='checkbox'
                      checked={filters.overdue_only || false}
                      onChange={(e) => handleFilterChange('overdue_only', e.target.checked)}
                      className='mr-2'
                    />
                    Show overdue only
                  </label>
                </div>

                <Button variant='outline' onClick={clearFilters} className='w-full'>
                  Clear Filters
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Bulk Operations */}
        {allowBulkOperations && filteredProjects.length > 0 && (
          <Card className='p-4'>
            <div className='flex items-center justify-between'>
              <label className='flex items-center'>
                <input
                  type='checkbox'
                  checked={
                    selectedProjects.size === filteredProjects.length && filteredProjects.length > 0
                  }
                  onChange={selectAll}
                  className='mr-2'
                />
                Select All ({selectedProjects.size} selected)
              </label>

              {selectedProjects.size > 0 && (
                <div className='flex items-center gap-2'>
                  <Button variant='outline' size='sm'>
                    Bulk Update
                  </Button>
                  <Button variant='outline' size='sm'>
                    Export Selected
                  </Button>
                </div>
              )}
            </div>
          </Card>
        )}
      </div>

      {/* Project List */}
      {loading ? (
        <div className='space-y-4'>
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i} className='animate-pulse p-4'>
              <div className='h-6 bg-gray-200 rounded w-1/4 mb-2'></div>
              <div className='h-4 bg-gray-200 rounded w-3/4 mb-2'></div>
              <div className='h-4 bg-gray-200 rounded w-1/2'></div>
            </Card>
          ))}
        </div>
      ) : filteredProjects.length > 0 ? (
        <div className='space-y-4'>
          {filteredProjects.map((project) => {
            const isOverdue =
              project.planned_end_date &&
              new Date(project.planned_end_date) < new Date() &&
              !['completed', 'cancelled'].includes(project.project_status);

            return (
              <Card
                key={project.id}
                className={`p-4 hover:shadow-md transition-shadow cursor-pointer ${
                  isOverdue ? 'border-red-200 bg-red-50' : ''
                }`}
                onClick={() => onProjectSelect?.(project)}
              >
                <div className='flex items-start justify-between'>
                  <div className='flex-1'>
                    <div className='flex items-center gap-3 mb-2'>
                      {allowBulkOperations && (
                        <input
                          type='checkbox'
                          checked={selectedProjects.has(project.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleProjectSelect(project.id, e.target.checked);
                          }}
                          className='rounded'
                        />
                      )}

                      <div className='flex items-center gap-2'>
                        {getStatusIcon(project.project_status)}
                        <h3 className='font-semibold text-gray-900'>{project.project_name}</h3>
                        {isOverdue && <AlertTriangle className='h-4 w-4 text-red-500' />}
                      </div>
                    </div>

                    <div className='flex items-center gap-4 text-sm text-gray-600 mb-2'>
                      <span>{project.project_number}</span>
                      <span>•</span>
                      <span>{project.project_type.replace('_', ' ')}</span>
                      {project.client_name && (
                        <>
                          <span>•</span>
                          <span className='flex items-center gap-1'>
                            <User className='h-3 w-3' />
                            {project.client_name}
                          </span>
                        </>
                      )}
                    </div>

                    {project.description && (
                      <p className='text-sm text-gray-700 mb-3 line-clamp-2'>
                        {project.description}
                      </p>
                    )}

                    <div className='flex items-center gap-4 text-xs text-gray-500'>
                      {project.planned_end_date && (
                        <span className='flex items-center gap-1'>
                          <Calendar className='h-3 w-3' />
                          Due {format(new Date(project.planned_end_date), 'MMM dd, yyyy')}
                        </span>
                      )}

                      <span>
                        Updated{' '}
                        {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
                      </span>

                      {project.project_manager && <span>PM: {project.project_manager}</span>}
                    </div>
                  </div>

                  <div className='flex flex-col items-end gap-2'>
                    <div className='flex items-center gap-2'>
                      <span className={getStatusBadgeClass(project.project_status)}>
                        {project.project_status.replace('_', ' ')}
                      </span>

                      <span className={getPriorityBadgeClass(project.priority)}>
                        {project.priority}
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className='flex items-center gap-2'>
                      <span className='text-xs text-gray-500 w-8'>
                        {project.completion_percentage}%
                      </span>
                      <div className='w-20 bg-gray-200 rounded-full h-2'>
                        <div
                          className='bg-blue-600 h-2 rounded-full transition-all duration-300'
                          style={{ width: `${project.completion_percentage}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Budget info */}
                    {project.approved_budget && (
                      <div className='text-xs text-gray-500'>
                        Budget: ${project.approved_budget.toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className='p-8 text-center'>
          <div className='text-gray-400 mb-4'>
            <FolderOpen className='h-12 w-12 mx-auto' />
          </div>
          <h3 className='text-lg font-medium text-gray-600 mb-2'>No projects found</h3>
          <p className='text-gray-500'>
            {searchQuery || Object.keys(filters).length > 0
              ? 'Try adjusting your search or filters'
              : 'Create your first project to get started'}
          </p>
        </Card>
      )}
    </div>
  );
};
