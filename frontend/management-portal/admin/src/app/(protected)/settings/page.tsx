'use client';

import { useState } from 'react';
import {
  ProfileSettings,
  NotificationSettings,
  SecuritySettings,
  AppearanceSettings,
  useSettings,
  getDefaultNotificationSettings,
  getDefaultSecuritySettings,
  getDefaultAppearanceSettings,
  type ProfileData,
  type NotificationSettings as NotificationSettingsType,
  type SecuritySettings as SecuritySettingsType,
  type AppearanceSettings as AppearanceSettingsType,
} from '@/components/adapters/SettingsComponents';
import { User, Bell, Shield, Palette, Save, Crown, Settings } from 'lucide-react';

// Management Admin-specific mock data
const mockManagementAdminProfileData: ProfileData = {
  id: 'mgmt_admin_001',
  firstName: 'Emma',
  lastName: 'Thompson',
  email: 'emma.thompson@dotmac.enterprise',
  phone: '+1 (555) 999-0000',
  dateOfBirth: '1982-07-14',
  address: {
    street: '1000 Enterprise Plaza, Executive Floor',
    city: 'New York',
    state: 'NY',
    zipCode: '10001',
    country: 'United States',
  },
  preferences: {
    language: 'en-US',
    timezone: 'America/New_York',
    dateFormat: 'YYYY-MM-DD',
    currency: 'USD',
  },
  emergencyContact: {
    name: 'James Thompson',
    relationship: 'Spouse',
    phone: '+1 (555) 888-9999',
    email: 'james.thompson@email.com',
  },
  lastUpdated: '2024-01-28T08:00:00Z',
};

