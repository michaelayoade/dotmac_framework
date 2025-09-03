/**
 * Plugin Security Dashboard Component
 * Integrates with the existing plugin security framework
 * Connects frontend UI to the comprehensive backend security system
 */

import React, { useState, useEffect } from 'react';
import {
  ShieldCheckIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  BugAntIcon,
  CheckCircleIcon,
  ClockIcon,
  EyeIcon,
  PlayIcon,
  StopIcon,
  DocumentTextIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/http';
import { useToast } from '@/components/ui/Toast';

interface SecurityThreat {
  threat_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  location: string;
  line_number?: number;
  evidence?: string;
  remediation?: string;
  cve_references: string[];
}

interface PluginSecurityReport {
  plugin_id: string;
  scan_id: string;
  timestamp: string;
  security_level: 'safe' | 'low_risk' | 'medium_risk' | 'high_risk' | 'critical';
  risk_score: number;
  threats_detected: SecurityThreat[];
  file_hash: string;
  file_size: number;
  line_count: number;
  scan_duration_ms: number;
  recommendations: string[];
}

interface ValidationResult {
  status: 'pending' | 'approved' | 'rejected' | 'in_review';
  review_notes?: string;
  certification_level?: 'basic' | 'standard' | 'enterprise';
}

interface PluginSecurityDashboardProps {
  className?: string;
}

export function PluginSecurityDashboard({ className = '' }: PluginSecurityDashboardProps) {
  const [selectedPlugin, setSelectedPlugin] = useState<string>('');
  const [scanningPlugin, setScanningPlugin] = useState<string>('');
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  // Fetch installed plugins for security scanning
  const { data: plugins = [], isLoading: loadingPlugins } = useQuery({
    queryKey: ['installed-plugins'],
    queryFn: async () => {
      const res = await api.get<any[]>('/api/v1/plugins/installed');
      return res.data;
    },
  });

  // Fetch security reports for all plugins
  const { data: securityReports = [], isLoading: loadingReports } = useQuery({
    queryKey: ['plugin-security-reports'],
    queryFn: async () => {
      const res = await api.get<PluginSecurityReport[]>('/api/v1/plugins/security/reports');
      return res.data;
    },
  });

  // Security scan mutation
  const scanMutation = useMutation({
    mutationFn: async (pluginId: string) => {
      const res = await api.post<PluginSecurityReport>(`/api/v1/plugins/${pluginId}/security/scan`);
      return res.data;
    },
    onMutate: (pluginId) => {
      setScanningPlugin(pluginId);
    },
    onSuccess: (data) => {
      success(`Security scan completed for plugin. Risk Score: ${data.risk_score}/100`);
      queryClient.invalidateQueries({ queryKey: ['plugin-security-reports'] });
    },
    onError: (err: any) => {
      error('Security scan failed', err.message);
    },
    onSettled: () => {
      setScanningPlugin('');
    },
  });

  const handleScanPlugin = (pluginId: string) => {
    scanMutation.mutate(pluginId);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getSecurityLevelBadge = (level: string) => {
    switch (level) {
      case 'safe':
        return 'bg-green-100 text-green-800';
      case 'low_risk':
        return 'bg-blue-100 text-blue-800';
      case 'medium_risk':
        return 'bg-yellow-100 text-yellow-800';
      case 'high_risk':
        return 'bg-orange-100 text-orange-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRiskScoreColor = (score: number) => {
    if (score >= 80) return 'text-red-600';
    if (score >= 60) return 'text-orange-600';
    if (score >= 30) return 'text-yellow-600';
    return 'text-green-600';
  };

  if (loadingPlugins || loadingReports) {
    return (
      <div className={`flex justify-center items-center py-12 ${className}`}>
        <LoadingSpinner size='large' />
      </div>
    );
  }

  const totalThreats = securityReports.reduce(
    (sum: number, report: PluginSecurityReport) => sum + report.threats_detected.length,
    0
  );

  const criticalThreats = securityReports.reduce(
    (sum: number, report: PluginSecurityReport) =>
      sum + report.threats_detected.filter((t: SecurityThreat) => t.severity === 'critical').length,
    0
  );

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Security Overview */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>Total Plugins</p>
              <p className='text-3xl font-bold text-gray-900'>{plugins.length}</p>
            </div>
            <ShieldCheckIcon className='h-8 w-8 text-blue-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>Scanned Today</p>
              <p className='text-3xl font-bold text-gray-900'>{securityReports.length}</p>
            </div>
            <BugAntIcon className='h-8 w-8 text-green-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>Total Threats</p>
              <p className='text-3xl font-bold text-orange-600'>{totalThreats}</p>
            </div>
            <ExclamationTriangleIcon className='h-8 w-8 text-orange-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-gray-600'>Critical Issues</p>
              <p className='text-3xl font-bold text-red-600'>{criticalThreats}</p>
            </div>
            <ShieldExclamationIcon className='h-8 w-8 text-red-500' />
          </div>
        </div>
      </div>

      {/* Security Actions */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
        <div className='px-6 py-4 border-b border-gray-200'>
          <div className='flex items-center justify-between'>
            <div>
              <h3 className='text-lg font-medium text-gray-900'>Security Actions</h3>
              <p className='text-sm text-gray-500'>Scan plugins and manage security policies</p>
            </div>
            <div className='flex space-x-3'>
              <button
                onClick={() =>
                  queryClient.invalidateQueries({ queryKey: ['plugin-security-reports'] })
                }
                className='flex items-center space-x-2 px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200'
              >
                <ArrowPathIcon className='h-4 w-4' />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        <div className='p-6'>
          <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
            {/* Bulk Scan */}
            <div className='space-y-4'>
              <h4 className='font-medium text-gray-900'>Bulk Security Scan</h4>
              <div className='flex space-x-3'>
                <button
                  onClick={() => plugins.forEach((plugin: any) => handleScanPlugin(plugin.id))}
                  disabled={scanningPlugin !== ''}
                  className='flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50'
                >
                  <PlayIcon className='h-4 w-4' />
                  <span>Scan All Plugins</span>
                </button>
              </div>
              <p className='text-sm text-gray-500'>
                Run comprehensive security scans on all installed plugins
              </p>
            </div>

            {/* Security Policy */}
            <div className='space-y-4'>
              <h4 className='font-medium text-gray-900'>Security Policy</h4>
              <div className='space-y-2'>
                <label className='flex items-center'>
                  <input
                    type='checkbox'
                    defaultChecked
                    className='rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                  />
                  <span className='ml-2 text-sm text-gray-700'>
                    Block plugins with critical vulnerabilities
                  </span>
                </label>
                <label className='flex items-center'>
                  <input
                    type='checkbox'
                    defaultChecked
                    className='rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                  />
                  <span className='ml-2 text-sm text-gray-700'>Require code signatures</span>
                </label>
                <label className='flex items-center'>
                  <input
                    type='checkbox'
                    className='rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                  />
                  <span className='ml-2 text-sm text-gray-700'>
                    Auto-quarantine suspicious plugins
                  </span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Plugin Security Status */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
        <div className='px-6 py-4 border-b border-gray-200'>
          <h3 className='text-lg font-medium text-gray-900'>Plugin Security Status</h3>
        </div>

        <div className='divide-y divide-gray-200'>
          {plugins.map((plugin: any) => {
            const report = securityReports.find(
              (r: PluginSecurityReport) => r.plugin_id === plugin.id
            );
            const isScanning = scanningPlugin === plugin.id;

            return (
              <div key={plugin.id} className='p-6 hover:bg-gray-50'>
                <div className='flex items-start justify-between'>
                  <div className='flex-1'>
                    <div className='flex items-center space-x-3'>
                      <div className='flex-shrink-0'>
                        {plugin.icon ? (
                          <img
                            src={plugin.icon}
                            alt={plugin.name}
                            className='h-10 w-10 rounded-lg'
                          />
                        ) : (
                          <div className='h-10 w-10 bg-gray-200 rounded-lg flex items-center justify-center'>
                            <BugAntIcon className='h-6 w-6 text-gray-500' />
                          </div>
                        )}
                      </div>

                      <div className='flex-1'>
                        <h4 className='text-lg font-medium text-gray-900'>{plugin.name}</h4>
                        <p className='text-sm text-gray-500'>
                          v{plugin.version} • {plugin.author}
                        </p>
                        <div className='flex items-center space-x-4 mt-2'>
                          {report ? (
                            <>
                              <span
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSecurityLevelBadge(report.security_level)}`}
                              >
                                {report.security_level.replace('_', ' ')}
                              </span>
                              <span
                                className={`text-sm font-medium ${getRiskScoreColor(report.risk_score)}`}
                              >
                                Risk Score: {report.risk_score}/100
                              </span>
                              <span className='text-sm text-gray-500'>
                                {report.threats_detected.length} threats detected
                              </span>
                            </>
                          ) : (
                            <span className='text-sm text-gray-500 italic'>Not scanned</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Threats Summary */}
                    {report && report.threats_detected.length > 0 && (
                      <div className='mt-4 space-y-2'>
                        {report.threats_detected
                          .slice(0, 3)
                          .map((threat: SecurityThreat, index: number) => (
                            <div
                              key={index}
                              className='flex items-start space-x-3 p-3 bg-gray-50 rounded-md'
                            >
                              <ExclamationTriangleIcon
                                className={`h-5 w-5 flex-shrink-0 ${
                                  threat.severity === 'critical'
                                    ? 'text-red-500'
                                    : threat.severity === 'high'
                                      ? 'text-orange-500'
                                      : threat.severity === 'medium'
                                        ? 'text-yellow-500'
                                        : 'text-blue-500'
                                }`}
                              />
                              <div className='flex-1'>
                                <p className='text-sm font-medium text-gray-900'>
                                  {threat.threat_type}
                                </p>
                                <p className='text-sm text-gray-600'>{threat.description}</p>
                                <p className='text-xs text-gray-500 mt-1'>
                                  Location: {threat.location}
                                </p>
                              </div>
                              <span
                                className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(threat.severity)}`}
                              >
                                {threat.severity}
                              </span>
                            </div>
                          ))}
                        {report.threats_detected.length > 3 && (
                          <p className='text-sm text-gray-500 pl-8'>
                            + {report.threats_detected.length - 3} more threats
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  <div className='ml-4 flex items-center space-x-2'>
                    <button
                      onClick={() => handleScanPlugin(plugin.id)}
                      disabled={isScanning}
                      className='flex items-center space-x-2 px-3 py-2 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 disabled:opacity-50'
                    >
                      {isScanning ? (
                        <>
                          <LoadingSpinner size='small' />
                          <span>Scanning...</span>
                        </>
                      ) : (
                        <>
                          <ShieldCheckIcon className='h-4 w-4' />
                          <span>Scan</span>
                        </>
                      )}
                    </button>

                    {report && (
                      <button className='p-2 text-gray-400 hover:text-gray-600'>
                        <DocumentTextIcon className='h-5 w-5' title='View full report' />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {plugins.length === 0 && (
            <div className='p-8 text-center'>
              <ShieldCheckIcon className='mx-auto h-12 w-12 text-gray-400' />
              <h4 className='mt-4 text-lg font-medium text-gray-900'>No Plugins Installed</h4>
              <p className='mt-2 text-gray-600'>
                Install plugins from the marketplace to see security status
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
