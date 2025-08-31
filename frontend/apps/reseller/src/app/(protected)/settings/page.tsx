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
import { User, Bell, Shield, Palette, Save, DollarSign, Briefcase } from 'lucide-react';

// Reseller-specific mock data
const mockResellerProfileData: ProfileData = {
  id: 'reseller_789',
  firstName: 'David',
  lastName: 'Chen',
  email: 'david.chen@techpartners.com',
  phone: '+1 (555) 456-7890',
  dateOfBirth: '1988-11-10',
  address: {
    street: '321 Business Center Dr, Floor 15',
    city: 'Austin',
    state: 'TX',
    zipCode: '73301',
    country: 'United States',
  },
  preferences: {
    language: 'en-US',
    timezone: 'America/Chicago',
    dateFormat: 'MM/DD/YYYY',
    currency: 'USD',
  },
  emergencyContact: {
    name: 'Lisa Chen',
    relationship: 'Partner',
    phone: '+1 (555) 789-0123',
    email: 'lisa.chen@email.com',
  },
  lastUpdated: '2024-01-22T16:45:00Z',
};

export default function ResellerSettingsPage() {
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'security' | 'appearance'>('profile');
  const [profileData, setProfileData] = useState<ProfileData>(mockResellerProfileData);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettingsType>(() => {
    const defaults = getDefaultNotificationSettings();
    // Reseller-specific notification settings
    return {
      ...defaults,
      contactMethods: [
        { type: 'email', value: 'david.chen@techpartners.com', verified: true, primary: true },
        { type: 'sms', value: '+1 (555) 456-7890', verified: true, primary: false },
        { type: 'push', value: 'reseller-device-token', verified: true, primary: false },
      ],
      preferences: defaults.preferences.map(pref => ({
        ...pref,
        // Enable business-critical notifications for resellers
        email: ['billing', 'service', 'account', 'commission'].includes(pref.category) ? true : pref.email,
        sms: ['service', 'account'].includes(pref.category) ? true : pref.sms,
        push: ['service', 'account', 'commission'].includes(pref.category) ? true : pref.push,
      })),
      globalSettings: {
        enableAll: true,
        quietHours: {
          enabled: false, // Business hours availability
          start: '22:00',
          end: '08:00',
        },
      },
    };
  });
  const [securitySettings, setSecuritySettings] = useState<SecuritySettingsType>(() => {
    const defaults = getDefaultSecuritySettings();
    return {
      ...defaults,
      // Reseller-appropriate security settings
      passwordPolicy: {
        ...defaults.passwordPolicy,
        minLength: 10,
        expiryDays: 90,
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSpecialChars: true,
      },
      twoFactor: {
        ...defaults.twoFactor,
        required: false, // Recommended but not mandatory
      },
      sessions: {
        maxConcurrent: 4, // Multiple devices for business use
        timeoutMinutes: 180, // Extended for business workflows
      },
    };
  });
  const [appearanceSettings, setAppearanceSettings] = useState<AppearanceSettingsType>(() => {
    const defaults = getDefaultAppearanceSettings();
    return {
      ...defaults,
      // Business-focused defaults
      theme: {
        ...defaults.theme,
        mode: 'light', // Professional appearance
        compactMode: false, // Better readability for business use
      },
      layout: {
        ...defaults.layout,
        density: 'comfortable',
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
    persistKey: 'reseller-settings',
    autoSave: false,
  });

  const tabs = [
    {
      id: 'profile' as const,
      label: 'Profile',
      icon: User,
      description: 'Business profile and contact details'
    },
    {
      id: 'notifications' as const,
      label: 'Notifications',
      icon: Bell,
      description: 'Business alerts and communications'
    },
    {
      id: 'security' as const,
      label: 'Security',
      icon: Shield,
      description: 'Account protection and access control'
    },
    {
      id: 'appearance' as const,
      label: 'Appearance',
      icon: Palette,
      description: 'Interface customization'
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
        // Settings saved successfully - success handled by UI feedback
      }
      return success;
    } catch (error) {
      console.error('Failed to save reseller settings:', error);
      return false;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Briefcase className="h-8 w-8 text-gray-600 mr-3" />
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">Business Account Settings</h1>
                <p className="mt-1 text-sm text-gray-600">
                  Manage your reseller account and business preferences
                </p>
              </div>
            </div>
            {settingsContext.isDirty && (
              <div className="flex items-center space-x-3">
                <div className="flex items-center text-amber-600">
                  <div className="h-2 w-2 bg-amber-400 rounded-full mr-2"></div>
                  <span className="text-sm font-medium">Unsaved changes</span>
                </div>
                <button
                  onClick={handleSaveAll}
                  disabled={settingsContext.isLoading}
                  className="inline-flex items-center px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  <Save className="mr-2 h-4 w-4" />
                  {settingsContext.isLoading ? 'Saving...' : 'Save All Settings'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="lg:grid lg:grid-cols-12 lg:gap-x-8">
          {/* Sidebar Navigation */}
          <aside className="py-6 px-2 sm:px-6 lg:py-0 lg:px-0 lg:col-span-3">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="p-4">
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                  Account Settings
                </h3>
                <nav className="mt-4 space-y-2">
                  {tabs.map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`group rounded-lg p-3 w-full text-left transition-all ${
                        activeTab === tab.id
                          ? 'bg-green-50 border-l-4 border-green-500 text-green-700'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                      }`}
                    >
                      <div className="flex items-center">
                        <div className={`flex-shrink-0 ${
                          activeTab === tab.id ? 'text-green-500' : 'text-gray-400 group-hover:text-gray-500'
                        }`}>
                          <tab.icon className="h-5 w-5" />
                        </div>
                        <div className="ml-3">
                          <p className={`text-sm font-medium ${
                            activeTab === tab.id ? 'text-green-900' : 'text-gray-900'
                          }`}>
                            {tab.label}
                          </p>
                          <p className={`text-xs mt-0.5 ${
                            activeTab === tab.id ? 'text-green-700' : 'text-gray-500'
                          }`}>
                            {tab.description}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </nav>
              </div>
            </div>

            {/* Business Status Card */}
            <div className="mt-6 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg p-4 text-white">
              <div className="flex items-center">
                <DollarSign className="h-6 w-6 mr-3" />
                <div>
                  <p className="text-sm font-semibold">Reseller Account</p>
                  <p className="text-xs opacity-90">Business partner access</p>
                </div>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <main className="mt-6 lg:mt-0 lg:col-span-9">
            {activeTab === 'profile' && (
              <ProfileSettings
                profileData={profileData}
                onUpdate={handleProfileUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className="shadow-sm"
              />
            )}

            {activeTab === 'notifications' && (
              <NotificationSettings
                settings={notificationSettings}
                onUpdate={handleNotificationUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className="shadow-sm"
              />
            )}

            {activeTab === 'security' && (
              <SecuritySettings
                settings={securitySettings}
                onUpdate={handleSecurityUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className="shadow-sm"
              />
            )}

            {activeTab === 'appearance' && (
              <AppearanceSettings
                settings={appearanceSettings}
                onUpdate={handleAppearanceUpdate}
                onSave={handleSaveAll}
                isLoading={settingsContext.isLoading}
                className="shadow-sm"
              />
            )}
          </main>
        </div>

        {/* Global Error Display */}
        {Object.keys(settingsContext.errors).length > 0 && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="font-semibold text-red-900 mb-2">Configuration Errors</h4>
            <ul className="text-sm text-red-700 space-y-1">
              {Object.entries(settingsContext.errors).map(([key, error]) => (
                <li key={key}>• {error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Business Notice */}
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-start">
            <Briefcase className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
            <div className="ml-3">
              <h4 className="font-medium text-green-900">Business Account Information</h4>
              <p className="mt-1 text-sm text-green-700">
                Your reseller account settings affect customer management capabilities and commission tracking.
                Enable business notifications to stay informed about sales opportunities and customer service requests.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
