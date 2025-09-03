/**
 * Project Detail Drawer Component
 * Displays comprehensive project information including tasks and milestones
 */

import React from 'react';
import {
  FolderOpen,
  Calendar,
  DollarSign,
  Users,
  Clock,
  CheckCircle,
  AlertTriangle,
  BarChart3,
  MapPin,
  User,
  X,
} from 'lucide-react';
import { formatCurrency, formatDate } from '@dotmac/utils';

export interface ProjectDetailProps {
  project: {
    id: string;
    name: string;
    description?: string;
    status: string;
    progress: number;
    project_type: string;
    priority: string;
    owner?: { id: string; name: string };
    start_date: string;
    due_date: string;
    budget_allocated: number;
    budget_used_percentage: number;
    team_size: number;
    location?: { id: string; name: string };
    tasks?: Array<{
      id: string;
      name: string;
      status: string;
      progress: number;
      assignee: string;
    }>;
    milestones?: Array<{
      name: string;
      date: string;
      status: string;
    }>;
  };
  isOpen: boolean;
  onClose: () => void;
}

const StatusIcon = ({ status }: { status: string }) => {
  switch (status.toLowerCase()) {
    case 'completed':
      return <CheckCircle className='w-4 h-4 text-green-500' />;
    case 'in_progress':
      return <Clock className='w-4 h-4 text-blue-500' />;
    case 'on_hold':
    case 'pending':
      return <AlertTriangle className='w-4 h-4 text-yellow-500' />;
    case 'cancelled':
      return <X className='w-4 h-4 text-red-500' />;
    default:
      return <FolderOpen className='w-4 h-4 text-gray-500' />;
  }
};

