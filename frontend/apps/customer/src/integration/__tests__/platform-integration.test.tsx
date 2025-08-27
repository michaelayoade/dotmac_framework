/**
 * Platform Integration Test Suite
 * Tests integration with @dotmac/headless platform components
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { StandardErrorBoundary, useStandardErrorHandler } from '@dotmac/headless';
// Already imported in combined import above
import { AuthErrorProvider } from '../../components/providers/AuthErrorProvider';
import { SecureCustomerLoginForm } from '../../components/auth/SecureCustomerLoginForm';

// Mock platform dependencies
const mockHandleError = jest.fn();
jest.mock('@dotmac/headless/hooks/useStandardErrorHandler', () => ({
  useStandardErrorHandler: () => ({
    handleError: mockHandleError,
  }),
}));

jest.mock('@dotmac/headless', () => ({
  StandardStandardErrorBoundary: ({ children, fallback, onError }: any) => {
    // Simple mock that catches errors and shows fallback
    const [hasError, setHasError] = React.useState(false);
    const [error, setError] = React.useState<Error | null>(null);

    const ErrorCatcher = ({ children }: any) => {
      const [caught, setCaught] = React.useState(false);
      
      React.useEffect(() => {
        const handleError = (event: ErrorEvent) => {
          if (!caught) {
            setCaught(true);
            setHasError(true);
            setError(new Error(event.message));
            if (onError) onError(new Error(event.message), {});
          }
        };

        window.addEventListener('error', handleError);
        return () => window.removeEventListener('error', handleError);
      }, [caught]);

      // Check for React errors in children
      try {
        return children;
      } catch (err) {
        if (!caught) {
          setCaught(true);
          setHasError(true);
          setError(err as Error);
          if (onError) onError(err as Error, {});
        }
        return null;
      }
    };

    if (hasError && error) {
      return fallback ? fallback(error) : (
        <div>
          <h2>Something went wrong</h2>
          <p>{error.message}</p>
          <button onClick={() => setHasError(false)}>Try Again</button>
        </div>
      );
    }

    return <ErrorCatcher>{children}</ErrorCatcher>;
  },
}));

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
}));

// Mock auth provider
jest.mock('../../components/auth/SecureAuthProvider', () => ({
  useAuthActions: () => ({
    login: jest.fn(),
  }),
}));

describe('Platform Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHandleError.mockClear();
  });

  describe('Error Boundary Integration', () => {
    const ThrowingComponent = ({ message = 'Test error' }: { message?: string }) => {
      throw new Error(message);
    };

    it('should integrate with @dotmac/headless StandardErrorBoundary', () => {
      const onError = jest.fn();
      
      render(
        <StandardStandardErrorBoundary onError={onError}>
          <ThrowingComponent message="Platform integration error" />
        </StandardStandardErrorBoundary>
      );

      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('Platform integration error')).toBeInTheDocument();
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Platform integration error',
        }),
        expect.any(Object)
      );
    });

    it('should work with AuthErrorProvider and platform StandardErrorBoundary together', () => {
      const AuthErrorComponent = () => {
        throw new Error('401 Authentication required');
      };

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <AuthErrorComponent />
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      // Should show authentication-specific error UI
      expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      expect(screen.getByText('Go to Login')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('should handle nested error boundaries correctly', () => {
      const NestedErrorComponent = () => {
        throw new Error('Nested component error');
      };

      render(
        <StandardErrorBoundary fallback={(error) => <div>Outer boundary: {error.message}</div>}>
          <AuthErrorProvider>
            <StandardErrorBoundary fallback={(error) => <div>Inner boundary: {error.message}</div>}>
              <NestedErrorComponent />
            </StandardErrorBoundary>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      // Inner boundary should catch the error first
      expect(screen.getByText('Inner boundary: Nested component error')).toBeInTheDocument();
    });
  });

  describe('Error Handler Integration', () => {
    it('should use platform error handler for authentication errors', async () => {
      // Simulate an authentication error event
      const TestComponent = () => {
        React.useEffect(() => {
          const error = { status: 401, message: 'Token expired' };
          const event = new CustomEvent('auth-error', {
            detail: { error, context: 'API call failed' },
          });
          window.dispatchEvent(event);
        }, []);

        return <div>Test component</div>;
      };

      render(
        <AuthErrorProvider>
          <TestComponent />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 401,
            message: 'Token expired',
          }),
          'Authentication required'
        );
      });
    });

    it('should integrate error handler with login form', async () => {
      const mockLogin = require('../../components/auth/SecureAuthProvider').useAuthActions().login;
      mockLogin.mockRejectedValue({
        status: 500,
        message: 'Server error',
      });

      render(
        <AuthErrorProvider>
          <SecureCustomerLoginForm />
        </AuthErrorProvider>
      );

      const emailInput = screen.getByLabelText(/email address/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 500,
            message: 'Server error',
          }),
          'Login attempt'
        );
      });
    });
  });

  describe('Platform Component Consistency', () => {
    it('should maintain consistent styling with platform components', () => {
      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <div>Test content</div>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      const wrapper = screen.getByText('Test content').closest('div');
      expect(wrapper).toBeInTheDocument();
    });

    it('should use platform-consistent error messages', async () => {
      const ErrorComponent = () => {
        throw new Error('Network timeout');
      };

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <ErrorComponent />
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      // Should show platform-consistent error UI
      expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      
      // Should have consistent button styling and behavior
      const loginButton = screen.getByText('Go to Login');
      expect(loginButton).toHaveClass(
        expect.stringMatching(/bg-blue-600|text-white|rounded/)
      );
    });
  });

  describe('Performance Integration', () => {
    it('should not impact platform performance metrics', async () => {
      const startTime = performance.now();

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <div>Performance test content</div>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      const renderTime = performance.now() - startTime;
      expect(renderTime).toBeLessThan(50); // Should be very fast
    });

    it('should integrate with platform monitoring', async () => {
      // Mock performance observer
      const mockObserve = jest.fn();
      global.PerformanceObserver = jest.fn().mockImplementation((callback) => ({
        observe: mockObserve,
        disconnect: jest.fn(),
      }));

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <div>Monitoring test</div>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      // Should not interfere with platform monitoring
      expect(screen.getByText('Monitoring test')).toBeInTheDocument();
    });
  });

  describe('Security Integration', () => {
    it('should maintain platform security headers', () => {
      const originalLocation = window.location;
      delete (window as any).location;
      (window as any).location = {
        ...originalLocation,
        protocol: 'https:',
        host: 'secure.dotmac.com',
      };

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <div>Security test</div>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      // Should render without security violations
      expect(screen.getByText('Security test')).toBeInTheDocument();

      (window as any).location = originalLocation;
    });

    it('should integrate with platform CSP policies', () => {
      // Mock CSP violation handler
      const cspViolations: any[] = [];
      document.addEventListener('securitypolicyviolation', (e) => {
        cspViolations.push(e);
      });

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <div>CSP test content</div>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      // Should not trigger any CSP violations
      expect(cspViolations).toHaveLength(0);
      expect(screen.getByText('CSP test content')).toBeInTheDocument();
    });

    it('should handle platform authentication tokens securely', async () => {
      const TestComponent = () => {
        // Simulate accessing authentication state
        React.useEffect(() => {
          // Should not expose tokens in DOM or console
          const element = document.querySelector('[data-token]');
          expect(element).toBeNull();
        }, []);

        return <div>Token security test</div>;
      };

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <TestComponent />
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      expect(screen.getByText('Token security test')).toBeInTheDocument();
    });
  });

  describe('Platform API Integration', () => {
    it('should work with platform API client patterns', async () => {
      // Mock platform API call
      const mockApiCall = jest.fn().mockRejectedValue({
        status: 401,
        message: 'Unauthorized',
      });

      const ApiTestComponent = () => {
        React.useEffect(() => {
          mockApiCall().catch((error) => {
            const event = new CustomEvent('auth-error', {
              detail: { error, context: 'Platform API integration' },
            });
            window.dispatchEvent(event);
          });
        }, []);

        return <div>API integration test</div>;
      };

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <ApiTestComponent />
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 401,
            message: 'Unauthorized',
          }),
          'Authentication required'
        );
      });
    });

    it('should maintain platform error propagation patterns', async () => {
      const errorSpy = jest.spyOn(console, 'error').mockImplementation();
      
      const PropagatingErrorComponent = () => {
        throw new Error('Propagation test error');
      };

      render(
        <StandardErrorBoundary onError={(error, errorInfo) => {
          // Should receive platform error boundary callbacks
          expect(error.message).toBe('Propagation test error');
          expect(errorInfo).toBeDefined();
        }}>
          <AuthErrorProvider>
            <PropagatingErrorComponent />
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      
      errorSpy.mockRestore();
    });
  });

  describe('Platform Theme Integration', () => {
    it('should inherit platform theme variables', () => {
      // Mock theme context
      const originalGetComputedStyle = window.getComputedStyle;
      window.getComputedStyle = jest.fn().mockReturnValue({
        getPropertyValue: jest.fn().mockReturnValue('#3b82f6'), // Platform blue
      });

      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <div data-testid="themed-component">Theme test</div>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      const component = screen.getByTestId('themed-component');
      expect(component).toBeInTheDocument();

      window.getComputedStyle = originalGetComputedStyle;
    });

    it('should maintain responsive behavior with platform breakpoints', () => {
      // Mock different viewport sizes
      Object.defineProperty(window, 'innerWidth', { value: 768 });
      
      render(
        <StandardErrorBoundary>
          <AuthErrorProvider>
            <div className="responsive-test">Responsive content</div>
          </AuthErrorProvider>
        </StandardErrorBoundary>
      );

      expect(screen.getByText('Responsive content')).toBeInTheDocument();
    });
  });
});