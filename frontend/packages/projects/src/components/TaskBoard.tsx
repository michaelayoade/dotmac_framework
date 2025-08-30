import React, { useState, useEffect } from 'react';
import { Card, Button } from '@dotmac/primitives';
import {
  Plus,
  Filter,
  User,
  Calendar,
  Clock,
  Flag,
  MessageSquare,
  Paperclip
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useTasks } from '../hooks';
import type { TaskBoardProps, ProjectTask, TaskStatus, TaskPriority } from '../types';

const TASK_STATUSES: TaskStatus[] = ['todo', 'in_progress', 'review', 'done'];

const STATUS_CONFIG = {
  todo: {
    title: 'To Do',
    color: 'border-gray-300 bg-gray-50',
    headerColor: 'bg-gray-100',
    textColor: 'text-gray-700'
  },
  in_progress: {
    title: 'In Progress',
    color: 'border-yellow-300 bg-yellow-50',
    headerColor: 'bg-yellow-100',
    textColor: 'text-yellow-700'
  },
  review: {
    title: 'Review',
    color: 'border-blue-300 bg-blue-50',
    headerColor: 'bg-blue-100',
    textColor: 'text-blue-700'
  },
  done: {
    title: 'Done',
    color: 'border-green-300 bg-green-50',
    headerColor: 'bg-green-100',
    textColor: 'text-green-700'
  },
  blocked: {
    title: 'Blocked',
    color: 'border-red-300 bg-red-50',
    headerColor: 'bg-red-100',
    textColor: 'text-red-700'
  },
  cancelled: {
    title: 'Cancelled',
    color: 'border-gray-300 bg-gray-50',
    headerColor: 'bg-gray-100',
    textColor: 'text-gray-500'
  }
};

