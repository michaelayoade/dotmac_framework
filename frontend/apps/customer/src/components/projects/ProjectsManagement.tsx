'use client';

import React, { useState } from 'react';
import { ManagementPageTemplate } from '@dotmac/primitives/templates/ManagementPageTemplate';
import { 
  PlusIcon,
  EyeIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  WrenchScrewdriverIcon,
  BuildingOffice2Icon,
  SignalIcon
} from '@heroicons/react/24/outline';

interface Project {
  id: string;
  title: string;
  description: string;
  type: 'installation' | 'upgrade' | 'maintenance' | 'repair' | 'expansion';
  status: 'requested' | 'approved' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  requestDate: string;
  scheduledDate?: string;
  completionDate?: string;
  estimatedCost?: number;
  actualCost?: number;
  assignedTechnician?: string;
  workOrderId?: string;
  address: string;
  requirements: string[];
  notes?: string;
  attachments: {
    id: string;
    name: string;
    type: string;
    url: string;
  }[];
}

const mockProjects: Project[] = [
  {
    id: '1',
    title: 'Fiber Internet Installation',
    description: 'Install high-speed fiber internet connection to home office',
    type: 'installation',
    status: 'completed',
    priority: 'high',
    requestDate: '2023-11-01T10:00:00Z',
    scheduledDate: '2023-11-15T09:00:00Z',
    completionDate: '2023-11-15T14:30:00Z',
    estimatedCost: 299,
    actualCost: 299,
    assignedTechnician: 'John Smith',
    workOrderId: 'WO-2023-001',
    address: '123 Main Street, Anytown, ST 12345',
    requirements: [
      'Fiber cable run from street to home',
      'Install ONT in basement',
      'Configure home router',
      'Test connection speeds'
    ],
    notes: 'Installation completed successfully. Achieved 1Gbps down/up speeds.',
    attachments: [
      {
        id: 'att1',
        name: 'Installation Photos.zip',
        type: 'photos',
        url: '/api/attachments/att1'
      },
      {
        id: 'att2',
        name: 'Speed Test Results.pdf',
        type: 'document',
        url: '/api/attachments/att2'
      }
    ]
  },
  {
    id: '2',
    title: 'Network Equipment Upgrade',
    description: 'Upgrade modem and router to support higher speeds',
    type: 'upgrade',
    status: 'in_progress',
    priority: 'medium',
    requestDate: '2023-11-20T14:30:00Z',
    scheduledDate: '2023-12-05T11:00:00Z',
    estimatedCost: 150,
    assignedTechnician: 'Sarah Johnson',
    workOrderId: 'WO-2023-002',
    address: '123 Main Street, Anytown, ST 12345',
    requirements: [
      'Replace DOCSIS 3.0 modem with DOCSIS 3.1',
      'Install Wi-Fi 6 router',
      'Update network configuration',
      'Verify all devices connect properly'
    ],
    notes: 'Equipment ordered and ready for installation.',
    attachments: [
      {
        id: 'att3',
        name: 'Equipment Specifications.pdf',
        type: 'document',
        url: '/api/attachments/att3'
      }
    ]
  },
  {
    id: '3',
    title: 'Home Office Network Expansion',
    description: 'Add wired network connections to home office',
    type: 'expansion',
    status: 'approved',
    priority: 'low',
    requestDate: '2023-11-25T16:00:00Z',
    scheduledDate: '2023-12-15T13:00:00Z',
    estimatedCost: 200,
    address: '123 Main Street, Anytown, ST 12345',
    requirements: [
      'Run ethernet cables to 3 office locations',
      'Install wall jacks',
      'Configure network switch',
      'Test all connections'
    ],
    attachments: []
  },
  {
    id: '4',
    title: 'Signal Booster Installation',
    description: 'Install wireless signal booster for better coverage',
    type: 'installation',
    status: 'requested',
    priority: 'medium',
    requestDate: '2023-11-28T09:15:00Z',
    estimatedCost: 75,
    address: '123 Main Street, Anytown, ST 12345',
    requirements: [
      'Assess current signal coverage',
      'Install Wi-Fi range extender',
      'Optimize placement for best coverage',
      'Test signal strength in all areas'
    ],
    attachments: [
      {
        id: 'att4',
        name: 'Coverage Analysis.pdf',
        type: 'document',
        url: '/api/attachments/att4'
      }
    ]
  }
];

