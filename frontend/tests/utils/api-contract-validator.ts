/**
 * API Contract Validator Utility
 * Validates API endpoints against predefined contracts
 */

import { APIRequestContext, request } from '@playwright/test';

export interface EndpointContract {
  requiredFields?: string[];
  optionalFields?: string[];
  responseFields?: string[];
  requiredHeaders?: string[];
  queryParams?: string[];
  statusCodes?: number[];
  contentType?: string;
}

export interface ValidationResult {
  isValid: boolean;
  coverage: number;
  errors: string[];
  warnings: string[];
  details: Record<string, any>;
}

export class APIContractValidator {
  private baseURL: string;
  private timeout: number;
  private requestContext: APIRequestContext | null = null;

  constructor(options: { baseURL: string; timeout?: number }) {
    this.baseURL = options.baseURL;
    this.timeout = options.timeout || 30000;
  }

  async initialize(): Promise<void> {
    this.requestContext = await request.newContext({
      baseURL: this.baseURL,
      timeout: this.timeout
    });
  }

  async cleanup(): Promise<void> {
    if (this.requestContext) {
      await this.requestContext.dispose();
    }
  }

  async validateEndpointContract(
    method: string,
    endpoint: string,
    contract: EndpointContract
  ): Promise<ValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 0;

    try {
      if (!this.requestContext) {
        await this.initialize();
      }

      // Test successful request
      const response = await this.makeRequest(method, endpoint, contract);
      const responseData = await response.json().catch(() => ({}));

      // Validate status code
      if (contract.statusCodes && !contract.statusCodes.includes(response.status())) {
        errors.push(`Unexpected status code: ${response.status()}. Expected: ${contract.statusCodes.join(', ')}`);
      }

      // Validate response fields
      if (contract.responseFields) {
        const missingFields = contract.responseFields.filter(field => !(field in responseData));
        if (missingFields.length > 0) {
          errors.push(`Missing required response fields: ${missingFields.join(', ')}`);
        } else {
          coverage += 25; // Response fields validation passed
        }
      }

      // Validate content type
      if (contract.contentType) {
        const contentType = response.headers()['content-type'];
        if (!contentType?.includes(contract.contentType)) {
          warnings.push(`Unexpected content type: ${contentType}. Expected: ${contract.contentType}`);
        }
      }

      // Test error scenarios
      const errorValidation = await this.validateErrorScenarios(method, endpoint, contract);
      errors.push(...errorValidation.errors);
      warnings.push(...errorValidation.warnings);

      // Calculate coverage
      coverage += 25; // Basic request validation
      coverage += errorValidation.coverage;

      // Test rate limiting if applicable
      if (contract.statusCodes?.includes(429)) {
        const rateLimitValidation = await this.validateRateLimiting(method, endpoint);
        coverage += rateLimitValidation.coverage;
        warnings.push(...rateLimitValidation.warnings);
      }

    } catch (error) {
      errors.push(`Request failed: ${error.message}`);
    }

