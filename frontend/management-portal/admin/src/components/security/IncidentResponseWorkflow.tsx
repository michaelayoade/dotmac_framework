/**
 * Incident Response Workflow Component
 * Integrates with existing security incident handling system
 * Connects to unified audit monitor and plugin audit system
 */

import React, { useState, useEffect } from 'react';
import {
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  UserIcon,
  DocumentTextIcon,
  PlayIcon,
  PauseIcon,
  StopIcon,
  ArrowRightIcon,
  CogIcon,
  BellAlertIcon,
  ChatBubbleLeftRightIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/http';

interface SecurityIncident {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'investigating' | 'containment' | 'eradication' | 'recovery' | 'closed';
  type: 'malware' | 'data_breach' | 'unauthorized_access' | 'ddos' | 'phishing' | 'vulnerability';
  affected_systems: string[];
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
  timeline: IncidentTimelineEntry[];
  artifacts: IncidentArtifact[];
  playbook_id?: string;
}

interface IncidentTimelineEntry {
  id: string;
  timestamp: string;
  action: string;
  description: string;
  user: string;
  status: string;
}

interface IncidentArtifact {
  id: string;
  name: string;
  type: 'log' | 'screenshot' | 'report' | 'evidence';
  size: number;
  created_at: string;
  url: string;
}

interface IncidentPlaybook {
  id: string;
  name: string;
  description: string;
  incident_types: string[];
  steps: PlaybookStep[];
}

interface PlaybookStep {
  id: string;
  title: string;
  description: string;
  order: number;
  automated: boolean;
  estimated_duration: number;
  required_roles: string[];
}

interface IncidentResponseWorkflowProps {
  className?: string;
}

export function IncidentResponseWorkflow({ className = '' }: IncidentResponseWorkflowProps) {
  const [selectedIncident, setSelectedIncident] = useState<SecurityIncident | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'artifacts' | 'playbook'>(
    'overview'
  );
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  const queryClient = useQueryClient();

  // Fetch incidents
  const { data: incidents = [], isLoading: loadingIncidents } = useQuery({
    queryKey: ['security-incidents', filterStatus, filterSeverity],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filterStatus !== 'all') params.status = filterStatus;
      if (filterSeverity !== 'all') params.severity = filterSeverity;
      const res = await api.get<SecurityIncident[]>(`/api/v1/security/incidents`, {
        params,
      });
      return res.data;
    },
    refetchInterval: 30000,
  });

  // Fetch available playbooks
  const { data: playbooks = [] } = useQuery({
    queryKey: ['incident-playbooks'],
    queryFn: async () => {
      const res = await api.get<IncidentPlaybook[]>(`/api/v1/security/playbooks`);
      return res.data;
    },
  });

  // Update incident status mutation
  const updateStatusMutation = useMutation({
    mutationFn: async ({
      incidentId,
      status,
      notes,
    }: {
      incidentId: string;
      status: string;
      notes?: string;
    }) => {
      const res = await api.patch(`/api/v1/security/incidents/${incidentId}/status`, {
        status,
        notes,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['security-incidents'] });
    },
  });

  // Assign incident mutation
  const assignIncidentMutation = useMutation({
    mutationFn: async ({ incidentId, assignee }: { incidentId: string; assignee: string }) => {
      const res = await api.patch(`/api/v1/security/incidents/${incidentId}/assign`, {
        assignee,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['security-incidents'] });
    },
  });

  // Execute playbook mutation
  const executePlaybookMutation = useMutation({
    mutationFn: async ({ incidentId, playbookId }: { incidentId: string; playbookId: string }) => {
      const res = await api.post(`/api/v1/security/incidents/${incidentId}/playbook`, {
        playbook_id: playbookId,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['security-incidents'] });
    },
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-100';
      case 'high':
        return 'text-orange-600 bg-orange-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'low':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'text-red-600 bg-red-100';
      case 'investigating':
        return 'text-yellow-600 bg-yellow-100';
      case 'containment':
        return 'text-orange-600 bg-orange-100';
      case 'eradication':
        return 'text-purple-600 bg-purple-100';
      case 'recovery':
        return 'text-blue-600 bg-blue-100';
      case 'closed':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ShieldExclamationIcon className='h-5 w-5 text-red-600' />;
      case 'high':
        return <ExclamationTriangleIcon className='h-5 w-5 text-orange-600' />;
      case 'medium':
        return <BellAlertIcon className='h-5 w-5 text-yellow-600' />;
      case 'low':
        return <EyeIcon className='h-5 w-5 text-blue-600' />;
      default:
        return <EyeIcon className='h-5 w-5 text-gray-600' />;
    }
  };

  if (loadingIncidents) {
    return (
      <div className={`flex justify-center items-center py-12 ${className}`}>
        <LoadingSpinner size='large' />
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Incident Response</h1>
          <p className='text-gray-600 mt-1'>Manage security incidents and response workflows</p>
        </div>

        <div className='flex items-center space-x-4'>
          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className='px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
          >
            <option value='all'>All Status</option>
            <option value='open'>Open</option>
            <option value='investigating'>Investigating</option>
            <option value='containment'>Containment</option>
            <option value='eradication'>Eradication</option>
            <option value='recovery'>Recovery</option>
            <option value='closed'>Closed</option>
          </select>

          {/* Severity Filter */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className='px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
          >
            <option value='all'>All Severity</option>
            <option value='critical'>Critical</option>
            <option value='high'>High</option>
            <option value='medium'>Medium</option>
            <option value='low'>Low</option>
          </select>
        </div>
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        {/* Incidents List */}
        <div className='lg:col-span-1'>
          <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
            <div className='px-6 py-4 border-b border-gray-200'>
              <h3 className='text-lg font-medium text-gray-900'>
                Active Incidents ({incidents.length})
              </h3>
            </div>

            <div className='divide-y divide-gray-200 max-h-96 overflow-y-auto'>
              {incidents.map((incident: SecurityIncident) => (
                <div
                  key={incident.id}
                  className={`px-6 py-4 cursor-pointer hover:bg-gray-50 ${
                    selectedIncident?.id === incident.id
                      ? 'bg-blue-50 border-r-4 border-blue-500'
                      : ''
                  }`}
                  onClick={() => setSelectedIncident(incident)}
                >
                  <div className='flex items-start justify-between'>
                    <div className='flex-1'>
                      <div className='flex items-center space-x-2'>
                        {getSeverityIcon(incident.severity)}
                        <h4 className='text-sm font-medium text-gray-900 truncate'>
                          {incident.title}
                        </h4>
                      </div>

                      <div className='mt-2 flex items-center space-x-2'>
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getSeverityColor(incident.severity)}`}
                        >
                          {incident.severity}
                        </span>
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getStatusColor(incident.status)}`}
                        >
                          {incident.status}
                        </span>
                      </div>

                      <p className='mt-1 text-xs text-gray-500'>
                        {new Date(incident.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))}

              {incidents.length === 0 && (
                <div className='px-6 py-8 text-center'>
                  <CheckCircleIcon className='mx-auto h-12 w-12 text-green-500' />
                  <h4 className='mt-4 text-lg font-medium text-gray-900'>No Active Incidents</h4>
                  <p className='mt-2 text-gray-600'>All security incidents have been resolved</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Incident Details */}
        <div className='lg:col-span-2'>
          {selectedIncident ? (
            <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
              {/* Incident Header */}
              <div className='px-6 py-4 border-b border-gray-200'>
                <div className='flex items-start justify-between'>
                  <div className='flex-1'>
                    <div className='flex items-center space-x-3'>
                      {getSeverityIcon(selectedIncident.severity)}
                      <h3 className='text-lg font-medium text-gray-900'>
                        {selectedIncident.title}
                      </h3>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(selectedIncident.severity)}`}
                      >
                        {selectedIncident.severity}
                      </span>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(selectedIncident.status)}`}
                      >
                        {selectedIncident.status}
                      </span>
                    </div>
                    <p className='mt-2 text-gray-700'>{selectedIncident.description}</p>
                  </div>

                  {/* Quick Actions */}
                  <div className='flex items-center space-x-2'>
                    <select
                      value={selectedIncident.status}
                      onChange={(e) =>
                        updateStatusMutation.mutate({
                          incidentId: selectedIncident.id,
                          status: e.target.value,
                        })
                      }
                      className='px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                    >
                      <option value='open'>Open</option>
                      <option value='investigating'>Investigating</option>
                      <option value='containment'>Containment</option>
                      <option value='eradication'>Eradication</option>
                      <option value='recovery'>Recovery</option>
                      <option value='closed'>Closed</option>
                    </select>

                    {playbooks.length > 0 && (
                      <select
                        onChange={(e) => {
                          if (e.target.value) {
                            executePlaybookMutation.mutate({
                              incidentId: selectedIncident.id,
                              playbookId: e.target.value,
                            });
                          }
                        }}
                        className='px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500'
                      >
                        <option value=''>Execute Playbook</option>
                        {playbooks
                          .filter((pb: IncidentPlaybook) =>
                            pb.incident_types.includes(selectedIncident.type)
                          )
                          .map((playbook: IncidentPlaybook) => (
                            <option key={playbook.id} value={playbook.id}>
                              {playbook.name}
                            </option>
                          ))}
                      </select>
                    )}
                  </div>
                </div>

                {/* Tabs */}
                <div className='mt-4 border-b border-gray-200'>
                  <nav className='-mb-px flex space-x-8'>
                    {[
                      { key: 'overview', label: 'Overview', icon: EyeIcon },
                      { key: 'timeline', label: 'Timeline', icon: ClockIcon },
                      { key: 'artifacts', label: 'Artifacts', icon: DocumentTextIcon },
                      { key: 'playbook', label: 'Playbook', icon: CogIcon },
                    ].map(({ key, label, icon: Icon }) => (
                      <button
                        key={key}
                        className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                          activeTab === key
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                        onClick={() => setActiveTab(key as any)}
                      >
                        <Icon className='h-4 w-4' />
                        <span>{label}</span>
                      </button>
                    ))}
                  </nav>
                </div>
              </div>

              {/* Tab Content */}
              <div className='px-6 py-4'>
                {activeTab === 'overview' && (
                  <div className='space-y-6'>
                    <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                      <div>
                        <h4 className='text-sm font-medium text-gray-900 mb-2'>Incident Details</h4>
                        <dl className='space-y-2'>
                          <div className='flex justify-between'>
                            <dt className='text-sm text-gray-600'>Type:</dt>
                            <dd className='text-sm text-gray-900'>{selectedIncident.type}</dd>
                          </div>
                          <div className='flex justify-between'>
                            <dt className='text-sm text-gray-600'>Created:</dt>
                            <dd className='text-sm text-gray-900'>
                              {new Date(selectedIncident.created_at).toLocaleString()}
                            </dd>
                          </div>
                          <div className='flex justify-between'>
                            <dt className='text-sm text-gray-600'>Updated:</dt>
                            <dd className='text-sm text-gray-900'>
                              {new Date(selectedIncident.updated_at).toLocaleString()}
                            </dd>
                          </div>
                          <div className='flex justify-between'>
                            <dt className='text-sm text-gray-600'>Assigned to:</dt>
                            <dd className='text-sm text-gray-900'>
                              {selectedIncident.assigned_to || 'Unassigned'}
                            </dd>
                          </div>
                        </dl>
                      </div>

                      <div>
                        <h4 className='text-sm font-medium text-gray-900 mb-2'>Affected Systems</h4>
                        <div className='space-y-1'>
                          {selectedIncident.affected_systems.map((system, index) => (
                            <div key={index} className='flex items-center space-x-2'>
                              <div className='w-2 h-2 bg-red-500 rounded-full'></div>
                              <span className='text-sm text-gray-700'>{system}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'timeline' && (
                  <div className='space-y-4'>
                    {selectedIncident.timeline.map((entry: IncidentTimelineEntry) => (
                      <div key={entry.id} className='flex items-start space-x-4'>
                        <div className='flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2'></div>
                        <div className='flex-1'>
                          <div className='flex items-center justify-between'>
                            <h5 className='text-sm font-medium text-gray-900'>{entry.action}</h5>
                            <span className='text-xs text-gray-500'>
                              {new Date(entry.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <p className='text-sm text-gray-700 mt-1'>{entry.description}</p>
                          <p className='text-xs text-gray-500 mt-1'>by {entry.user}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'artifacts' && (
                  <div className='space-y-4'>
                    {selectedIncident.artifacts.map((artifact: IncidentArtifact) => (
                      <div
                        key={artifact.id}
                        className='flex items-center justify-between p-4 border border-gray-200 rounded-lg'
                      >
                        <div className='flex items-center space-x-3'>
                          <DocumentTextIcon className='h-8 w-8 text-gray-400' />
                          <div>
                            <h5 className='text-sm font-medium text-gray-900'>{artifact.name}</h5>
                            <p className='text-xs text-gray-500'>
                              {artifact.type} • {(artifact.size / 1024).toFixed(1)}KB •{' '}
                              {new Date(artifact.created_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <button className='text-blue-600 hover:text-blue-800 text-sm'>
                          Download
                        </button>
                      </div>
                    ))}

                    {selectedIncident.artifacts.length === 0 && (
                      <p className='text-center text-gray-500 py-8'>No artifacts collected yet</p>
                    )}
                  </div>
                )}

                {activeTab === 'playbook' && (
                  <div className='space-y-4'>
                    {selectedIncident.playbook_id ? (
                      <div className='p-4 bg-blue-50 border border-blue-200 rounded-lg'>
                        <p className='text-blue-800'>Playbook execution in progress...</p>
                      </div>
                    ) : (
                      <div className='text-center py-8'>
                        <CogIcon className='mx-auto h-12 w-12 text-gray-400 mb-4' />
                        <p className='text-gray-500'>No playbook assigned</p>
                        <p className='text-sm text-gray-400 mt-1'>
                          Select a playbook from the dropdown above to automate response
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center'>
              <ShieldExclamationIcon className='mx-auto h-12 w-12 text-gray-400 mb-4' />
              <h3 className='text-lg font-medium text-gray-900'>Select an Incident</h3>
              <p className='text-gray-600 mt-2'>
                Choose an incident from the list to view details and manage response
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
