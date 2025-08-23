'use client';

import { useState } from 'react';
import { Card } from '@dotmac/styled-components/customer';
import { 
  User, 
  Mail, 
  Phone, 
  MapPin, 
  Shield, 
  Bell, 
  CreditCard, 
  Key,
  Settings,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Download
} from 'lucide-react';

interface PersonalInfo {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  ssn: string; // Masked
}

interface Address {
  type: 'service' | 'billing';
  street: string;
  city: string;
  state: string;
  zipCode: string;
  instructions?: string;
}

interface SecuritySettings {
  twoFactorEnabled: boolean;
  passwordLastChanged: string;
  securityQuestions: boolean;
  deviceTrust: boolean;
}

interface NotificationPreferences {
  billingReminders: boolean;
  serviceAlerts: boolean;
  promotionalEmails: boolean;
  smsNotifications: boolean;
  maintenanceUpdates: boolean;
}

interface Document {
  id: string;
  name: string;
  type: string;
  date: string;
  size: string;
}

export default function AccountPage() {
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'notifications' | 'documents'>('profile');
  const [isEditing, setIsEditing] = useState(false);

  // Mock data
  const [personalInfo, setPersonalInfo] = useState<PersonalInfo>({
    firstName: 'John',
    lastName: 'Doe',
    email: 'john.doe@email.com',
    phone: '+1 (555) 123-4567',
    dateOfBirth: '1985-06-15',
    ssn: '***-**-1234'
  });

  const [addresses, setAddresses] = useState<Address[]>([
    {
      type: 'service',
      street: '123 Main Street',
      city: 'Anytown',
      state: 'ST',
      zipCode: '12345',
      instructions: 'Apartment 2B, use side entrance'
    },
    {
      type: 'billing',
      street: '123 Main Street',
      city: 'Anytown', 
      state: 'ST',
      zipCode: '12345'
    }
  ]);

  const [securitySettings, setSecuritySettings] = useState<SecuritySettings>({
    twoFactorEnabled: true,
    passwordLastChanged: '2024-01-15',
    securityQuestions: true,
    deviceTrust: false
  });

  const [notifications, setNotifications] = useState<NotificationPreferences>({
    billingReminders: true,
    serviceAlerts: true,
    promotionalEmails: false,
    smsNotifications: true,
    maintenanceUpdates: true
  });

  const documents: Document[] = [
    {
      id: 'DOC-001',
      name: 'Service Agreement',
      type: 'Contract',
      date: '2024-01-15',
      size: '2.1 MB'
    },
    {
      id: 'DOC-002', 
      name: 'Installation Receipt',
      type: 'Receipt',
      date: '2024-01-15',
      size: '345 KB'
    },
    {
      id: 'DOC-003',
      name: 'Privacy Policy',
      type: 'Legal',
      date: '2024-01-01',
      size: '1.8 MB'
    }
  ];

  const handleSaveProfile = () => {
    // API call would go here
    setIsEditing(false);
    // Show success toast
  };

  const handleSecurityChange = (setting: keyof SecuritySettings) => {
    setSecuritySettings(prev => ({
      ...prev,
      [setting]: !prev[setting]
    }));
  };

  const handleNotificationChange = (setting: keyof NotificationPreferences) => {
    setNotifications(prev => ({
      ...prev,
      [setting]: !prev[setting]
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Account Settings</h1>
        <p className="text-gray-600">Manage your account information and preferences</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'profile', label: 'Profile', icon: User },
            { id: 'security', label: 'Security', icon: Shield },
            { id: 'notifications', label: 'Notifications', icon: Bell },
            { id: 'documents', label: 'Documents', icon: FileText }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center border-b-2 px-1 py-4 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                <Icon className="mr-2 h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          {/* Personal Information */}
          <Card className="p-6">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Personal Information</h3>
              {!isEditing ? (
                <button
                  onClick={() => setIsEditing(true)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Edit Profile
                </button>
              ) : (
                <div className="space-x-2">
                  <button
                    onClick={() => setIsEditing(false)}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveProfile}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
                  >
                    Save Changes
                  </button>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700">First Name</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={personalInfo.firstName}
                    onChange={(e) => setPersonalInfo(prev => ({ ...prev, firstName: e.target.value }))}
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                ) : (
                  <p className="mt-1 text-gray-900">{personalInfo.firstName}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Last Name</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={personalInfo.lastName}
                    onChange={(e) => setPersonalInfo(prev => ({ ...prev, lastName: e.target.value }))}
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                ) : (
                  <p className="mt-1 text-gray-900">{personalInfo.lastName}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Email Address</label>
                {isEditing ? (
                  <input
                    type="email"
                    value={personalInfo.email}
                    onChange={(e) => setPersonalInfo(prev => ({ ...prev, email: e.target.value }))}
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                ) : (
                  <p className="mt-1 text-gray-900">{personalInfo.email}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Phone Number</label>
                {isEditing ? (
                  <input
                    type="tel"
                    value={personalInfo.phone}
                    onChange={(e) => setPersonalInfo(prev => ({ ...prev, phone: e.target.value }))}
                    className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                ) : (
                  <p className="mt-1 text-gray-900">{personalInfo.phone}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Date of Birth</label>
                <p className="mt-1 text-gray-900">{new Date(personalInfo.dateOfBirth).toLocaleDateString()}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Social Security Number</label>
                <p className="mt-1 text-gray-900">{personalInfo.ssn}</p>
              </div>
            </div>
          </Card>

          {/* Addresses */}
          <Card className="p-6">
            <h3 className="mb-6 text-lg font-semibold text-gray-900">Addresses</h3>
            <div className="space-y-6">
              {addresses.map((address, index) => (
                <div key={`${address.type}-${index}`} className="rounded-lg border p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <h4 className="font-medium text-gray-900 capitalize">
                      {address.type} Address
                    </h4>
                    <button className="text-blue-600 text-sm hover:text-blue-700">
                      Edit
                    </button>
                  </div>
                  <div className="text-gray-600 text-sm">
                    <p>{address.street}</p>
                    <p>{address.city}, {address.state} {address.zipCode}</p>
                    {address.instructions && (
                      <p className="mt-2 italic">Instructions: {address.instructions}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'security' && (
        <div className="space-y-6">
          {/* Security Overview */}
          <Card className="p-6">
            <h3 className="mb-6 text-lg font-semibold text-gray-900">Security Settings</h3>
            
            <div className="space-y-6">
              {/* Password */}
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center">
                  <Key className="mr-3 h-5 w-5 text-gray-400" />
                  <div>
                    <h4 className="font-medium text-gray-900">Password</h4>
                    <p className="text-gray-600 text-sm">
                      Last changed: {new Date(securitySettings.passwordLastChanged).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                  Change Password
                </button>
              </div>

              {/* Two-Factor Authentication */}
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center">
                  <Shield className="mr-3 h-5 w-5 text-gray-400" />
                  <div>
                    <h4 className="font-medium text-gray-900">Two-Factor Authentication</h4>
                    <p className="text-gray-600 text-sm">
                      {securitySettings.twoFactorEnabled ? 'Enabled' : 'Disabled'}
                    </p>
                  </div>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={securitySettings.twoFactorEnabled}
                    onChange={() => handleSecurityChange('twoFactorEnabled')}
                    className="peer sr-only"
                  />
                  <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300"></div>
                </label>
              </div>

              {/* Security Questions */}
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center">
                  <AlertTriangle className="mr-3 h-5 w-5 text-gray-400" />
                  <div>
                    <h4 className="font-medium text-gray-900">Security Questions</h4>
                    <p className="text-gray-600 text-sm">
                      {securitySettings.securityQuestions ? 'Configured' : 'Not configured'}
                    </p>
                  </div>
                </div>
                <button className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                  {securitySettings.securityQuestions ? 'Update' : 'Setup'}
                </button>
              </div>

              {/* Trusted Devices */}
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center">
                  <Settings className="mr-3 h-5 w-5 text-gray-400" />
                  <div>
                    <h4 className="font-medium text-gray-900">Trusted Devices</h4>
                    <p className="text-gray-600 text-sm">
                      {securitySettings.deviceTrust ? 'Enabled' : 'Disabled'}
                    </p>
                  </div>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={securitySettings.deviceTrust}
                    onChange={() => handleSecurityChange('deviceTrust')}
                    className="peer sr-only"
                  />
                  <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300"></div>
                </label>
              </div>
            </div>
          </Card>

          {/* Account Activity */}
          <Card className="p-6">
            <h3 className="mb-6 text-lg font-semibold text-gray-900">Recent Activity</h3>
            <div className="space-y-3">
              {[
                { action: 'Login from Chrome on Windows', time: '2 hours ago', status: 'success' },
                { action: 'Password changed', time: '3 days ago', status: 'success' },
                { action: 'Failed login attempt', time: '1 week ago', status: 'warning' }
              ].map((activity, index) => (
                <div key={index} className="flex items-center justify-between rounded-lg border p-3">
                  <div className="flex items-center">
                    {activity.status === 'success' ? (
                      <CheckCircle className="mr-3 h-4 w-4 text-green-600" />
                    ) : (
                      <AlertTriangle className="mr-3 h-4 w-4 text-yellow-600" />
                    )}
                    <span className="text-gray-900 text-sm">{activity.action}</span>
                  </div>
                  <span className="text-gray-500 text-sm">{activity.time}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'notifications' && (
        <Card className="p-6">
          <h3 className="mb-6 text-lg font-semibold text-gray-900">Notification Preferences</h3>
          
          <div className="space-y-6">
            {[
              { key: 'billingReminders', label: 'Billing Reminders', description: 'Get notified before bills are due' },
              { key: 'serviceAlerts', label: 'Service Alerts', description: 'Critical service updates and outages' },
              { key: 'maintenanceUpdates', label: 'Maintenance Updates', description: 'Scheduled maintenance notifications' },
              { key: 'smsNotifications', label: 'SMS Notifications', description: 'Receive alerts via text message' },
              { key: 'promotionalEmails', label: 'Promotional Emails', description: 'Special offers and new services' }
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">{item.label}</h4>
                  <p className="text-gray-600 text-sm">{item.description}</p>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={notifications[item.key as keyof NotificationPreferences]}
                    onChange={() => handleNotificationChange(item.key as keyof NotificationPreferences)}
                    className="peer sr-only"
                  />
                  <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300"></div>
                </label>
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'documents' && (
        <Card className="p-6">
          <h3 className="mb-6 text-lg font-semibold text-gray-900">Account Documents</h3>
          
          <div className="space-y-4">
            {documents.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center">
                  <FileText className="mr-3 h-5 w-5 text-gray-400" />
                  <div>
                    <h4 className="font-medium text-gray-900">{doc.name}</h4>
                    <p className="text-gray-600 text-sm">
                      {doc.type} • {new Date(doc.date).toLocaleDateString()} • {doc.size}
                    </p>
                  </div>
                </div>
                <button className="flex items-center rounded-lg border border-gray-300 px-3 py-2 text-gray-700 text-sm hover:bg-gray-50">
                  <Download className="mr-1 h-4 w-4" />
                  Download
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}