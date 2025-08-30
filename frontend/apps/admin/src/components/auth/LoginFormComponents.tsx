/**
 * Login Form Composition Components
 *
 * Breaks down complex LoginForm into smaller, focused components
 */

import { Button, Input } from '@dotmac/ui/admin';
import { AlertCircle, Eye, EyeOff } from 'lucide-react';
import type React from 'react';
import { useId } from 'react';

// Error display component
export const ErrorAlert: React.FC<{ error: string | null }> = ({ error }) => {
  if (!error) {
    return null;
  }

  return (
    <div className='flex items-center space-x-2 rounded-md border border-red-200 bg-red-50 p-3'>
      <AlertCircle className='h-4 w-4 text-red-500' />
      <span className='text-red-700 text-sm'>{error}</span>
    </div>
  );
};

// Email input component
export const EmailInput: React.FC<{
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}> = ({ value, onChange }) => {
  const emailId = useId();
  return (
    <div>
      <label htmlFor={emailId} className='block font-medium text-gray-700 text-sm'>
        Email address
      </label>
      <Input
        id={emailId}
        name='email'
        type='email'
        autoComplete='email'
        required
        value={value}
        onChange={onChange}
        className='mt-1'
      />
    </div>
  );
};

// Password input component
export const PasswordInput: React.FC<{
  value: string;
  showPassword: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onTogglePassword: () => void;
}> = ({ value, showPassword, onChange, onTogglePassword }) => {
  const passwordId = useId();
  return (
    <div>
      <label htmlFor={passwordId} className='block font-medium text-gray-700 text-sm'>
        Password
      </label>
      <div className='relative mt-1'>
        <Input
          id={passwordId}
          name='password'
          type={showPassword ? 'text' : 'password'}
          autoComplete='current-password'
          required
          value={value}
          onChange={onChange}
          className='pr-10'
        />
        <button
          type='button'
          className='absolute inset-y-0 right-0 flex items-center pr-3'
          onClick={onTogglePassword}
          onKeyDown={(e) => e.key === 'Enter' && onTogglePassword()}
        >
          {showPassword ? (
            <EyeOff className='h-4 w-4 text-gray-400' />
          ) : (
            <Eye className='h-4 w-4 text-gray-400' />
          )}
        </button>
      </div>
    </div>
  );
};

// Remember me checkbox component
export const RememberMeCheckbox: React.FC<{
  checked: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}> = ({ checked, onChange }) => {
  const checkboxId = useId();
  return (
    <input
      id={checkboxId}
      name='remember-me'
      type='checkbox'
      checked={checked}
      onChange={onChange}
      className='h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary'
    />
  );
};

// Action links component
export const ActionLinks: React.FC<{
  onForgotPassword: () => void;
  onContactAdmin: () => void;
}> = ({ onForgotPassword, onContactAdmin }) => (
  <>
    <div className='text-sm'>
      <button
        type='button'
        onClick={onForgotPassword}
        onKeyDown={(e) => e.key === 'Enter' && onForgotPassword}
        className='text-left font-medium text-primary hover:text-primary/80'
      >
        Forgot your password?
      </button>
    </div>
    <div className='text-center'>
      <p className='text-gray-600 text-sm'>
        Don&apos;t have an account?{' '}
        <button
          type='button'
          onClick={onContactAdmin}
          onKeyDown={(e) => e.key === 'Enter' && onContactAdmin}
          className='font-medium text-primary hover:text-primary/80'
        >
          Contact your administrator
        </button>
      </p>
    </div>
  </>
);

// Submit button component
export const SubmitButton: React.FC<{
  isLoading: boolean;
}> = ({ isLoading }) => (
  <Button type='submit' disabled={isLoading} className='w-full' size='lg'>
    {isLoading ? 'Signing in...' : 'Sign in'}
  </Button>
);
