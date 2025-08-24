'use client';

import { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Save, 
  RefreshCw, 
  AlertCircle,
  CheckCircle,
  Palette,
  Globe,
  Shield,
  Bell,
  Database,
} from 'lucide-react';
import { useTenantAuth } from '@/components/auth/TenantAuthProvider';

interface ConfigCategory {
  category: string;
  display_name: string;
  description: string;
  settings: Record<string, any>;
  editable_by_tenant: boolean;
  requires_restart: boolean;
}

export default function SettingsPage() {
  const { tenant, user } = useTenantAuth();
  const [configs, setConfigs] = useState<ConfigCategory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('general');
  const [changes, setChanges] = useState<Record<string, Record<string, any>>>({});
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  useEffect(() => {
    loadConfigurations();
  }, []);

  const loadConfigurations = async () => {
    setIsLoading(true);
    try {
      // Mock configuration data - would fetch from API
      const mockConfigs: ConfigCategory[] = [
        {
          category: 'general',
          display_name: 'General Settings',
          description: 'Basic instance configuration settings',
          settings: {
            instance_name: tenant?.display_name || 'My ISP Platform',
            timezone: 'UTC',
            default_language: 'en',
            date_format: 'YYYY-MM-DD',
            currency: 'USD',
          },
          editable_by_tenant: true,
          requires_restart: false,
        },
        {
          category: 'branding',
          display_name: 'Branding & Appearance',
          description: 'Customize the look and feel of your platform',
          settings: {
            primary_color: tenant?.primary_color || '#1f2937',
            logo_url: tenant?.logo_url || '',
            favicon_url: '',
            company_name: tenant?.display_name || '',
            custom_css: '',
          },
          editable_by_tenant: true,
          requires_restart: false,
        },
        {
          category: 'features',
          display_name: 'Feature Settings',
          description: 'Enable or disable platform features',
          settings: {
            customer_self_service: true,
            api_access: true,
            advanced_analytics: false,
            white_labeling: true,
            two_factor_auth: true,
            sms_notifications: false,
          },
          editable_by_tenant: true,
          requires_restart: true,
        },
        {
          category: 'notifications',
          display_name: 'Notification Settings',
          description: 'Configure email and system notifications',
          settings: {
            email_notifications: true,
            welcome_emails: true,
            billing_notifications: true,
            system_alerts: true,
            maintenance_notices: true,
            newsletter_subscription: false,
          },
          editable_by_tenant: true,
          requires_restart: false,
        },
        {
          category: 'security',
          display_name: 'Security Settings',
          description: 'Security and authentication settings',
          settings: {
            session_timeout_minutes: 60,
            password_complexity: 'medium',
            ip_whitelist_enabled: false,
            audit_logging: true,
          },
          editable_by_tenant: false,
          requires_restart: true,
        },
      ];

      setConfigs(mockConfigs);
    } catch (error) {
      console.error('Failed to load configurations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSettingChange = (category: string, key: string, value: any) => {
    setChanges(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value,
      },
    }));
    setSaveStatus('idle');
  };

  const handleSave = async (category: string) => {
    setSaving(true);
    setSaveStatus('idle');

    try {
      // Mock API call - would send to management platform
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Apply changes to local state
      setConfigs(prev => prev.map(config => {
        if (config.category === category && changes[category]) {
          return {
            ...config,
            settings: {
              ...config.settings,
              ...changes[category],
            },
          };
        }
        return config;
      }));

      // Clear changes for this category
      setChanges(prev => {
        const newChanges = { ...prev };
        delete newChanges[category];
        return newChanges;
      });

      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  const getDisplayValue = (category: string, key: string, value: any) => {
    const changedValue = changes[category]?.[key];
    return changedValue !== undefined ? changedValue : value;
  };

  const hasChanges = (category: string) => {
    return changes[category] && Object.keys(changes[category]).length > 0;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'general', name: 'General', icon: SettingsIcon },
    { id: 'branding', name: 'Branding', icon: Palette },
    { id: 'features', name: 'Features', icon: Database },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'security', name: 'Security', icon: Shield },
  ];

  const activeConfig = configs.find(c => c.category === activeTab);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Instance Settings</h2>
        <p className="text-gray-600">
          Configure your {tenant?.display_name} instance settings and preferences.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Navigation */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const config = configs.find(c => c.category === tab.id);
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              const hasUnsavedChanges = hasChanges(tab.id);
              
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-tenant-50 text-tenant-700 border-r-2 border-tenant-600'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-3" />
                  {tab.name}
                  {hasUnsavedChanges && (
                    <div className="ml-auto h-2 w-2 bg-yellow-400 rounded-full" />
                  )}
                  {!config?.editable_by_tenant && (
                    <Shield className="ml-auto h-4 w-4 text-gray-400" />
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-3">
          {activeConfig && (
            <div className="tenant-card p-6">
              {/* Category Header */}
              <div className="border-b border-gray-200 pb-4 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {activeConfig.display_name}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {activeConfig.description}
                    </p>
                  </div>
                  
                  {!activeConfig.editable_by_tenant && (
                    <div className="flex items-center px-2 py-1 bg-gray-100 rounded-md">
                      <Shield className="h-4 w-4 text-gray-500 mr-1" />
                      <span className="text-xs text-gray-600">Managed by platform</span>
                    </div>
                  )}
                </div>

                {activeConfig.requires_restart && hasChanges(activeConfig.category) && (
                  <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-center">
                      <AlertCircle className="h-4 w-4 text-yellow-600 mr-2" />
                      <span className="text-sm text-yellow-800">
                        Changes to these settings require an instance restart
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Settings Form */}
              <div className="space-y-6">
                {Object.entries(activeConfig.settings).map(([key, value]) => {
                  const displayValue = getDisplayValue(activeConfig.category, key, value);
                  const fieldName = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                  
                  return (
                    <div key={key}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {fieldName}
                      </label>
                      
                      {typeof value === 'boolean' ? (
                        <div className="flex items-center">
                          <input
                            type="checkbox"
                            checked={displayValue}
                            onChange={(e) => handleSettingChange(activeConfig.category, key, e.target.checked)}
                            disabled={!activeConfig.editable_by_tenant}
                            className="h-4 w-4 text-tenant-600 focus:ring-tenant-500 border-gray-300 rounded"
                          />
                          <span className="ml-2 text-sm text-gray-600">
                            {displayValue ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                      ) : key === 'primary_color' ? (
                        <div className="flex items-center space-x-3">
                          <input
                            type="color"
                            value={displayValue}
                            onChange={(e) => handleSettingChange(activeConfig.category, key, e.target.value)}
                            disabled={!activeConfig.editable_by_tenant}
                            className="h-10 w-20 border border-gray-300 rounded-md"
                          />
                          <input
                            type="text"
                            value={displayValue}
                            onChange={(e) => handleSettingChange(activeConfig.category, key, e.target.value)}
                            disabled={!activeConfig.editable_by_tenant}
                            className="tenant-input flex-1"
                            placeholder="#000000"
                          />
                        </div>
                      ) : key.includes('url') ? (
                        <input
                          type="url"
                          value={displayValue}
                          onChange={(e) => handleSettingChange(activeConfig.category, key, e.target.value)}
                          disabled={!activeConfig.editable_by_tenant}
                          className="tenant-input"
                          placeholder="https://example.com"
                        />
                      ) : key === 'custom_css' ? (
                        <textarea
                          value={displayValue}
                          onChange={(e) => handleSettingChange(activeConfig.category, key, e.target.value)}
                          disabled={!activeConfig.editable_by_tenant}
                          className="tenant-input h-24 font-mono text-sm"
                          placeholder="/* Custom CSS styles */"
                        />
                      ) : key.includes('complexity') || key.includes('language') ? (
                        <select
                          value={displayValue}
                          onChange={(e) => handleSettingChange(activeConfig.category, key, e.target.value)}
                          disabled={!activeConfig.editable_by_tenant}
                          className="tenant-input"
                        >
                          {key.includes('complexity') ? (
                            <>
                              <option value="low">Low</option>
                              <option value="medium">Medium</option>
                              <option value="high">High</option>
                            </>
                          ) : (
                            <>
                              <option value="en">English</option>
                              <option value="es">Spanish</option>
                              <option value="fr">French</option>
                            </>
                          )}
                        </select>
                      ) : typeof value === 'number' ? (
                        <input
                          type="number"
                          value={displayValue}
                          onChange={(e) => handleSettingChange(activeConfig.category, key, parseInt(e.target.value))}
                          disabled={!activeConfig.editable_by_tenant}
                          className="tenant-input"
                        />
                      ) : (
                        <input
                          type="text"
                          value={displayValue}
                          onChange={(e) => handleSettingChange(activeConfig.category, key, e.target.value)}
                          disabled={!activeConfig.editable_by_tenant}
                          className="tenant-input"
                        />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Save Button */}
              {activeConfig.editable_by_tenant && (
                <div className="mt-8 flex items-center justify-between pt-6 border-t border-gray-200">
                  <div className="flex items-center space-x-4">
                    {saveStatus === 'success' && (
                      <div className="flex items-center text-green-600">
                        <CheckCircle className="h-4 w-4 mr-1" />
                        <span className="text-sm">Settings saved successfully</span>
                      </div>
                    )}
                    {saveStatus === 'error' && (
                      <div className="flex items-center text-red-600">
                        <AlertCircle className="h-4 w-4 mr-1" />
                        <span className="text-sm">Failed to save settings</span>
                      </div>
                    )}
                  </div>

                  <div className="flex space-x-3">
                    <button
                      onClick={() => setChanges(prev => ({ ...prev, [activeConfig.category]: {} }))}
                      disabled={!hasChanges(activeConfig.category) || isSaving}
                      className="tenant-button-secondary"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Reset
                    </button>
                    
                    <button
                      onClick={() => handleSave(activeConfig.category)}
                      disabled={!hasChanges(activeConfig.category) || isSaving}
                      className="tenant-button-primary"
                    >
                      {isSaving ? (
                        <div className="flex items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                          Saving...
                        </div>
                      ) : (
                        <>
                          <Save className="h-4 w-4 mr-2" />
                          Save Changes
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}