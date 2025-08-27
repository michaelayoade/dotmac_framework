'use client';

import { useGlobalLoading } from '@/store';
import { Loader2 } from 'lucide-react';

interface LoadingOverlayProps {
  message?: string;
}

export function LoadingOverlay({ message = 'Loading...' }: LoadingOverlayProps) {
  const isLoading = useGlobalLoading();

  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center">
      <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm w-full mx-4">
        <div className="flex items-center space-x-4">
          <Loader2 className="h-6 w-6 animate-spin text-management-600" />
          <div>
            <h3 className="text-sm font-medium text-gray-900">{message}</h3>
            <p className="text-xs text-gray-500 mt-1">Please wait while we process your request</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Page-specific loading component
interface PageLoadingProps {
  page: string;
  message?: string;
}

export function PageLoading({ page, message }: PageLoadingProps) {
  return (
    <div className="flex items-center justify-center min-h-96">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin text-management-600 mx-auto mb-4" />
        <h3 className="text-sm font-medium text-gray-900 mb-1">
          {message || `Loading ${page}...`}
        </h3>
        <p className="text-xs text-gray-500">This shouldn't take long</p>
      </div>
    </div>
  );
}

// Inline loading spinner
export function InlineLoading({ size = 'sm', message }: { size?: 'sm' | 'md' | 'lg'; message?: string }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <div className="flex items-center space-x-2">
      <Loader2 className={`animate-spin text-management-600 ${sizeClasses[size]}`} />
      {message && (
        <span className="text-sm text-gray-600">{message}</span>
      )}
    </div>
  );
}