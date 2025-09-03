/**
 * @jest-environment jsdom
 */

import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '../authStore';

// Mock fetch for API calls
global.fetch = jest.fn();

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset the store state before each test
    useAuthStore.getState().logout();
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  afterEach(() => {
    jest.clearAllTimers();
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.sessionExpiry).toBeNull();
      expect(result.current.lastActivity).toBeNull();
    });
  });

  describe('Login Flow', () => {
    it('should handle successful login', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin' as const,
        permissions: ['read', 'write'],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          user: mockUser,
          expiresAt: Date.now() + 3600000, // 1 hour
        }),
      });

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.sessionExpiry).toBeTruthy();
      expect(result.current.lastActivity).toBeTruthy();
    });

    it('should handle login failure', async () => {
      const errorMessage = 'Invalid credentials';

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          success: false,
          error: errorMessage,
        }),
      });

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        try {
          await result.current.login({
            email: 'test@example.com',
            password: 'wrongpassword',
          });
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe(errorMessage);
    });

    it('should set loading state during login', async () => {
      let resolveLogin: (value: any) => void;
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve;
      });

      (global.fetch as jest.Mock).mockImplementation(() => loginPromise);

      const { result } = renderHook(() => useAuthStore());

      // Start login
      act(() => {
        result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      // Should be loading
      expect(result.current.isLoading).toBe(true);

      // Resolve the login
      await act(async () => {
        resolveLogin!({
          ok: true,
          json: async () => ({
            success: true,
            user: { id: '1', email: 'test@example.com', name: 'Test' },
            expiresAt: Date.now() + 3600000,
          }),
        });
      });

      expect(result.current.isLoading).toBe(false);
    });

    it('should handle network errors during login', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        try {
          await result.current.login({
            email: 'test@example.com',
            password: 'password123',
          });
        } catch (error) {
          // Expected to throw
        }
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.error).toBe('Network error');
    });
  });

  describe('Logout Flow', () => {
    it('should clear user state on logout', async () => {
      const { result } = renderHook(() => useAuthStore());

      // Set up authenticated state first
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test User',
            role: 'admin',
            permissions: ['read'],
          },
          isAuthenticated: true,
          sessionExpiry: Date.now() + 3600000,
          lastActivity: Date.now(),
        });
      });
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.sessionExpiry).toBeNull();
      expect(result.current.lastActivity).toBeNull();
      expect(result.current.error).toBeNull();
    });

    it('should handle logout API call failure gracefully', async () => {
      const { result } = renderHook(() => useAuthStore());

      // Set up authenticated state
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test',
            role: 'admin',
            permissions: [],
          },
          isAuthenticated: true,
        });
      });
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await act(async () => {
        await result.current.logout();
      });

      // Should still clear local state even if API call fails
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('Session Management', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it('should validate session expiry', () => {
      const { result } = renderHook(() => useAuthStore());

      // Set session to expire in the past
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test',
            role: 'admin',
            permissions: [],
          },
          isAuthenticated: true,
          sessionExpiry: Date.now() - 1000, // Expired 1 second ago
        });
      });

      const isValid = result.current.isSessionValid();
      expect(isValid).toBe(false);
    });

    it('should validate unexpired session', () => {
      const { result } = renderHook(() => useAuthStore());

      // Set session to expire in the future
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test',
            role: 'admin',
            permissions: [],
          },
          isAuthenticated: true,
          sessionExpiry: Date.now() + 3600000, // Expires in 1 hour
        });
      });

      const isValid = result.current.isSessionValid();
      expect(isValid).toBe(true);
    });

    it('should update activity timestamp', () => {
      const { result } = renderHook(() => useAuthStore());

      const beforeActivity = Date.now();

      act(() => {
        result.current.updateActivity();
      });

      expect(result.current.lastActivity).toBeGreaterThanOrEqual(beforeActivity);
    });

    it('should refresh token before expiry', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          expiresAt: Date.now() + 7200000, // 2 hours
        }),
      });

      const { result } = renderHook(() => useAuthStore());

      // Set up authenticated state with session expiring soon
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test',
            role: 'admin',
            permissions: [],
          },
          isAuthenticated: true,
          sessionExpiry: Date.now() + 300000, // 5 minutes
        });
      });

      await act(async () => {
        await result.current.refreshToken();
      });

      // Should have updated session expiry
      expect(result.current.sessionExpiry).toBeGreaterThan(Date.now() + 3600000);
    });

    it('should handle refresh token failure', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          success: false,
          error: 'Token expired',
        }),
      });

      const { result } = renderHook(() => useAuthStore());

      // Set up authenticated state
      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test',
            role: 'admin',
            permissions: [],
          },
          isAuthenticated: true,
          sessionExpiry: Date.now() + 300000,
        });
      });

      await act(async () => {
        try {
          await result.current.refreshToken();
        } catch (error) {
          // Expected to throw
        }
      });

      // Should logout user on refresh failure
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('Permission Checks', () => {
    it('should check user permissions correctly', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test User',
            role: 'admin',
            permissions: ['read', 'write', 'delete'],
          },
          isAuthenticated: true,
        });
      });

      expect(result.current.hasPermission('read')).toBe(true);
      expect(result.current.hasPermission('write')).toBe(true);
      expect(result.current.hasPermission('admin')).toBe(false);
      expect(result.current.hasPermission('nonexistent')).toBe(false);
    });

    it('should return false for permissions when not authenticated', () => {
      const { result } = renderHook(() => useAuthStore());

      expect(result.current.hasPermission('read')).toBe(false);
      expect(result.current.hasPermission('write')).toBe(false);
    });

    it('should check multiple permissions with hasAnyPermission', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test User',
            role: 'admin',
            permissions: ['read', 'write'],
          },
          isAuthenticated: true,
        });
      });

      expect(result.current.hasAnyPermission(['read', 'admin'])).toBe(true);
      expect(result.current.hasAnyPermission(['admin', 'superuser'])).toBe(false);
    });

    it('should check all permissions with hasAllPermissions', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test User',
            role: 'admin',
            permissions: ['read', 'write', 'delete'],
          },
          isAuthenticated: true,
        });
      });

      expect(result.current.hasAllPermissions(['read', 'write'])).toBe(true);
      expect(result.current.hasAllPermissions(['read', 'write', 'admin'])).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('should clear errors when clearing error state', () => {
      const { result } = renderHook(() => useAuthStore());

      act(() => {
        useAuthStore.setState({
          error: 'Some error occurred',
        });
      });

      expect(result.current.error).toBe('Some error occurred');

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it('should handle malformed API responses gracefully', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}), // Missing required fields
      });

      const { result } = renderHook(() => useAuthStore());

      await act(async () => {
        try {
          await result.current.login({
            email: 'test@example.com',
            password: 'password123',
          });
        } catch (error) {
          // Expected to handle gracefully
        }
      });

      expect(result.current.isAuthenticated).toBe(false);
    });
  });
});
