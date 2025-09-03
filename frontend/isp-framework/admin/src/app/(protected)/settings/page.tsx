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
} from '@dotmac/settings-system';
import { User, Bell, Shield, Palette, Save, Settings } from 'lucide-react';

// Admin-specific mock data
const mockAdminProfileData: ProfileData = {
  id: 'admin_456',
  firstName: 'Alex',
  lastName: 'Rodriguez',
  email: 'alex.rodriguez@company.com',
  phone: '+1 (555) 987-6543',
  dateOfBirth: '1985-09-22',
  address: {
    street: '789 Corporate Blvd, Suite 200',
    city: 'San Francisco',
    state: 'CA',
    zipCode: '94107',
    country: 'United States',
  },
  preferences: {
    language: 'en-US',
    timezone: 'America/Los_Angeles',
    dateFormat: 'YYYY-MM-DD',
    currency: 'USD',
  },
  emergencyContact: {
    name: 'Maria Rodriguez',
    relationship: 'Spouse',
    phone: '+1 (555) 123-9876',
    email: 'maria.rodriguez@email.com',
  },
  lastUpdated: '2024-01-25T09:15:00Z',
};

export default function AdminSettingsPage() {
  const [activeTab, setActiveTab] = useState<
    'profile' | 'notifications' | 'security' | 'appearance'
  >('profile');
  const [profileData, setProfileData] = useState<ProfileData>(mockAdminProfileData);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettingsType>(() => {
    const defaults = getDefaultNotificationSettings();
    // Admin-specific notification settings
    return {
      ...defaults,
      contactMethods: [
        { type: 'email', value: 'alex.rodriguez@company.com', verified: true, primary: true },
        { type: 'sms', value: '+1 (555) 987-6543', verified: true, primary: false },
        { type: 'push', value: 'admin-device-token', verified: true, primary: false },
      ],
      preferences: defaults.preferences.map((pref) => ({
        ...pref,
        // Enable all critical notifications for admins
        email: ['billing', 'service', 'account', 'technical', 'support'].includes(pref.category)
          ? true
          : pref.email,
        sms: ['service', 'account', 'technical'].includes(pref.category) ? true : pref.sms,
        push: ['service', 'account', 'technical', 'support'].includes(pref.category)
          ? true
          : pref.push,
      })),
      globalSettings: {
        enableAll: true,
        quietHours: {
          enabled: true,
          start: '23:00',
          end: '07:00',
        },
      },
    };
  });
  const [securitySettings, setSecuritySettings] = useState<SecuritySettingsType>(() => {
    const defaults = getDefaultSecuritySettings();
    return {
      ...defaults,
      // Admin-specific stricter security settings
      passwordPolicy: {
        ...defaults.passwordPolicy,
        minLength: 12,
        expiryDays: 60, // Shorter for admins
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSpecialChars: true,
      },
      twoFactor: {
        ...defaults.twoFactor,
        required: true, // Mandatory for admins
      },
      sessions: {
        maxConcurrent: 3, // Limited for admins
        timeoutMinutes: 60, // Shorter timeout
      },
    };
  });
  const [appearanceSettings, setAppearanceSettings] = useState<AppearanceSettingsType>(() => {
    const defaults = getDefaultAppearanceSettings();
    return {
      ...defaults,
      // Admin-friendly defaults
      theme: {
        ...defaults.theme,
        mode: 'system',
        compactMode: true, // More info density for admins
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
    persistKey: 'admin-settings',
    autoSave: false,
  });

  const tabs = [
    {
      id: 'profile' as const,
      label: 'Profile',
      icon: User,
      description: 'Administrator profile and details',
    },
    {
      id: 'notifications' as const,
      label: 'Notifications',
      icon: Bell,
      description: 'System alerts and communications',
    },
    {
      id: 'security' as const,
      label: 'Security',
      icon: Shield,
      description: 'Enhanced security settings',
    },
    {
      id: 'appearance' as const,
      label: 'Appearance',
      icon: Palette,
      description: 'Interface and accessibility',
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
        console.log('Admin settings saved successfully');
      }
      return success;
    } catch (error) {
      console.error('Failed to save admin settings:', error);
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
                <h1 className='text-2xl font-semibold text-gray-900'>Administrator Settings</h1>
                <p className='mt-1 text-sm text-gray-600'>
                  Manage your administrative account and system preferences
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
                  className='inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50'
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
                  Settings Categories
                </h3>
                <nav className='mt-4 space-y-2'>
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`group rounded-lg p-3 w-full text-left transition-all ${
                        activeTab === tab.id
                          ? 'bg-blue-50 border-l-4 border-blue-500 text-blue-700'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                      }`}
                    >
                      <div className='flex items-center'>
                        <div
                          className={`flex-shrink-0 ${
                            activeTab === tab.id
                              ? 'text-blue-500'
                              : 'text-gray-400 group-hover:text-gray-500'
                          }`}
                        >
                          <tab.icon className='h-5 w-5' />
                        </div>
                        <div className='ml-3'>
                          <p
                            className={`text-sm font-medium ${
                              activeTab === tab.id ? 'text-blue-900' : 'text-gray-900'
                            }`}
                          >
                            {tab.label}
                          </p>
                          <p
                            className={`text-xs mt-0.5 ${
                              activeTab === tab.id ? 'text-blue-700' : 'text-gray-500'
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

            {/* Admin Status Card */}
            <div className='mt-6 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-4 text-white'>
              <div className='flex items-center'>
                <Shield className='h-6 w-6 mr-3' />
                <div>
                  <p className='text-sm font-semibold'>Administrator Account</p>
                  <p className='text-xs opacity-90'>Enhanced security required</p>
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

        {/* Admin Notice */}
        <div className='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
          <div className='flex items-start'>
            <Shield className='h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0' />
            <div className='ml-3'>
              <h4 className='font-medium text-blue-900'>Administrator Notice</h4>
              <p className='mt-1 text-sm text-blue-700'>
                These settings apply to your administrator account. Changes to security settings may
                require re-authentication. All administrative actions are logged for security
                auditing purposes.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
