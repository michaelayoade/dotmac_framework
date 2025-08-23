'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface NetworkErrorContextType {
  isOnline: boolean;
  hasNetworkError: boolean;
  retryConnection: () => void;
  dismissError: () => void;
}

const NetworkErrorContext = createContext<NetworkErrorContextType | undefined>(undefined);

export const useNetworkError = () => {
  const context = useContext(NetworkErrorContext);
  if (context === undefined) {
    throw new Error('useNetworkError must be used within a NetworkErrorProvider');
  }
  return context;
};

interface NetworkErrorProviderProps {
  children: ReactNode;
}

export const NetworkErrorProvider: React.FC<NetworkErrorProviderProps> = ({ children }) => {
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [hasNetworkError, setHasNetworkError] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setHasNetworkError(false);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setHasNetworkError(true);
    };

    // Global error handler for network errors
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const error = event.reason;
      if (
        error instanceof TypeError &&
        (error.message.includes('fetch') || 
         error.message.includes('Network') ||
         error.message.includes('Failed to fetch'))
      ) {
        setHasNetworkError(true);
        event.preventDefault(); // Prevent unhandled rejection error
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);

  const retryConnection = async () => {
    try {
      // Test connection with a lightweight request
      const response = await fetch('/api/v1/health', {
        method: 'GET',
        cache: 'no-cache',
      });
      
      if (response.ok) {
        setHasNetworkError(false);
        setIsOnline(true);
      } else {
        throw new Error('Health check failed');
      }
    } catch (error) {
      console.error('Connection retry failed:', error);
      setHasNetworkError(true);
      setIsOnline(false);
    }
  };

  const dismissError = () => {
    setHasNetworkError(false);
  };

  const contextValue: NetworkErrorContextType = {
    isOnline,
    hasNetworkError,
    retryConnection,
    dismissError,
  };

  return (
    <NetworkErrorContext.Provider value={contextValue}>
      {children}
      {(hasNetworkError || !isOnline) && <NetworkErrorBanner />}
    </NetworkErrorContext.Provider>
  );
};

const NetworkErrorBanner: React.FC = () => {
  const { isOnline, retryConnection, dismissError } = useNetworkError();
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetry = async () => {
    setIsRetrying(true);
    await retryConnection();
    setIsRetrying(false);
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white p-3 shadow-lg">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <svg className="h-5 w-5 text-red-200" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" 
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" 
                  clipRule="evenodd" />
          </svg>
          <span className="font-medium">
            {!isOnline 
              ? 'You are currently offline' 
              : 'Connection error - Some features may not work properly'}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            className="bg-red-500 hover:bg-red-400 disabled:opacity-50 px-3 py-1 rounded text-sm font-medium transition-colors"
          >
            {isRetrying ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-white inline" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" 
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Retrying...
              </>
            ) : (
              'Retry'
            )}
          </button>
          
          <button
            onClick={dismissError}
            className="text-red-200 hover:text-white p-1"
            aria-label="Dismiss error"
          >
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" 
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" 
                    clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default NetworkErrorProvider;