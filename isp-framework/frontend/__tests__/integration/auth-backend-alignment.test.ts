/**
 * Authentication Backend Alignment Test
 * Verifies that frontend auth calls work with actual backend endpoints
 */

import { AuthApiClient } from '../../packages/headless/src/api/clients/AuthApiClient';

describe('Authentication Backend Alignment', () => {
  let authClient: AuthApiClient;
  const mockBaseURL = process.env.TEST_API_URL || 'http://localhost:8001/api/v1/identity';

  beforeEach(() => {
    authClient = new AuthApiClient(mockBaseURL);
  });

  describe('Endpoint Path Alignment', () => {
    it('should use correct paths for user profile endpoints', () => {
      // Test that the client methods use the correct backend paths
      const getCurrentUserSpy = jest.spyOn(authClient, 'request');
      
      // Mock the request method to just resolve without making actual calls
      getCurrentUserSpy.mockResolvedValue({
        data: { id: 'test-user', email: 'test@example.com' },
        success: true,
        message: 'Success'
      });

      // Test getCurrentUser uses /me (not /auth/me)
      authClient.getCurrentUser();
      expect(getCurrentUserSpy).toHaveBeenCalledWith('GET', '/me');

      // Test updateProfile uses PUT /me (not PATCH /auth/profile)
      authClient.updateProfile({ name: 'Test User' });
      expect(getCurrentUserSpy).toHaveBeenCalledWith('PUT', '/me', { name: 'Test User' });

      getCurrentUserSpy.mockRestore();
    });

    it('should use correct paths for authentication endpoints', () => {
      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockResolvedValue({
        data: { access_token: 'test-token' },
        success: true,
        message: 'Success'
      });

      // Test login uses /auth/login (correct)
      authClient.login({
        email: 'test@example.com',
        password: 'password',
        portal: 'admin'
      });
      expect(requestSpy).toHaveBeenCalledWith('POST', '/auth/login', {
        email: 'test@example.com',
        password: 'password',
        portal: 'admin'
      });

      // Test logout uses /auth/logout (correct)
      authClient.logout();
      expect(requestSpy).toHaveBeenCalledWith('POST', '/auth/logout');

      requestSpy.mockRestore();
    });
  });

  describe('Login Flow Integration', () => {
    it('should handle complete login flow with correct data structure', async () => {
      const mockLoginResponse = {
        data: {
          user: {
            id: 'user-123',
            email: 'admin@test.com',
            name: 'Test Admin',
            role: 'admin',
            permissions: ['read', 'write'],
            portal: 'admin',
            tenant_id: 'tenant-123',
            last_login: '2024-01-01T00:00:00Z'
          },
          tokens: {
            access_token: 'access-token-123',
            refresh_token: 'refresh-token-123',
            expires_at: Date.now() + 3600000,
            token_type: 'Bearer'
          },
          tenant: {
            id: 'tenant-123',
            name: 'Test Tenant',
            plan: 'enterprise',
            features: ['billing', 'analytics']
          },
          session: {
            id: 'session-123',
            expires_at: Date.now() + 86400000,
            ip_address: '127.0.0.1',
            user_agent: 'Test Browser'
          }
        },
        success: true,
        message: 'Login successful'
      };

      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockResolvedValue(mockLoginResponse);

      const result = await authClient.login({
        email: 'admin@test.com',
        password: 'password',
        portal: 'admin'
      });

      expect(result.success).toBe(true);
      expect(result.data?.user.email).toBe('admin@test.com');
      expect(result.data?.tokens.access_token).toBe('access-token-123');
      expect(result.data?.tenant.name).toBe('Test Tenant');

      requestSpy.mockRestore();
    });

    it('should handle login errors correctly', async () => {
      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockRejectedValue({
        response: {
          status: 401,
          data: { detail: 'Invalid email or password' }
        }
      });

      try {
        await authClient.login({
          email: 'wrong@test.com',
          password: 'wrongpassword',
          portal: 'admin'
        });
        // Should not reach here
        expect(true).toBe(false);
      } catch (error: any) {
        expect(error.response?.status).toBe(401);
        expect(error.response?.data?.detail).toBe('Invalid email or password');
      }

      requestSpy.mockRestore();
    });
  });

  describe('Portal-specific Login', () => {
    it('should support admin portal login', () => {
      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockResolvedValue({ data: {}, success: true, message: 'Success' });

      authClient.login({
        email: 'admin@test.com',
        password: 'password',
        portal: 'admin'
      });

      expect(requestSpy).toHaveBeenCalledWith('POST', '/auth/login', 
        expect.objectContaining({
          portal: 'admin'
        })
      );

      requestSpy.mockRestore();
    });

    it('should support customer portal login with portalId', () => {
      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockResolvedValue({ data: {}, success: true, message: 'Success' });

      authClient.login({
        portalId: 'CUST123456',
        password: 'password',
        portal: 'customer'
      });

      expect(requestSpy).toHaveBeenCalledWith('POST', '/auth/login',
        expect.objectContaining({
          portalId: 'CUST123456',
          portal: 'customer'
        })
      );

      requestSpy.mockRestore();
    });

    it('should support reseller portal login with partnerCode', () => {
      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockResolvedValue({ data: {}, success: true, message: 'Success' });

      authClient.login({
        partnerCode: 'RESELLER001',
        password: 'password',
        portal: 'reseller'
      });

      expect(requestSpy).toHaveBeenCalledWith('POST', '/auth/login',
        expect.objectContaining({
          partnerCode: 'RESELLER001',
          portal: 'reseller'
        })
      );

      requestSpy.mockRestore();
    });
  });

  describe('Token Management', () => {
    it('should handle token refresh correctly', async () => {
      const mockRefreshResponse = {
        data: {
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
          expires_at: Date.now() + 3600000,
          token_type: 'Bearer'
        },
        success: true,
        message: 'Token refreshed'
      };

      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockResolvedValue(mockRefreshResponse);

      const result = await authClient.refreshToken('refresh-token-123');

      expect(requestSpy).toHaveBeenCalledWith('POST', '/auth/refresh', {
        refresh_token: 'refresh-token-123'
      });
      expect(result.data?.access_token).toBe('new-access-token');

      requestSpy.mockRestore();
    });
  });

  describe('Session Management', () => {
    it('should get current user profile correctly', async () => {
      const mockUserResponse = {
        data: {
          id: 'user-123',
          email: 'admin@test.com',
          username: 'admin',
          first_name: 'Admin',
          last_name: 'User',
          full_name: 'Admin User',
          is_active: true,
          is_verified: true,
          last_login: '2024-01-01T00:00:00Z',
          tenant_id: 'tenant-123',
          created_at: '2023-01-01T00:00:00Z'
        },
        success: true,
        message: 'Profile retrieved'
      };

      const requestSpy = jest.spyOn(authClient, 'request');
      requestSpy.mockResolvedValue(mockUserResponse);

      const result = await authClient.getCurrentUser();

      expect(requestSpy).toHaveBeenCalledWith('GET', '/me');
      expect(result.data?.email).toBe('admin@test.com');
      expect(result.data?.full_name).toBe('Admin User');

      requestSpy.mockRestore();
    });
  });
});