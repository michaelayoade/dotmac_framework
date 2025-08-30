'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { StandardErrorBoundary, useStandardErrorHandler } from '@dotmac/headless';

interface AuthErrorProviderProps {
  children: React.ReactNode;
}

/**
 * Provides authentication error handling context
 * Integrates with platform error handling instead of hard redirects
 */
export function AuthErrorProvider({ children }: AuthErrorProviderProps) {
  const router = useRouter();
  const errorHandler = useStandardErrorHandler({
    context: 'auth',
    enableRetry: true,
    enableNotifications: true,
    enableLogging: true
  });

  useEffect(() => {
    // Listen for authentication errors globally
    const handleAuthError = (event: CustomEvent) => {
      const { error, context } = event.detail;

      // Handle different auth error types gracefully
      if (error.status === 401) {
        // Authentication required - show login prompt instead of redirect
        const currentPath = window.location.pathname;
        if (!currentPath.includes('/login')) {
          sessionStorage.setItem('redirect_after_login', currentPath);
        }

        errorHandler.handleError(error, 'Authentication required');
      } else if (error.status === 403) {
        // Access denied - handle gracefully
        errorHandler.handleError(error, 'Access denied');
      } else {
        // Other auth errors
        errorHandler.handleError(error, context || 'Authentication error');
      }
    };

    // Listen for custom auth error events
    window.addEventListener('auth-error' as any, handleAuthError);

    return () => {
      window.removeEventListener('auth-error' as any, handleAuthError);
    };
  }, [errorHandler]);

  const handleAuthBoundaryError = (error: Error, errorInfo?: any) => {
    // Check if it's an authentication-related error
    if (error.message?.includes('401') || error.message?.includes('unauthorized')) {
      const redirectPath = sessionStorage.getItem('redirect_after_login') || '/dashboard';

      // Show user-friendly error instead of crashing
      console.error('Authentication error caught by boundary:', error);

      // Optionally navigate to login with context
      setTimeout(() => {
        router.push(`/login?redirect=${encodeURIComponent(redirectPath)}`);
      }, 2000);
    }
  };

  const AuthErrorFallback = (error: Error) => (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="rounded-lg bg-white p-8 shadow-md max-w-md w-full mx-4">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 mb-4">
            <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Authentication Required</h2>
          <p className="text-gray-600 mb-6">
            Your session has expired or you need to log in to access this page.
          </p>
          <div className="space-y-3">
            <button
              onClick={() => router.push('/login')}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Go to Login
            </button>
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <StandardErrorBoundary
      fallback={AuthErrorFallback}
      onError={handleAuthBoundaryError}
      resetOnPropsChange={true}
    >
      {children}
    </StandardErrorBoundary>
  );
}
