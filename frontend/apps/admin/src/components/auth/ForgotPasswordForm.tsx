'use client';

import { useState } from 'react';
import { Button, Input } from '@dotmac/styled-components';
import { AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface ForgotPasswordFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ForgotPasswordForm({ onSuccess, onCancel }: ForgotPasswordFormProps) {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Simulate API call for password reset
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Mock validation
      if (!email.includes('@')) {
        throw new Error('Please enter a valid email address');
      }

      // In a real app, this would call an API endpoint
      console.log('Password reset requested for:', email);

      setIsSuccess(true);
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className='text-center'>
        <div className='mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4'>
          <CheckCircle className='h-6 w-6 text-green-600' />
        </div>
        <h3 className='text-lg font-medium text-gray-900 mb-2'>Reset Link Sent</h3>
        <p className='text-sm text-gray-600 mb-6'>
          We've sent a password reset link to <strong>{email}</strong>. Please check your email and
          follow the instructions to reset your password.
        </p>
        <div className='space-y-3'>
          <Link href='/login' className='block'>
            <Button variant='outline' className='w-full'>
              <ArrowLeft className='h-4 w-4 mr-2' />
              Back to Login
            </Button>
          </Link>
          <p className='text-xs text-gray-500'>
            Didn't receive the email? Check your spam folder or contact your administrator.
          </p>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className='space-y-6'>
      <div>
        <h3 className='text-lg font-medium text-gray-900 mb-2'>Reset Your Password</h3>
        <p className='text-sm text-gray-600 mb-6'>
          Enter your email address and we'll send you a link to reset your password.
        </p>
      </div>

      {error && (
        <div className='rounded-md border border-red-200 bg-red-50 p-4'>
          <div className='flex'>
            <AlertCircle className='h-5 w-5 text-red-400' />
            <div className='ml-3'>
              <h3 className='font-medium text-red-800 text-sm'>Error</h3>
              <p className='mt-2 text-red-700 text-sm'>{error}</p>
            </div>
          </div>
        </div>
      )}

      <div>
        <label htmlFor='reset-email' className='block font-medium text-gray-700 text-sm'>
          Email Address
        </label>
        <div className='mt-1'>
          <Input
            id='reset-email'
            name='email'
            type='email'
            autoComplete='email'
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder='admin@yourcompany.com'
            className='w-full'
          />
        </div>
      </div>

      <div className='space-y-3'>
        <Button type='submit' disabled={isLoading || !email.trim()} className='w-full' size='lg'>
          {isLoading ? 'Sending Reset Link...' : 'Send Reset Link'}
        </Button>

        <Link href='/login' className='block'>
          <Button variant='outline' className='w-full'>
            <ArrowLeft className='h-4 w-4 mr-2' />
            Back to Login
          </Button>
        </Link>
      </div>

      <div className='text-center'>
        <p className='text-xs text-gray-500'>
          For security reasons, password reset links expire in 1 hour.
        </p>
      </div>
    </form>
  );
}
