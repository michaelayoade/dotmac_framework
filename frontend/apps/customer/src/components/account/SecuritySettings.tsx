'use client';

import { useState } from 'react';
import { Card } from '@dotmac/styled-components/customer';
import {
  Shield,
  Key,
  Smartphone,
  Lock,
  Eye,
  EyeOff,
  Check,
  X,
  AlertTriangle,
  RefreshCw,
  Download,
  Upload,
  Calendar,
  MapPin,
  Monitor,
  Clock,
} from 'lucide-react';

interface SecurityEvent {
  id: string;
  type: 'login' | 'password_change' | 'device_added' | 'suspicious_activity';
  description: string;
  timestamp: string;
  location: string;
  device: string;
  ipAddress: string;
  success: boolean;
}

interface TwoFactorMethod {
  id: string;
  type: 'sms' | 'authenticator' | 'email';
  label: string;
  identifier: string;
  isEnabled: boolean;
  isPrimary: boolean;
  addedDate: string;
}

const mockSecurityEvents: SecurityEvent[] = [
  {
    id: '1',
    type: 'login',
    description: 'Successful login to customer portal',
    timestamp: '2024-01-29T14:30:00Z',
    location: 'San Francisco, CA',
    device: 'Chrome on MacOS',
    ipAddress: '192.168.1.100',
    success: true,
  },
  {
    id: '2',
    type: 'device_added',
    description: 'New device authorized',
    timestamp: '2024-01-28T10:15:00Z',
    location: 'San Francisco, CA',
    device: 'Safari on iPhone',
    ipAddress: '192.168.1.101',
    success: true,
  },
  {
    id: '3',
    type: 'password_change',
    description: 'Password successfully changed',
    timestamp: '2024-01-25T16:45:00Z',
    location: 'San Francisco, CA',
    device: 'Chrome on MacOS',
    ipAddress: '192.168.1.100',
    success: true,
  },
  {
    id: '4',
    type: 'login',
    description: 'Failed login attempt',
    timestamp: '2024-01-24T09:20:00Z',
    location: 'Unknown',
    device: 'Chrome on Windows',
    ipAddress: '203.0.113.1',
    success: false,
  },
];

const mockTwoFactorMethods: TwoFactorMethod[] = [
  {
    id: '1',
    type: 'authenticator',
    label: 'Authenticator App',
    identifier: 'Google Authenticator',
    isEnabled: true,
    isPrimary: true,
    addedDate: '2024-01-15T10:30:00Z',
  },
  {
    id: '2',
    type: 'sms',
    label: 'SMS Text Message',
    identifier: '+1 (555) ***-4567',
    isEnabled: true,
    isPrimary: false,
    addedDate: '2024-01-10T14:20:00Z',
  },
  {
    id: '3',
    type: 'email',
    label: 'Email Verification',
    identifier: 'john.doe@email.com',
    isEnabled: false,
    isPrimary: false,
    addedDate: '2024-01-01T12:00:00Z',
  },
];

