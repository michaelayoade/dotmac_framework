import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';
import { AlertTriangle, RefreshCw, Home, ArrowLeft, Wifi } from 'lucide-react';

const errorShellVariants = cva(
  'flex flex-col items-center justify-center p-6 text-center',
  {
    variants: {
      variant: {
        default: 'bg-white border border-red-200 rounded-lg shadow-sm',
        minimal: 'bg-transparent',
        destructive: 'bg-red-50 border border-red-200 rounded-lg',
        warning: 'bg-yellow-50 border border-yellow-200 rounded-lg',
        info: 'bg-blue-50 border border-blue-200 rounded-lg',
      },
      size: {
        sm: 'min-h-[200px] p-4',
        md: 'min-h-[300px] p-6',
        lg: 'min-h-[400px] p-8',
        full: 'min-h-screen',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
);

interface ErrorShellProps extends VariantProps<typeof errorShellVariants> {
  title?: string;
  message?: string;
  error?: Error | string;
  showRetry?: boolean;
  showHome?: boolean;
  showBack?: boolean;
  onRetry?: () => void;
  onHome?: () => void;
  onBack?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export const ErrorShell: React.FC<ErrorShellProps> = ({
  variant,
  size,
  title = 'Something went wrong',
  message,
  error,
  showRetry = true,
  showHome = false,
  showBack = false,
  onRetry,
  onHome,
  onBack,
  className,
  children,
}) => {
  const errorMessage = React.useMemo(() => {
    if (message) return message;
    if (typeof error === 'string') return error;
    if (error instanceof Error) return error.message;
    return 'An unexpected error occurred';
  }, [message, error]);

  const getIcon = () => {
    switch (variant) {
      case 'warning':
        return <AlertTriangle className="w-12 h-12 text-yellow-500" />;
      case 'info':
        return <AlertTriangle className="w-12 h-12 text-blue-500" />;
      default:
        return <AlertTriangle className="w-12 h-12 text-red-500" />;
    }
  };

  return (
    <div className={clsx(errorShellVariants({ variant, size }), className)} role="alert">
      {getIcon()}
      
      <div className="mt-4 space-y-2">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600 max-w-md">{errorMessage}</p>
      </div>

      {children && <div className="mt-4">{children}</div>}

      <div className="flex gap-2 mt-6">
        {showRetry && onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </button>
        )}
        
        {showBack && onBack && (
          <button
            onClick={onBack}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </button>
        )}
        
        {showHome && onHome && (
          <button
            onClick={onHome}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <Home className="w-4 h-4 mr-2" />
            Home
          </button>
        )}
      </div>
    </div>
  );
};

// Specific error components
export const NetworkErrorShell: React.FC<{
  onRetry?: () => void;
  className?: string;
}> = ({ onRetry, className }) => {
  return (
    <ErrorShell
      variant="warning"
      title="Network Connection Error"
      message="Please check your internet connection and try again"
      showRetry
      onRetry={onRetry}
      className={className}
    >
      <Wifi className="w-8 h-8 text-gray-400 mx-auto mt-2" />
    </ErrorShell>
  );
};

export const NotFoundErrorShell: React.FC<{
  resource?: string;
  onHome?: () => void;
  onBack?: () => void;
  className?: string;
}> = ({ resource = 'page', onHome, onBack, className }) => {
  return (
    <ErrorShell
      variant="info"
      title="Not Found"
      message={`The ${resource} you're looking for doesn't exist or has been moved`}
      showHome={!!onHome}
      showBack={!!onBack}
      onHome={onHome}
      onBack={onBack}
      className={className}
    />
  );
};

export const UnauthorizedErrorShell: React.FC<{
  onLogin?: () => void;
  onHome?: () => void;
  className?: string;
}> = ({ onLogin, onHome, className }) => {
  return (
    <ErrorShell
      variant="warning"
      title="Access Denied"
      message="You don't have permission to view this content. Please sign in or contact support."
      showHome={!!onHome}
      onHome={onHome}
      className={className}
    >
      {onLogin && (
        <button
          onClick={onLogin}
          className="mt-4 inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Sign In
        </button>
      )}
    </ErrorShell>
  );
};

export const ServerErrorShell: React.FC<{
  onRetry?: () => void;
  onHome?: () => void;
  className?: string;
}> = ({ onRetry, onHome, className }) => {
  return (
    <ErrorShell
      variant="destructive"
      title="Server Error"
      message="We're experiencing technical difficulties. Our team has been notified."
      showRetry={!!onRetry}
      showHome={!!onHome}
      onRetry={onRetry}
      onHome={onHome}
      className={className}
    />
  );
};