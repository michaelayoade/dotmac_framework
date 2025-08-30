'use client';

import { ErrorBoundary } from '@dotmac/providers/error';
import type React from 'react';

export default function ErrorBoundaryClient({
  children,
  level = 'page',
}: {
  children: React.ReactNode;
  level?: 'page' | 'section' | 'component';
}) {
  const handleError = (error: Error, errorInfo: React.ErrorInfo, errorId: string) => {
    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group('🚨 Error Boundary Caught Error');
      console.error('Error:', error);
      console.error('Error ID:', errorId);
      console.error('Component Stack:', errorInfo.componentStack);
      console.groupEnd();
    }

    // Send to error tracking service (Sentry, LogRocket, etc.)
    if (typeof window !== 'undefined') {
      // Example: Send to monitoring service
      try {
        // This would be replaced with actual error tracking service
        fetch('/api/errors', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            errorId,
            message: error.message,
            stack: error.stack,
            componentStack: errorInfo.componentStack,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            userId: 'user-id-placeholder', // Would get from auth context
            level,
          }),
        }).catch(() => {
          // Fail silently to not cause additional errors
        });
      } catch {
        // Fail silently
      }
    }
  };

  return (
    <ErrorBoundary level={level} onError={handleError}>
      {children}
    </ErrorBoundary>
  );
}