export const ProjectsManagement: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const [filteredProjects, setFilteredProjects] = useState<Project[]>(mockProjects);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="w-5 h-5 text-green-600" />;
      case 'in_progress':
        return <ClockIcon className="w-5 h-5 text-blue-600" />;
      case 'cancelled':
        return <ExclamationCircleIcon className="w-5 h-5 text-red-600" />;
      default:
        return <ClockIcon className="w-5 h-5 text-gray-600" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'installation':
        return <BuildingOffice2Icon className="w-4 h-4" />;
      case 'upgrade':
        return <SignalIcon className="w-4 h-4" />;
      case 'maintenance':
      case 'repair':
        return <WrenchScrewdriverIcon className="w-4 h-4" />;
      default:
        return <WrenchScrewdriverIcon className="w-4 h-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'requested': return 'bg-yellow-100 text-yellow-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'scheduled': return 'bg-blue-100 text-blue-800';
      case 'in_progress': return 'bg-indigo-100 text-indigo-800';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const columns = [
    {
      key: 'title' as keyof Project,
      label: 'Project Title',
      render: (value: string, item: Project) => (
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg bg-blue-50 text-blue-600`}>
            {getTypeIcon(item.type)}
          </div>
          <div>
            <div className="font-medium text-gray-900">{value}</div>
            <div className="text-sm text-gray-500 capitalize">{item.type}</div>
          </div>
        </div>
      )
    },
    {
      key: 'status' as keyof Project,
      label: 'Status',
      render: (value: string) => (
        <div className="flex items-center space-x-2">
          {getStatusIcon(value)}
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(value)}`}>
            {value.replace('_', ' ')}
          </span>
        </div>
      )
    },
    {
      key: 'priority' as keyof Project,
      label: 'Priority',
      render: (value: string) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getPriorityColor(value)}`}>
          {value}
        </span>
      )
    },
    {
      key: 'scheduledDate' as keyof Project,
      label: 'Scheduled Date',
      render: (value: string | undefined) => 
        value ? new Date(value).toLocaleDateString() : 'Not scheduled'
    },
    {
      key: 'estimatedCost' as keyof Project,
      label: 'Cost',
      render: (value: number | undefined, item: Project) => (
        <div className="text-sm">
          {value ? (
            <div>
              <div className="font-medium">${value}</div>
              {item.actualCost && item.actualCost !== value && (
                <div className="text-gray-500">Actual: ${item.actualCost}</div>
              )}
            </div>
          ) : (
            <span className="text-gray-500">TBD</span>
          )}
        </div>
      )
    },
    {
      key: 'assignedTechnician' as keyof Project,
      label: 'Technician',
      render: (value: string | undefined) => value || 'Not assigned'
    },
    {
      key: 'id' as keyof Project,
      label: 'Actions',
      render: (value: string, item: Project) => (
        <button
          onClick={() => setSelectedProject(item)}
          className="text-blue-600 hover:text-blue-800 flex items-center space-x-1"
          aria-label={`View details for ${item.title}`}
        >
          <EyeIcon className="w-4 h-4" />
          <span className="text-sm">Details</span>
        </button>
      )
    }
  ];

  const handleSearch = (query: string) => {
    const filtered = projects.filter(project => 
      project.title.toLowerCase().includes(query.toLowerCase()) ||
      project.description.toLowerCase().includes(query.toLowerCase()) ||
      project.type.toLowerCase().includes(query.toLowerCase()) ||
      project.workOrderId?.toLowerCase().includes(query.toLowerCase())
    );
    setFilteredProjects(filtered);
  };

  const handleFilter = (filters: Record<string, string>) => {
    let filtered = projects;
    
    if (filters.status) {
      filtered = filtered.filter(project => project.status === filters.status);
    }
    if (filters.type) {
      filtered = filtered.filter(project => project.type === filters.type);
    }
    if (filters.priority) {
      filtered = filtered.filter(project => project.priority === filters.priority);
    }
    
    setFilteredProjects(filtered);
  };

  const actions = [
    {
      label: 'New Project Request',
      onClick: () => setShowCreateModal(true),
      variant: 'primary' as const,
      icon: PlusIcon
    }
  ];

  const filters = [
    {
      key: 'status',
      label: 'Status',
      options: [
        { value: 'requested', label: 'Requested' },
        { value: 'approved', label: 'Approved' },
        { value: 'scheduled', label: 'Scheduled' },
        { value: 'in_progress', label: 'In Progress' },
        { value: 'completed', label: 'Completed' },
        { value: 'cancelled', label: 'Cancelled' }
      ]
    },
    {
      key: 'type',
      label: 'Type',
      options: [
        { value: 'installation', label: 'Installation' },
        { value: 'upgrade', label: 'Upgrade' },
        { value: 'maintenance', label: 'Maintenance' },
        { value: 'repair', label: 'Repair' },
        { value: 'expansion', label: 'Expansion' }
      ]
    },
    {
      key: 'priority',
      label: 'Priority',
      options: [
        { value: 'urgent', label: 'Urgent' },
        { value: 'high', label: 'High' },
        { value: 'medium', label: 'Medium' },
        { value: 'low', label: 'Low' }
      ]
    }
  ];

  return (
    <>
      <ManagementPageTemplate
        title="My Projects"
        subtitle={`${projects.length} projects • ${projects.filter(p => p.status === 'in_progress').length} in progress`}
        data={filteredProjects}
        columns={columns}
        onSearch={handleSearch}
        onFilter={handleFilter}
        actions={actions}
        filters={filters}
        searchPlaceholder="Search projects by title, description, or work order..."
        emptyMessage="No projects found"
        className="h-full"
      />

      {/* Project Details Modal */}
      {selectedProject && (
        <ProjectDetailsModal
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
          onUpdate={(updatedProject) => {
            setProjects(prev => prev.map(p => 
              p.id === updatedProject.id ? updatedProject : p
            ));
            setFilteredProjects(prev => prev.map(p => 
              p.id === updatedProject.id ? updatedProject : p
            ));
            setSelectedProject(updatedProject);
          }}
        />
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onCreate={(newProject) => {
            setProjects(prev => [newProject, ...prev]);
            setFilteredProjects(prev => [newProject, ...prev]);
          }}
        />
      )}
    </>
  );
};

// Project Details Modal Component
const ProjectDetailsModal: React.FC<{
  project: Project;
  onClose: () => void;
  onUpdate: (project: Project) => void;
}> = ({ project, onClose, onUpdate }) => {
  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-labelledby="project-details-title"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                {getTypeIcon(project.type)}
              </div>
              <div>
                <h2 id="project-details-title" className="text-xl font-semibold text-gray-900">
                  {project.title}
                </h2>
                <p className="text-gray-600 capitalize">{project.type} Project</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Details */}
            <div className="lg:col-span-2 space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Project Details</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-700 mb-4">{project.description}</p>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-900">Status:</span>
                      <div className="mt-1">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(project.status)}`}>
                          {project.status.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-900">Priority:</span>
                      <div className="mt-1">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getPriorityColor(project.priority)}`}>
                          {project.priority}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="font-medium text-gray-900">Requested:</span>
                      <p className="text-gray-600 mt-1">{new Date(project.requestDate).toLocaleDateString()}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-900">Scheduled:</span>
                      <p className="text-gray-600 mt-1">
                        {project.scheduledDate ? new Date(project.scheduledDate).toLocaleDateString() : 'Not scheduled'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Requirements</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <ul className="space-y-2">
                    {project.requirements.map((req, index) => (
                      <li key={index} className="flex items-start space-x-2">
                        <CheckCircleIcon className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-700">{req}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {project.attachments.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Attachments</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="space-y-2">
                      {project.attachments.map((attachment) => (
                        <div key={attachment.id} className="flex items-center justify-between p-2 bg-white rounded border">
                          <div className="flex items-center space-x-2">
                            <DocumentIcon className="w-4 h-4 text-gray-600" />
                            <span className="text-sm text-gray-900">{attachment.name}</span>
                          </div>
                          <button
                            onClick={() => window.open(attachment.url, '_blank')}
                            className="text-blue-600 hover:text-blue-800 text-sm"
                          >
                            View
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Project Info</h3>
                <div className="space-y-3 text-sm">
                  <div>
                    <span className="font-medium text-gray-900">Work Order:</span>
                    <p className="text-gray-600">{project.workOrderId || 'Not assigned'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-900">Address:</span>
                    <p className="text-gray-600">{project.address}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-900">Technician:</span>
                    <p className="text-gray-600">{project.assignedTechnician || 'Not assigned'}</p>
                  </div>
                  <div>
                    <span className="font-medium text-gray-900">Estimated Cost:</span>
                    <p className="text-gray-600">${project.estimatedCost || 'TBD'}</p>
                  </div>
                  {project.actualCost && (
                    <div>
                      <span className="font-medium text-gray-900">Actual Cost:</span>
                      <p className="text-gray-600">${project.actualCost}</p>
                    </div>
                  )}
                </div>
              </div>

              {project.notes && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Notes</h3>
                  <p className="text-sm text-gray-700">{project.notes}</p>
                </div>
              )}

              <div className="space-y-2">
                <button
                  onClick={() => {
                    // Navigate to support/create ticket
                  }}
                  className="w-full px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100"
                >
                  Contact Support
                </button>
                
                {project.status === 'completed' && (
                  <button
                    onClick={() => {
                      // Leave feedback
                    }}
                    className="w-full px-4 py-2 text-sm font-medium text-green-600 bg-green-50 rounded-md hover:bg-green-100"
                  >
                    Leave Feedback
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Create Project Modal Component
const CreateProjectModal: React.FC<{
  onClose: () => void;
  onCreate: (project: Project) => void;
}> = ({ onClose, onCreate }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'installation' as Project['type'],
    priority: 'medium' as Project['priority'],
    requirements: [''],
    estimatedBudget: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const newProject: Project = {
      id: `proj-${Date.now()}`,
      title: formData.title,
      description: formData.description,
      type: formData.type,
      status: 'requested',
      priority: formData.priority,
      requestDate: new Date().toISOString(),
      address: '123 Main Street, Anytown, ST 12345', // Would come from user profile
      requirements: formData.requirements.filter(req => req.trim() !== ''),
      attachments: []
    };

    onCreate(newProject);
    onClose();
  };

  const addRequirement = () => {
    setFormData(prev => ({
      ...prev,
      requirements: [...prev.requirements, '']
    }));
  };

  const updateRequirement = (index: number, value: string) => {
    setFormData(prev => ({
      ...prev,
      requirements: prev.requirements.map((req, i) => i === index ? value : req)
    }));
  };

  const removeRequirement = (index: number) => {
    setFormData(prev => ({
      ...prev,
      requirements: prev.requirements.filter((_, i) => i !== index)
    }));
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-labelledby="create-project-title"
      aria-modal="true"
    >
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-auto">
        <div className="p-6">
          <h2 id="create-project-title" className="text-xl font-semibold mb-6">New Project Request</h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="project-title" className="block text-sm font-medium text-gray-700 mb-1">
                  Project Title *
                </label>
                <input
                  id="project-title"
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label htmlFor="project-type" className="block text-sm font-medium text-gray-700 mb-1">
                  Project Type *
                </label>
                <select
                  id="project-type"
                  value={formData.type}
                  onChange={(e) => setFormData({...formData, type: e.target.value as Project['type']})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="installation">Installation</option>
                  <option value="upgrade">Upgrade</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="repair">Repair</option>
                  <option value="expansion">Expansion</option>
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="project-description" className="block text-sm font-medium text-gray-700 mb-1">
                Description *
              </label>
              <textarea
                id="project-description"
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Describe what you need done..."
                required
              />
            </div>

            <div>
              <label htmlFor="project-priority" className="block text-sm font-medium text-gray-700 mb-1">
                Priority
              </label>
              <select
                id="project-priority"
                value={formData.priority}
                onChange={(e) => setFormData({...formData, priority: e.target.value as Project['priority']})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Requirements
              </label>
              <div className="space-y-2">
                {formData.requirements.map((req, index) => (
                  <div key={index} className="flex space-x-2">
                    <input
                      type="text"
                      value={req}
                      onChange={(e) => updateRequirement(index, e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Enter requirement..."
                    />
                    {formData.requirements.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRequirement(index)}
                        className="px-3 py-2 text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addRequirement}
                  className="text-blue-600 hover:text-blue-800 text-sm"
                >
                  + Add Requirement
                </button>
              </div>
            </div>

            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Submit Request
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// Helper function to avoid redefinition
const getTypeIcon = (type: string) => {
  switch (type) {
    case 'installation':
      return <BuildingOffice2Icon className="w-4 h-4" />;
    case 'upgrade':
      return <SignalIcon className="w-4 h-4" />;
    case 'maintenance':
    case 'repair':
      return <WrenchScrewdriverIcon className="w-4 h-4" />;
    default:
      return <WrenchScrewdriverIcon className="w-4 h-4" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'requested': return 'bg-yellow-100 text-yellow-800';
    case 'approved': return 'bg-green-100 text-green-800';
    case 'scheduled': return 'bg-blue-100 text-blue-800';
    case 'in_progress': return 'bg-indigo-100 text-indigo-800';
    case 'completed': return 'bg-green-100 text-green-800';
    case 'cancelled': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'urgent': return 'bg-red-100 text-red-800';
    case 'high': return 'bg-orange-100 text-orange-800';
    case 'medium': return 'bg-yellow-100 text-yellow-800';
    case 'low': return 'bg-green-100 text-green-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};