'use client';

import { useState } from 'react';
import { Bell, Mail, MessageSquare, Phone, Plus, Shield, Smartphone, X } from 'lucide-react';
import {
  ContactMethod,
  NotificationPreference,
  NotificationSettings as NotificationSettingsType,
} from '../types';

export interface NotificationSettingsProps {
  settings: NotificationSettingsType;
  onUpdate: (settings: Partial<NotificationSettingsType>) => void;
  onSave?: () => Promise<boolean>;
  isLoading?: boolean;
  readonly?: boolean;
  className?: string;
}

export function NotificationSettings({
  settings,
  onUpdate,
  onSave,
  isLoading = false,
  readonly = false,
  className = '',
}: NotificationSettingsProps) {
  const [showAddContact, setShowAddContact] = useState(false);
  const [newContact, setNewContact] = useState({
    type: 'email' as const,
    value: '',
  });

  const updateNotificationPreference = (
    category: string,
    channel: keyof Pick<NotificationPreference, 'email' | 'sms' | 'push'>,
    enabled: boolean
  ) => {
    const updatedPreferences = settings.preferences.map((pref) =>
      pref.category === category ? { ...pref, [channel]: enabled } : pref
    );
    onUpdate({ preferences: updatedPreferences });
  };

  const addContactMethod = () => {
    if (newContact.value.trim()) {
      const contact: ContactMethod = {
        ...newContact,
        verified: false,
        primary: settings.contactMethods.length === 0,
      };
      onUpdate({
        contactMethods: [...settings.contactMethods, contact],
      });
      setNewContact({ type: 'email', value: '' });
      setShowAddContact(false);
    }
  };

  const setPrimaryContact = (index: number) => {
    const updatedMethods = settings.contactMethods.map((method, i) => ({
      ...method,
      primary: i === index,
    }));
    onUpdate({ contactMethods: updatedMethods });
  };

  const removeContactMethod = (index: number) => {
    onUpdate({
      contactMethods: settings.contactMethods.filter((_, i) => i !== index),
    });
  };

  const toggleGlobalSetting = (key: keyof NotificationSettingsType['globalSettings']) => {
    onUpdate({
      globalSettings: {
        ...settings.globalSettings,
        [key]: !settings.globalSettings[key],
      },
    });
  };

  const updateQuietHours = (field: 'start' | 'end', value: string) => {
    onUpdate({
      globalSettings: {
        ...settings.globalSettings,
        quietHours: {
          ...settings.globalSettings.quietHours,
          [field]: value,
        },
      },
    });
  };

  const getContactIcon = (type: string) => {
    const icons = {
      email: <Mail className='h-5 w-5' />,
      sms: <MessageSquare className='h-5 w-5' />,
      phone: <Phone className='h-5 w-5' />,
      push: <Bell className='h-5 w-5' />,
    };
    return icons[type as keyof typeof icons] || icons.email;
  };

  const getContactTypeColor = (type: string) => {
    const colors = {
      email: 'text-blue-600',
      sms: 'text-green-600',
      phone: 'text-purple-600',
      push: 'text-orange-600',
    };
    return colors[type as keyof typeof colors] || 'text-gray-600';
  };

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      <div className='p-6'>
        <div className='mb-6'>
          <h2 className='text-xl font-semibold text-gray-900'>Notification Preferences</h2>
          <p className='mt-1 text-sm text-gray-500'>
            Manage how and when you receive notifications
          </p>
        </div>

        {/* Global Settings */}
        <div className='mb-8 p-4 bg-gray-50 rounded-lg'>
          <h3 className='text-lg font-medium text-gray-900 mb-4'>Global Settings</h3>
          <div className='space-y-4'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Enable All Notifications</h4>
                <p className='text-sm text-gray-500'>Master switch for all notifications</p>
              </div>
              <button
                onClick={() => toggleGlobalSetting('enableAll')}
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.globalSettings.enableAll ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.globalSettings.enableAll ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Quiet Hours</h4>
                <p className='text-sm text-gray-500'>
                  Disable notifications during specified hours
                </p>
              </div>
              <button
                onClick={() => toggleGlobalSetting('quietHours.enabled')}
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.globalSettings.quietHours.enabled ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.globalSettings.quietHours.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {settings.globalSettings.quietHours.enabled && (
              <div className='grid grid-cols-2 gap-4 pl-4'>
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-1'>Start Time</label>
                  <input
                    type='time'
                    value={settings.globalSettings.quietHours.start}
                    onChange={(e) => updateQuietHours('start', e.target.value)}
                    disabled={readonly || isLoading}
                    className='w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50'
                  />
                </div>
                <div>
                  <label className='block text-sm font-medium text-gray-700 mb-1'>End Time</label>
                  <input
                    type='time'
                    value={settings.globalSettings.quietHours.end}
                    onChange={(e) => updateQuietHours('end', e.target.value)}
                    disabled={readonly || isLoading}
                    className='w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50'
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Contact Methods */}
        <div className='mb-8'>
          <div className='flex items-center justify-between mb-4'>
            <h3 className='text-lg font-medium text-gray-900'>Contact Methods</h3>
            {!readonly && (
              <button
                onClick={() => setShowAddContact(!showAddContact)}
                disabled={isLoading}
                className='flex items-center px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50'
              >
                <Plus className='mr-1 h-4 w-4' />
                {showAddContact ? 'Cancel' : 'Add Contact'}
              </button>
            )}
          </div>

          {/* Add Contact Form */}
          {showAddContact && !readonly && (
            <div className='mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg'>
              <div className='grid grid-cols-1 md:grid-cols-3 gap-3'>
                <select
                  value={newContact.type}
                  onChange={(e) => setNewContact({ ...newContact, type: e.target.value as any })}
                  className='px-3 py-2 border border-gray-300 rounded-md text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                >
                  <option value='email'>Email</option>
                  <option value='sms'>SMS</option>
                  <option value='phone'>Phone</option>
                  <option value='push'>Push</option>
                </select>
                <input
                  type='text'
                  placeholder={
                    newContact.type === 'email'
                      ? 'email@example.com'
                      : newContact.type === 'push'
                        ? 'Device token'
                        : '+1 (555) 123-4567'
                  }
                  value={newContact.value}
                  onChange={(e) => setNewContact({ ...newContact, value: e.target.value })}
                  className='px-3 py-2 border border-gray-300 rounded-md text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                />
                <button
                  onClick={addContactMethod}
                  className='px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors'
                >
                  Add
                </button>
              </div>
            </div>
          )}

          {/* Contact Methods List */}
          <div className='space-y-3'>
            {settings.contactMethods.map((method, index) => (
              <div
                key={index}
                className='flex items-center justify-between p-3 border border-gray-200 rounded-lg'
              >
                <div className='flex items-center space-x-3'>
                  <div className={getContactTypeColor(method.type)}>
                    {getContactIcon(method.type)}
                  </div>
                  <div>
                    <div className='flex items-center space-x-2'>
                      <span className='text-sm font-medium text-gray-900'>{method.value}</span>
                      {method.verified && (
                        <span className='px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full'>
                          Verified
                        </span>
                      )}
                      {method.primary && (
                        <span className='px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full'>
                          Primary
                        </span>
                      )}
                    </div>
                    <p className='text-xs text-gray-500 capitalize'>{method.type}</p>
                  </div>
                </div>
                {!readonly && (
                  <div className='flex items-center space-x-2'>
                    {!method.primary && (
                      <button
                        onClick={() => setPrimaryContact(index)}
                        disabled={isLoading}
                        className='text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50'
                      >
                        Set Primary
                      </button>
                    )}
                    <button
                      onClick={() => removeContactMethod(index)}
                      disabled={isLoading}
                      className='text-sm text-red-600 hover:text-red-700 font-medium disabled:opacity-50'
                    >
                      <X className='h-4 w-4' />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {settings.contactMethods.length === 0 && (
            <div className='text-center py-8 text-gray-500'>
              <Mail className='h-12 w-12 mx-auto mb-3 text-gray-300' />
              <p className='text-sm'>No contact methods configured</p>
              <p className='text-xs mt-1'>Add a contact method to receive notifications</p>
            </div>
          )}
        </div>

        {/* Notification Preferences */}
        <div className='mb-6'>
          <h3 className='text-lg font-medium text-gray-900 mb-4'>Notification Categories</h3>
          <div className='space-y-4'>
            {settings.preferences.map((pref) => (
              <div key={pref.category} className='border border-gray-200 rounded-lg p-4'>
                <div className='flex items-start justify-between mb-3'>
                  <div className='flex-1'>
                    <h4 className='text-sm font-medium text-gray-900'>{pref.label}</h4>
                    <p className='text-sm text-gray-600 mt-1'>{pref.description}</p>
                  </div>
                </div>

                <div className='grid grid-cols-3 gap-4'>
                  <label className='flex items-center'>
                    <input
                      type='checkbox'
                      checked={pref.email && settings.globalSettings.enableAll}
                      onChange={(e) =>
                        updateNotificationPreference(pref.category, 'email', e.target.checked)
                      }
                      disabled={readonly || isLoading || !settings.globalSettings.enableAll}
                      className='rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50'
                    />
                    <span className='ml-2 text-sm text-gray-700 flex items-center'>
                      <Mail className='h-4 w-4 mr-1' />
                      Email
                    </span>
                  </label>
                  <label className='flex items-center'>
                    <input
                      type='checkbox'
                      checked={pref.sms && settings.globalSettings.enableAll}
                      onChange={(e) =>
                        updateNotificationPreference(pref.category, 'sms', e.target.checked)
                      }
                      disabled={readonly || isLoading || !settings.globalSettings.enableAll}
                      className='rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50'
                    />
                    <span className='ml-2 text-sm text-gray-700 flex items-center'>
                      <MessageSquare className='h-4 w-4 mr-1' />
                      SMS
                    </span>
                  </label>
                  <label className='flex items-center'>
                    <input
                      type='checkbox'
                      checked={pref.push && settings.globalSettings.enableAll}
                      onChange={(e) =>
                        updateNotificationPreference(pref.category, 'push', e.target.checked)
                      }
                      disabled={readonly || isLoading || !settings.globalSettings.enableAll}
                      className='rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50'
                    />
                    <span className='ml-2 text-sm text-gray-700 flex items-center'>
                      <Smartphone className='h-4 w-4 mr-1' />
                      Push
                    </span>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Save Button */}
        {!readonly && onSave && (
          <div className='pt-4 border-t'>
            <button
              onClick={onSave}
              disabled={isLoading}
              className='w-full sm:w-auto px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
            >
              {isLoading ? (
                <div className='flex items-center'>
                  <div className='mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent' />
                  Saving...
                </div>
              ) : (
                'Save Preferences'
              )}
            </button>
          </div>
        )}

        {/* Info Banner */}
        <div className='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
          <div className='flex items-start'>
            <Shield className='h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0' />
            <div className='ml-3'>
              <h4 className='font-medium text-blue-900'>Notification Tips</h4>
              <div className='mt-1 text-sm text-blue-700'>
                <ul className='list-disc pl-5 space-y-1'>
                  <li>Verify your contact methods to ensure reliable delivery</li>
                  <li>Set one method as primary for critical notifications</li>
                  <li>Use quiet hours to avoid disruptions during sleep</li>
                  <li>Enable push notifications for real-time alerts</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
