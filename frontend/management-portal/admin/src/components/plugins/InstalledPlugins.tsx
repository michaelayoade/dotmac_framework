/**
 * Installed Plugins Management Component
 * Following DRY patterns from existing components
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  PowerIcon,
  Cog6ToothIcon,
  ArrowPathIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  InformationCircleIcon,
  ChartBarIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { Button, IconButton } from '@dotmac/primitives';
import { Modal, ConfirmModal } from '../ui/Modal';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { useApiClient } from '@dotmac/headless';
import type { InstalledPlugin, PluginUpdateInfo } from '@dotmac/headless';

interface InstalledPluginsProps {
  className?: string;
}

export function InstalledPlugins({ className = '' }: InstalledPluginsProps) {
  const apiClient = useApiClient();
  const [plugins, setPlugins] = useState<InstalledPlugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlugin, setSelectedPlugin] = useState<InstalledPlugin | null>(null);
  const [configuringPlugin, setConfiguringPlugin] = useState<InstalledPlugin | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: 'enable' | 'disable' | 'uninstall' | 'update';
    plugin: InstalledPlugin;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [updates, setUpdates] = useState<Record<string, PluginUpdateInfo>>({});

  const loadPlugins = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [pluginsResponse, updatesResponse] = await Promise.all([
        apiClient.getInstalledPlugins({ limit: 50 }),
        apiClient.getPluginUpdates().catch(() => ({ data: {} })),
      ]);

      setPlugins(pluginsResponse.data);
      setUpdates(updatesResponse.data);
    } catch (err) {
      setError('Failed to load installed plugins');
      console.error('Installed plugins error:', err);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    loadPlugins();
  }, [loadPlugins]);

  const handlePluginAction = async (
    action: 'enable' | 'disable' | 'uninstall' | 'update',
    plugin: InstalledPlugin
  ) => {
    setActionLoading(`${action}-${plugin.installation_id}`);

    try {
      let response;

      switch (action) {
        case 'enable':
          response = await apiClient.enablePlugin(plugin.installation_id);
          break;
        case 'disable':
          response = await apiClient.disablePlugin(plugin.installation_id);
          break;
        case 'uninstall':
          await apiClient.uninstallPlugin(plugin.installation_id, { backup: true });
          break;
        case 'update':
          await apiClient.updatePlugin(plugin.installation_id, {
            backup: true,
            auto_restart: true,
          });
          break;
      }

      // Reload plugins after successful action
      await loadPlugins();
      setConfirmAction(null);
    } catch (err) {
      console.error(`${action} plugin error:`, err);
      alert(`Failed to ${action} plugin`);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusIcon = (status: InstalledPlugin['status']) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className='h-5 w-5 text-green-500' />;
      case 'inactive':
        return <ClockIcon className='h-5 w-5 text-yellow-500' />;
      case 'disabled':
        return <PowerIcon className='h-5 w-5 text-gray-400' />;
      case 'error':
        return <ExclamationTriangleIcon className='h-5 w-5 text-red-500' />;
      default:
        return <InformationCircleIcon className='h-5 w-5 text-gray-400' />;
    }
  };

  const getStatusColor = (status: InstalledPlugin['status']) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-100';
      case 'inactive':
        return 'text-yellow-600 bg-yellow-100';
      case 'disabled':
        return 'text-gray-600 bg-gray-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getHealthColor = (health: InstalledPlugin['health']['status']) => {
    switch (health) {
      case 'healthy':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'critical':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Installed Plugins</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Manage your installed plugins and their configurations
          </p>
        </div>

        <Button onClick={loadPlugins} leftIcon={ArrowPathIcon}>
          Refresh
        </Button>
      </div>

      {/* Quick Stats */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <div className='flex items-center'>
            <div className='p-3 rounded-full bg-green-100'>
              <CheckCircleIcon className='h-6 w-6 text-green-600' />
            </div>
            <div className='ml-4'>
              <h3 className='text-sm font-medium text-gray-500'>Active Plugins</h3>
              <p className='text-2xl font-semibold text-gray-900'>
                {plugins.filter((p) => p.status === 'active').length}
              </p>
            </div>
          </div>
        </div>

        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <div className='flex items-center'>
            <div className='p-3 rounded-full bg-yellow-100'>
              <ExclamationTriangleIcon className='h-6 w-6 text-yellow-600' />
            </div>
            <div className='ml-4'>
              <h3 className='text-sm font-medium text-gray-500'>Updates Available</h3>
              <p className='text-2xl font-semibold text-gray-900'>{Object.keys(updates).length}</p>
            </div>
          </div>
        </div>

        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <div className='flex items-center'>
            <div className='p-3 rounded-full bg-red-100'>
              <ShieldCheckIcon className='h-6 w-6 text-red-600' />
            </div>
            <div className='ml-4'>
              <h3 className='text-sm font-medium text-gray-500'>Health Issues</h3>
              <p className='text-2xl font-semibold text-gray-900'>
                {plugins.filter((p) => p.health.status !== 'healthy').length}
              </p>
            </div>
          </div>
        </div>

        <div className='bg-white p-6 rounded-lg border border-gray-200'>
          <div className='flex items-center'>
            <div className='p-3 rounded-full bg-blue-100'>
              <ChartBarIcon className='h-6 w-6 text-blue-600' />
            </div>
            <div className='ml-4'>
              <h3 className='text-sm font-medium text-gray-500'>Total Plugins</h3>
              <p className='text-2xl font-semibold text-gray-900'>{plugins.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Plugins List */}
      {loading ? (
        <div className='flex justify-center py-12'>
          <LoadingSpinner size='large' />
        </div>
      ) : error ? (
        <div className='text-center py-12'>
          <ExclamationTriangleIcon className='mx-auto h-12 w-12 text-red-400' />
          <h3 className='mt-2 text-sm font-medium text-gray-900'>Error loading plugins</h3>
          <p className='mt-1 text-sm text-gray-500'>{error}</p>
          <Button className='mt-4' onClick={loadPlugins}>
            Try Again
          </Button>
        </div>
      ) : plugins.length === 0 ? (
        <div className='text-center py-12'>
          <div className='text-gray-400 text-lg'>No plugins installed</div>
          <p className='text-gray-500 mt-2'>Install plugins from the marketplace to get started</p>
        </div>
      ) : (
        <div className='bg-white shadow rounded-lg overflow-hidden'>
          <div className='px-6 py-4 border-b border-gray-200'>
            <h2 className='text-lg font-medium text-gray-900'>Plugin List</h2>
          </div>

          <div className='overflow-x-auto'>
            <table className='min-w-full divide-y divide-gray-200'>
              <thead className='bg-gray-50'>
                <tr>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Plugin
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Status
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Health
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Version
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Usage
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className='bg-white divide-y divide-gray-200'>
                {plugins.map((plugin) => (
                  <tr key={plugin.installation_id} className='hover:bg-gray-50'>
                    <td className='px-6 py-4 whitespace-nowrap'>
                      <div className='flex items-center'>
                        <div className='flex-shrink-0'>
                          {plugin.plugin.icon ? (
                            <img
                              src={plugin.plugin.icon}
                              alt={plugin.plugin.name}
                              className='h-10 w-10 rounded'
                            />
                          ) : (
                            <div className='h-10 w-10 bg-gray-100 rounded flex items-center justify-center'>
                              <Cog6ToothIcon className='h-6 w-6 text-gray-400' />
                            </div>
                          )}
                        </div>
                        <div className='ml-4'>
                          <div className='text-sm font-medium text-gray-900'>
                            {plugin.plugin.name}
                          </div>
                          <div className='text-sm text-gray-500'>{plugin.plugin.category}</div>
                        </div>
                      </div>
                    </td>

                    <td className='px-6 py-4 whitespace-nowrap'>
                      <div className='flex items-center'>
                        {getStatusIcon(plugin.status)}
                        <span
                          className={`ml-2 inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(plugin.status)}`}
                        >
                          {plugin.status}
                        </span>
                      </div>
                    </td>

                    <td className='px-6 py-4 whitespace-nowrap'>
                      <div
                        className={`text-sm font-medium ${getHealthColor(plugin.health.status)}`}
                      >
                        {plugin.health.status}
                      </div>
                      {plugin.health.issues.length > 0 && (
                        <div className='text-xs text-gray-500'>
                          {plugin.health.issues.length} issue(s)
                        </div>
                      )}
                    </td>

                    <td className='px-6 py-4 whitespace-nowrap'>
                      <div className='text-sm text-gray-900'>v{plugin.version}</div>
                      {updates[plugin.installation_id] && (
                        <div className='text-xs text-blue-600'>
                          v{updates[plugin.installation_id].available_version} available
                        </div>
                      )}
                    </td>

                    <td className='px-6 py-4 whitespace-nowrap'>
                      <div className='text-xs text-gray-500'>
                        <div>CPU: {plugin.usage.cpu_usage}%</div>
                        <div>Memory: {Math.round(plugin.usage.memory_usage / 1024 / 1024)}MB</div>
                        <div>API: {plugin.usage.api_calls.toLocaleString()}</div>
                      </div>
                    </td>

                    <td className='px-6 py-4 whitespace-nowrap text-sm font-medium'>
                      <div className='flex items-center space-x-2'>
                        {plugin.status === 'active' ? (
                          <IconButton
                            icon={PowerIcon}
                            size='sm'
                            variant='outline'
                            aria-label='Disable plugin'
                            onClick={() => setConfirmAction({ type: 'disable', plugin })}
                            disabled={actionLoading !== null}
                          />
                        ) : (
                          <IconButton
                            icon={PowerIcon}
                            size='sm'
                            variant='primary'
                            aria-label='Enable plugin'
                            onClick={() => setConfirmAction({ type: 'enable', plugin })}
                            disabled={actionLoading !== null}
                          />
                        )}

                        <IconButton
                          icon={Cog6ToothIcon}
                          size='sm'
                          variant='outline'
                          aria-label='Configure plugin'
                          onClick={() => setConfiguringPlugin(plugin)}
                        />

                        {updates[plugin.installation_id] && (
                          <IconButton
                            icon={ArrowPathIcon}
                            size='sm'
                            variant='success'
                            aria-label='Update plugin'
                            onClick={() => setConfirmAction({ type: 'update', plugin })}
                            disabled={actionLoading !== null}
                          />
                        )}

                        <IconButton
                          icon={ChartBarIcon}
                          size='sm'
                          variant='outline'
                          aria-label='View details'
                          onClick={() => setSelectedPlugin(plugin)}
                        />

                        <IconButton
                          icon={TrashIcon}
                          size='sm'
                          variant='danger'
                          aria-label='Uninstall plugin'
                          onClick={() => setConfirmAction({ type: 'uninstall', plugin })}
                          disabled={actionLoading !== null}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Plugin Details Modal */}
      {selectedPlugin && (
        <PluginDetailsModal plugin={selectedPlugin} onClose={() => setSelectedPlugin(null)} />
      )}

      {/* Configuration Modal */}
      {configuringPlugin && (
        <PluginConfigModal
          plugin={configuringPlugin}
          onClose={() => setConfiguringPlugin(null)}
          onSave={async (config) => {
            try {
              await apiClient.configurePlugin(configuringPlugin.installation_id, config);
              await loadPlugins();
              setConfiguringPlugin(null);
            } catch (err) {
              console.error('Configure plugin error:', err);
              alert('Failed to save configuration');
            }
          }}
        />
      )}

      {/* Confirm Action Modal */}
      {confirmAction && (
        <ConfirmModal
          isOpen={true}
          onClose={() => setConfirmAction(null)}
          onConfirm={() => handlePluginAction(confirmAction.type, confirmAction.plugin)}
          title={`${confirmAction.type.charAt(0).toUpperCase() + confirmAction.type.slice(1)} Plugin`}
          message={`Are you sure you want to ${confirmAction.type} "${confirmAction.plugin.plugin.name}"?`}
          confirmText={confirmAction.type.charAt(0).toUpperCase() + confirmAction.type.slice(1)}
          variant={confirmAction.type === 'uninstall' ? 'danger' : 'info'}
          loading={actionLoading !== null}
        />
      )}
    </div>
  );
}

// Plugin Details Modal Component
interface PluginDetailsModalProps {
  plugin: InstalledPlugin;
  onClose: () => void;
}

function PluginDetailsModal({ plugin, onClose }: PluginDetailsModalProps) {
  return (
    <Modal isOpen={true} onClose={onClose} title={`${plugin.plugin.name} Details`} size='lg'>
      <div className='space-y-6'>
        {/* Plugin Overview */}
        <div className='flex items-start space-x-4'>
          <div className='w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center'>
            {plugin.plugin.icon ? (
              <img src={plugin.plugin.icon} alt={plugin.plugin.name} className='w-12 h-12' />
            ) : (
              <Cog6ToothIcon className='h-8 w-8 text-gray-400' />
            )}
          </div>

          <div className='flex-1'>
            <h3 className='text-lg font-semibold text-gray-900'>{plugin.plugin.name}</h3>
            <p className='text-gray-600 mb-2'>{plugin.plugin.description}</p>
            <div className='flex items-center space-x-4 text-sm text-gray-500'>
              <span>v{plugin.version}</span>
              <span>Status: {plugin.status}</span>
              <span>Health: {plugin.health.status}</span>
            </div>
          </div>
        </div>

        {/* Usage Statistics */}
        <div>
          <h4 className='font-medium text-gray-900 mb-3'>Resource Usage</h4>
          <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
            <div className='bg-gray-50 p-3 rounded'>
              <div className='text-sm text-gray-500'>CPU Usage</div>
              <div className='text-lg font-semibold'>{plugin.usage.cpu_usage}%</div>
            </div>
            <div className='bg-gray-50 p-3 rounded'>
              <div className='text-sm text-gray-500'>Memory</div>
              <div className='text-lg font-semibold'>
                {Math.round(plugin.usage.memory_usage / 1024 / 1024)}MB
              </div>
            </div>
            <div className='bg-gray-50 p-3 rounded'>
              <div className='text-sm text-gray-500'>Storage</div>
              <div className='text-lg font-semibold'>
                {Math.round(plugin.usage.storage_usage / 1024 / 1024)}MB
              </div>
            </div>
            <div className='bg-gray-50 p-3 rounded'>
              <div className='text-sm text-gray-500'>API Calls</div>
              <div className='text-lg font-semibold'>{plugin.usage.api_calls.toLocaleString()}</div>
            </div>
          </div>
        </div>

        {/* License Information */}
        <div>
          <h4 className='font-medium text-gray-900 mb-3'>License</h4>
          <div className='bg-gray-50 p-3 rounded'>
            <div className='flex justify-between items-center'>
              <span className='text-sm text-gray-600'>Tier:</span>
              <span className='font-medium'>{plugin.license.tier}</span>
            </div>
            {plugin.license.expires_at && (
              <div className='flex justify-between items-center mt-2'>
                <span className='text-sm text-gray-600'>Expires:</span>
                <span className='font-medium'>
                  {new Date(plugin.license.expires_at).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Health Issues */}
        {plugin.health.issues.length > 0 && (
          <div>
            <h4 className='font-medium text-gray-900 mb-3'>Health Issues</h4>
            <div className='space-y-2'>
              {plugin.health.issues.map((issue, index) => (
                <div key={index} className='flex items-start space-x-3 p-3 bg-red-50 rounded'>
                  <ExclamationTriangleIcon className='h-5 w-5 text-red-500 mt-0.5' />
                  <div>
                    <div className='font-medium text-red-900'>{issue.type}</div>
                    <div className='text-sm text-red-700'>{issue.message}</div>
                    <div className='text-xs text-red-600 mt-1'>
                      {new Date(issue.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

// Plugin Configuration Modal Component
interface PluginConfigModalProps {
  plugin: InstalledPlugin;
  onClose: () => void;
  onSave: (configuration: Record<string, any>) => void;
}

function PluginConfigModal({ plugin, onClose, onSave }: PluginConfigModalProps) {
  const [config, setConfig] = useState(plugin.configuration);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(config);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title={`Configure ${plugin.plugin.name}`} size='lg'>
      <div className='space-y-4'>
        <p className='text-sm text-gray-600'>Update the configuration settings for this plugin.</p>

        <div className='bg-gray-50 p-4 rounded border'>
          <textarea
            value={JSON.stringify(config, null, 2)}
            onChange={(e) => {
              try {
                setConfig(JSON.parse(e.target.value));
              } catch {
                // Invalid JSON, keep the text for now
              }
            }}
            className='w-full h-64 p-3 border border-gray-300 rounded font-mono text-sm'
            placeholder='Plugin configuration (JSON format)'
          />
        </div>

        <div className='flex justify-end space-x-3'>
          <Button variant='outline' onClick={onClose}>
            Cancel
          </Button>
          <Button variant='primary' loading={saving} onClick={handleSave}>
            Save Configuration
          </Button>
        </div>
      </div>
    </Modal>
  );
}
