import { TenantProvisioningService } from '../services/TenantProvisioningService';
import type { TenantProvisioningRequest } from '../types';
import { getApiClient } from '@dotmac/headless/api';

describe('TenantProvisioningService', () => {
  let service: TenantProvisioningService;
  let mockApiClient: any;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Get the mocked API client
    mockApiClient = (getApiClient as jest.Mock)();

    service = new TenantProvisioningService();
  });

  describe('provisionTenant', () => {
    it('should provision a tenant successfully', async () => {
      const mockRequest: TenantProvisioningRequest = {
        name: 'Test Tenant',
        slug: 'test-tenant',
        tier: 'basic',
        adminUser: {
          email: 'admin@test.com',
          firstName: 'Test',
          lastName: 'Admin',
        },
      };

      const mockResponse = {
        data: {
          requestId: 'req_123',
          status: {
            requestId: 'req_123',
            status: 'pending',
            progress: 0,
            currentStep: 'Initializing',
            steps: [],
          },
        },
      };

      mockApiClient.request.mockResolvedValueOnce(mockResponse);

      const requestId = await service.provisionTenant(mockRequest);

      expect(requestId).toBe('req_123');
      expect(mockApiClient.request).toHaveBeenCalledWith(
        '/api/v1/tenants/provision',
        {
          method: 'POST',
          body: JSON.stringify(mockRequest),
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
    });

    it('should handle provisioning errors', async () => {
      const mockRequest: TenantProvisioningRequest = {
        name: 'Test Tenant',
        slug: 'test-tenant',
        tier: 'basic',
        adminUser: {
          email: 'admin@test.com',
          firstName: 'Test',
          lastName: 'Admin',
        },
      };

      const mockError = new Error('Provisioning failed');
      mockApiClient.request.mockRejectedValueOnce(mockError);

      await expect(service.provisionTenant(mockRequest)).rejects.toThrow(
        'Failed to provision tenant: Provisioning failed'
      );
    });
  });

  describe('getTenant', () => {
    it('should retrieve tenant details', async () => {
      const tenantId = 'tenant_123';
      const mockTenant = {
        id: tenantId,
        name: 'Test Tenant',
        slug: 'test-tenant',
        status: 'active',
        tier: 'basic',
        features: [],
        settings: {},
        limits: {
          users: 10,
          storage: 1024 * 1024 * 1024,
          bandwidth: 10 * 1024 * 1024 * 1024,
          apiCalls: 10000,
          customDomains: 1,
          projects: 5,
        },
        metadata: {},
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      mockApiClient.request.mockResolvedValueOnce({
        data: mockTenant,
      });

      const result = await service.getTenant(tenantId);

      expect(result).toEqual(mockTenant);
      expect(mockApiClient.request).toHaveBeenCalledWith(
        `/api/v1/tenants/${tenantId}`,
        { method: 'GET' }
      );
    });
  });

  describe('listTenants', () => {
    it('should list tenants with pagination', async () => {
      const mockResponse = {
        data: {
          tenants: [
            {
              id: 'tenant_1',
              name: 'Tenant 1',
              slug: 'tenant-1',
              status: 'active',
              tier: 'basic',
            },
          ],
          pagination: {
            page: 1,
            size: 10,
            total: 1,
            totalPages: 1,
          },
        },
      };

      mockApiClient.request.mockResolvedValueOnce(mockResponse);

      const result = await service.listTenants({
        page: 1,
        size: 10,
        status: 'active',
      });

      expect(result).toEqual(mockResponse.data);
      expect(mockApiClient.request).toHaveBeenCalledWith(
        '/api/v1/tenants?page=1&size=10&status=active',
        { method: 'GET' }
      );
    });
  });

  describe('suspendTenant', () => {
    it('should suspend a tenant', async () => {
      const tenantId = 'tenant_123';
      const reason = 'Policy violation';

      mockApiClient.request.mockResolvedValueOnce({ data: {} });

      await service.suspendTenant(tenantId, reason);

      expect(mockApiClient.request).toHaveBeenCalledWith(
        `/api/v1/tenants/${tenantId}/suspend`,
        {
          method: 'POST',
          body: JSON.stringify({ reason }),
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
    });
  });

  describe('checkSlugAvailability', () => {
    it('should check if slug is available', async () => {
      const slug = 'test-tenant';
      const mockResponse = {
        data: {
          available: true,
        },
      };

      mockApiClient.request.mockResolvedValueOnce(mockResponse);

      const result = await service.checkSlugAvailability(slug);

      expect(result).toEqual({ available: true });
      expect(mockApiClient.request).toHaveBeenCalledWith(
        `/api/v1/tenants/check-slug/${encodeURIComponent(slug)}`,
        { method: 'GET' }
      );
    });

    it('should return suggestion when slug is unavailable', async () => {
      const slug = 'taken-slug';
      const mockResponse = {
        data: {
          available: false,
          suggestion: 'taken-slug-2',
        },
      };

      mockApiClient.request.mockResolvedValueOnce(mockResponse);

      const result = await service.checkSlugAvailability(slug);

      expect(result).toEqual({
        available: false,
        suggestion: 'taken-slug-2',
      });
    });
  });
});
