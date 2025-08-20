import { useCallback, useState } from 'react';

export interface ErrorInfo {
  message: string;
  code?: string;
  status?: number;
  timestamp: Date;
  context?: string;
  retryable?: boolean;
  fallbackAvailable?: boolean;
}

export interface ErrorHandlerOptions {
  enableLogging?: boolean;
  enableRetry?: boolean;
  maxRetries?: number;
  retryDelay?: number;
  enableFallback?: boolean;
  onError?: (error: ErrorInfo) => void;
  onRetry?: (attempt: number) => void;
  onFallback?: () => void;
}

export interface UseErrorHandlerResult {
  error: ErrorInfo | null;
  isRetrying: boolean;
  retryCount: number;
  clearError: () => void;
  retry: () => Promise<void>;
  handleError: (error: unknown, context?: string) => ErrorInfo;
}

export function useErrorHandler(
  options: ErrorHandlerOptions = {
    // Implementation pending
  }
): UseErrorHandlerResult {
  const {
    enableLogging = true,
    _enableRetry = true,
    maxRetries = 3,
    retryDelay = 1000,
    enableFallback = true,
    onError,
    onRetry,
    _onFallback,
  } = options;

  const [error, setError] = useState<ErrorInfo | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const clearError = useCallback(() => {
    setError(null);
    setRetryCount(0);
    setIsRetrying(false);
  }, []);

  const handleError = useCallback(
    (rawError: unknown, context?: string): ErrorInfo => {
      const errorInfo: ErrorInfo = {
        message: rawError?.message || 'An unknown error occurred',
        code: rawError?.code,
        status: rawError?.status,
        timestamp: new Date(),
        context,
        retryable: isRetryableError(rawError),
        fallbackAvailable: enableFallback,
      };

      if (enableLogging) {
        console.error(`Error in ${context}:`, errorInfo);
      }

      setError(errorInfo);
      onError?.(errorInfo);

      return errorInfo;
    },
    [enableLogging, enableFallback, onError]
  );

  const retry = useCallback(async () => {
    if (!error || !error.retryable || retryCount >= maxRetries) {
      return;
    }

    setIsRetrying(true);
    setRetryCount((prev) => prev + 1);

    try {
      await new Promise((resolve) => setTimeout(resolve, retryDelay * 2 ** retryCount));
      onRetry?.(retryCount + 1);
    } finally {
      setIsRetrying(false);
    }
  }, [error, retryCount, maxRetries, retryDelay, onRetry]);

  return {
    error,
    isRetrying,
    retryCount,
    clearError,
    retry,
    handleError,
  };
}

function isRetryableError(error: unknown): boolean {
  // Network errors are generally retryable
  if (error?.status === 0 || error?.name === 'NetworkError') {
    return true;
  }

  // Server errors (5xx) are retryable
  if (error?.status >= 500 && error?.status < 600) {
    return true;
  }

  // Rate limiting (429) is retryable
  if (error?.status === 429) {
    return true;
  }

  // Timeout errors are retryable
  if (error?.name === 'TimeoutError' || error?.code === 'TIMEOUT') {
    return true;
  }

  // Client errors (4xx) are generally not retryable
  if (error?.status >= 400 && error?.status < 500) {
    return false;
  }

  return false;
}

// Specialized error boundary hook for React components
export function useErrorBoundary() {
  const [hasError, setHasError] = useState(false);
  const [errorInfo, setErrorInfo] = useState<ErrorInfo | null>(null);

  const resetError = useCallback(() => {
    setHasError(false);
    setErrorInfo(null);
  }, []);

  const captureError = useCallback((error: unknown, _errorBoundary?: unknown) => {
    const info: ErrorInfo = {
      message: error?.message || 'Component error',
      timestamp: new Date(),
      context: 'React Error Boundary',
      retryable: false,
    };

    setErrorInfo(info);
    setHasError(true);
  }, []);

  return {
    hasError,
    errorInfo,
    resetError,
    captureError,
  };
}

// Hook for handling API errors with automatic fallbacks
export function useApiErrorHandler(apiOperation: () => Promise<unknown>, fallbackData?: unknown) {
  const [data, setData] = useState(fallbackData);
  const [isLoading, setIsLoading] = useState(false);
  const errorHandler = useErrorHandler({
    enableRetry: true,
    enableFallback: true,
    onFallback: () => {
      if (fallbackData) {
        setData(fallbackData);
      }
    },
  });

  const execute = useCallback(async () => {
    setIsLoading(true);

    try {
      const result = await apiOperation();
      setData(result);
      errorHandler.clearError();
    } catch (error) {
      const errorInfo = errorHandler.handleError(error, 'API Operation');

      if (errorInfo.fallbackAvailable && fallbackData) {
        setData(fallbackData);
      }
    } finally {
      setIsLoading(false);
    }
  }, [apiOperation, fallbackData, errorHandler]);

  return {
    data,
    isLoading,
    execute,
    ...errorHandler,
  };
}

// Global error handler for unhandled errors
let globalErrorHandler: ((error: ErrorInfo) => void) | null = null;

export function setGlobalErrorHandler(handler: (error: ErrorInfo) => void) {
  globalErrorHandler = handler;
}

// Window error event listeners
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    if (globalErrorHandler) {
      globalErrorHandler({
        message: event.message,
        timestamp: new Date(),
        context: 'Global Error Handler',
        retryable: false,
      });
    }
  });

  window.addEventListener('unhandledrejection', (event) => {
    if (globalErrorHandler) {
      globalErrorHandler({
        message: event.reason?.message || 'Unhandled Promise Rejection',
        timestamp: new Date(),
        context: 'Unhandled Promise',
        retryable: false,
      });
    }
  });
}