export default function ManagementAdminSettingsPage() {
  const [activeTab, setActiveTab] = useState<
    'profile' | 'notifications' | 'security' | 'appearance'
  >('profile');
  const [profileData, setProfileData] = useState<ProfileData>(mockManagementAdminProfileData);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettingsType>(() => {
    const defaults = getDefaultNotificationSettings();
    // Management Admin-specific notification settings
    return {
      ...defaults,
      contactMethods: [
        { type: 'email', value: 'emma.thompson@dotmac.enterprise', verified: true, primary: true },
        { type: 'sms', value: '+1 (555) 999-0000', verified: true, primary: false },
        { type: 'push', value: 'mgmt-admin-device-token', verified: true, primary: false },
      ],
      preferences: defaults.preferences.map((pref) => ({
        ...pref,
        // Enable all critical notifications for management admins
        email: ['billing', 'service', 'account', 'technical', 'support', 'system'].includes(
          pref.category
        )
          ? true
          : pref.email,
        sms: ['service', 'account', 'technical', 'system'].includes(pref.category)
          ? true
          : pref.sms,
        push: ['service', 'account', 'technical', 'support', 'system'].includes(pref.category)
          ? true
          : pref.push,
      })),
      globalSettings: {
        enableAll: true,
        quietHours: {
          enabled: false, // 24/7 availability for critical management
          start: '23:30',
          end: '06:00',
        },
      },
    };
  });
  const [securitySettings, setSecuritySettings] = useState<SecuritySettingsType>(() => {
    const defaults = getDefaultSecuritySettings();
    return {
      ...defaults,
      // Management Admin-specific strictest security settings
      passwordPolicy: {
        ...defaults.passwordPolicy,
        minLength: 14, // Highest security requirement
        expiryDays: 30, // Most frequent password changes
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSpecialChars: true,
      },
      twoFactor: {
        ...defaults.twoFactor,
        required: true, // Absolutely mandatory
      },
      sessions: {
        maxConcurrent: 2, // Most restrictive for security
        timeoutMinutes: 30, // Shortest timeout for maximum security
      },
    };
  });
  const [appearanceSettings, setAppearanceSettings] = useState<AppearanceSettingsType>(() => {
    const defaults = getDefaultAppearanceSettings();
    return {
      ...defaults,
      // Management-focused defaults
      theme: {
        ...defaults.theme,
        mode: 'system',
        compactMode: true, // Maximum information density
      },
      layout: {
        ...defaults.layout,
        density: 'compact',
        showTooltips: true,
      },
    };
  });

  const settingsContext = useSettings({
    initialData: {
      profile: profileData,
      notifications: notificationSettings,
      security: securitySettings,
      appearance: appearanceSettings,
    },
    persistKey: 'management-admin-settings',
    autoSave: false,
  });

  const tabs = [
    {
      id: 'profile' as const,
      label: 'Profile',
      icon: User,
      description: 'Executive profile and credentials',
    },
    {
      id: 'notifications' as const,
      label: 'Notifications',
      icon: Bell,
      description: 'System-wide alerts and monitoring',
    },
    {
      id: 'security' as const,
      label: 'Security',
      icon: Shield,
      description: 'Maximum security protocols',
    },
    {
      id: 'appearance' as const,
      label: 'Appearance',
      icon: Palette,
      description: 'Interface optimization',
    },
  ];

  const handleProfileUpdate = (data: Partial<ProfileData>) => {
    const updatedProfile = { ...profileData, ...data, lastUpdated: new Date().toISOString() };
    setProfileData(updatedProfile);
    settingsContext.updateSetting('profile', updatedProfile);
  };

  const handleNotificationUpdate = (data: Partial<NotificationSettingsType>) => {
    const updated = { ...notificationSettings, ...data };
    setNotificationSettings(updated);
    settingsContext.updateSetting('notifications', updated);
  };

  const handleSecurityUpdate = (data: Partial<SecuritySettingsType>) => {
    const updated = { ...securitySettings, ...data };
    setSecuritySettings(updated);
    settingsContext.updateSetting('security', updated);
  };

  const handleAppearanceUpdate = (data: Partial<AppearanceSettingsType>) => {
    const updated = { ...appearanceSettings, ...data };
    setAppearanceSettings(updated);
    settingsContext.updateSetting('appearance', updated);
  };

  const handleSaveAll = async (): Promise<boolean> => {
    try {
      const success = await settingsContext.saveSettings();
      if (success) {
        console.log('Management admin settings saved successfully');
      }
      return success;
    } catch (error) {
      console.error('Failed to save management admin settings:', error);
      return false;
    }
  };

  return (
    <div className='min-h-screen bg-gray-50'>
      {/* Header */}
      <div className='bg-white border-b border-gray-200 shadow-sm'>
        <div className='max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center'>
              <Settings className='h-8 w-8 text-gray-600 mr-3' />
              <div>
                <h1 className='text-2xl font-semibold text-gray-900'>
                  Master Administration Settings
                </h1>
                <p className='mt-1 text-sm text-gray-600'>
                  Configure enterprise-level management account and system preferences
                </p>
              </div>
            </div>
            {settingsContext.isDirty && (
              <div className='flex items-center space-x-3'>
                <div className='flex items-center text-amber-600'>
                  <div className='h-2 w-2 bg-amber-400 rounded-full mr-2'></div>
                  <span className='text-sm font-medium'>Unsaved changes</span>
                </div>
                <button
                  onClick={handleSaveAll}
                  disabled={settingsContext.isLoading}
                  className='inline-flex items-center px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 transition-colors disabled:opacity-50'
                >
                  <Save className='mr-2 h-4 w-4' />
                  {settingsContext.isLoading ? 'Saving...' : 'Save All Settings'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className='max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8'>
        <div className='lg:grid lg:grid-cols-12 lg:gap-x-8'>
          {/* Sidebar Navigation */}
          <aside className='py-6 px-2 sm:px-6 lg:py-0 lg:px-0 lg:col-span-3'>
            <div className='bg-white rounded-lg border border-gray-200 shadow-sm'>
              <div className='p-4'>
                <h3 className='text-sm font-semibold text-gray-900 uppercase tracking-wide'>
                  Master Settings
                </h3>
                <nav className='mt-4 space-y-2'>
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`group rounded-lg p-3 w-full text-left transition-all ${
                        activeTab === tab.id
                          ? 'bg-purple-50 border-l-4 border-purple-500 text-purple-700'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                      }`}
                    >
                      <div className='flex items-center'>
                        <div
                          className={`flex-shrink-0 ${
                            activeTab === tab.id
                              ? 'text-purple-500'
                              : 'text-gray-400 group-hover:text-gray-500'
                          }`}
                        >
                          <tab.icon className='h-5 w-5' />
                        </div>
                        <div className='ml-3'>
                          <p
                            className={`text-sm font-medium ${
                              activeTab === tab.id ? 'text-purple-900' : 'text-gray-900'
                            }`}
                          >
                            {tab.label}
                          </p>
                          <p
                            className={`text-xs mt-0.5 ${
                              activeTab === tab.id ? 'text-purple-700' : 'text-gray-500'
                            }`}
                          >
                            {tab.description}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </nav>
              </div>
            </div>

            {/* Executive Status Card */}
            <div className='mt-6 bg-gradient-to-r from-purple-600 to-indigo-700 rounded-lg p-4 text-white'>
              <div className='flex items-center'>
                <Crown className='h-6 w-6 mr-3' />
                <div>
                  <p className='text-sm font-semibold'>Master Administrator</p>
                  <p className='text-xs opacity-90'>Enterprise-level access</p>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className='mt-6 lg:mt-0 lg:col-span-9'>
            {activeTab === 'profile' && (
              <ProfileSettings
                profileData={profileData}
                onUpdate={handleProfileUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className='shadow-sm'
              />
            )}

            {activeTab === 'notifications' && (
              <NotificationSettings
                settings={notificationSettings}
                onUpdate={handleNotificationUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className='shadow-sm'
              />
            )}

            {activeTab === 'security' && (
              <SecuritySettings
                settings={securitySettings}
                onUpdate={handleSecurityUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className='shadow-sm'
              />
            )}

            {activeTab === 'appearance' && (
              <AppearanceSettings
                settings={appearanceSettings}
                onUpdate={handleAppearanceUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className='shadow-sm'
              />
            )}
          </main>
        </div>

        {/* Global Error Display */}
        {Object.keys(settingsContext.errors).length > 0 && (
          <div className='mt-6 p-4 bg-red-50 border border-red-200 rounded-lg'>
            <h4 className='font-semibold text-red-900 mb-2'>Configuration Errors</h4>
            <ul className='text-sm text-red-700 space-y-1'>
              {Object.entries(settingsContext.errors).map(([key, error]) => (
                <li key={key}>• {error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Executive Notice */}
        <div className='mt-6 p-4 bg-purple-50 border border-purple-200 rounded-lg'>
          <div className='flex items-start'>
            <Crown className='h-5 w-5 text-purple-600 mt-0.5 flex-shrink-0' />
            <div className='ml-3'>
              <h4 className='font-medium text-purple-900'>Master Administrator Notice</h4>
              <p className='mt-1 text-sm text-purple-700'>
                These settings control enterprise-wide administrative access and monitoring
                capabilities. All configuration changes are subject to the highest security
                protocols and are audited for compliance. Changes to security settings may require
                additional authentication and approval processes.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
