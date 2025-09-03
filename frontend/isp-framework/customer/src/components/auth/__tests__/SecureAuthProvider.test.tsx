/**
 * Unit Tests for SecureAuthProvider
 * Tests authentication context, token refresh, and state management
 */

import { act, render, screen, waitFor } from '@testing-library/react';
import type React from 'react';
import { secureTokenManager } from '../../lib/auth/secureTokenManager';
import { SecureAuthProvider, useSecureAuth } from '../SecureAuthProvider';

// Mock the secure token manager
jest.mock('../../lib/auth/secureTokenManager');

const mockSecureTokenManager = secureTokenManager as jest.Mocked<typeof secureTokenManager>;

// Test component to access auth context
const TestComponent: React.FC = () => {
  const { user, isAuthenticated, isLoading, login, logout } = useSecureAuth();

  return (
    <div>
      <div data-testid='auth-status'>
        {isLoading ? 'loading' : isAuthenticated ? 'authenticated' : 'unauthenticated'}
      </div>
      <div data-testid='user-email'>{user?.email || 'no-user'}</div>
      <button
        data-testid='login-btn'
        onClick={() => login({ email: 'test@example.com', password: 'password' })}
      >
        Login
      </button>
      <button data-testid='logout-btn' onClick={logout}>
        Logout
      </button>
    </div>
  );
};

const renderWithProvider = (children: React.ReactNode) => {
  return render(<SecureAuthProvider>{children}</SecureAuthProvider>);
};

describe('SecureAuthProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Initial State', () => {
    it('should start with unauthenticated state', () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: false,
        error: 'Not authenticated',
      });

      renderWithProvider(<TestComponent />);

      expect(screen.getByTestId('auth-status')).toHaveTextContent('loading');
    });

    it('should check for existing authentication on mount', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: true,
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
      });

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
        expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
      });

      expect(mockSecureTokenManager.getCurrentUser).toHaveBeenCalled();
    });
  });

  describe('Login Flow', () => {
    it('should successfully login user', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: false,
        error: 'Not authenticated',
      });

      mockSecureTokenManager.login.mockResolvedValue({
        success: true,
        accessToken: 'test-token',
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
      });

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
      });

      await act(async () => {
        screen.getByTestId('login-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
        expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
      });

      expect(mockSecureTokenManager.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password',
      });
    });

    it('should handle login failure', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: false,
        error: 'Not authenticated',
      });

      mockSecureTokenManager.login.mockResolvedValue({
        success: false,
        error: 'Invalid credentials',
      });

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
      });

      await act(async () => {
        screen.getByTestId('login-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
        expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
      });
    });
  });

  describe('Logout Flow', () => {
    it('should successfully logout user', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: true,
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
      });

      mockSecureTokenManager.logout.mockResolvedValue({
        success: true,
      });

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });

      await act(async () => {
        screen.getByTestId('logout-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
        expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
      });

      expect(mockSecureTokenManager.logout).toHaveBeenCalled();
    });
  });

  describe('Token Refresh', () => {
    it('should automatically refresh tokens every 14 minutes', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: true,
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
      });

      mockSecureTokenManager.refreshToken.mockResolvedValue({
        success: true,
        accessToken: 'new-token',
      });

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });

      // Fast-forward 14 minutes
      act(() => {
        jest.advanceTimersByTime(14 * 60 * 1000);
      });

      await waitFor(() => {
        expect(mockSecureTokenManager.refreshToken).toHaveBeenCalled();
      });
    });

    it('should handle token refresh failure by logging out', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: true,
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
      });

      mockSecureTokenManager.refreshToken.mockResolvedValue({
        success: false,
        error: 'Token expired',
      });

      mockSecureTokenManager.logout.mockResolvedValue({
        success: true,
      });

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });

      // Fast-forward 14 minutes
      act(() => {
        jest.advanceTimersByTime(14 * 60 * 1000);
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
      });

      expect(mockSecureTokenManager.refreshToken).toHaveBeenCalled();
      expect(mockSecureTokenManager.logout).toHaveBeenCalled();
    });

    it('should not refresh tokens when user is not authenticated', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: false,
        error: 'Not authenticated',
      });

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
      });

      // Fast-forward 14 minutes
      act(() => {
        jest.advanceTimersByTime(14 * 60 * 1000);
      });

      // Should not call refresh when not authenticated
      expect(mockSecureTokenManager.refreshToken).not.toHaveBeenCalled();
    });
  });

  describe('Context Error Handling', () => {
    it('should throw error when useSecureAuth is used outside provider', () => {
      const spy = jest.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => render(<TestComponent />)).toThrow(
        'useSecureAuth must be used within a SecureAuthProvider'
      );

      spy.mockRestore();
    });
  });

  describe('Cleanup', () => {
    it('should clear refresh timer on unmount', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: true,
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User',
        },
      });

      const { unmount } = renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });

      unmount();

      // Fast-forward 14 minutes after unmount
      act(() => {
        jest.advanceTimersByTime(14 * 60 * 1000);
      });

      // Should not call refresh after unmount
      expect(mockSecureTokenManager.refreshToken).not.toHaveBeenCalled();
    });
  });

  describe('Loading States', () => {
    it('should show loading state during login', async () => {
      mockSecureTokenManager.getCurrentUser.mockResolvedValue({
        success: false,
        error: 'Not authenticated',
      });

      let loginResolve: (value: any) => void;
      mockSecureTokenManager.login.mockImplementation(
        () =>
          new Promise((resolve) => {
            loginResolve = resolve;
          })
      );

      renderWithProvider(<TestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('unauthenticated');
      });

      act(() => {
        screen.getByTestId('login-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('loading');
      });

      act(() => {
        loginResolve!({
          success: true,
          user: { id: '123', email: 'test@example.com', name: 'Test User' },
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      });
    });
  });
});
