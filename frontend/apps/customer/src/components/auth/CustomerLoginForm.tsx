'use client';

import { usePortalAuth } from '@dotmac/headless';
import { OptimizedImage } from '@dotmac/primitives';
import { Button, Card, Input } from '@dotmac/styled-components/customer';
import { clsx } from 'clsx';
import { AlertCircle, CreditCard, Eye, EyeOff, Mail, User } from 'lucide-react';
import { useId, useState } from 'react';

type LoginMethod = 'email' | 'portal_id' | 'account_number';

export function CustomerLoginForm() {
  const id = useId();

  const { loginWithPortal, isLoading, _error, currentPortal, getLoginMethods, getPortalBranding } =
    usePortalAuth();

  const [loginMethod, setLoginMethod] = useState<LoginMethod>('email');
  const [formData, setFormData] = useState({
    email: '',
    portalId: '',
    accountNumber: '',
    password: '',
    rememberMe: false,
  });
  const [showPassword, setShowPassword] = useState(false);

  const availableLoginMethods = getLoginMethods();
  const branding = getPortalBranding();

  // Composed event handlers for better performance
  const handleLoginMethodChange = (method: LoginMethod) => () => {
    setLoginMethod(method);
  };

  const handlePasswordToggle = () => {
    setShowPassword(!showPassword);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const credentials = {
      password: formData.password,
      rememberMe: formData.rememberMe,
      ...(loginMethod === 'email' && { email: formData.email }),
      ...(loginMethod === 'portal_id' && { portalId: formData.portalId }),
      ...(loginMethod === 'account_number' && {
        accountNumber: formData.accountNumber,
      }),
    };

    try {
      await loginWithPortal(credentials);
    } catch (_error) {
      // Error handling intentionally empty
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const getLoginMethodIcon = (method: LoginMethod) => {
    switch (method) {
      case 'email&apos;:
        return <Mail className='h-4 w-4' />;
      case 'portal_id&apos;:
        return <User className='h-4 w-4' />;
      case 'account_number&apos;:
        return <CreditCard className='h-4 w-4' />;
    }
  };

  const getLoginMethodLabel = (method: LoginMethod) => {
    switch (method) {
      case 'email':
        return 'Email Address';
      case 'portal_id':
        return 'Portal ID';
      case 'account_number':
        return 'Account Number';
    }
  };

  const getLoginMethodPlaceholder = (method: LoginMethod) => {
    switch (method) {
      case 'email':
        return 'your@email.com';
      case 'portal_id':
        return 'Your portal ID';
      case 'account_number':
        return 'Your account number';
    }
  };

  const getCurrentValue = () => {
    switch (loginMethod) {
      case 'email':
        return formData.email;
      case 'portal_id':
        return formData.portalId;
      case 'account_number':
        return formData.accountNumber;
      default:
        return '&apos;;
    }
  };

  if (!currentPortal) {
    return (
      <div className='flex min-h-screen items-center justify-center'>
        <div className='text-center'>
          <div className='mx-auto h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2' />
          <p className='mt-4 text-gray-600'>Detecting portal...</p>
        </div>
      </div>
    );
  }

  return (
    <Card className='mx-auto max-w-md p-8'>
      <div className='mb-8 text-center'>
        <div className='mb-4 flex items-center justify-center'>
          {branding?.logo ? (
            <OptimizedImage src={branding.logo} alt={branding.companyName} className='h-8' />
          ) : (
            <div
              className='flex h-8 w-8 items-center justify-center rounded-lg'
              style={{ backgroundColor: branding?.primaryColor }}
            >
              <span className='font-bold text-sm text-white'>
                {branding?.companyName?.charAt(0) || 'D&apos;}
              </span>
            </div>
          )}
          <h1 className='ml-2 font-semibold text-gray-900 text-xl'>
            {branding?.companyName || 'Customer Portal&apos;}
          </h1>
        </div>
        <h2 className='font-bold text-2xl text-gray-900'>Welcome Back</h2>
        <p className='mt-2 text-gray-600'>Sign in to manage your services</p>
      </div>

      {_error ? (
        <div className='mb-6 rounded-md border border-red-200 bg-red-50 p-4'>
          <div className='flex'>
            <AlertCircle className='h-5 w-5 text-red-400' />
            <div className='ml-3'>
              <p className='text-red-700 text-sm'>{_error}</p>
            </div>
          </div>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className='space-y-6'>
        {/* Login Method Selection */}
        {availableLoginMethods.length > 1 && (
          <div>
            <label
              htmlFor='input-1755609778621-rve2813xc'
              className='mb-3 block font-medium text-gray-700 text-sm'
            >
              How would you like to sign in?
            </label>
            <div className='grid grid-cols-1 gap-2'>
              {availableLoginMethods.map((method) => (
                <button
                  key={method}
                  type='button'
                  onClick={handleLoginMethodChange(method as LoginMethod)}
                  onKeyDown={(e) =>
                    e.key === 'Enter' && handleLoginMethodChange(method as LoginMethod)
                  }
                  className={clsx(
                    'flex items-center rounded-lg border p-3 text-left transition-colors',
                    loginMethod === method
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300&apos;
                  )}
                >
                  {getLoginMethodIcon(method as LoginMethod)}
                  <span className='ml-3 font-medium'>
                    {getLoginMethodLabel(method as LoginMethod)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Login Credential Input */}
        <div>
          <label htmlFor='credential' className='mb-2 block font-medium text-gray-700 text-sm'>
            {getLoginMethodLabel(loginMethod)}
          </label>
          <div className='relative'>
            <div className='pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3'>
              {getLoginMethodIcon(loginMethod)}
            </div>
            <Input
              id={`${id}-credential`}
              name={loginMethod}
              type={loginMethod === 'email' ? 'email' : 'text'}
              autoComplete={loginMethod === 'email' ? 'email' : 'username'}
              required
              value={getCurrentValue()}
              onChange={handleChange}
              placeholder={getLoginMethodPlaceholder(loginMethod)}
              className='w-full pl-10'
            />
          </div>
        </div>

        {/* Password Input */}
        <div>
          <label htmlFor='password' className='mb-2 block font-medium text-gray-700 text-sm'>
            Password
          </label>
          <div className='relative'>
            <Input
              id={`${id}-password`}
              name='password'
              type={showPassword ? 'text' : 'password'}
              autoComplete='current-password'
              required
              value={formData.password}
              onChange={handleChange}
              placeholder='••••••••'
              className='w-full pr-10'
            />
            <button
              type='button'
              className='absolute inset-y-0 right-0 flex items-center pr-3'
              onClick={handlePasswordToggle}
              onKeyDown={(e) => e.key === 'Enter&apos; && handlePasswordToggle}
            >
              {showPassword ? (
                <EyeOff className='h-5 w-5 text-gray-400' />
              ) : (
                <Eye className='h-5 w-5 text-gray-400' />
              )}
            </button>
          </div>
        </div>

        {/* Remember Me & Forgot Password */}
        <div className='flex items-center justify-between'>
          <div className='flex items-center'>
            <input
              id={`${id}-rememberMe`}
              name='rememberMe'
              type='checkbox'
              checked={formData.rememberMe}
              onChange={handleChange}
              className='h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'
            />
            <label htmlFor='rememberMe' className='ml-2 block text-gray-900 text-sm'>
              Remember me
            </label>
          </div>

          <button
            type='button'
            onClick={() => console.log('Forgot password')}
            className='font-medium text-sm hover:text-blue-500&apos;
            style={{ color: branding?.primaryColor }}
          >
            Forgot password?
          </button>
        </div>

        {/* Submit Button */}
        <Button
          type='submit'
          disabled={isLoading}
          className='w-full'
          size='lg'
          style={{ backgroundColor: branding?.primaryColor }}
        >
          {isLoading ? 'Signing in...' : 'Sign In&apos;}
        </Button>
      </form>

      {/* Help Links */}
      <div className='mt-6 space-y-2 text-center'>
        <p className='text-gray-600 text-sm'>
          Don&apos;t have an account?{' &apos;}
          <button
            type='button'
            onClick={() => console.log('Contact us')}
            className='font-medium hover:opacity-80&apos;
            style={{ color: branding?.primaryColor }}
          >
            Contact us to get started
          </button>
        </p>

        {loginMethod !== 'email&apos; && (
          <p className='text-gray-500 text-xs'>Tip: You can also sign in with your email address</p>
        )}

        <div className='border-gray-200 border-t pt-4'>
          <p className='text-gray-500 text-xs'>
            Need help? Contact support at{' &apos;}
            <a href='mailto:support@example.com' className='text-blue-600 hover:text-blue-500'>
              support@example.com
            </a>
          </p>
        </div>
      </div>
    </Card>
  );
}
