'use client';

import { usePortalIdAuth } from '@dotmac/headless';
import { AlertTriangle, Eye, EyeOff, Shield } from 'lucide-react';
import { useState } from 'react';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Input } from '../ui/Input';

interface PortalIdLoginProps {
  onLogin: (customer: any) => void;
}

export function PortalIdLogin({ onLogin }: PortalIdLoginProps) {
  const {
    login,
    isLoading,
    error,
    requiresMfa,
    requiresPasswordChange,
    validatePortalId,
    customerData,
  } = usePortalIdAuth();

  const [credentials, setCredentials] = useState({
    portal_id: '',
    password: '',
    mfa_code: '',
    remember_device: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationErrors([]);

    // Validate Portal ID format before submission
    const validation = validatePortalId(credentials.portal_id);
    if (!validation.is_valid) {
      setValidationErrors(validation.errors);
      return;
    }

    // Attempt login with validated credentials
    const success = await login({
      portal_id: validation.formatted,
      password: credentials.password,
      mfa_code: credentials.mfa_code || undefined,
      remember_device: credentials.remember_device,
    });

    if (success && customerData) {
      onLogin(customerData);
    }
  };

  const formatPortalId = (value: string) => {
    // Auto-format Portal ID using validation helper
    const validation = validatePortalId(value);
    return validation.formatted;
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-center flex items-center justify-center">
          <Shield className="w-5 h-5 mr-2" />
          Portal ID Login
        </CardTitle>
        <p className="text-sm text-gray-600 text-center">Access your ISP customer portal</p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="portal_id" className="block text-sm font-medium text-gray-700 mb-1">
              Portal ID
            </label>
            <Input
              id="portal_id"
              type="text"
              value={credentials.portal_id}
              onChange={e =>
                setCredentials(prev => ({
                  ...prev,
                  portal_id: formatPortalId(e.target.value),
                }))
              }
              required
              placeholder="Enter your 8-character Portal ID"
              disabled={isLoading}
              maxLength={8}
              className="font-mono tracking-wide text-center text-lg uppercase"
            />
            <p className="text-xs text-gray-500 mt-1">
              Your Portal ID is 8 characters (letters A-Z, numbers 2-9)
            </p>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={credentials.password}
                onChange={e => setCredentials(prev => ({ ...prev, password: e.target.value }))}
                required
                placeholder="Enter your password"
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {requiresMfa && (
            <div>
              <label htmlFor="mfa_code" className="block text-sm font-medium text-gray-700 mb-1">
                Two-Factor Authentication Code
              </label>
              <Input
                id="mfa_code"
                type="text"
                value={credentials.mfa_code}
                onChange={e =>
                  setCredentials(prev => ({
                    ...prev,
                    mfa_code: e.target.value.replace(/\D/g, '').slice(0, 6),
                  }))
                }
                placeholder="Enter 6-digit code"
                disabled={isLoading}
                maxLength={6}
                className="text-center font-mono text-lg tracking-wider"
              />
            </div>
          )}

          <div className="flex items-center">
            <input
              id="remember_device"
              type="checkbox"
              checked={credentials.remember_device}
              onChange={e =>
                setCredentials(prev => ({
                  ...prev,
                  remember_device: e.target.checked,
                }))
              }
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="remember_device" className="ml-2 block text-sm text-gray-700">
              Remember this device for 30 days
            </label>
          </div>

          {validationErrors.length > 0 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <div>
                {validationErrors.map((err, index) => (
                  <div key={index}>{err}</div>
                ))}
              </div>
            </Alert>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <div>
                <div className="font-medium">{error.message}</div>
                {error.code === 'ACCOUNT_LOCKED' && error.locked_until && (
                  <div className="text-sm mt-1">
                    Account locked until {new Date(error.locked_until).toLocaleString()}
                  </div>
                )}
                {error.requires_2fa && (
                  <div className="text-sm mt-1">
                    Please enter your authentication code to continue
                  </div>
                )}
              </div>
            </Alert>
          )}

          {requiresPasswordChange && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <div>
                <div className="font-medium">Password Change Required</div>
                <div className="text-sm mt-1">
                  Your password has expired and must be changed before you can continue.
                </div>
              </div>
            </Alert>
          )}

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Signing in...' : 'Sign In to My Portal'}
          </Button>
        </form>

        <div className="mt-6 space-y-4">
          <div className="p-3 bg-green-50 rounded-md">
            <p className="text-xs text-green-600">
              <strong>Demo Login:</strong> Portal ID: ABC123XY, Password: password
            </p>
          </div>

          <div className="text-center space-y-2">
            <button className="text-sm text-blue-600 hover:underline block w-full">
              Forgot your Portal ID?
            </button>
            <button className="text-sm text-blue-600 hover:underline block w-full">
              Reset Password
            </button>
            <button className="text-sm text-blue-600 hover:underline block w-full">
              Contact Support
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
