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
import { User, Bell, Shield, Palette, Save } from 'lucide-react';

// Mock data matching customer portal context
const mockProfileData: ProfileData = {
  id: 'customer_123',
  firstName: 'Sarah',
  lastName: 'Johnson',
  email: 'sarah.johnson@email.com',
  phone: '+1 (555) 123-4567',
  dateOfBirth: '1990-03-15',
  address: {
    street: '456 Oak Avenue, Unit 3A',
    city: 'Portland',
    state: 'OR',
    zipCode: '97205',
    country: 'United States',
  },
  preferences: {
    language: 'en-US',
    timezone: 'America/Los_Angeles',
    dateFormat: 'MM/DD/YYYY',
    currency: 'USD',
  },
  emergencyContact: {
    name: 'Michael Johnson',
    relationship: 'Spouse',
    phone: '+1 (555) 987-6543',
    email: 'michael.johnson@email.com',
  },
  lastUpdated: '2024-01-20T14:30:00Z',
};

export default function CustomerSettingsPage() {
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'security' | 'appearance'>('profile');
  const [profileData, setProfileData] = useState<ProfileData>(mockProfileData);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettingsType>(() => {
    const defaults = getDefaultNotificationSettings();
    // Customer-specific notification settings
    return {
      ...defaults,
      contactMethods: [
        { type: 'email', value: 'sarah.johnson@email.com', verified: true, primary: true },
        { type: 'sms', value: '+1 (555) 123-4567', verified: true, primary: false },
      ],
      preferences: defaults.preferences.map(pref => ({
        ...pref,
        // Enable billing notifications for customers
        email: pref.category === 'billing' ? true : pref.email,
        sms: pref.category === 'service' ? true : pref.sms,
      })),
    };
  });
  const [securitySettings, setSecuritySettings] = useState<SecuritySettingsType>(() => {
    const defaults = getDefaultSecuritySettings();
    return {
      ...defaults,
      // Customer-appropriate security settings
      passwordPolicy: {
        ...defaults.passwordPolicy,
        minLength: 8,
        expiryDays: 180, // Longer for customers
      },
      sessions: {
        maxConcurrent: 5, // More sessions for customers
        timeoutMinutes: 240, // Longer timeout
      },
    };
  });
  const [appearanceSettings, setAppearanceSettings] = useState<AppearanceSettingsType>(
    getDefaultAppearanceSettings()
  );

  const settingsContext = useSettings({
    initialData: {
      profile: profileData,
      notifications: notificationSettings,
      security: securitySettings,
      appearance: appearanceSettings,
    },
    persistKey: 'customer-settings',
    autoSave: false,
  });

  const tabs = [
    {
      id: 'profile' as const,
      label: 'Profile',
      icon: User,
      description: 'Personal and account information'
    },
    {
      id: 'notifications' as const,
      label: 'Notifications',
      icon: Bell,
      description: 'Service alerts and communications'
    },
    {
      id: 'security' as const,
      label: 'Security',
      icon: Shield,
      description: 'Password and account security'
    },
    {
      id: 'appearance' as const,
      label: 'Appearance',
      icon: Palette,
      description: 'Display and accessibility'
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
        // Could trigger a toast notification here
        console.log('Customer settings saved successfully');
      }
      return success;
    } catch (error) {
      console.error('Failed to save customer settings:', error);
      return false;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Account Settings</h1>
              <p className="mt-1 text-sm text-gray-600">
                Manage your account preferences and service settings
              </p>
            </div>
            {settingsContext.isDirty && (
              <button
                onClick={handleSaveAll}
                disabled={settingsContext.isLoading}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                <Save className="mr-2 h-4 w-4" />
                {settingsContext.isLoading ? 'Saving...' : 'Save Changes'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {/* Unsaved Changes Banner */}
        {settingsContext.isDirty && (
          <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-2 w-2 bg-amber-400 rounded-full"></div>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-amber-800">
                    You have unsaved changes to your account settings
                  </p>
                </div>
              </div>
              <button
                onClick={handleSaveAll}
                disabled={settingsContext.isLoading}
                className="ml-3 px-3 py-1 bg-amber-600 text-white text-sm font-medium rounded-md hover:bg-amber-700 transition-colors disabled:opacity-50"
              >
                {settingsContext.isLoading ? 'Saving...' : 'Save Now'}
              </button>
            </div>
          </div>
        )}

        <div className="lg:grid lg:grid-cols-12 lg:gap-x-8">
          {/* Sidebar Navigation */}
          <aside className="py-6 px-2 sm:px-6 lg:py-0 lg:px-0 lg:col-span-3">
            <nav className="space-y-2">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group rounded-lg p-4 w-full text-left transition-all ${
                    activeTab === tab.id
                      ? 'bg-blue-50 border-2 border-blue-200 text-blue-700 shadow-sm'
                      : 'bg-white border-2 border-gray-200 text-gray-900 hover:bg-gray-50 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center">
                    <div className={`flex-shrink-0 ${
                      activeTab === tab.id ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
                    }`}>
                      <tab.icon className="h-6 w-6" />
                    </div>
                    <div className="ml-3">
                      <p className={`text-sm font-semibold ${
                        activeTab === tab.id ? 'text-blue-900' : 'text-gray-900'
                      }`}>
                        {tab.label}
                      </p>
                      <p className={`text-xs mt-0.5 ${
                        activeTab === tab.id ? 'text-blue-700' : 'text-gray-500'
                      }`}>
                        {tab.description}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </nav>
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
            <h4 className="font-semibold text-red-900 mb-2">Settings Errors</h4>
            <ul className="text-sm text-red-700 space-y-1">
              {Object.entries(settingsContext.errors).map(([key, error]) => (
                <li key={key}>• {error}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