export function SecuritySettings() {
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [twoFactorMethods, setTwoFactorMethods] = useState(mockTwoFactorMethods);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current: '',
    new: '',
    confirm: '',
  });
  const [passwordStrength, setPasswordStrength] = useState(0);

  const calculatePasswordStrength = (password: string) => {
    let strength = 0;

    // Length check
    if (password.length >= 8) strength += 1;
    if (password.length >= 12) strength += 1;

    // Character checks
    if (/[A-Z]/.test(password)) strength += 1;
    if (/[a-z]/.test(password)) strength += 1;
    if (/[0-9]/.test(password)) strength += 1;
    if (/[^A-Za-z0-9]/.test(password)) strength += 1;

    return Math.min(strength, 5);
  };

  const handlePasswordChange = (field: string, value: string) => {
    setPasswordData((prev) => ({ ...prev, [field]: value }));

    if (field === 'new') {
      setPasswordStrength(calculatePasswordStrength(value));
    }
  };

  const handleToggleTwoFactor = (methodId: string) => {
    setTwoFactorMethods((prev) =>
      prev.map((method) =>
        method.id === methodId ? { ...method, isEnabled: !method.isEnabled } : method
      )
    );
  };

  const handleSetPrimaryTwoFactor = (methodId: string) => {
    setTwoFactorMethods((prev) =>
      prev.map((method) => ({
        ...method,
        isPrimary: method.id === methodId,
      }))
    );
  };

  const getPasswordStrengthLabel = (strength: number) => {
    switch (strength) {
      case 0:
      case 1:
        return 'Weak';
      case 2:
      case 3:
        return 'Fair';
      case 4:
        return 'Good';
      case 5:
        return 'Strong';
      default:
        return 'Weak';
    }
  };

  const getPasswordStrengthColor = (strength: number) => {
    switch (strength) {
      case 0:
      case 1:
        return 'bg-red-500';
      case 2:
      case 3:
        return 'bg-yellow-500';
      case 4:
        return 'bg-blue-500';
      case 5:
        return 'bg-green-500';
      default:
        return 'bg-gray-300';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const getEventIcon = (type: string, success: boolean) => {
    const iconClass = success ? 'text-green-600' : 'text-red-600';

    switch (type) {
      case 'login':
        return <Shield className={`h-4 w-4 ${iconClass}`} />;
      case 'password_change':
        return <Key className={`h-4 w-4 ${iconClass}`} />;
      case 'device_added':
        return <Smartphone className={`h-4 w-4 ${iconClass}`} />;
      case 'suspicious_activity':
        return <AlertTriangle className={`h-4 w-4 ${iconClass}`} />;
      default:
        return <Shield className={`h-4 w-4 ${iconClass}`} />;
    }
  };

  const getTwoFactorIcon = (type: string) => {
    switch (type) {
      case 'authenticator':
        return <Smartphone className='h-5 w-5 text-blue-600' />;
      case 'sms':
        return <Smartphone className='h-5 w-5 text-green-600' />;
      case 'email':
        return <Shield className='h-5 w-5 text-purple-600' />;
      default:
        return <Shield className='h-5 w-5 text-gray-600' />;
    }
  };

  return (
    <div className='space-y-6'>
      {/* Password Security */}
      <Card className='p-6'>
        <div className='flex items-center justify-between mb-6'>
          <div>
            <h3 className='text-lg font-semibold text-gray-900'>Password Security</h3>
            <p className='mt-1 text-sm text-gray-500'>
              Manage your password and account security settings
            </p>
          </div>
          <button
            onClick={() => setShowChangePassword(!showChangePassword)}
            className='rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'
          >
            <Key className='mr-2 h-4 w-4' />
            Change Password
          </button>
        </div>

        {/* Password Strength Indicator */}
        <div className='mb-6 p-4 bg-gray-50 rounded-lg'>
          <div className='flex items-center justify-between mb-2'>
            <span className='text-sm font-medium text-gray-700'>Password Strength</span>
            <span className='text-sm text-green-600 font-medium'>Strong</span>
          </div>
          <div className='h-2 bg-gray-200 rounded-full'>
            <div className='h-2 bg-green-500 rounded-full' style={{ width: '100%' }} />
          </div>
          <p className='mt-2 text-xs text-gray-600'>Last changed 5 days ago • Expires in 85 days</p>
        </div>

        {/* Change Password Form */}
        {showChangePassword && (
          <div className='border-t pt-6'>
            <div className='space-y-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>
                  Current Password
                </label>
                <div className='relative'>
                  <input
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={passwordData.current}
                    onChange={(e) => handlePasswordChange('current', e.target.value)}
                    className='w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  />
                  <button
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className='absolute right-3 top-2.5 text-gray-400 hover:text-gray-600'
                  >
                    {showCurrentPassword ? (
                      <EyeOff className='h-4 w-4' />
                    ) : (
                      <Eye className='h-4 w-4' />
                    )}
                  </button>
                </div>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>New Password</label>
                <div className='relative'>
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={passwordData.new}
                    onChange={(e) => handlePasswordChange('new', e.target.value)}
                    className='w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  />
                  <button
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className='absolute right-3 top-2.5 text-gray-400 hover:text-gray-600'
                  >
                    {showNewPassword ? <EyeOff className='h-4 w-4' /> : <Eye className='h-4 w-4' />}
                  </button>
                </div>
                {passwordData.new && (
                  <div className='mt-2'>
                    <div className='flex items-center justify-between mb-1'>
                      <span className='text-xs text-gray-600'>Password strength</span>
                      <span className='text-xs font-medium'>
                        {getPasswordStrengthLabel(passwordStrength)}
                      </span>
                    </div>
                    <div className='h-1 bg-gray-200 rounded-full'>
                      <div
                        className={`h-1 rounded-full transition-all duration-300 ${getPasswordStrengthColor(passwordStrength)}`}
                        style={{ width: `${(passwordStrength / 5) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>
                  Confirm New Password
                </label>
                <div className='relative'>
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={passwordData.confirm}
                    onChange={(e) => handlePasswordChange('confirm', e.target.value)}
                    className='w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                  />
                  <button
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className='absolute right-3 top-2.5 text-gray-400 hover:text-gray-600'
                  >
                    {showConfirmPassword ? (
                      <EyeOff className='h-4 w-4' />
                    ) : (
                      <Eye className='h-4 w-4' />
                    )}
                  </button>
                </div>
                {passwordData.confirm && passwordData.new !== passwordData.confirm && (
                  <p className='mt-1 text-sm text-red-600'>Passwords do not match</p>
                )}
              </div>

              <div className='flex space-x-3 pt-4'>
                <button className='rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'>
                  Update Password
                </button>
                <button
                  onClick={() => setShowChangePassword(false)}
                  className='rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50'
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Two-Factor Authentication */}
      <Card className='p-6'>
        <div className='mb-6'>
          <h3 className='text-lg font-semibold text-gray-900'>Two-Factor Authentication</h3>
          <p className='mt-1 text-sm text-gray-500'>
            Add an extra layer of security to your account
          </p>
        </div>

        <div className='space-y-4'>
          {twoFactorMethods.map((method) => (
            <div
              key={method.id}
              className='flex items-center justify-between p-4 border rounded-lg'
            >
              <div className='flex items-center space-x-4'>
                {getTwoFactorIcon(method.type)}
                <div>
                  <h4 className='font-medium text-gray-900'>{method.label}</h4>
                  <p className='text-sm text-gray-600'>{method.identifier}</p>
                  {method.isPrimary && (
                    <span className='inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 mt-1'>
                      Primary
                    </span>
                  )}
                </div>
              </div>
              <div className='flex items-center space-x-2'>
                {method.isEnabled && !method.isPrimary && (
                  <button
                    onClick={() => handleSetPrimaryTwoFactor(method.id)}
                    className='text-sm text-blue-600 hover:text-blue-800'
                  >
                    Make Primary
                  </button>
                )}
                <button
                  onClick={() => handleToggleTwoFactor(method.id)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    method.isEnabled ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      method.isEnabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
          <div className='flex items-start'>
            <Shield className='h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0' />
            <div className='ml-3'>
              <h4 className='font-medium text-blue-900'>Security Recommendation</h4>
              <p className='mt-1 text-sm text-blue-700'>
                Enable at least two different 2FA methods for maximum security. We recommend using
                an authenticator app as your primary method.
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Session Management */}
      <Card className='p-6'>
        <div className='flex items-center justify-between mb-6'>
          <div>
            <h3 className='text-lg font-semibold text-gray-900'>Active Sessions</h3>
            <p className='mt-1 text-sm text-gray-500'>
              Monitor and manage devices with access to your account
            </p>
          </div>
          <button className='rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50'>
            <RefreshCw className='mr-2 h-4 w-4' />
            Refresh
          </button>
        </div>

        <div className='space-y-4'>
          <div className='flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg'>
            <div className='flex items-center space-x-4'>
              <Monitor className='h-5 w-5 text-green-600' />
              <div>
                <h4 className='font-medium text-green-900'>Current Session</h4>
                <p className='text-sm text-green-700'>Chrome on MacOS • San Francisco, CA</p>
                <p className='text-xs text-green-600'>192.168.1.100 • Active now</p>
              </div>
            </div>
            <span className='inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800'>
              Current
            </span>
          </div>

          <div className='flex items-center justify-between p-4 border rounded-lg'>
            <div className='flex items-center space-x-4'>
              <Smartphone className='h-5 w-5 text-gray-600' />
              <div>
                <h4 className='font-medium text-gray-900'>Safari on iPhone</h4>
                <p className='text-sm text-gray-600'>San Francisco, CA</p>
                <p className='text-xs text-gray-500'>192.168.1.101 • Last active 2 hours ago</p>
              </div>
            </div>
            <button className='text-sm text-red-600 hover:text-red-800'>Sign Out</button>
          </div>
        </div>

        <div className='mt-6'>
          <button className='text-sm text-red-600 hover:text-red-800 font-medium'>
            Sign out all other sessions
          </button>
        </div>
      </Card>

      {/* Security Activity */}
      <Card className='p-6'>
        <div className='flex items-center justify-between mb-6'>
          <div>
            <h3 className='text-lg font-semibold text-gray-900'>Recent Security Activity</h3>
            <p className='mt-1 text-sm text-gray-500'>
              Monitor recent security events on your account
            </p>
          </div>
          <div className='flex items-center space-x-2'>
            <button className='rounded-lg border border-gray-300 px-3 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50'>
              <Download className='mr-1 h-3 w-3' />
              Export
            </button>
            <button className='text-sm text-blue-600 hover:text-blue-800'>View All</button>
          </div>
        </div>

        <div className='space-y-3'>
          {mockSecurityEvents.map((event) => (
            <div
              key={event.id}
              className='flex items-start space-x-4 p-3 rounded-lg hover:bg-gray-50'
            >
              <div className='flex-shrink-0 mt-0.5'>{getEventIcon(event.type, event.success)}</div>
              <div className='flex-grow min-w-0'>
                <div className='flex items-center justify-between'>
                  <p className='font-medium text-gray-900 text-sm'>{event.description}</p>
                  <span className='text-xs text-gray-500'>{formatTimestamp(event.timestamp)}</span>
                </div>
                <div className='mt-1 flex items-center space-x-4 text-xs text-gray-600'>
                  <div className='flex items-center'>
                    <MapPin className='mr-1 h-3 w-3' />
                    {event.location}
                  </div>
                  <div className='flex items-center'>
                    <Monitor className='mr-1 h-3 w-3' />
                    {event.device}
                  </div>
                  <div className='flex items-center'>
                    <Globe className='mr-1 h-3 w-3' />
                    {event.ipAddress}
                  </div>
                </div>
              </div>
              {!event.success && <AlertTriangle className='h-4 w-4 text-red-600 flex-shrink-0' />}
            </div>
          ))}
        </div>
      </Card>

      {/* Security Recommendations */}
      <Card className='p-6 border-yellow-200 bg-yellow-50'>
        <div className='flex items-start'>
          <AlertTriangle className='h-6 w-6 text-yellow-600 mt-1 flex-shrink-0' />
          <div className='ml-4'>
            <h3 className='font-medium text-yellow-900'>Security Recommendations</h3>
            <div className='mt-2 space-y-1 text-sm text-yellow-800'>
              <p>• Consider using a hardware security key for maximum protection</p>
              <p>• Review and remove unused devices from your active sessions</p>
              <p>• Enable email notifications for all security events</p>
              <p>• Update your password every 90 days</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