export const TaskBoard: React.FC<TaskBoardProps> = ({
  projectId,
  userId,
  showFilters = true,
  allowDragDrop = true,
  groupBy = 'status'
}) => {
  const { tasks, loading, error, getTasksByProject, getTasksByUser, changeTaskStatus } = useTasks();
  const [filteredTasks, setFilteredTasks] = useState<ProjectTask[]>([]);
  const [draggedTask, setDraggedTask] = useState<string | null>(null);
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const [filters, setFilters] = useState({
    priority: [] as TaskPriority[],
    assigned_to: '',
    search: ''
  });

  // Load tasks based on project or user
  useEffect(() => {
    const loadTasks = async () => {
      if (projectId) {
        await getTasksByProject(projectId);
      } else if (userId) {
        await getTasksByUser(userId);
      }
    };

    loadTasks();
  }, [projectId, userId, getTasksByProject, getTasksByUser]);

  // Filter tasks
  useEffect(() => {
    let filtered = tasks;

    if (filters.priority.length > 0) {
      filtered = filtered.filter(task => filters.priority.includes(task.task_priority));
    }

    if (filters.assigned_to) {
      filtered = filtered.filter(task => task.assigned_to === filters.assigned_to);
    }

    if (filters.search.trim()) {
      const query = filters.search.toLowerCase();
      filtered = filtered.filter(task =>
        task.task_title.toLowerCase().includes(query) ||
        task.task_description?.toLowerCase().includes(query)
      );
    }

    setFilteredTasks(filtered);
  }, [tasks, filters]);

  const handleDragStart = (taskId: string) => {
    if (!allowDragDrop) return;
    setDraggedTask(taskId);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent, newStatus: TaskStatus) => {
    e.preventDefault();

    if (!allowDragDrop || !draggedTask) return;

    try {
      await changeTaskStatus(draggedTask, newStatus);
      setDraggedTask(null);
    } catch (err) {
      console.error('Failed to update task status:', err);
    }
  };

  const getTasksByStatus = (status: TaskStatus) => {
    return filteredTasks.filter(task => task.task_status === status);
  };

  const getPriorityIcon = (priority: TaskPriority) => {
    const priorityConfig = {
      low: <Flag className="h-3 w-3 text-gray-400" />,
      medium: <Flag className="h-3 w-3 text-blue-400" />,
      high: <Flag className="h-3 w-3 text-yellow-500" />,
      urgent: <Flag className="h-3 w-3 text-red-500" />
    };

    return priorityConfig[priority];
  };

  const getPriorityBadgeClass = (priority: TaskPriority) => {
    const priorityClasses = {
      low: 'bg-gray-100 text-gray-700',
      medium: 'bg-blue-100 text-blue-700',
      high: 'bg-yellow-100 text-yellow-700',
      urgent: 'bg-red-100 text-red-700'
    };

    return `px-2 py-1 text-xs font-medium rounded ${priorityClasses[priority]}`;
  };

  const isOverdue = (dueDate?: string) => {
    return dueDate && new Date(dueDate) < new Date();
  };

  if (loading) {
    return (
      <div className="task-board animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 h-96">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-gray-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50 p-4">
        <div className="text-red-800">
          <h3 className="font-semibold">Error Loading Tasks</h3>
          <p>{error}</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="task-board space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Task Board</h2>
          <p className="text-gray-600">{filteredTasks.length} tasks</p>
        </div>

        <div className="flex items-center gap-2">
          {showFilters && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFiltersPanel(!showFiltersPanel)}
            >
              <Filter className="h-4 w-4" />
              Filters
            </Button>
          )}

          <Button size="sm">
            <Plus className="h-4 w-4" />
            Add Task
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFiltersPanel && (
        <Card className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Priority</label>
              <select
                multiple
                value={filters.priority}
                onChange={(e) => setFilters(prev => ({
                  ...prev,
                  priority: Array.from(e.target.selectedOptions, option => option.value as TaskPriority)
                }))}
                className="w-full p-2 border border-gray-300 rounded-md"
                size={4}
              >
                {(['low', 'medium', 'high', 'urgent'] as TaskPriority[]).map(priority => (
                  <option key={priority} value={priority}>
                    {priority.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Search</label>
              <input
                type="text"
                placeholder="Search tasks..."
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-md"
              />
            </div>

            <div className="flex items-end">
              <Button
                variant="outline"
                onClick={() => setFilters({ priority: [], assigned_to: '', search: '' })}
              >
                Clear Filters
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {TASK_STATUSES.map(status => {
          const config = STATUS_CONFIG[status];
          const statusTasks = getTasksByStatus(status);

          return (
            <div
              key={status}
              className={`min-h-96 rounded-lg border-2 ${config.color}`}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, status)}
            >
              {/* Column Header */}
              <div className={`p-3 rounded-t-lg border-b ${config.headerColor}`}>
                <div className="flex items-center justify-between">
                  <h3 className={`font-semibold ${config.textColor}`}>
                    {config.title}
                  </h3>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.textColor} bg-white bg-opacity-50`}>
                    {statusTasks.length}
                  </span>
                </div>
              </div>

              {/* Task Cards */}
              <div className="p-2 space-y-2">
                {statusTasks.map(task => (
                  <Card
                    key={task.id}
                    className={`p-3 cursor-pointer hover:shadow-md transition-shadow ${
                      draggedTask === task.id ? 'opacity-50' : ''
                    } ${isOverdue(task.due_date) ? 'border-red-200 bg-red-50' : ''}`}
                    draggable={allowDragDrop}
                    onDragStart={() => handleDragStart(task.id)}
                  >
                    {/* Task Header */}
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-sm line-clamp-2">
                        {task.task_title}
                      </h4>
                      {getPriorityIcon(task.task_priority)}
                    </div>

                    {/* Task Description */}
                    {task.task_description && (
                      <p className="text-xs text-gray-600 line-clamp-2 mb-2">
                        {task.task_description}
                      </p>
                    )}

                    {/* Task Meta */}
                    <div className="space-y-2">
                      {/* Due Date */}
                      {task.due_date && (
                        <div className={`flex items-center gap-1 text-xs ${
                          isOverdue(task.due_date) ? 'text-red-600' : 'text-gray-500'
                        }`}>
                          <Calendar className="h-3 w-3" />
                          <span>
                            {formatDistanceToNow(new Date(task.due_date), { addSuffix: true })}
                          </span>
                        </div>
                      )}

                      {/* Assignee */}
                      {task.assigned_to && (
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <User className="h-3 w-3" />
                          <span>{task.assigned_to}</span>
                        </div>
                      )}

                      {/* Time Estimate */}
                      {task.estimated_hours && (
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <Clock className="h-3 w-3" />
                          <span>{task.estimated_hours}h</span>
                        </div>
                      )}

                      {/* Tags */}
                      {task.tags && task.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {task.tags.slice(0, 2).map(tag => (
                            <span
                              key={tag}
                              className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                            >
                              {tag}
                            </span>
                          ))}
                          {task.tags.length > 2 && (
                            <span className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                              +{task.tags.length - 2}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Task Footer */}
                    <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100">
                      <div className="flex items-center gap-2">
                        {/* Comments count */}
                        {task.comments && task.comments.length > 0 && (
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            <MessageSquare className="h-3 w-3" />
                            <span>{task.comments.length}</span>
                          </div>
                        )}

                        {/* Attachments count */}
                        {task.attachments && task.attachments.length > 0 && (
                          <div className="flex items-center gap-1 text-xs text-gray-500">
                            <Paperclip className="h-3 w-3" />
                            <span>{task.attachments.length}</span>
                          </div>
                        )}
                      </div>

                      {/* Priority badge */}
                      <span className={getPriorityBadgeClass(task.task_priority)}>
                        {task.task_priority}
                      </span>
                    </div>

                    {/* Checklist Progress */}
                    {task.checklist_items && task.checklist_items.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-100">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-1">
                            <div
                              className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                              style={{
                                width: `${(task.checklist_items.filter(item => item.completed).length / task.checklist_items.length) * 100}%`
                              }}
                            ></div>
                          </div>
                          <span className="text-xs text-gray-500">
                            {task.checklist_items.filter(item => item.completed).length}/{task.checklist_items.length}
                          </span>
                        </div>
                      </div>
                    )}
                  </Card>
                ))}

                {/* Add Task Button */}
                {statusTasks.length === 0 && (
                  <button className="w-full p-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors">
                    <Plus className="h-5 w-5 mx-auto mb-1" />
                    <span className="text-sm">Add task</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
