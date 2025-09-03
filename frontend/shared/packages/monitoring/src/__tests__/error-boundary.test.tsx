/**
 * @fileoverview Tests for monitoring error boundary component
 * Validates error capture, fallback rendering, and Sentry integration
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from '../sentry/error-boundary';

// Mock Sentry
const mockCaptureException = jest.fn();
const mockWithScope = jest.fn();
const mockSetTag = jest.fn();
const mockSetContext = jest.fn();
const mockSetUser = jest.fn();

jest.mock('@sentry/react', () => ({
  captureException: mockCaptureException,
  withScope: mockWithScope.mockImplementation((callback) => {
    callback({
      setTag: mockSetTag,
      setContext: mockSetContext,
      setUser: mockSetUser,
    });
  }),
}));

// Test component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean; errorMessage?: string }> = ({
  shouldThrow = false,
  errorMessage = 'Test error',
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div data-testid='no-error'>No error occurred</div>;
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Suppress error boundary console.error in tests
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
  });

  describe('Normal Rendering', () => {
    it('should render children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('no-error')).toBeInTheDocument();
      expect(mockCaptureException).not.toHaveBeenCalled();
    });

    it('should pass through props to children', () => {
      const TestChild: React.FC<{ testProp: string }> = ({ testProp }) => (
        <div data-testid='test-child'>{testProp}</div>
      );

      render(
        <ErrorBoundary>
          <TestChild testProp='test-value' />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('test-child')).toHaveTextContent('test-value');
    });
  });

  describe('Error Handling', () => {
    it('should catch and display error fallback', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage='Component failed' />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.queryByTestId('no-error')).not.toBeInTheDocument();
    });

    it('should capture error with Sentry', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage='Sentry test error' />
        </ErrorBoundary>
      );

      expect(mockCaptureException).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Sentry test error',
        })
      );
    });

    it('should set Sentry context with error details', () => {
      render(
        <ErrorBoundary portal='admin' userId='user-123'>
          <ThrowError shouldThrow={true} errorMessage='Context test error' />
        </ErrorBoundary>
      );

      expect(mockWithScope).toHaveBeenCalled();
      expect(mockSetTag).toHaveBeenCalledWith('portal', 'admin');
      expect(mockSetUser).toHaveBeenCalledWith({ id: 'user-123' });
      expect(mockSetContext).toHaveBeenCalledWith('errorBoundary', {
        portal: 'admin',
        userId: 'user-123',
        timestamp: expect.any(String),
      });
    });
  });

  describe('Portal-Specific Error Handling', () => {
    const portals = [
      'admin',
      'customer',
      'technician',
      'reseller',
      'management-admin',
      'management-reseller',
      'tenant-portal',
    ];

    portals.forEach((portal) => {
      it(`should handle errors appropriately for ${portal} portal`, () => {
        render(
          <ErrorBoundary portal={portal}>
            <ThrowError shouldThrow={true} />
          </ErrorBoundary>
        );

        expect(mockSetTag).toHaveBeenCalledWith('portal', portal);
        expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
      });
    });

    it('should show portal-specific error messages', () => {
      render(
        <ErrorBoundary portal='customer'>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const errorElement = screen.getByTestId('error-boundary-fallback');
      expect(errorElement).toHaveAttribute('data-portal', 'customer');
    });
  });

  describe('Custom Error Fallback', () => {
    it('should render custom fallback component', () => {
      const CustomFallback = ({ error, resetError }: any) => (
        <div data-testid='custom-fallback'>
          <h2>Custom Error: {error.message}</h2>
          <button onClick={resetError} data-testid='custom-retry'>
            Try Again
          </button>
        </div>
      );

      render(
        <ErrorBoundary fallback={CustomFallback}>
          <ThrowError shouldThrow={true} errorMessage='Custom fallback test' />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByText('Custom Error: Custom fallback test')).toBeInTheDocument();
      expect(screen.getByTestId('custom-retry')).toBeInTheDocument();
    });

    it('should provide resetError function to custom fallback', () => {
      const CustomFallback = ({ resetError }: any) => (
        <div data-testid='custom-fallback'>
          <button onClick={resetError} data-testid='reset-button'>
            Reset
          </button>
        </div>
      );

      const { rerender } = render(
        <ErrorBoundary fallback={CustomFallback}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();

      // Click reset and re-render without error
      screen.getByTestId('reset-button').click();

      rerender(
        <ErrorBoundary fallback={CustomFallback}>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('no-error')).toBeInTheDocument();
    });
  });

  describe('Error Recovery', () => {
    it('should reset error state when children change', () => {
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();

      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('no-error')).toBeInTheDocument();
    });

    it('should provide retry functionality', () => {
      let shouldThrow = true;
      const RetryableComponent = () => {
        if (shouldThrow) {
          throw new Error('Retryable error');
        }
        return <div data-testid='success'>Success!</div>;
      };

      render(
        <ErrorBoundary showRetry={true}>
          <RetryableComponent />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
      expect(screen.getByTestId('retry-button')).toBeInTheDocument();

      // Simulate fixing the error and retrying
      shouldThrow = false;
      screen.getByTestId('retry-button').click();

      expect(screen.getByTestId('success')).toBeInTheDocument();
    });
  });

  describe('Development vs Production Behavior', () => {
    const originalNodeEnv = process.env.NODE_ENV;

    afterEach(() => {
      process.env.NODE_ENV = originalNodeEnv;
    });

    it('should show detailed error info in development', () => {
      process.env.NODE_ENV = 'development';

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage='Development error' />
        </ErrorBoundary>
      );

      const errorElement = screen.getByTestId('error-boundary-fallback');
      expect(errorElement).toHaveAttribute('data-environment', 'development');
      // In development, might show stack trace or detailed error info
    });

    it('should show generic error message in production', () => {
      process.env.NODE_ENV = 'production';

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage='Production error' />
        </ErrorBoundary>
      );

      const errorElement = screen.getByTestId('error-boundary-fallback');
      expect(errorElement).toHaveAttribute('data-environment', 'production');
      // Should not expose sensitive error details
    });
  });

  describe('Error Categorization', () => {
    it('should categorize network errors', () => {
      const NetworkError = () => {
        throw new Error('fetch failed');
      };

      render(
        <ErrorBoundary>
          <NetworkError />
        </ErrorBoundary>
      );

      expect(mockSetTag).toHaveBeenCalledWith('errorType', 'network');
    });

    it('should categorize rendering errors', () => {
      const RenderError = () => {
        throw new Error('Cannot read property of undefined');
      };

      render(
        <ErrorBoundary>
          <RenderError />
        </ErrorBoundary>
      );

      expect(mockSetTag).toHaveBeenCalledWith('errorType', 'render');
    });

    it('should categorize permission errors', () => {
      const PermissionError = () => {
        throw new Error('Access denied');
      };

      render(
        <ErrorBoundary>
          <PermissionError />
        </ErrorBoundary>
      );

      expect(mockSetTag).toHaveBeenCalledWith('errorType', 'permission');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes in error state', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const errorElement = screen.getByRole('alert');
      expect(errorElement).toHaveAttribute('aria-live', 'assertive');
      expect(errorElement).toBeInTheDocument();
    });

    it('should focus retry button when available', () => {
      render(
        <ErrorBoundary showRetry={true}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const retryButton = screen.getByTestId('retry-button');
      expect(retryButton).toHaveFocus();
    });

    it('should provide screen reader friendly error messages', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toHaveTextContent(/error occurred/i);
    });
  });

  describe('Performance Impact', () => {
    it('should not impact render performance when no errors occur', () => {
      const renderStart = performance.now();

      render(
        <ErrorBoundary>
          <div>No error component</div>
        </ErrorBoundary>
      );

      const renderEnd = performance.now();
      const renderTime = renderEnd - renderStart;

      // Should not add significant overhead
      expect(renderTime).toBeLessThan(100);
    });
  });

  describe('Error Boundary Nesting', () => {
    it('should handle nested error boundaries correctly', () => {
      render(
        <ErrorBoundary portal='admin'>
          <div>
            <ErrorBoundary portal='customer'>
              <ThrowError shouldThrow={true} />
            </ErrorBoundary>
          </div>
        </ErrorBoundary>
      );

      // Inner error boundary should catch the error
      expect(mockSetTag).toHaveBeenCalledWith('portal', 'customer');
      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
    });
  });

  describe('Integration with Monitoring', () => {
    it('should trigger monitoring hooks on error', () => {
      const mockOnError = jest.fn();

      render(
        <ErrorBoundary onError={mockOnError}>
          <ThrowError shouldThrow={true} errorMessage='Monitoring test' />
        </ErrorBoundary>
      );

      expect(mockOnError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Monitoring test',
        }),
        expect.any(Object)
      );
    });

    it('should include component stack in monitoring data', () => {
      const mockOnError = jest.fn();

      render(
        <ErrorBoundary onError={mockOnError}>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(mockSetContext).toHaveBeenCalledWith(
        'componentStack',
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      );
    });
  });
});
