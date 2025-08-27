/**
 * Secure Login Form Component
 * Implements security best practices for authentication
 */

'use client';

import { Button, Input } from '@dotmac/styled-components/admin';
import { AlertCircle, Eye, EyeOff, Shield } from 'lucide-react';
import { useId, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useSecureAuthStore } from '../../stores/secureAuthStore';
import { useValidatedForm } from '../../hooks/useValidatedForm';
import { LoginSchema } from '../../lib/schemas';
import { sanitizeInput } from '../../lib/security';

export function SecureLoginForm() {
  const id = useId();
  const router = useRouter();
  const { 
    login, 
    isLoading, 
    error, 
    clearError, 
    user, 
    isAuthenticated 
  } = useSecureAuthStore();
  
  const [showPassword, setShowPassword] = useState(false);
  const [csrfToken, setCsrfToken] = useState<string>('');
  const [attemptCount, setAttemptCount] = useState(0);
  const [isBlocked, setIsBlocked] = useState(false);
  const [blockTimeRemaining, setBlockTimeRemaining] = useState(0);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      const redirect = new URLSearchParams(window.location.search).get('redirect');
      router.replace(redirect || '/dashboard');
    }
  }, [isAuthenticated, user, router]);

  // Get CSRF token on component mount
  useEffect(() => {
    fetchCSRFToken();
  }, []);

  // Handle client-side rate limiting for failed attempts
  useEffect(() => {
    if (attemptCount >= 3) {
      setIsBlocked(true);
      setBlockTimeRemaining(300); // 5 minutes
      
      const timer = setInterval(() => {
        setBlockTimeRemaining(prev => {
          if (prev <= 1) {
            setIsBlocked(false);
            setAttemptCount(0);
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
      return () => clearInterval(timer);
    }
  }, [attemptCount]);

  const fetchCSRFToken = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/csrf', {
        method: 'GET',
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setCsrfToken(data.csrfToken);
      }
    } catch (error) {
      console.error('Failed to fetch CSRF token:', error);
    }
  }, []);

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
      // Check if blocked due to too many attempts
      if (isBlocked) {
        return;
      }

      clearError();
      
      try {
        // Sanitize email input
        const sanitizedEmail = sanitizeInput(data.email).toLowerCase();
        
        if (!sanitizedEmail || !data.password) {
          setAttemptCount(prev => prev + 1);
          return;
        }

        const result = await login({
          email: sanitizedEmail,
          password: data.password,
        });
        
        if (result.success) {
          // Reset attempt count on success
          setAttemptCount(0);
          
          // Redirect will happen via useEffect
        } else {
          // Increment failed attempt count
          setAttemptCount(prev => prev + 1);
        }
        
      } catch (error) {
        console.error('Login submission error:', error);
        setAttemptCount(prev => prev + 1);
      }
    },
  });

  // Format remaining block time
  const formatBlockTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-100">
            <Shield className="h-6 w-6 text-blue-600" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to Admin Portal
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Secure access to ISP management system
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {/* Security Notice */}
          <div className="rounded-md bg-blue-50 p-4">
            <div className="flex">
              <Shield className="h-5 w-5 text-blue-400" />
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  This system uses secure authentication with session monitoring
                  and CSRF protection.
                </p>
              </div>
            </div>
          </div>

          {/* Rate Limiting Warning */}
          {isBlocked && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-700">
                    Too many failed attempts. Try again in {formatBlockTime(blockTimeRemaining)}.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Attempt Counter */}
          {attemptCount > 0 && attemptCount < 3 && (
            <div className="rounded-md bg-yellow-50 p-4">
              <p className="text-sm text-yellow-700">
                {3 - attemptCount} attempts remaining before temporary lockout.
              </p>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor={`${id}-email`} className="sr-only">
                Email address
              </label>
              <Input
                {...getFieldProps('email')}
                id={`${id}-email`}
                name="email"
                type="email"
                autoComplete="email"
                required
                className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
                disabled={isSubmitting || isBlocked}
                maxLength={254}
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email}</p>
              )}
            </div>

            {/* Password Field */}
            <div className="relative">
              <label htmlFor={`${id}-password`} className="sr-only">
                Password
              </label>
              <Input
                {...getFieldProps('password')}
                id={`${id}-password`}
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                className="appearance-none rounded-md relative block w-full px-3 py-2 pr-10 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                disabled={isSubmitting || isBlocked}
                maxLength={128}
              />
              <button
                type="button"
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isSubmitting || isBlocked}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5 text-gray-400" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400" />
                )}
              </button>
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password}</p>
              )}
            </div>
          </div>

          {/* Remember Me */}
          <div className="flex items-center">
            <input
              {...getFieldProps('rememberMe')}
              id={`${id}-remember`}
              name="rememberMe"
              type="checkbox"
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              disabled={isSubmitting || isBlocked}
            />
            <label htmlFor={`${id}-remember`} className="ml-2 block text-sm text-gray-900">
              Remember me (extends session to 7 days)
            </label>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isSubmitting || isBlocked || !csrfToken}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Signing in...
              </span>
            ) : (
              'Sign in'
            )}
          </Button>

          {/* Forgot Password Link */}
          <div className="text-center">
            <Link
              href="/forgot-password"
              className="font-medium text-blue-600 hover:text-blue-500"
            >
              Forgot your password?
            </Link>
          </div>
        </form>

        {/* Security Footer */}
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>
            This system is monitored for security. All access is logged.
          </p>
          <p className="mt-1">
            Session timeout: 30 minutes • Failed attempts lockout: 5 minutes
          </p>
        </div>
      </div>
    </div>
  );
}