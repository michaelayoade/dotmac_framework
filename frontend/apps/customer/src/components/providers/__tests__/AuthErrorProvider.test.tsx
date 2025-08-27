/**
 * Integration Tests for AuthErrorProvider
 * Tests the new authentication error handling system
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import React from 'react';
import { AuthErrorProvider } from '../AuthErrorProvider';
import { useStandardErrorHandler } from '@dotmac/headless/hooks/useStandardErrorHandler';

// Mock Next.js router
jest.mock('next/navigation');
const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
};
(useRouter as jest.Mock).mockReturnValue(mockRouter);

// Mock platform error handler
const mockHandleError = jest.fn();
jest.mock('@dotmac/headless/hooks/useStandardErrorHandler', () => ({
  useStandardErrorHandler: () => ({
    handleError: mockHandleError,
  }),
}));

// Test component that can trigger auth errors
const TestComponent: React.FC<{ shouldTriggerError?: boolean; errorType?: string }> = ({
  shouldTriggerError = false,
  errorType = '401',
}) => {
  React.useEffect(() => {
    if (shouldTriggerError) {
      const error = { status: parseInt(errorType), message: `Error ${errorType}` };
      const event = new CustomEvent('auth-error', {
        detail: { error, context: 'Test authentication error' },
      });
      window.dispatchEvent(event);
    }
  }, [shouldTriggerError, errorType]);

  return <div data-testid="test-component">Test Component</div>;
};

// Component that throws errors for error boundary testing
const ErrorThrowingComponent: React.FC<{ errorMessage?: string }> = ({
  errorMessage = '401 Unauthorized',
}) => {
  throw new Error(errorMessage);
};

describe('AuthErrorProvider Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRouter.push.mockClear();
    mockHandleError.mockClear();
    
    // Clear sessionStorage
    sessionStorage.clear();
    
    // Mock window.location for JSDOM
    delete (window as any).location;
    (window as any).location = { pathname: '/dashboard', reload: jest.fn() };
  });

  describe('Authentication Error Event Handling', () => {
    it('should handle 401 authentication errors gracefully', async () => {
      render(
        <AuthErrorProvider>
          <TestComponent shouldTriggerError errorType="401" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 401,
            message: 'Error 401',
          }),
          'Authentication required'
        );
      });

      // Should store redirect path
      expect(sessionStorage.getItem('redirect_after_login')).toBe('/dashboard');
    });

    it('should handle 403 access denied errors', async () => {
      render(
        <AuthErrorProvider>
          <TestComponent shouldTriggerError errorType="403" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 403,
            message: 'Error 403',
          }),
          'Access denied'
        );
      });
    });

    it('should handle generic authentication errors', async () => {
      render(
        <AuthErrorProvider>
          <TestComponent shouldTriggerError errorType="500" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 500,
            message: 'Error 500',
          }),
          'Test authentication error'
        );
      });
    });

    it('should not store redirect path for login page', async () => {
      (window as any).location.pathname = '/login';
      
      render(
        <AuthErrorProvider>
          <TestComponent shouldTriggerError errorType="401" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalled();
      });

      expect(sessionStorage.getItem('redirect_after_login')).toBeNull();
    });
  });

  describe('Error Boundary Integration', () => {
    it('should catch 401 errors and show authentication UI', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      render(
        <AuthErrorProvider>
          <ErrorThrowingComponent errorMessage="401 Authentication required" />
        </AuthErrorProvider>
      );

      // Should show authentication required UI
      await waitFor(() => {
        expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      });

      expect(screen.getByText(/your session has expired/i)).toBeInTheDocument();
      expect(screen.getByText('Go to Login')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();

      consoleSpy.mockRestore();
    });

    it('should handle login button click', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      sessionStorage.setItem('redirect_after_login', '/dashboard');

      render(
        <AuthErrorProvider>
          <ErrorThrowingComponent errorMessage="401 Unauthorized" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('Go to Login')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Go to Login'));

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/login?redirect=%2Fdashboard');
      });

      consoleSpy.mockRestore();
    });

    it('should handle retry button click', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const reloadSpy = jest.spyOn(window.location, 'reload').mockImplementation();

      render(
        <AuthErrorProvider>
          <ErrorThrowingComponent errorMessage="401 Token expired" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry'));

      expect(reloadSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
      reloadSpy.mockRestore();
    });

    it('should redirect to login after delay for authentication errors', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      sessionStorage.setItem('redirect_after_login', '/dashboard');

      // Mock setTimeout to control timing
      jest.useFakeTimers();

      render(
        <AuthErrorProvider>
          <ErrorThrowingComponent errorMessage="401 Session expired" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      });

      // Fast-forward time
      jest.advanceTimersByTime(2000);

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/login?redirect=%2Fdashboard');
      });

      jest.useRealTimers();
      consoleSpy.mockRestore();
    });
  });

  describe('Normal Component Rendering', () => {
    it('should render children normally when no errors occur', () => {
      render(
        <AuthErrorProvider>
          <TestComponent />
        </AuthErrorProvider>
      );

      expect(screen.getByTestId('test-component')).toBeInTheDocument();
      expect(screen.getByText('Test Component')).toBeInTheDocument();
      expect(screen.queryByText('Authentication Required')).not.toBeInTheDocument();
    });

    it('should not interfere with normal component updates', () => {
      const { rerender } = render(
        <AuthErrorProvider>
          <div data-testid="content">Initial content</div>
        </AuthErrorProvider>
      );

      expect(screen.getByText('Initial content')).toBeInTheDocument();

      rerender(
        <AuthErrorProvider>
          <div data-testid="content">Updated content</div>
        </AuthErrorProvider>
      );

      expect(screen.getByText('Updated content')).toBeInTheDocument();
    });
  });

  describe('Event Cleanup', () => {
    it('should clean up event listeners on unmount', () => {
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');

      const { unmount } = render(
        <AuthErrorProvider>
          <TestComponent />
        </AuthErrorProvider>
      );

      expect(addEventListenerSpy).toHaveBeenCalledWith('auth-error', expect.any(Function));

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('auth-error', expect.any(Function));

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });

  describe('Platform Integration', () => {
    it('should integrate with platform error handling system', async () => {
      render(
        <AuthErrorProvider>
          <TestComponent shouldTriggerError errorType="401" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 401,
          }),
          'Authentication required'
        );
      });

      // Should use platform error handler, not custom implementation
      expect(mockHandleError).toHaveBeenCalledTimes(1);
    });

    it('should work with platform error boundary system', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      // Test that it works with @dotmac/headless error boundaries
      render(
        <AuthErrorProvider>
          <ErrorThrowingComponent errorMessage="Unauthorized access" />
        </AuthErrorProvider>
      );

      // Should catch and handle the error
      await waitFor(() => {
        expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      });

      // Should provide consistent error boundary interface
      expect(screen.getByRole('button', { name: 'Go to Login' })).toHaveAttribute('type', 'button');
      expect(screen.getByRole('button', { name: 'Retry' })).toHaveAttribute('type', 'button');

      consoleSpy.mockRestore();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes for error states', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      render(
        <AuthErrorProvider>
          <ErrorThrowingComponent errorMessage="401 Authentication failed" />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      });

      // Should be keyboard accessible
      const loginButton = screen.getByText('Go to Login');
      const retryButton = screen.getByText('Retry');

      expect(loginButton).toHaveAttribute('type', 'button');
      expect(retryButton).toHaveAttribute('type', 'button');

      // Should be focusable
      loginButton.focus();
      expect(document.activeElement).toBe(loginButton);

      consoleSpy.mockRestore();
    });

    it('should support keyboard navigation', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      render(
        <AuthErrorProvider>
          <ErrorThrowingComponent />
        </AuthErrorProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('Go to Login')).toBeInTheDocument();
      });

      // Tab navigation should work
      const loginButton = screen.getByText('Go to Login');
      const retryButton = screen.getByText('Retry');

      loginButton.focus();
      expect(document.activeElement).toBe(loginButton);

      fireEvent.keyDown(loginButton, { key: 'Tab' });
      expect(document.activeElement).toBe(retryButton);

      consoleSpy.mockRestore();
    });
  });
});