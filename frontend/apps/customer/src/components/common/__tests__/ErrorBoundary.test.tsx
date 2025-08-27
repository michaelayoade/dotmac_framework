/**
 * Component Tests for CustomerErrorBoundary
 * Tests error handling, recovery, and reporting functionality
 */

import { fireEvent, render, screen } from '@testing-library/react';
import type React from 'react';
import CustomerErrorBoundary, {
  ApplicationErrorBoundary,
  ComponentErrorBoundary,
  PageErrorBoundary,
} from '../ErrorBoundary';

// Mock console methods to prevent noise in tests
const originalError = console.error;
const originalLog = console.log;

beforeAll(() => {
  console.error = jest.fn();
  console.log = jest.fn();
});

afterAll(() => {
  console.error = originalError;
  console.log = originalLog;
});

// Mock window.location
const mockLocation = {
  reload: jest.fn(),
  href: '/',
};
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

// Mock window.gtag
Object.defineProperty(window, 'gtag', {
  value: jest.fn(),
  writable: true,
});

// Test component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean; errorMessage?: string }> = ({
  shouldThrow = false,
  errorMessage = 'Test error',
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div data-testid="success">Component rendered successfully</div>;
};

describe('CustomerErrorBoundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocation.reload.mockClear();
    (window.gtag as jest.Mock).mockClear();
  });

  describe('Normal Operation', () => {
    it('should render children when no error occurs', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError />
        </CustomerErrorBoundary>
      );

      expect(screen.getByTestId('success')).toBeInTheDocument();
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });

    it('should not interfere with normal component updates', () => {
      const { rerender } = render(
        <CustomerErrorBoundary>
          <div data-testid="content">Initial content</div>
        </CustomerErrorBoundary>
      );

      expect(screen.getByTestId('content')).toHaveTextContent('Initial content');

      rerender(
        <CustomerErrorBoundary>
          <div data-testid="content">Updated content</div>
        </CustomerErrorBoundary>
      );

      expect(screen.getByTestId('content')).toHaveTextContent('Updated content');
    });
  });

  describe('Error Handling', () => {
    it('should catch and display error when child component throws', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow errorMessage="Test component error" />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByText(/we encountered an unexpected error/i)).toBeInTheDocument();
      expect(screen.queryByTestId('success')).not.toBeInTheDocument();
    });

    it('should display error details in development mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow errorMessage="Development error details" />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/error details \(development only\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Error: Development error details/)).toBeInTheDocument();

      process.env.NODE_ENV = originalEnv;
    });

    it('should not display error details in production mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow errorMessage="Production error" />
        </CustomerErrorBoundary>
      );

      expect(screen.queryByText(/error details/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Production error/)).not.toBeInTheDocument();

      process.env.NODE_ENV = originalEnv;
    });

    it('should generate unique error ID for each error', () => {
      const { unmount } = render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow errorMessage="First error" />
        </CustomerErrorBoundary>
      );

      const firstErrorId = screen.getByText(/error id:/i).textContent;
      unmount();

      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow errorMessage="Second error" />
        </CustomerErrorBoundary>
      );

      const secondErrorId = screen.getByText(/error id:/i).textContent;
      expect(firstErrorId).not.toBe(secondErrorId);
    });
  });

  describe('Error Boundary Levels', () => {
    it('should display appropriate title for component level errors', () => {
      render(
        <CustomerErrorBoundary level="component">
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.queryByText(/application error/i)).not.toBeInTheDocument();
    });

    it('should display appropriate title for application level errors', () => {
      render(
        <CustomerErrorBoundary level="application">
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/application error/i)).toBeInTheDocument();
      expect(
        screen.getByText(/the application encountered an unexpected error/i)
      ).toBeInTheDocument();
    });

    it('should show different recovery options based on error level', () => {
      const { rerender } = render(
        <CustomerErrorBoundary level="component">
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/try again/i)).toBeInTheDocument();
      expect(screen.getByText(/go to dashboard/i)).toBeInTheDocument();

      rerender(
        <CustomerErrorBoundary level="application">
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.queryByText(/try again/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/go to dashboard/i)).not.toBeInTheDocument();
    });
  });

  describe('Recovery Actions', () => {
    it('should allow retry for component level errors', () => {
      let shouldThrow = true;
      const TestComponent = () => <ThrowError shouldThrow={shouldThrow} />;

      const { rerender } = render(
        <CustomerErrorBoundary level="component">
          <TestComponent />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      // Simulate fixing the error
      shouldThrow = false;

      fireEvent.click(screen.getByText(/try again/i));

      // The component should reset its error state
      rerender(
        <CustomerErrorBoundary level="component">
          <TestComponent />
        </CustomerErrorBoundary>
      );

      // After rerender, the error boundary should be reset
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });

    it('should reload page when reload button is clicked', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      fireEvent.click(screen.getByText(/reload page/i));
      expect(mockLocation.reload).toHaveBeenCalled();
    });

    it('should navigate to dashboard when dashboard button is clicked', () => {
      render(
        <CustomerErrorBoundary level="component">
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      fireEvent.click(screen.getByText(/go to dashboard/i));
      expect(mockLocation.href).toBe('/dashboard');
    });
  });

  describe('Error Reporting', () => {
    it('should report error to analytics when gtag is available', () => {
      render(
        <CustomerErrorBoundary level="component">
          <ThrowError shouldThrow errorMessage="Analytics test error" />
        </CustomerErrorBoundary>
      );

      expect(window.gtag).toHaveBeenCalledWith(
        'event',
        'exception',
        expect.objectContaining({
          description: 'Error: Analytics test error',
          fatal: false,
          error_id: expect.any(String),
        })
      );
    });

    it('should mark application level errors as fatal', () => {
      render(
        <CustomerErrorBoundary level="application">
          <ThrowError shouldThrow errorMessage="Fatal error" />
        </CustomerErrorBoundary>
      );

      expect(window.gtag).toHaveBeenCalledWith(
        'event',
        'exception',
        expect.objectContaining({
          fatal: true,
        })
      );
    });

    it('should call custom error handler when provided', () => {
      const customErrorHandler = jest.fn();

      render(
        <CustomerErrorBoundary onError={customErrorHandler}>
          <ThrowError shouldThrow errorMessage="Custom handler test" />
        </CustomerErrorBoundary>
      );

      expect(customErrorHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Custom handler test',
        }),
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      );
    });

    it('should log structured error report to console', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow errorMessage="Console logging test" />
        </CustomerErrorBoundary>
      );

      expect(console.error).toHaveBeenCalledWith(
        '[CustomerErrorBoundary] Error report:',
        expect.objectContaining({
          timestamp: expect.any(String),
          errorId: expect.any(String),
          level: 'component',
          error: expect.objectContaining({
            name: 'Error',
            message: 'Console logging test',
          }),
        })
      );
    });
  });

  describe('Custom Fallback', () => {
    it('should render custom fallback when provided', () => {
      const customFallback = <div data-testid="custom-fallback">Custom Error UI</div>;

      render(
        <CustomerErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByText('Custom Error UI')).toBeInTheDocument();
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });
  });

  describe('Support Contact', () => {
    it('should display support contact information', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/if this problem persists/i)).toBeInTheDocument();
      expect(screen.getByText(/email support/i)).toBeInTheDocument();
    });

    it('should include error ID in support email', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      const supportLink = screen.getByText(/email support/i);
      const href = supportLink.getAttribute('href');

      expect(href).toContain('mailto:support@dotmac.com');
      expect(href).toContain('subject=Customer Portal Error');
      expect(href).toContain('body=Error ID:');
    });
  });

  describe('Convenience Wrapper Components', () => {
    it('should create ComponentErrorBoundary with correct level', () => {
      render(
        <ComponentErrorBoundary>
          <ThrowError shouldThrow />
        </ComponentErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByText(/try again/i)).toBeInTheDocument();
    });

    it('should create PageErrorBoundary with correct level', () => {
      render(
        <PageErrorBoundary>
          <ThrowError shouldThrow />
        </PageErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });

    it('should create ApplicationErrorBoundary with correct level', () => {
      render(
        <ApplicationErrorBoundary>
          <ThrowError shouldThrow />
        </ApplicationErrorBoundary>
      );

      expect(screen.getByText(/application error/i)).toBeInTheDocument();
      expect(screen.queryByText(/try again/i)).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      const errorContainer = screen.getByRole('alert', { hidden: true });
      expect(errorContainer).toBeInTheDocument();
    });

    it('should be keyboard navigable', () => {
      render(
        <CustomerErrorBoundary level="component">
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      const tryAgainButton = screen.getByText(/try again/i);
      const reloadButton = screen.getByText(/reload page/i);
      const dashboardButton = screen.getByText(/go to dashboard/i);

      expect(tryAgainButton).toHaveAttribute('tabIndex', '0');
      expect(reloadButton).toHaveAttribute('tabIndex', '0');
      expect(dashboardButton).toHaveAttribute('tabIndex', '0');
    });

    it('should announce errors to screen readers', () => {
      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      // The error message should be in an element with role="alert" or aria-live
      const errorMessage = screen.getByText(/we encountered an unexpected error/i);
      expect(errorMessage.closest('[role="alert"]')).toBeTruthy();
    });
  });

  describe('Edge Cases', () => {
    it('should handle errors during error reporting gracefully', () => {
      // Mock gtag to throw an error
      (window.gtag as jest.Mock).mockImplementation(() => {
        throw new Error('Analytics error');
      });

      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      // Should still render error boundary UI despite analytics failure
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(console.error).toHaveBeenCalledWith(
        '[CustomerErrorBoundary] Failed to report error:',
        expect.any(Error)
      );
    });

    it('should handle missing window.gtag gracefully', () => {
      const originalGtag = window.gtag;
      delete (window as any).gtag;

      render(
        <CustomerErrorBoundary>
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      // Restore gtag
      (window as any).gtag = originalGtag;
    });

    it('should reset error state properly', () => {
      const { rerender } = render(
        <CustomerErrorBoundary key="1">
          <ThrowError shouldThrow />
        </CustomerErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      // Rerender with a different key to reset the error boundary
      rerender(
        <CustomerErrorBoundary key="2">
          <ThrowError shouldThrow={false} />
        </CustomerErrorBoundary>
      );

      expect(screen.getByTestId('success')).toBeInTheDocument();
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });
  });
});
