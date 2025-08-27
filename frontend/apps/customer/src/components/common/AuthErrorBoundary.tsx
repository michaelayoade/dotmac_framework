'use client';

import { Lock, LogOut, Shield } from 'lucide-react';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  onAuthError?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorType: 'unauthorized' | 'session_expired' | 'auth_failed' | 'unknown';
}

export class AuthErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false,
      errorType: 'unknown'
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Analyze authentication error type
    let errorType: State['errorType'] = 'unknown';
    
    if (error.message.includes('401') || error.message.includes('Unauthorized')) {
      errorType = 'unauthorized';
    } else if (error.message.includes('Session expired') || error.message.includes('Token')) {
      errorType = 'session_expired';
    } else if (error.message.includes('Authentication') || error.message.includes('Login')) {
      errorType = 'auth_failed';
    }

    return { 
      hasError: true, 
      error,
      errorType
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ error, errorInfo });
    
    console.error('AuthErrorBoundary caught an authentication error:', error);
    
    // Call custom auth error handler
    this.props.onAuthError?.();
    
    // Track authentication errors
    if (typeof window !== 'undefined') {
      window.gtag?.('event', 'auth_error', {
        error_type: this.state.errorType,
        error_message: error.message,
      });
    }
  }

  private handleLogin = () => {
    window.location.href = '/';
  };

  private handleLogout = () => {
    // Clear any stored auth data
    if (typeof window !== 'undefined') {
      localStorage.clear();
      sessionStorage.clear();
      document.cookie.split(';').forEach(cookie => {
        const [name] = cookie.split('=');
        document.cookie = `${name.trim()}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
      });
    }
    
    window.location.href = '/';
  };

  private getErrorContent() {
    switch (this.state.errorType) {
      case 'session_expired':
        return {
          icon: <Lock className="h-16 w-16 text-orange-500" />,
          title: 'Session Expired',
          message: 'Your session has expired for security reasons. Please log in again to continue.',
          actionText: 'Log In Again',
          action: this.handleLogin,
          showLogout: false,
        };
      
      case 'unauthorized':
        return {
          icon: <Shield className="h-16 w-16 text-red-500" />,
          title: 'Access Denied',
          message: 'You don\'t have permission to access this resource. Please check your account status.',
          actionText: 'Go to Login',
          action: this.handleLogin,
          showLogout: true,
        };
        
      case 'auth_failed':
        return {
          icon: <LogOut className="h-16 w-16 text-gray-500" />,
          title: 'Authentication Failed',
          message: 'We couldn\'t verify your identity. This might be a temporary issue.',
          actionText: 'Try Again',
          action: this.handleLogin,
          showLogout: true,
        };
        
      default:
        return {
          icon: <Lock className="h-16 w-16 text-gray-500" />,
          title: 'Authentication Error',
          message: 'An authentication error occurred. Please try logging in again.',
          actionText: 'Go to Login',
          action: this.handleLogin,
          showLogout: false,
        };
    }
  }

  render() {
    if (this.state.hasError) {
      const { icon, title, message, actionText, action, showLogout } = this.getErrorContent();

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12">
          <div className="max-w-md w-full text-center">
            <div className="mx-auto flex items-center justify-center">
              {icon}
            </div>
            
            <h1 className="mt-6 text-2xl font-bold text-gray-900">
              {title}
            </h1>
            
            <p className="mt-2 text-sm text-gray-600">
              {message}
            </p>

            <div className="mt-8 space-y-3">
              <button
                onClick={action}
                type="button"
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {actionText}
              </button>
              
              {showLogout && (
                <button
                  onClick={this.handleLogout}
                  type="button"
                  className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Clear Session & Logout
                </button>
              )}
            </div>

            <div className="mt-6 text-center">
              <p className="text-xs text-gray-500">
                Need help? Contact{' '}
                <a 
                  href="mailto:support@dotmac.com" 
                  className="text-blue-600 hover:text-blue-500"
                >
                  support@dotmac.com
                </a>
              </p>
            </div>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4 text-left">
                <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                  Error Details (Development)
                </summary>
                <pre className="mt-2 text-xs bg-gray-100 p-3 rounded text-left overflow-auto max-h-32">
                  {this.state.error.message}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}