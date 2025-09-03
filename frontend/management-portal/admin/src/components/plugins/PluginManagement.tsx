/**
 * Plugin Management Dashboard
 * Main component that orchestrates all plugin management functionality
 * Following DRY patterns from existing components
 */

import React, { useState } from 'react';
import {
  ShoppingBagIcon,
  CubeIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  BugAntIcon,
} from '@heroicons/react/24/outline';
import { Button } from '@dotmac/primitives';
import { PluginMarketplace } from './PluginMarketplace';
import { InstalledPlugins } from './InstalledPlugins';
import { PluginInstallationWizard } from './PluginInstallationWizard';
import { PluginSecurityDashboard } from './PluginSecurityDashboard';
import type { PluginCatalogItem } from '@dotmac/headless';

interface PluginManagementProps {
  className?: string;
}

type TabType = 'marketplace' | 'installed' | 'security' | 'analytics' | 'settings';

export function PluginManagement({ className = '' }: PluginManagementProps) {
  const [activeTab, setActiveTab] = useState<TabType>('installed');
  const [installWizardPlugin, setInstallWizardPlugin] = useState<PluginCatalogItem | null>(null);

  const tabs = [
    {
      id: 'installed' as TabType,
      name: 'Installed Plugins',
      icon: CubeIcon,
      description: 'Manage your installed plugins',
    },
    {
      id: 'marketplace' as TabType,
      name: 'Marketplace',
      icon: ShoppingBagIcon,
      description: 'Browse and install new plugins',
    },
    {
      id: 'security' as TabType,
      name: 'Security',
      icon: ShieldCheckIcon,
      description: 'Plugin security scanning and validation',
    },
    {
      id: 'analytics' as TabType,
      name: 'Analytics',
      icon: ChartBarIcon,
      description: 'Plugin usage and performance analytics',
    },
    {
      id: 'settings' as TabType,
      name: 'Settings',
      icon: Cog6ToothIcon,
      description: 'Plugin system configuration',
    },
  ];

  const handlePluginInstallFromMarketplace = (plugin: PluginCatalogItem) => {
    setInstallWizardPlugin(plugin);
  };

  const handleInstallationComplete = (installationId: string) => {
    console.log('Installation completed:', installationId);
    setInstallWizardPlugin(null);
    setActiveTab('installed');
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'marketplace':
        return <PluginMarketplace className='mt-6' />;

      case 'installed':
        return <InstalledPlugins className='mt-6' />;

      case 'security':
        return <PluginSecurityDashboard className='mt-6' />;

      case 'analytics':
        return <PluginAnalytics className='mt-6' />;

      case 'settings':
        return <PluginSystemSettings className='mt-6' />;

      default:
        return null;
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='bg-white shadow'>
        <div className='px-6 py-4'>
          <div className='flex items-center justify-between'>
            <div>
              <h1 className='text-2xl font-bold text-gray-900'>Plugin Management</h1>
              <p className='mt-1 text-sm text-gray-500'>
                Extend your platform with powerful plugins and integrations
              </p>
            </div>

            <div className='flex space-x-3'>
              <Button variant='outline' onClick={() => setActiveTab('marketplace')}>
                Browse Marketplace
              </Button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className='mt-6'>
            <nav className='-mb-px flex space-x-8'>
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;

                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      group inline-flex items-center py-2 px-1 border-b-2 font-medium text-sm
                      ${
                        isActive
                          ? 'border-primary-500 text-primary-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }
                    `}
                  >
                    <Icon
                      className={`
                        -ml-0.5 mr-2 h-5 w-5
                        ${isActive ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'}
                      `}
                    />
                    {tab.name}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className='px-6'>{renderTabContent()}</div>

      {/* Installation Wizard */}
      {installWizardPlugin && (
        <PluginInstallationWizard
          plugin={installWizardPlugin}
          isOpen={true}
          onClose={() => setInstallWizardPlugin(null)}
          onComplete={handleInstallationComplete}
        />
      )}
    </div>
  );
}

// Plugin Analytics Component
interface PluginAnalyticsProps {
  className?: string;
}

function PluginAnalytics({ className = '' }: PluginAnalyticsProps) {
  return (
    <div className={`space-y-6 ${className}`}>
      <div className='bg-white shadow rounded-lg p-6'>
        <h2 className='text-lg font-medium text-gray-900 mb-4'>Plugin Usage Analytics</h2>

        {/* Overview Cards */}
        <div className='grid grid-cols-1 md:grid-cols-4 gap-6 mb-8'>
          <div className='bg-gray-50 p-4 rounded-lg'>
            <div className='text-sm font-medium text-gray-500'>Total API Calls</div>
            <div className='text-2xl font-bold text-gray-900'>1,234,567</div>
            <div className='text-sm text-green-600'>+12% from last month</div>
          </div>

          <div className='bg-gray-50 p-4 rounded-lg'>
            <div className='text-sm font-medium text-gray-500'>Average Response Time</div>
            <div className='text-2xl font-bold text-gray-900'>45ms</div>
            <div className='text-sm text-green-600'>-8% from last month</div>
          </div>

          <div className='bg-gray-50 p-4 rounded-lg'>
            <div className='text-sm font-medium text-gray-500'>Error Rate</div>
            <div className='text-2xl font-bold text-gray-900'>0.12%</div>
            <div className='text-sm text-green-600'>-0.05% from last month</div>
          </div>

          <div className='bg-gray-50 p-4 rounded-lg'>
            <div className='text-sm font-medium text-gray-500'>Resource Usage</div>
            <div className='text-2xl font-bold text-gray-900'>23%</div>
            <div className='text-sm text-yellow-600'>+3% from last month</div>
          </div>
        </div>

        {/* Charts Placeholder */}
        <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
          <div className='bg-gray-50 p-6 rounded-lg'>
            <h3 className='text-sm font-medium text-gray-900 mb-4'>Plugin Performance</h3>
            <div className='h-64 flex items-center justify-center text-gray-500'>
              <div className='text-center'>
                <ChartBarIcon className='mx-auto h-12 w-12 mb-2' />
                <p>Performance charts will be displayed here</p>
              </div>
            </div>
          </div>

          <div className='bg-gray-50 p-6 rounded-lg'>
            <h3 className='text-sm font-medium text-gray-900 mb-4'>Resource Utilization</h3>
            <div className='h-64 flex items-center justify-center text-gray-500'>
              <div className='text-center'>
                <ChartBarIcon className='mx-auto h-12 w-12 mb-2' />
                <p>Resource utilization charts will be displayed here</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Plugin System Settings Component
interface PluginSystemSettingsProps {
  className?: string;
}

function PluginSystemSettings({ className = '' }: PluginSystemSettingsProps) {
  const [settings, setSettings] = useState({
    auto_updates: false,
    sandbox_enabled: true,
    require_signatures: true,
    allow_unsigned: false,
    max_memory_per_plugin: 512,
    max_cpu_time: 30,
    marketplace_url: 'https://marketplace.dotmac.io',
    backup_before_updates: true,
    telemetry_enabled: true,
  });

  const handleSettingChange = (key: keyof typeof settings, value: any) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <div className='bg-white shadow rounded-lg'>
        {/* Security Settings */}
        <div className='px-6 py-4 border-b border-gray-200'>
          <h2 className='text-lg font-medium text-gray-900'>Security Settings</h2>
          <p className='text-sm text-gray-500 mt-1'>
            Configure security policies for plugin execution
          </p>
        </div>

        <div className='px-6 py-4 space-y-4'>
          <div className='flex items-center justify-between'>
            <div>
              <label className='text-sm font-medium text-gray-900'>Sandbox Enabled</label>
              <p className='text-sm text-gray-500'>Run plugins in isolated sandbox environment</p>
            </div>
            <input
              type='checkbox'
              checked={settings.sandbox_enabled}
              onChange={(e) => handleSettingChange('sandbox_enabled', e.target.checked)}
              className='h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            />
          </div>

          <div className='flex items-center justify-between'>
            <div>
              <label className='text-sm font-medium text-gray-900'>Require Code Signatures</label>
              <p className='text-sm text-gray-500'>
                Only allow signed plugins from verified publishers
              </p>
            </div>
            <input
              type='checkbox'
              checked={settings.require_signatures}
              onChange={(e) => handleSettingChange('require_signatures', e.target.checked)}
              className='h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            />
          </div>

          <div className='flex items-center justify-between'>
            <div>
              <label className='text-sm font-medium text-gray-900'>Allow Unsigned Plugins</label>
              <p className='text-sm text-gray-500'>
                Permit installation of unsigned plugins (not recommended)
              </p>
            </div>
            <input
              type='checkbox'
              checked={settings.allow_unsigned}
              onChange={(e) => handleSettingChange('allow_unsigned', e.target.checked)}
              className='h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            />
          </div>
        </div>

        {/* Resource Limits */}
        <div className='px-6 py-4 border-t border-gray-200'>
          <h3 className='text-base font-medium text-gray-900 mb-4'>Resource Limits</h3>

          <div className='space-y-4'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>
                Maximum Memory per Plugin (MB)
              </label>
              <input
                type='number'
                value={settings.max_memory_per_plugin}
                onChange={(e) =>
                  handleSettingChange('max_memory_per_plugin', parseInt(e.target.value))
                }
                className='block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
              />
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>
                Maximum CPU Time (seconds)
              </label>
              <input
                type='number'
                value={settings.max_cpu_time}
                onChange={(e) => handleSettingChange('max_cpu_time', parseInt(e.target.value))}
                className='block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
              />
            </div>
          </div>
        </div>

        {/* Update Settings */}
        <div className='px-6 py-4 border-t border-gray-200'>
          <h3 className='text-base font-medium text-gray-900 mb-4'>Update Settings</h3>

          <div className='space-y-4'>
            <div className='flex items-center justify-between'>
              <div>
                <label className='text-sm font-medium text-gray-900'>Automatic Updates</label>
                <p className='text-sm text-gray-500'>Automatically install plugin updates</p>
              </div>
              <input
                type='checkbox'
                checked={settings.auto_updates}
                onChange={(e) => handleSettingChange('auto_updates', e.target.checked)}
                className='h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
              />
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <label className='text-sm font-medium text-gray-900'>Backup Before Updates</label>
                <p className='text-sm text-gray-500'>Create backup before applying updates</p>
              </div>
              <input
                type='checkbox'
                checked={settings.backup_before_updates}
                onChange={(e) => handleSettingChange('backup_before_updates', e.target.checked)}
                className='h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
              />
            </div>

            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>
                Marketplace URL
              </label>
              <input
                type='url'
                value={settings.marketplace_url}
                onChange={(e) => handleSettingChange('marketplace_url', e.target.value)}
                className='block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
              />
            </div>
          </div>
        </div>

        {/* Privacy Settings */}
        <div className='px-6 py-4 border-t border-gray-200'>
          <h3 className='text-base font-medium text-gray-900 mb-4'>Privacy Settings</h3>

          <div className='flex items-center justify-between'>
            <div>
              <label className='text-sm font-medium text-gray-900'>Telemetry Enabled</label>
              <p className='text-sm text-gray-500'>
                Send anonymous usage data to improve the platform
              </p>
            </div>
            <input
              type='checkbox'
              checked={settings.telemetry_enabled}
              onChange={(e) => handleSettingChange('telemetry_enabled', e.target.checked)}
              className='h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            />
          </div>
        </div>

        {/* Save Button */}
        <div className='px-6 py-4 border-t border-gray-200 bg-gray-50'>
          <div className='flex justify-end'>
            <Button onClick={() => console.log('Settings saved:', settings)}>Save Settings</Button>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className='bg-white shadow rounded-lg p-6'>
        <h2 className='text-lg font-medium text-gray-900 mb-4'>System Status</h2>

        <div className='space-y-4'>
          <div className='flex items-center justify-between py-2'>
            <span className='text-sm font-medium text-gray-700'>Plugin System</span>
            <div className='flex items-center'>
              <div className='w-2 h-2 bg-green-400 rounded-full mr-2'></div>
              <span className='text-sm text-green-600'>Operational</span>
            </div>
          </div>

          <div className='flex items-center justify-between py-2'>
            <span className='text-sm font-medium text-gray-700'>Marketplace Connection</span>
            <div className='flex items-center'>
              <div className='w-2 h-2 bg-green-400 rounded-full mr-2'></div>
              <span className='text-sm text-green-600'>Connected</span>
            </div>
          </div>

          <div className='flex items-center justify-between py-2'>
            <span className='text-sm font-medium text-gray-700'>Security Scanner</span>
            <div className='flex items-center'>
              <div className='w-2 h-2 bg-yellow-400 rounded-full mr-2'></div>
              <span className='text-sm text-yellow-600'>Updating</span>
            </div>
          </div>

          <div className='flex items-center justify-between py-2'>
            <span className='text-sm font-medium text-gray-700'>License Validation</span>
            <div className='flex items-center'>
              <div className='w-2 h-2 bg-green-400 rounded-full mr-2'></div>
              <span className='text-sm text-green-600'>Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
