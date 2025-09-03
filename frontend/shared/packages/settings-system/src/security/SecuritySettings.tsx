'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  Calendar,
  Check,
  Clock,
  Download,
  Eye,
  EyeOff,
  Globe,
  Key,
  Lock,
  MapPin,
  Monitor,
  RefreshCw,
  Shield,
  Smartphone,
  Upload,
  X,
} from 'lucide-react';
import { SecuritySettings as SecuritySettingsType, SecurityEvent, TwoFactorMethod } from '../types';

export interface SecuritySettingsProps {
  settings: SecuritySettingsType;
  onUpdate: (settings: Partial<SecuritySettingsType>) => void;
  onSave?: () => Promise<boolean>;
  isLoading?: boolean;
  readonly?: boolean;
  className?: string;
}

export function SecuritySettings({
  settings,
  onUpdate,
  onSave,
  isLoading = false,
  readonly = false,
  className = '',
}: SecuritySettingsProps) {
  const [showChangePassword, setShowChangePassword] = useState(false);
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

    if (password.length >= 8) strength += 1;
    if (password.length >= 12) strength += 1;
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
    const updatedMethods = settings.twoFactor.methods.map((method) =>
      method.id === methodId ? { ...method, isEnabled: !method.isEnabled } : method
    );
    onUpdate({
      twoFactor: {
        ...settings.twoFactor,
        methods: updatedMethods,
      },
    });
  };

  const handleSetPrimaryTwoFactor = (methodId: string) => {
    const updatedMethods = settings.twoFactor.methods.map((method) => ({
      ...method,
      isPrimary: method.id === methodId,
    }));
    onUpdate({
      twoFactor: {
        ...settings.twoFactor,
        methods: updatedMethods,
      },
    });
  };

  const updatePasswordPolicy = (key: keyof SecuritySettingsType['passwordPolicy'], value: any) => {
    onUpdate({
      passwordPolicy: {
        ...settings.passwordPolicy,
        [key]: value,
      },
    });
  };

  const updateSessionSettings = (key: keyof SecuritySettingsType['sessions'], value: any) => {
    onUpdate({
      sessions: {
        ...settings.sessions,
        [key]: value,
      },
    });
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
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      <div className='p-6 space-y-8'>
        <div>
          <h2 className='text-xl font-semibold text-gray-900'>Security Settings</h2>
          <p className='mt-1 text-sm text-gray-500'>
            Manage your account security and privacy settings
          </p>
        </div>

        {/* Password Security */}
        <div>
          <div className='flex items-center justify-between mb-6'>
            <div>
              <h3 className='text-lg font-semibold text-gray-900'>Password Security</h3>
              <p className='mt-1 text-sm text-gray-500'>
                Manage your password and account security settings
              </p>
            </div>
            {!readonly && (
              <button
                onClick={() => setShowChangePassword(!showChangePassword)}
                disabled={isLoading}
                className='rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:opacity-50'
              >
                <Key className='mr-2 h-4 w-4' />
                Change Password
              </button>
            )}
          </div>

          {/* Password Policy */}
          <div className='mb-6 p-4 bg-gray-50 rounded-lg'>
            <h4 className='font-medium text-gray-900 mb-4'>Password Requirements</h4>
            <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>
                  Minimum Length
                </label>
                {readonly ? (
                  <p className='text-gray-900'>{settings.passwordPolicy.minLength} characters</p>
                ) : (
                  <input
                    type='number'
                    min='6'
                    max='128'
                    value={settings.passwordPolicy.minLength}
                    onChange={(e) => updatePasswordPolicy('minLength', parseInt(e.target.value))}
                    disabled={isLoading}
                    className='w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50'
                  />
                )}
              </div>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>
                  Expires After (days)
                </label>
                {readonly ? (
                  <p className='text-gray-900'>{settings.passwordPolicy.expiryDays} days</p>
                ) : (
                  <input
                    type='number'
                    min='30'
                    max='365'
                    value={settings.passwordPolicy.expiryDays}
                    onChange={(e) => updatePasswordPolicy('expiryDays', parseInt(e.target.value))}
                    disabled={isLoading}
                    className='w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50'
                  />
                )}
              </div>
            </div>

            <div className='mt-4 space-y-3'>
              {[
                { key: 'requireUppercase', label: 'Require uppercase letters' },
                { key: 'requireLowercase', label: 'Require lowercase letters' },
                { key: 'requireNumbers', label: 'Require numbers' },
                { key: 'requireSpecialChars', label: 'Require special characters' },
              ].map(({ key, label }) => (
                <div key={key} className='flex items-center justify-between'>
                  <span className='text-sm text-gray-700'>{label}</span>
                  {readonly ? (
                    <span className='text-sm text-gray-900'>
                      {settings.passwordPolicy[key as keyof typeof settings.passwordPolicy]
                        ? 'Yes'
                        : 'No'}
                    </span>
                  ) : (
                    <button
                      onClick={() =>
                        updatePasswordPolicy(
                          key as any,
                          !settings.passwordPolicy[key as keyof typeof settings.passwordPolicy]
                        )
                      }
                      disabled={isLoading}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        settings.passwordPolicy[key as keyof typeof settings.passwordPolicy]
                          ? 'bg-blue-600'
                          : 'bg-gray-200'
                      } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          settings.passwordPolicy[key as keyof typeof settings.passwordPolicy]
                            ? 'translate-x-6'
                            : 'translate-x-1'
                        }`}
                      />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Change Password Form */}
          {showChangePassword && !readonly && (
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
                      type='button'
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
                  <label className='block text-sm font-medium text-gray-700 mb-2'>
                    New Password
                  </label>
                  <div className='relative'>
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={passwordData.new}
                      onChange={(e) => handlePasswordChange('new', e.target.value)}
                      className='w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
                    />
                    <button
                      type='button'
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className='absolute right-3 top-2.5 text-gray-400 hover:text-gray-600'
                    >
                      {showNewPassword ? (
                        <EyeOff className='h-4 w-4' />
                      ) : (
                        <Eye className='h-4 w-4' />
                      )}
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
                      type='button'
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
                  <button
                    type='button'
                    className='rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'
                  >
                    Update Password
                  </button>
                  <button
                    type='button'
                    onClick={() => setShowChangePassword(false)}
                    className='rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50'
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Two-Factor Authentication */}
        <div>
          <div className='mb-6'>
            <h3 className='text-lg font-semibold text-gray-900'>Two-Factor Authentication</h3>
            <p className='mt-1 text-sm text-gray-500'>
              Add an extra layer of security to your account
            </p>
          </div>

          <div className='mb-4'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Require 2FA</h4>
                <p className='text-sm text-gray-500'>Make two-factor authentication mandatory</p>
              </div>
              {readonly ? (
                <span className='text-sm text-gray-900'>
                  {settings.twoFactor.required ? 'Required' : 'Optional'}
                </span>
              ) : (
                <button
                  onClick={() =>
                    onUpdate({
                      twoFactor: {
                        ...settings.twoFactor,
                        required: !settings.twoFactor.required,
                      },
                    })
                  }
                  disabled={isLoading}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.twoFactor.required ? 'bg-blue-600' : 'bg-gray-200'
                  } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      settings.twoFactor.required ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              )}
            </div>
          </div>

          <div className='space-y-4'>
            {settings.twoFactor.methods.map((method) => (
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
                {!readonly && (
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
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Session Management */}
        <div>
          <div className='mb-6'>
            <h3 className='text-lg font-semibold text-gray-900'>Session Settings</h3>
            <p className='mt-1 text-sm text-gray-500'>Control how sessions are managed</p>
          </div>

          <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>
                Maximum Concurrent Sessions
              </label>
              {readonly ? (
                <p className='text-gray-900'>{settings.sessions.maxConcurrent}</p>
              ) : (
                <input
                  type='number'
                  min='1'
                  max='10'
                  value={settings.sessions.maxConcurrent}
                  onChange={(e) => updateSessionSettings('maxConcurrent', parseInt(e.target.value))}
                  disabled={isLoading}
                  className='w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50'
                />
              )}
            </div>
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-2'>
                Session Timeout (minutes)
              </label>
              {readonly ? (
                <p className='text-gray-900'>{settings.sessions.timeoutMinutes} minutes</p>
              ) : (
                <input
                  type='number'
                  min='15'
                  max='1440'
                  value={settings.sessions.timeoutMinutes}
                  onChange={(e) =>
                    updateSessionSettings('timeoutMinutes', parseInt(e.target.value))
                  }
                  disabled={isLoading}
                  className='w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50'
                />
              )}
            </div>
          </div>
        </div>

        {/* Security Activity */}
        <div>
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
            {settings.activityLog.slice(0, 5).map((event) => (
              <div
                key={event.id}
                className='flex items-start space-x-4 p-3 rounded-lg hover:bg-gray-50'
              >
                <div className='flex-shrink-0 mt-0.5'>
                  {getEventIcon(event.type, event.success)}
                </div>
                <div className='flex-grow min-w-0'>
                  <div className='flex items-center justify-between'>
                    <p className='font-medium text-gray-900 text-sm'>{event.description}</p>
                    <span className='text-xs text-gray-500'>
                      {formatTimestamp(event.timestamp)}
                    </span>
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
                'Save Security Settings'
              )}
            </button>
          </div>
        )}

        {/* Security Recommendations */}
        <div className='p-4 bg-yellow-50 border border-yellow-200 rounded-lg'>
          <div className='flex items-start'>
            <AlertTriangle className='h-6 w-6 text-yellow-600 mt-1 flex-shrink-0' />
            <div className='ml-4'>
              <h3 className='font-medium text-yellow-900'>Security Recommendations</h3>
              <div className='mt-2 space-y-1 text-sm text-yellow-800'>
                <p>• Use strong, unique passwords for all accounts</p>
                <p>• Enable two-factor authentication on all methods</p>
                <p>• Regularly review your security activity</p>
                <p>• Keep your recovery methods up to date</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
