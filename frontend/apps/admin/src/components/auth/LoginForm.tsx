'use client';

import { useAuth } from '@dotmac/headless';
import { Button, Input } from '@dotmac/styled-components';
import { AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useId, useState } from 'react';

export function LoginForm() {
  const id = useId();

  const { login, isLoading, error } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  });
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(formData.email, formData.password);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleForgotPassword = () => {
    console.log('Forgot password clicked');
    // TODO: Implement forgot password functionality
  };

  const handleContactAdmin = () => {
    console.log('Contact admin clicked');
    // TODO: Implement contact admin functionality
  };

  const _handleTogglePassword = () => {
    setShowPassword(!showPassword);
  };

  return (
    <form onSubmit={handleSubmit} className='space-y-6'>
      {error ? (
        <div className='rounded-md border border-red-200 bg-red-50 p-4'>
          <div className='flex'>
            <AlertCircle className='h-5 w-5 text-red-400' />
            <div className='ml-3'>
              <h3 className='font-medium text-red-800 text-sm'>Authentication Failed</h3>
              <p className='mt-2 text-red-700 text-sm'>{error}</p>
            </div>
          </div>
        </div>
      ) : null}

      <div>
        <label htmlFor='email' className='block font-medium text-gray-700 text-sm'>
          Email Address
        </label>
        <div className='mt-1'>
          <Input
            id={`${id}-email`}
            name='email'
            type='email'
            autoComplete='email'
            required
            value={formData.email}
            onChange={handleChange}
            placeholder='admin@yourcompany.com'
            className='w-full'
          />
        </div>
      </div>

      <div>
        <label htmlFor='password' className='block font-medium text-gray-700 text-sm'>
          Password
        </label>
        <div className='relative mt-1'>
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
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeOff className='h-5 w-5 text-gray-400' />
            ) : (
              <Eye className='h-5 w-5 text-gray-400' />
            )}
          </button>
        </div>
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
          <button
            type='button'
            onClick={handleForgotPassword}
            onKeyDown={(e) => e.key === 'Enter' && handleForgotPassword}
            className='text-left font-medium text-primary hover:text-primary/80&apos;
          >
            Forgot your password?
          </button>
        </div>
      </div>

      <div>
        <Button type='submit' disabled={isLoading} className='w-full' size='lg'>
          {isLoading ? 'Signing in...' : 'Sign in&apos;}
        </Button>
      </div>

      <div className='text-center'>
        <p className='text-gray-600 text-sm'>
          Don&apos;t have an account?{' &apos;}
          <button
            type='button'
            onClick={handleContactAdmin}
            onKeyDown={(e) => e.key === 'Enter' && handleContactAdmin}
            className='font-medium text-primary hover:text-primary/80&apos;
          >
            Contact your administrator
          </button>
        </p>
      </div>
    </form>
  );
}
