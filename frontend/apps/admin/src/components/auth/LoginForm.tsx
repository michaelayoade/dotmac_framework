'use client';

import { Button, Input } from '@dotmac/styled-components/admin';
import { AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useId, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '../../stores/authStore';
import { useValidatedForm } from '../../hooks/useValidatedForm';
import { LoginSchema } from '../../lib/schemas';
import { useAuthErrorTracking } from '../../hooks/useErrorTracking';

export function LoginForm() {
  const id = useId();
  const router = useRouter();
  const { login, isLoading, error, clearError } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const { trackLoginAttempt } = useAuthErrorTracking();

  const {
    data: formData,
    errors,
    isSubmitting,
    getFieldProps,
    handleSubmit,
  } = useValidatedForm({
    initialData: {
      email: '',
      password: '',
      portal: 'admin' as const,
      rememberMe: false,
    },
    schema: LoginSchema,
    onSubmit: async (data) => {
      clearError();
      
      try {
        const result = await login({ email: data.email, password: data.password });
        
        if (result.success) {
          trackLoginAttempt(true, undefined, { 
            email: data.email,
            userId: result.user?.id,
            method: 'password'
          });
          
          // Redirect to dashboard or intended page
          const redirect = new URLSearchParams(window.location.search).get('redirect');
          router.push(redirect || '/dashboard');
        } else {
          const error = new Error(result.error || 'Login failed');
          trackLoginAttempt(false, error, { 
            email: data.email,
            method: 'password'
          });
        }
      } catch (error) {
        trackLoginAttempt(false, error as Error, { 
          email: data.email,
          method: 'password'
        });
      }
    },
    validateOnChange: false, // Don't validate while typing for login
  });

  const handleForgotPassword = () => {
    // Handled by Link component below
  };

  const handleContactAdmin = () => {
    const subject = encodeURIComponent('Account Access Request - ISP Management Platform');
    const body = encodeURIComponent(
      'Hello,\n\n' +
        'I need access to the ISP Management Platform.\n\n' +
        'Company/ISP: \n' +
        'Contact Person: \n' +
        'Email: \n' +
        'Phone: \n' +
        'Role Requested: \n\n' +
        'Please provide me with login credentials or additional information on how to access the platform.\n\n' +
        'Thank you'
    );

    // Use environment variable for support email or fallback to a secure default
    const supportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL || 'support@yourcompany.com';
    window.open(`mailto:${supportEmail}?subject=${subject}&body=${body}`, '_blank');
  };

  const _handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  return (
    <form onSubmit={handleSubmit} className='space-y-6'>
      {(error || errors.form) && (
        <div className='rounded-md border border-red-200 bg-red-50 p-4'>
          <div className='flex'>
            <AlertCircle className='h-5 w-5 text-red-400' suppressHydrationWarning />
            <div className='ml-3'>
              <h3 className='font-medium text-red-800 text-sm'>Authentication Failed</h3>
              <p className='mt-2 text-red-700 text-sm'>{error || errors.form?.join(', ')}</p>
            </div>
          </div>
        </div>
      )}

      <div>
        <label htmlFor='email' className='block font-medium text-gray-700 text-sm'>
          Email Address
        </label>
        <div className='mt-1'>
          <Input
            {...getFieldProps('email')}
            id={`${id}-email`}
            type='email'
            autoComplete='email'
            required
            placeholder='admin@yourcompany.com'
            className='w-full'
          />
          {errors.email && (
            <p className='mt-1 text-sm text-red-600' id='email-error'>
              {errors.email.join(', ')}
            </p>
          )}
        </div>
      </div>

      <div>
        <label htmlFor='password' className='block font-medium text-gray-700 text-sm'>
          Password
        </label>
        <div className='relative mt-1'>
          <Input
            {...getFieldProps('password')}
            id={`${id}-password`}
            type={showPassword ? 'text' : 'password'}
            autoComplete='current-password'
            required
            placeholder='••••••••'
            className='w-full pr-10'
          />
          <button
            type='button'
            className='absolute inset-y-0 right-0 flex items-center pr-3'
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeOff className='h-5 w-5 text-gray-400' suppressHydrationWarning />
            ) : (
              <Eye className='h-5 w-5 text-gray-400' suppressHydrationWarning />
            )}
          </button>
        </div>
        {errors.password && (
          <p className='mt-1 text-sm text-red-600' id='password-error'>
            {errors.password.join(', ')}
          </p>
        )}
      </div>

      <div className='flex items-center justify-between'>
        <div className='flex items-center'>
          <input
            id={`${id}-remember-me`}
            name='remember-me'
            type='checkbox'
            className='h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary'
          />
          <label htmlFor='remember-me' className='ml-2 block text-gray-900 text-sm'>
            Remember me
          </label>
        </div>

        <div className='text-sm'>
          <Link
            href='/forgot-password'
            className='text-left font-medium text-primary hover:text-primary/80'
          >
            Forgot your password?
          </Link>
        </div>
      </div>

      <div>
        <Button type='submit' disabled={isLoading || isSubmitting} className='w-full' size='lg'>
          {(isLoading || isSubmitting) ? 'Signing in...' : 'Sign in'}
        </Button>
      </div>

      <div className='text-center'>
        <p className='text-gray-600 text-sm'>
          Don't have an account?{' '}
          <button
            type='button'
            onClick={handleContactAdmin}
            onKeyDown={(e) => e.key === 'Enter' && handleContactAdmin}
            className='font-medium text-primary hover:text-primary/80'
          >
            Contact your administrator
          </button>
        </p>
      </div>
    </form>
  );
}