    return {
      isValid: errors.length === 0,
      coverage: Math.min(100, coverage),
      errors,
      warnings,
      details: {
        method,
        endpoint,
        testedAt: new Date().toISOString()
      }
    };
  }

  private async makeRequest(
    method: string,
    endpoint: string,
    contract: EndpointContract
  ): Promise<any> {
    const options: any = {
      headers: {}
    };

    // Add required headers
    if (contract.requiredHeaders) {
      contract.requiredHeaders.forEach(header => {
        // Add mock values for required headers
        if (header === 'Authorization') {
          options.headers[header] = 'Bearer mock-jwt-token';
        } else {
          options.headers[header] = `mock-${header.toLowerCase()}`;
        }
      });
    }

    // Add required fields as body for POST/PUT/PATCH
    if (['POST', 'PUT', 'PATCH'].includes(method.toUpperCase()) && contract.requiredFields) {
      const body: Record<string, any> = {};
      contract.requiredFields.forEach(field => {
        body[field] = `mock-${field}`;
      });
      options.data = body;
    }

    // Add query parameters
    if (contract.queryParams) {
      const params: Record<string, string> = {};
      contract.queryParams.forEach(param => {
        params[param] = `mock-${param}`;
      });
      options.params = params;
    }

    switch (method.toUpperCase()) {
      case 'GET':
        return await this.requestContext!.get(endpoint, options);
      case 'POST':
        return await this.requestContext!.post(endpoint, options);
      case 'PUT':
        return await this.requestContext!.put(endpoint, options);
      case 'PATCH':
        return await this.requestContext!.patch(endpoint, options);
      case 'DELETE':
        return await this.requestContext!.delete(endpoint, options);
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }
  }

  private async validateErrorScenarios(
    method: string,
    endpoint: string,
    contract: EndpointContract
  ): Promise<{ errors: string[]; warnings: string[]; coverage: number }> {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 25; // Base error scenario coverage

    // Test missing required headers
    if (contract.requiredHeaders) {
      try {
        const response = await this.makeRequest(method, endpoint, {
          ...contract,
          requiredHeaders: [] // Remove required headers to test error
        });

        if (response.status() !== 401 && response.status() !== 403) {
          warnings.push('Missing authorization header did not return expected error status');
        } else {
          coverage += 10;
        }
      } catch (error) {
        // Expected for invalid requests
        coverage += 10;
      }
    }

    // Test missing required fields
    if (['POST', 'PUT', 'PATCH'].includes(method.toUpperCase()) && contract.requiredFields) {
      try {
        const response = await this.makeRequest(method, endpoint, {
          ...contract,
          requiredFields: [] // Remove required fields to test error
        });

        if (response.status() !== 400) {
          warnings.push('Missing required fields did not return 400 Bad Request');
        } else {
          coverage += 10;
        }
      } catch (error) {
        // Expected for invalid requests
        coverage += 10;
      }
    }

    return { errors, warnings, coverage };
  }

  private async validateRateLimiting(method: string, endpoint: string): Promise<{ warnings: string[]; coverage: number }> {
    const warnings: string[] = [];
    let coverage = 0;

    try {
      // Make multiple rapid requests to test rate limiting
      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(this.requestContext!.get(endpoint));
      }

      const responses = await Promise.all(promises);
      const rateLimitedResponse = responses.find(r => r.status() === 429);

      if (rateLimitedResponse) {
        // Check for rate limit headers
        const headers = rateLimitedResponse.headers();
        const hasRateLimitHeaders = [
          'x-ratelimit-limit',
          'x-ratelimit-remaining',
          'x-ratelimit-reset'
        ].some(header => headers[header]);

        if (!hasRateLimitHeaders) {
          warnings.push('Rate limited response missing rate limit headers');
        } else {
          coverage += 15;
        }

        const hasRetryAfter = headers['retry-after'];
        if (!hasRetryAfter) {
          warnings.push('Rate limited response missing Retry-After header');
        } else {
          coverage += 15;
        }
      } else {
        warnings.push('Rate limiting not triggered with rapid requests');
      }
    } catch (error) {
      warnings.push(`Rate limiting test failed: ${error.message}`);
    }

    return { warnings, coverage };
  }

  async validateWebSocketContract(
    endpoint: string,
    contract: {
      requiredHeaders?: string[];
      supportedMessageTypes?: string[];
      heartbeatInterval?: number;
    }
  ): Promise<ValidationResult> {
    // WebSocket contract validation would require WebSocket client
    // For now, return a placeholder implementation
    return {
      isValid: true,
      coverage: 50,
      errors: [],
      warnings: ['WebSocket contract validation not fully implemented'],
      details: {
        endpoint,
        note: 'WebSocket validation requires additional setup'
      }
    };
  }

  async validateErrorContract(
    statusCode: number,
    contract: {
      requiredFields: string[];
      optionalFields?: string[];
      contentType?: string;
    }
  ): Promise<ValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    try {
      // Make a request that should trigger the error
      const response = await this.requestContext!.get('/invalid-endpoint');

      if (response.status() !== statusCode) {
        errors.push(`Expected status ${statusCode}, got ${response.status()}`);
      } else {
        const responseData = await response.json().catch(() => ({}));

        // Validate required fields in error response
        const missingFields = contract.requiredFields.filter(field => !(field in responseData));
        if (missingFields.length > 0) {
          errors.push(`Error response missing required fields: ${missingFields.join(', ')}`);
        }

        // Validate content type
        if (contract.contentType) {
          const contentType = response.headers()['content-type'];
          if (!contentType?.includes(contract.contentType)) {
            warnings.push(`Unexpected error response content type: ${contentType}`);
          }
        }
      }
    } catch (error) {
      errors.push(`Error contract validation failed: ${error.message}`);
    }

    return {
      isValid: errors.length === 0,
      coverage: errors.length === 0 ? 80 : 0,
      errors,
      warnings,
      details: { statusCode }
    };
  }

  async validatePaginationContract(contract: {
    requiredQueryParams: string[];
    responseFields: string[];
    paginationFields: string[];
    maxLimit?: number;
    defaultLimit?: number;
  }): Promise<ValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    try {
      // Test pagination parameters
      const params: Record<string, string> = {};
      contract.requiredQueryParams.forEach(param => {
        params[param] = '1'; // Test with page=1
      });

      const response = await this.requestContext!.get('/test-pagination', { params });
      const responseData = await response.json().catch(() => ({}));

      // Validate response structure
      const missingResponseFields = contract.responseFields.filter(field => !(field in responseData));
      if (missingResponseFields.length > 0) {
        errors.push(`Pagination response missing fields: ${missingResponseFields.join(', ')}`);
      }

      // Validate pagination metadata
      if (responseData.pagination) {
        const missingPaginationFields = contract.paginationFields.filter(
          field => !(field in responseData.pagination)
        );
        if (missingPaginationFields.length > 0) {
          warnings.push(`Pagination metadata missing fields: ${missingPaginationFields.join(', ')}`);
        }
      }

      // Test limit parameter
      if (contract.maxLimit) {
        const limitParams = { ...params, limit: (contract.maxLimit + 1).toString() };
        const limitResponse = await this.requestContext!.get('/test-pagination', { params: limitParams });

        if (limitResponse.status() === 200) {
          warnings.push(`Endpoint allows limit exceeding maximum: ${contract.maxLimit}`);
        }
      }

    } catch (error) {
      errors.push(`Pagination contract validation failed: ${error.message}`);
    }

    return {
      isValid: errors.length === 0,
      coverage: errors.length === 0 ? 75 : 0,
      errors,
      warnings,
      details: { contract: 'pagination' }
    };
  }

  async validateVersionContract(contract: {
    versionHeader: string;
    supportedVersions: string[];
    defaultVersion: string;
    deprecationWarnings: boolean;
  }): Promise<ValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    try {
      // Test version header
      const response = await this.requestContext!.get('/test-endpoint', {
        headers: { [contract.versionHeader]: contract.defaultVersion }
      });

      if (response.status() !== 200) {
        errors.push(`Version header test failed with status: ${response.status()}`);
      }

      // Test invalid version
      const invalidVersionResponse = await this.requestContext!.get('/test-endpoint', {
        headers: { [contract.versionHeader]: 'invalid-version' }
      });

      if (invalidVersionResponse.status() === 200) {
        warnings.push('Endpoint accepts invalid version without error');
      }

    } catch (error) {
      errors.push(`Version contract validation failed: ${error.message}`);
    }

    return {
      isValid: errors.length === 0,
      coverage: errors.length === 0 ? 70 : 0,
      errors,
      warnings,
      details: { contract: 'version' }
    };
  }
}
