/**
 * API Contract Testing Suite
 * Validates API contracts and ensures backward compatibility
 */

import { test, expect } from '@playwright/test';
import { APIContractValidator } from '../utils/api-contract-validator';
import { OpenAPISpecValidator } from '../utils/openapi-spec-validator';

test.describe('API Contract Validation', () => {
  let contractValidator: APIContractValidator;
  let specValidator: OpenAPISpecValidator;

  test.beforeAll(async () => {
    contractValidator = new APIContractValidator({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: 30000
    });

    specValidator = new OpenAPISpecValidator({
      specPath: './openapi-spec.yaml'
    });
  });

  test('OpenAPI Specification is Valid', async () => {
    const validationResult = await specValidator.validateSpec();

    expect(validationResult.isValid).toBe(true);
    expect(validationResult.errors).toHaveLength(0);

    if (validationResult.warnings.length > 0) {
      console.warn('OpenAPI Spec Warnings:', validationResult.warnings);
    }
  });

  test.describe('Authentication Endpoints', () => {
    test('POST /auth/login contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'POST',
        '/auth/login',
        {
          requiredFields: ['email', 'password'],
          responseFields: ['access_token', 'refresh_token', 'user', 'expires_in'],
          statusCodes: [200, 400, 401, 429]
        }
      );

      expect(contract.isValid).toBe(true);
      expect(contract.coverage).toBeGreaterThanOrEqual(80);
    });

    test('POST /auth/refresh contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'POST',
        '/auth/refresh',
        {
          requiredFields: ['refresh_token'],
          responseFields: ['access_token', 'expires_in'],
          statusCodes: [200, 400, 401]
        }
      );

      expect(contract.isValid).toBe(true);
    });

    test('POST /auth/logout contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'POST',
        '/auth/logout',
        {
          requiredHeaders: ['Authorization'],
          statusCodes: [200, 401]
        }
      );

      expect(contract.isValid).toBe(true);
    });
  });

  test.describe('User Management Endpoints', () => {
    test('GET /users/profile contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'GET',
        '/users/profile',
        {
          requiredHeaders: ['Authorization'],
          responseFields: ['id', 'email', 'name', 'role', 'tenant_id'],
          statusCodes: [200, 401, 403]
        }
      );

      expect(contract.isValid).toBe(true);
    });

    test('PUT /users/profile contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'PUT',
        '/users/profile',
        {
          requiredHeaders: ['Authorization'],
          optionalFields: ['name', 'phone', 'preferences'],
          responseFields: ['id', 'email', 'name', 'updated_at'],
          statusCodes: [200, 400, 401, 403]
        }
      );

      expect(contract.isValid).toBe(true);
    });
  });

  test.describe('Tenant Management Endpoints', () => {
    test('GET /tenants contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'GET',
        '/tenants',
        {
          requiredHeaders: ['Authorization'],
          queryParams: ['page', 'limit', 'search'],
          responseFields: ['data', 'pagination', 'total'],
          statusCodes: [200, 401, 403]
        }
      );

      expect(contract.isValid).toBe(true);
    });

    test('POST /tenants contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'POST',
        '/tenants',
        {
          requiredHeaders: ['Authorization'],
          requiredFields: ['name', 'domain'],
          optionalFields: ['description', 'settings'],
          responseFields: ['id', 'name', 'domain', 'created_at'],
          statusCodes: [201, 400, 401, 403]
        }
      );

      expect(contract.isValid).toBe(true);
    });
  });

  test.describe('Network Management Endpoints', () => {
    test('GET /network/devices contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'GET',
        '/network/devices',
        {
          requiredHeaders: ['Authorization'],
          queryParams: ['status', 'type', 'page', 'limit'],
          responseFields: ['data', 'pagination', 'total'],
          statusCodes: [200, 401, 403]
        }
      );

      expect(contract.isValid).toBe(true);
    });

    test('POST /network/devices contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'POST',
        '/network/devices',
        {
          requiredHeaders: ['Authorization'],
          requiredFields: ['name', 'ip_address', 'device_type'],
          optionalFields: ['description', 'location', 'config'],
          responseFields: ['id', 'name', 'ip_address', 'status'],
          statusCodes: [201, 400, 401, 403]
        }
      );

      expect(contract.isValid).toBe(true);
    });
  });

  test.describe('Billing Endpoints', () => {
    test('GET /billing/invoices contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'GET',
        '/billing/invoices',
        {
          requiredHeaders: ['Authorization'],
          queryParams: ['status', 'page', 'limit'],
          responseFields: ['data', 'pagination', 'total', 'summary'],
          statusCodes: [200, 401, 403]
        }
      );

      expect(contract.isValid).toBe(true);
    });

    test('POST /billing/payment contract compliance', async () => {
      const contract = await contractValidator.validateEndpointContract(
        'POST',
        '/billing/payment',
        {
          requiredHeaders: ['Authorization'],
          requiredFields: ['amount', 'currency', 'payment_method_id'],
          optionalFields: ['description', 'invoice_id'],
          responseFields: ['payment_id', 'status', 'transaction_id'],
          statusCodes: [200, 400, 401, 403, 402]
        }
      );

      expect(contract.isValid).toBe(true);
    });
  });

  test.describe('Real-time WebSocket Contracts', () => {
    test('WebSocket connection contract', async () => {
      const wsContract = await contractValidator.validateWebSocketContract(
        '/ws/notifications',
        {
          requiredHeaders: ['Authorization'],
          supportedMessageTypes: ['notification', 'update', 'error'],
          heartbeatInterval: 30000
        }
      );

      expect(wsContract.isValid).toBe(true);
    });
  });

  test.describe('Error Response Contracts', () => {
    test('400 Bad Request error contract', async () => {
      const errorContract = await contractValidator.validateErrorContract(
        400,
        {
          requiredFields: ['error', 'message'],
          optionalFields: ['details', 'field_errors'],
          contentType: 'application/json'
        }
      );

      expect(errorContract.isValid).toBe(true);
    });

    test('401 Unauthorized error contract', async () => {
      const errorContract = await contractValidator.validateErrorContract(
        401,
        {
          requiredFields: ['error', 'message'],
          optionalFields: ['login_url'],
          contentType: 'application/json'
        }
      );

      expect(errorContract.isValid).toBe(true);
    });

    test('403 Forbidden error contract', async () => {
      const errorContract = await contractValidator.validateErrorContract(
        403,
        {
          requiredFields: ['error', 'message'],
          optionalFields: ['required_permissions'],
          contentType: 'application/json'
        }
      );

      expect(errorContract.isValid).toBe(true);
    });

    test('404 Not Found error contract', async () => {
      const errorContract = await contractValidator.validateErrorContract(
        404,
        {
          requiredFields: ['error', 'message'],
          contentType: 'application/json'
        }
      );

      expect(errorContract.isValid).toBe(true);
    });

    test('500 Internal Server Error contract', async () => {
      const errorContract = await contractValidator.validateErrorContract(
        500,
        {
          requiredFields: ['error', 'message'],
          optionalFields: ['request_id', 'timestamp'],
          contentType: 'application/json'
        }
      );

      expect(errorContract.isValid).toBe(true);
    });
  });

  test.describe('Rate Limiting Contracts', () => {
    test('Rate limit headers contract', async () => {
      const rateLimitContract = await contractValidator.validateRateLimitContract({
        requiredHeaders: ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'],
        statusCode: 429,
        retryAfterHeader: true
      });

      expect(rateLimitContract.isValid).toBe(true);
    });
  });

  test.describe('Pagination Contracts', () => {
    test('List endpoint pagination contract', async () => {
      const paginationContract = await contractValidator.validatePaginationContract({
        requiredQueryParams: ['page', 'limit'],
        responseFields: ['data', 'pagination'],
        paginationFields: ['page', 'limit', 'total', 'total_pages'],
        maxLimit: 100,
        defaultLimit: 20
      });

      expect(paginationContract.isValid).toBe(true);
    });
  });

  test.describe('Version Compatibility', () => {
    test('API version headers contract', async () => {
      const versionContract = await contractValidator.validateVersionContract({
        versionHeader: 'X-API-Version',
        supportedVersions: ['v1', 'v2'],
        defaultVersion: 'v1',
        deprecationWarnings: true
      });

      expect(versionContract.isValid).toBe(true);
    });
  });
});
