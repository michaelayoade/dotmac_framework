import React, { useEffect, useState } from 'react';
import { Card } from '@dotmac/primitives';
import {
  FolderOpen,
  CheckCircle,
  Clock,
  AlertTriangle,
  Calendar,
  TrendingUp,
  Users,
  DollarSign,
} from 'lucide-react';
import { useProjects, useTimeTracking } from '../hooks';
import type { ProjectDashboardProps, ProjectAnalytics } from '../types';

export const ProjectDashboard: React.FC<ProjectDashboardProps> = ({
  showMetrics = true,
  showRecentProjects = true,
  showTaskSummary = true,
  refreshInterval = 30000,
}) => {
  const { projects, loading, error, getProjectAnalytics } = useProjects();
  const { timeEntries, isTimerRunning, currentDuration } = useTimeTracking();
  const [analytics, setAnalytics] = useState<ProjectAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  const activeProjects = projects.filter((p) => p.project_status === 'in_progress');
  const completedProjects = projects.filter((p) => p.project_status === 'completed');
  const overdueProjects = projects.filter(
    (p) =>
      p.planned_end_date &&
      new Date(p.planned_end_date) < new Date() &&
      !['completed', 'cancelled'].includes(p.project_status)
  );

  const fetchAnalytics = async () => {
    try {
      setAnalyticsLoading(true);
      const data = await getProjectAnalytics();
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();

    const interval = setInterval(fetchAnalytics, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  if (loading) {
    return (
      <div className='project-dashboard loading'>
        <div className='animate-pulse space-y-6'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className='h-24 bg-gray-200 rounded-lg'></div>
            ))}
          </div>
          <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
            {[1, 2].map((i) => (
              <div key={i} className='h-64 bg-gray-200 rounded-lg'></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className='project-dashboard error'>
        <Card className='border-red-200 bg-red-50'>
          <div className='flex items-center gap-2 p-4'>
            <AlertTriangle className='h-5 w-5 text-red-600' />
            <div>
              <h3 className='font-semibold text-red-800'>Dashboard Error</h3>
              <p className='text-red-600'>{error}</p>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className='project-dashboard space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div className='flex items-center gap-3'>
          <FolderOpen className='h-6 w-6 text-primary' />
          <h1 className='text-2xl font-bold'>Project Dashboard</h1>
        </div>

        {isTimerRunning && (
          <div className='flex items-center gap-2 px-4 py-2 bg-green-100 text-green-800 rounded-lg'>
            <Clock className='h-4 w-4 animate-pulse' />
            <span className='font-medium'>
              Timer Running: {Math.floor(currentDuration / 60)}m {currentDuration % 60}s
            </span>
          </div>
        )}
      </div>

      {/* Metrics Cards */}
      {showMetrics && (
        <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
          <Card className='p-4'>
            <div className='flex items-center gap-3'>
              <div className='p-2 bg-blue-100 rounded-lg'>
                <FolderOpen className='h-5 w-5 text-blue-600' />
              </div>
              <div>
                <p className='text-sm text-gray-600'>Total Projects</p>
                <p className='text-2xl font-bold'>{projects.length}</p>
              </div>
            </div>
          </Card>

          <Card className='p-4'>
            <div className='flex items-center gap-3'>
              <div className='p-2 bg-green-100 rounded-lg'>
                <CheckCircle className='h-5 w-5 text-green-600' />
              </div>
              <div>
                <p className='text-sm text-gray-600'>Active</p>
                <p className='text-2xl font-bold text-green-600'>{activeProjects.length}</p>
              </div>
            </div>
          </Card>

          <Card className='p-4'>
            <div className='flex items-center gap-3'>
              <div className='p-2 bg-purple-100 rounded-lg'>
                <TrendingUp className='h-5 w-5 text-purple-600' />
              </div>
              <div>
                <p className='text-sm text-gray-600'>Completed</p>
                <p className='text-2xl font-bold text-purple-600'>{completedProjects.length}</p>
              </div>
            </div>
          </Card>

          <Card className='p-4'>
            <div className='flex items-center gap-3'>
              <div className='p-2 bg-red-100 rounded-lg'>
                <AlertTriangle className='h-5 w-5 text-red-600' />
              </div>
              <div>
                <p className='text-sm text-gray-600'>Overdue</p>
                <p className='text-2xl font-bold text-red-600'>{overdueProjects.length}</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Analytics and Recent Projects */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Project Analytics */}
        {analytics && (
          <Card className='p-6'>
            <h3 className='text-lg font-semibold mb-4 flex items-center gap-2'>
              <TrendingUp className='h-5 w-5' />
              Analytics Overview
            </h3>

            <div className='space-y-4'>
              <div className='grid grid-cols-2 gap-4'>
                <div className='text-center p-3 bg-gray-50 rounded-lg'>
                  <div className='text-2xl font-bold text-blue-600'>
                    {analytics.avg_completion_days}
                  </div>
                  <div className='text-sm text-gray-600'>Avg. Completion Days</div>
                </div>

                <div className='text-center p-3 bg-gray-50 rounded-lg'>
                  <div className='text-2xl font-bold text-green-600'>
                    {analytics.on_time_completion_rate || 0}%
                  </div>
                  <div className='text-sm text-gray-600'>On-Time Rate</div>
                </div>
              </div>

              {/* Status Breakdown */}
              <div>
                <h4 className='font-medium mb-2'>Project Status Distribution</h4>
                <div className='space-y-2'>
                  {Object.entries(analytics.status_breakdown).map(([status, count]) => {
                    const percentage = (count / analytics.total_projects) * 100;
                    const statusColors = {
                      planning: 'bg-gray-400',
                      approved: 'bg-blue-400',
                      in_progress: 'bg-yellow-400',
                      completed: 'bg-green-400',
                      on_hold: 'bg-orange-400',
                      cancelled: 'bg-red-400',
                    };

                    return (
                      <div key={status} className='flex items-center gap-2'>
                        <div className='w-16 text-xs capitalize text-gray-600'>
                          {status.replace('_', ' ')}
                        </div>
                        <div className='flex-1 bg-gray-200 rounded-full h-2'>
                          <div
                            className={`h-2 rounded-full ${statusColors[status as keyof typeof statusColors] || 'bg-gray-400'}`}
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <div className='w-12 text-xs text-gray-600 text-right'>{count}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Recent Projects */}
        {showRecentProjects && (
          <Card className='p-6'>
            <h3 className='text-lg font-semibold mb-4 flex items-center gap-2'>
              <Clock className='h-5 w-5' />
              Recent Projects
            </h3>

            <div className='space-y-3'>
              {projects
                .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
                .slice(0, 6)
                .map((project) => {
                  const statusColors = {
                    planning: 'text-gray-600 bg-gray-100',
                    approved: 'text-blue-600 bg-blue-100',
                    in_progress: 'text-yellow-600 bg-yellow-100',
                    completed: 'text-green-600 bg-green-100',
                    on_hold: 'text-orange-600 bg-orange-100',
                    cancelled: 'text-red-600 bg-red-100',
                  };

                  return (
                    <div
                      key={project.id}
                      className='flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50'
                    >
                      <div className='flex-1'>
                        <h4 className='font-medium text-gray-900 truncate'>
                          {project.project_name}
                        </h4>
                        <p className='text-sm text-gray-500 truncate'>
                          {project.project_number} • {project.project_type.replace('_', ' ')}
                        </p>
                      </div>

                      <div className='flex items-center gap-3'>
                        <div className='text-right'>
                          <div className='text-sm font-medium'>
                            {project.completion_percentage}%
                          </div>
                          <div className='w-16 bg-gray-200 rounded-full h-1.5'>
                            <div
                              className='bg-blue-600 h-1.5 rounded-full'
                              style={{ width: `${project.completion_percentage}%` }}
                            ></div>
                          </div>
                        </div>

                        <span
                          className={`px-2 py-1 text-xs font-medium rounded-full ${
                            statusColors[project.project_status as keyof typeof statusColors]
                          }`}
                        >
                          {project.project_status.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  );
                })}
            </div>

            {projects.length === 0 && (
              <div className='text-center py-8 text-gray-500'>
                <FolderOpen className='h-12 w-12 mx-auto mb-3 opacity-50' />
                <p>No projects found</p>
              </div>
            )}
          </Card>
        )}
      </div>

      {/* Overdue Projects Alert */}
      {overdueProjects.length > 0 && (
        <Card className='border-red-200 bg-red-50 p-4'>
          <div className='flex items-center gap-2 mb-3'>
            <AlertTriangle className='h-5 w-5 text-red-600' />
            <h3 className='font-semibold text-red-800'>Overdue Projects</h3>
          </div>

          <div className='space-y-2'>
            {overdueProjects.slice(0, 5).map((project) => (
              <div key={project.id} className='text-sm text-red-700'>
                <span className='font-medium'>{project.project_name}</span>
                <span className='text-red-600 ml-2'>
                  Due:{' '}
                  {project.planned_end_date &&
                    new Date(project.planned_end_date).toLocaleDateString()}
                </span>
              </div>
            ))}
            {overdueProjects.length > 5 && (
              <p className='text-sm text-red-600'>
                And {overdueProjects.length - 5} more overdue projects...
              </p>
            )}
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <Card className='p-4'>
        <h3 className='font-semibold mb-4'>Quick Actions</h3>
        <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
          <button className='flex flex-col items-center gap-2 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors'>
            <FolderOpen className='h-6 w-6 text-blue-600' />
            <span className='text-sm font-medium'>New Project</span>
          </button>

          <button className='flex flex-col items-center gap-2 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors'>
            <Calendar className='h-6 w-6 text-green-600' />
            <span className='text-sm font-medium'>View Calendar</span>
          </button>

          <button className='flex flex-col items-center gap-2 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors'>
            <Users className='h-6 w-6 text-purple-600' />
            <span className='text-sm font-medium'>Team View</span>
          </button>

          <button className='flex flex-col items-center gap-2 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors'>
            <DollarSign className='h-6 w-6 text-orange-600' />
            <span className='text-sm font-medium'>Budget Report</span>
          </button>
        </div>
      </Card>
    </div>
  );
};