const PriorityBadge = ({ priority }: { priority: string }) => {
  const colors = {
    critical: 'bg-red-100 text-red-800 border-red-200',
    high: 'bg-orange-100 text-orange-800 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-green-100 text-green-800 border-green-200',
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full border ${colors[priority] || colors.medium}`}
    >
      {priority.toUpperCase()}
    </span>
  );
};

export const ProjectDetailDrawer: React.FC<ProjectDetailProps> = ({ project, isOpen, onClose }) => {
  if (!isOpen) return null;

  const budgetUsed = (project.budget_allocated * project.budget_used_percentage) / 100;
  const budgetRemaining = project.budget_allocated - budgetUsed;
  const daysUntilDue = Math.ceil(
    (new Date(project.due_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
  );

  return (
    <div className='fixed inset-0 z-50 overflow-hidden'>
      {/* Backdrop */}
      <div className='absolute inset-0 bg-black/50' onClick={onClose} />

      {/* Drawer */}
      <div className='absolute right-0 top-0 h-full w-full max-w-4xl bg-white shadow-xl'>
        <div className='flex flex-col h-full' data-testid='project-detail-drawer'>
          {/* Header */}
          <div className='flex items-center justify-between px-6 py-4 border-b'>
            <div className='flex items-center gap-3'>
              <FolderOpen className='w-6 h-6 text-blue-600' />
              <div>
                <h2 className='text-xl font-semibold'>Project Details</h2>
                <p className='text-sm text-gray-600'>{project.name}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className='p-2 hover:bg-gray-100 rounded-full transition-colors'
            >
              <X className='w-5 h-5' />
            </button>
          </div>

          {/* Content */}
          <div className='flex-1 overflow-y-auto'>
            <div className='p-6 space-y-6'>
              {/* Status Overview */}
              <div className='bg-gray-50 rounded-lg p-4'>
                <div className='flex items-center justify-between mb-4'>
                  <div className='flex items-center gap-3'>
                    <StatusIcon status={project.status} />
                    <span className='font-medium capitalize'>
                      {project.status.replace('_', ' ')}
                    </span>
                    <PriorityBadge priority={project.priority} />
                  </div>
                  <div className='text-right'>
                    <div className='text-2xl font-bold'>{project.progress}%</div>
                    <div className='text-sm text-gray-600'>Complete</div>
                  </div>
                </div>

                <div className='w-full bg-gray-200 rounded-full h-3 mb-4'>
                  <div
                    className='bg-blue-500 h-3 rounded-full transition-all'
                    style={{ width: `${project.progress}%` }}
                  />
                </div>

                <div className='grid grid-cols-3 gap-4 text-sm'>
                  <div>
                    <span className='text-gray-600'>Days Remaining</span>
                    <div
                      className={`font-medium ${daysUntilDue < 0 ? 'text-red-600' : daysUntilDue < 30 ? 'text-yellow-600' : 'text-green-600'}`}
                    >
                      {daysUntilDue < 0
                        ? `${Math.abs(daysUntilDue)} overdue`
                        : `${daysUntilDue} days`}
                    </div>
                  </div>
                  <div>
                    <span className='text-gray-600'>Budget Used</span>
                    <div className='font-medium'>{project.budget_used_percentage.toFixed(1)}%</div>
                  </div>
                  <div>
                    <span className='text-gray-600'>Team Size</span>
                    <div className='font-medium'>{project.team_size} members</div>
                  </div>
                </div>
              </div>

              {/* Project Information */}
              <div className='grid grid-cols-2 gap-6'>
                <div>
                  <h3 className='text-lg font-semibold mb-3'>Project Information</h3>
                  <div className='space-y-3'>
                    <div className='flex items-center gap-3'>
                      <FolderOpen className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Type</span>
                        <div className='font-medium capitalize'>
                          {project.project_type.replace('_', ' ')}
                        </div>
                      </div>
                    </div>

                    {project.owner && (
                      <div className='flex items-center gap-3'>
                        <User className='w-4 h-4 text-gray-500' />
                        <div>
                          <span className='text-sm text-gray-600'>Project Manager</span>
                          <div className='font-medium'>{project.owner.name}</div>
                        </div>
                      </div>
                    )}

                    {project.location && (
                      <div className='flex items-center gap-3'>
                        <MapPin className='w-4 h-4 text-gray-500' />
                        <div>
                          <span className='text-sm text-gray-600'>Location</span>
                          <div className='font-medium'>{project.location.name}</div>
                        </div>
                      </div>
                    )}

                    <div className='flex items-center gap-3'>
                      <Users className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Team Size</span>
                        <div className='font-medium'>{project.team_size} members</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className='text-lg font-semibold mb-3'>Timeline & Budget</h3>
                  <div className='space-y-3'>
                    <div className='flex items-center gap-3'>
                      <Calendar className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Start Date</span>
                        <div className='font-medium'>{formatDate(project.start_date)}</div>
                      </div>
                    </div>

                    <div className='flex items-center gap-3'>
                      <Calendar className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Due Date</span>
                        <div className='font-medium'>{formatDate(project.due_date)}</div>
                      </div>
                    </div>

                    <div className='flex items-center gap-3'>
                      <DollarSign className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Budget Allocated</span>
                        <div className='font-medium'>
                          {formatCurrency(project.budget_allocated)}
                        </div>
                      </div>
                    </div>

                    <div className='flex items-center gap-3'>
                      <BarChart3 className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Budget Used</span>
                        <div className='font-medium'>{formatCurrency(budgetUsed)}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Description */}
              {project.description && (
                <div>
                  <h3 className='text-lg font-semibold mb-3'>Description</h3>
                  <div className='bg-gray-50 rounded-lg p-4'>
                    <p className='text-gray-700'>{project.description}</p>
                  </div>
                </div>
              )}

              {/* Budget Breakdown */}
              <div>
                <h3 className='text-lg font-semibold mb-3'>Budget Breakdown</h3>
                <div className='bg-gray-50 rounded-lg p-4'>
                  <div className='flex justify-between items-center mb-3'>
                    <span className='font-medium'>Budget Utilization</span>
                    <span className='text-lg font-bold'>
                      {project.budget_used_percentage.toFixed(1)}%
                    </span>
                  </div>

                  <div className='w-full bg-gray-200 rounded-full h-3 mb-4'>
                    <div
                      className={`h-3 rounded-full transition-all ${
                        project.budget_used_percentage > 90
                          ? 'bg-red-500'
                          : project.budget_used_percentage > 75
                            ? 'bg-yellow-500'
                            : 'bg-green-500'
                      }`}
                      style={{ width: `${project.budget_used_percentage}%` }}
                    />
                  </div>

                  <div className='grid grid-cols-3 gap-4 text-sm'>
                    <div className='text-center'>
                      <div className='text-lg font-bold text-gray-900'>
                        {formatCurrency(project.budget_allocated)}
                      </div>
                      <div className='text-gray-600'>Allocated</div>
                    </div>
                    <div className='text-center'>
                      <div className='text-lg font-bold text-blue-600'>
                        {formatCurrency(budgetUsed)}
                      </div>
                      <div className='text-gray-600'>Used</div>
                    </div>
                    <div className='text-center'>
                      <div className='text-lg font-bold text-green-600'>
                        {formatCurrency(budgetRemaining)}
                      </div>
                      <div className='text-gray-600'>Remaining</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tasks */}
              {project.tasks && project.tasks.length > 0 && (
                <div>
                  <h3 className='text-lg font-semibold mb-3'>Tasks</h3>
                  <div className='space-y-2'>
                    {project.tasks.map((task, index) => (
                      <div
                        key={index}
                        className='border rounded-lg p-3 hover:bg-gray-50 transition-colors'
                      >
                        <div className='flex items-center justify-between mb-2'>
                          <div className='flex items-center gap-3'>
                            <StatusIcon status={task.status} />
                            <div>
                              <div className='font-medium'>{task.name}</div>
                              <div className='text-sm text-gray-600'>
                                Assigned to {task.assignee}
                              </div>
                            </div>
                          </div>
                          <div className='text-right'>
                            <div className='text-sm font-medium'>{task.progress}%</div>
                            <div className='text-xs text-gray-500 capitalize'>
                              {task.status.replace('_', ' ')}
                            </div>
                          </div>
                        </div>
                        <div className='w-full bg-gray-200 rounded-full h-2'>
                          <div
                            className='bg-blue-500 h-2 rounded-full transition-all'
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Milestones */}
              {project.milestones && project.milestones.length > 0 && (
                <div>
                  <h3 className='text-lg font-semibold mb-3'>Milestones</h3>
                  <div className='space-y-3'>
                    {project.milestones.map((milestone, index) => (
                      <div
                        key={index}
                        className='flex items-center gap-4 p-3 bg-gray-50 rounded-lg'
                      >
                        <StatusIcon status={milestone.status} />
                        <div className='flex-1'>
                          <div className='font-medium'>{milestone.name}</div>
                          <div className='text-sm text-gray-600'>{formatDate(milestone.date)}</div>
                        </div>
                        <div className='text-sm font-medium capitalize'>
                          {milestone.status.replace('_', ' ')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer Actions */}
          <div className='border-t px-6 py-4 bg-gray-50'>
            <div className='flex justify-between'>
              <div className='flex gap-2'>
                <button className='px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors'>
                  Export Report
                </button>
                <button className='px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors'>
                  View Timeline
                </button>
              </div>
              <div className='flex gap-2'>
                <button className='px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors'>
                  Update Status
                </button>
                <button className='px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors'>
                  Edit Project
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
