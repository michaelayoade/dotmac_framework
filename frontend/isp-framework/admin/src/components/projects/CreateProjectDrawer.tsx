/**
 * Create Project Drawer Component
 * Form for creating new infrastructure projects
 */

import React, { useState } from 'react';
import { FolderOpen, X, Plus, AlertTriangle } from 'lucide-react';

export interface CreateProjectDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (project: any) => void;
}

export const CreateProjectDrawer: React.FC<CreateProjectDrawerProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    project_type: 'network_expansion',
    priority: 'medium',
    owner_id: '',
    start_date: '',
    due_date: '',
    budget_allocated: '',
    location_id: '',
    team_size: '1',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const projectTypes = [
    { value: 'network_expansion', label: 'Network Expansion' },
    { value: 'infrastructure_upgrade', label: 'Infrastructure Upgrade' },
    { value: 'customer_deployment', label: 'Customer Deployment' },
    { value: 'maintenance', label: 'Maintenance' },
    { value: 'emergency_repair', label: 'Emergency Repair' },
    { value: 'fiber_installation', label: 'Fiber Installation' },
  ];

  const priorities = [
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Project name is required';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    if (!formData.start_date) {
      newErrors.start_date = 'Start date is required';
    }

    if (!formData.due_date) {
      newErrors.due_date = 'Due date is required';
    } else if (
      formData.start_date &&
      new Date(formData.due_date) <= new Date(formData.start_date)
    ) {
      newErrors.due_date = 'Due date must be after start date';
    }

    if (!formData.budget_allocated || parseFloat(formData.budget_allocated) <= 0) {
      newErrors.budget_allocated = 'Budget must be greater than 0';
    }

    if (!formData.team_size || parseInt(formData.team_size) < 1) {
      newErrors.team_size = 'Team size must be at least 1';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (validateForm()) {
      onSubmit({
        ...formData,
        id: `proj-${Date.now()}`, // Temporary ID
        status: 'planning', // New projects start in planning
        progress: 0,
        budget_allocated: parseFloat(formData.budget_allocated),
        budget_used_percentage: 0,
        team_size: parseInt(formData.team_size),
        owner: formData.owner_id ? { id: formData.owner_id, name: 'Project Manager' } : null,
        location: formData.location_id
          ? { id: formData.location_id, name: 'Project Location' }
          : null,
        created_at: new Date().toISOString(),
      });

      // Reset form
      setFormData({
        name: '',
        description: '',
        project_type: 'network_expansion',
        priority: 'medium',
        owner_id: '',
        start_date: '',
        due_date: '',
        budget_allocated: '',
        location_id: '',
        team_size: '1',
      });

      onClose();
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  // Calculate project duration in days
  const getProjectDuration = () => {
    if (formData.start_date && formData.due_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.due_date);
      const diffTime = Math.abs(end.getTime() - start.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays;
    }
    return 0;
  };

  if (!isOpen) return null;

  return (
    <div className='fixed inset-0 z-50 overflow-hidden'>
      {/* Backdrop */}
      <div className='absolute inset-0 bg-black/50' onClick={onClose} />

      {/* Drawer */}
      <div className='absolute right-0 top-0 h-full w-full max-w-xl bg-white shadow-xl'>
        <form
          onSubmit={handleSubmit}
          className='flex flex-col h-full'
          data-testid='create-project-drawer'
        >
          {/* Header */}
          <div className='flex items-center justify-between px-6 py-4 border-b'>
            <div className='flex items-center gap-3'>
              <Plus className='w-6 h-6 text-blue-600' />
              <div>
                <h2 className='text-xl font-semibold'>Create New Project</h2>
                <p className='text-sm text-gray-600'>Set up a new infrastructure project</p>
              </div>
            </div>
            <button
              type='button'
              onClick={onClose}
              className='p-2 hover:bg-gray-100 rounded-full transition-colors'
            >
              <X className='w-5 h-5' />
            </button>
          </div>

          {/* Form Content */}
          <div className='flex-1 overflow-y-auto p-6 space-y-6'>
            {/* Basic Information */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Basic Information</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Project Name *</label>
                  <input
                    type='text'
                    value={formData.name}
                    onChange={(e) => handleChange('name', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.name ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., Downtown Fiber Expansion'
                    data-testid='project-name-input'
                  />
                  {errors.name && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.name}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Project Type *</label>
                  <select
                    value={formData.project_type}
                    onChange={(e) => handleChange('project_type', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='project-type-select'
                  >
                    {projectTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Priority *</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => handleChange('priority', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='project-priority-select'
                  >
                    {priorities.map((priority) => (
                      <option key={priority.value} value={priority.value}>
                        {priority.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Description *</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleChange('description', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.description ? 'border-red-300' : 'border-gray-300'
                    }`}
                    rows={3}
                    placeholder='Describe the project objectives and scope'
                    data-testid='project-description-input'
                  />
                  {errors.description && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.description}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Timeline</h3>

              <div className='space-y-4'>
                <div className='grid grid-cols-2 gap-4'>
                  <div>
                    <label className='block text-sm font-medium mb-2'>Start Date *</label>
                    <input
                      type='date'
                      value={formData.start_date}
                      onChange={(e) => handleChange('start_date', e.target.value)}
                      className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        errors.start_date ? 'border-red-300' : 'border-gray-300'
                      }`}
                      data-testid='start-date-input'
                    />
                    {errors.start_date && (
                      <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                        <AlertTriangle className='w-4 h-4' />
                        {errors.start_date}
                      </div>
                    )}
                  </div>

                  <div>
                    <label className='block text-sm font-medium mb-2'>Due Date *</label>
                    <input
                      type='date'
                      value={formData.due_date}
                      onChange={(e) => handleChange('due_date', e.target.value)}
                      className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        errors.due_date ? 'border-red-300' : 'border-gray-300'
                      }`}
                      data-testid='due-date-input'
                    />
                    {errors.due_date && (
                      <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                        <AlertTriangle className='w-4 h-4' />
                        {errors.due_date}
                      </div>
                    )}
                  </div>
                </div>

                {getProjectDuration() > 0 && (
                  <div className='bg-blue-50 rounded-lg p-3'>
                    <div className='text-sm text-blue-800'>
                      <strong>Project Duration:</strong> {getProjectDuration()} days
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Budget & Resources */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Budget & Resources</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Budget Allocated *</label>
                  <div className='relative'>
                    <div className='absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none'>
                      <span className='text-gray-500 sm:text-sm'>$</span>
                    </div>
                    <input
                      type='number'
                      value={formData.budget_allocated}
                      onChange={(e) => handleChange('budget_allocated', e.target.value)}
                      className={`w-full pl-7 pr-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        errors.budget_allocated ? 'border-red-300' : 'border-gray-300'
                      }`}
                      placeholder='0.00'
                      min='0'
                      step='0.01'
                      data-testid='budget-input'
                    />
                  </div>
                  {errors.budget_allocated && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.budget_allocated}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Team Size *</label>
                  <input
                    type='number'
                    value={formData.team_size}
                    onChange={(e) => handleChange('team_size', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.team_size ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='Number of team members'
                    min='1'
                    data-testid='team-size-input'
                  />
                  {errors.team_size && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.team_size}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Assignment */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Assignment</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Project Manager</label>
                  <select
                    value={formData.owner_id}
                    onChange={(e) => handleChange('owner_id', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='owner-select'
                  >
                    <option value=''>Select Project Manager</option>
                    <option value='user-001'>Sarah Johnson</option>
                    <option value='user-002'>Mike Chen</option>
                    <option value='user-003'>Lisa Wang</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Location</label>
                  <select
                    value={formData.location_id}
                    onChange={(e) => handleChange('location_id', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='location-select'
                  >
                    <option value=''>Select Location</option>
                    <option value='loc-001'>Downtown District</option>
                    <option value='loc-002'>Seattle Data Center</option>
                    <option value='loc-003'>Tech Plaza</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Project Summary */}
            {formData.name && formData.budget_allocated && (
              <div>
                <h3 className='text-lg font-semibold mb-4'>Project Summary</h3>
                <div className='bg-gray-50 rounded-lg p-4'>
                  <div className='space-y-2 text-sm'>
                    <div className='flex justify-between'>
                      <span className='text-gray-600'>Project:</span>
                      <span className='font-medium'>{formData.name}</span>
                    </div>
                    <div className='flex justify-between'>
                      <span className='text-gray-600'>Type:</span>
                      <span className='font-medium capitalize'>
                        {formData.project_type.replace('_', ' ')}
                      </span>
                    </div>
                    <div className='flex justify-between'>
                      <span className='text-gray-600'>Priority:</span>
                      <span className='font-medium capitalize'>{formData.priority}</span>
                    </div>
                    <div className='flex justify-between'>
                      <span className='text-gray-600'>Budget:</span>
                      <span className='font-medium'>
                        ${parseFloat(formData.budget_allocated || '0').toLocaleString()}
                      </span>
                    </div>
                    {getProjectDuration() > 0 && (
                      <div className='flex justify-between'>
                        <span className='text-gray-600'>Duration:</span>
                        <span className='font-medium'>{getProjectDuration()} days</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className='border-t px-6 py-4 bg-gray-50'>
            <div className='flex justify-end gap-3'>
              <button
                type='button'
                onClick={onClose}
                className='px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors'
              >
                Cancel
              </button>
              <button
                type='submit'
                className='px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center gap-2'
                data-testid='create-project-submit'
              >
                <FolderOpen className='w-4 h-4' />
                Create Project
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
