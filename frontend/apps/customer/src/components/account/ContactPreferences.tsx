/**
 * Contact Preferences Component
 * Manages communication preferences and notification settings
 */

'use client';

import { useState } from 'react';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Input } from '../ui/Input';

interface ContactMethod {
  type: 'email' | 'sms' | 'phone' | 'push';
  value: string;
  verified: boolean;
  primary: boolean;
}

interface NotificationPreference {
  category: string;
  label: string;
  description: string;
  email: boolean;
  sms: boolean;
  push: boolean;
}

export function ContactPreferences() {
  const [contactMethods, setContactMethods] = useState<ContactMethod[]>([
    { type: 'email', value: 'john@example.com', verified: true, primary: true },
    { type: 'sms', value: '+1 (555) 123-4567', verified: true, primary: false },
    { type: 'phone', value: '+1 (555) 123-4567', verified: true, primary: false },
  ]);

  const [notifications, setNotifications] = useState<NotificationPreference[]>([
    {
      category: 'billing',
      label: 'Billing & Payments',
      description: 'Invoice notifications, payment confirmations, billing issues',
      email: true,
      sms: false,
      push: true,
    },
    {
      category: 'service',
      label: 'Service Updates',
      description: 'Outages, maintenance, service changes',
      email: true,
      sms: true,
      push: true,
    },
    {
      category: 'account',
      label: 'Account Security',
      description: 'Login alerts, security notifications, password changes',
      email: true,
      sms: true,
      push: true,
    },
    {
      category: 'marketing',
      label: 'Promotions & Offers',
      description: 'Special deals, new service announcements',
      email: false,
      sms: false,
      push: false,
    },
    {
      category: 'support',
      label: 'Support Updates',
      description: 'Ticket updates, support case notifications',
      email: true,
      sms: false,
      push: true,
    },
  ]);

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
    setNotifications(
      notifications.map(notif =>
        notif.category === category ? { ...notif, [channel]: enabled } : notif
      )
    );
  };

  const addContactMethod = () => {
    if (newContact.value) {
      const contact: ContactMethod = {
        ...newContact,
        verified: false,
        primary: false,
      };
      setContactMethods([...contactMethods, contact]);
      setNewContact({ type: 'email', value: '' });
      setShowAddContact(false);
    }
  };

  const setPrimaryContact = (index: number) => {
    const updatedMethods = contactMethods.map((method, i) => ({
      ...method,
      primary: i === index,
    }));
    setContactMethods(updatedMethods);
  };

  const removeContactMethod = (index: number) => {
    setContactMethods(contactMethods.filter((_, i) => i !== index));
  };

  const getContactIcon = (type: string) => {
    const icons = {
      email: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207"
          />
        </svg>
      ),
      sms: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      ),
      phone: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
          />
        </svg>
      ),
    };
    return icons[type as keyof typeof icons] || icons.email;
  };

  return (
    <Card>
      <div className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">Contact Preferences</h2>

        {/* Contact Methods */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-900">Contact Methods</h3>
            <Button size="sm" variant="outline" onClick={() => setShowAddContact(!showAddContact)}>
              {showAddContact ? 'Cancel' : 'Add Contact'}
            </Button>
          </div>

          {/* Add Contact Form */}
          {showAddContact && (
            <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <select
                  value={newContact.type}
                  onChange={e => setNewContact({ ...newContact, type: e.target.value as any })}
                  className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="email">Email</option>
                  <option value="sms">SMS</option>
                  <option value="phone">Phone</option>
                </select>
                <Input
                  placeholder={
                    newContact.type === 'email' ? 'email@example.com' : '+1 (555) 123-4567'
                  }
                  value={newContact.value}
                  onChange={e => setNewContact({ ...newContact, value: e.target.value })}
                />
                <Button size="sm" onClick={addContactMethod}>
                  Add
                </Button>
              </div>
            </div>
          )}

          {/* Contact Methods List */}
          <div className="space-y-3">
            {contactMethods.map((method, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  <div className="text-gray-500">{getContactIcon(method.type)}</div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-gray-900">{method.value}</span>
                      {method.verified && (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                          Verified
                        </span>
                      )}
                      {method.primary && (
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          Primary
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 capitalize">{method.type}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {!method.primary && (
                    <Button size="sm" variant="outline" onClick={() => setPrimaryContact(index)}>
                      Set Primary
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => removeContactMethod(index)}
                    className="text-red-600 hover:text-red-700"
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Notification Preferences */}
        <div>
          <h3 className="text-sm font-medium text-gray-900 mb-4">Notification Preferences</h3>
          <div className="space-y-4">
            {notifications.map(notif => (
              <div key={notif.category} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-gray-900">{notif.label}</h4>
                    <p className="text-sm text-gray-600 mt-1">{notif.description}</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={notif.email}
                      onChange={e =>
                        updateNotificationPreference(notif.category, 'email', e.target.checked)
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Email</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={notif.sms}
                      onChange={e =>
                        updateNotificationPreference(notif.category, 'sms', e.target.checked)
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">SMS</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={notif.push}
                      onChange={e =>
                        updateNotificationPreference(notif.category, 'push', e.target.checked)
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Push</span>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-6 pt-4 border-t">
          <Button>Save Preferences</Button>
        </div>
      </div>
    </Card>
  );
}
