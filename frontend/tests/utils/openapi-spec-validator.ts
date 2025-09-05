/**
 * OpenAPI Specification Validator
 * Validates OpenAPI specs for compliance and completeness
 */

import * as fs from 'fs';
import * as path from 'path';
import { parse as parseYaml } from 'yaml';

export interface OpenAPISpecValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  coverage: number;
  details: {
    specVersion: string;
    endpoints: number;
    schemas: number;
    securitySchemes: number;
    tags: number;
  };
}

export class OpenAPISpecValidator {
  private specPath: string;
  private spec: any = null;

  constructor(options: { specPath: string }) {
    this.specPath = options.specPath;
  }

  async validateSpec(): Promise<OpenAPISpecValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 0;

    try {
      // Load and parse the spec
      this.spec = await this.loadSpecFile();

      // Basic structure validation
      const basicValidation = this.validateBasicStructure();
      errors.push(...basicValidation.errors);
      warnings.push(...basicValidation.warnings);
      coverage += basicValidation.coverage;

      // Schema validation
      const schemaValidation = this.validateSchemas();
      errors.push(...schemaValidation.errors);
      warnings.push(...schemaValidation.warnings);
      coverage += schemaValidation.coverage;

      // Security validation
      const securityValidation = this.validateSecurity();
      errors.push(...securityValidation.errors);
      warnings.push(...securityValidation.warnings);
      coverage += securityValidation.coverage;

      // Endpoint validation
      const endpointValidation = this.validateEndpoints();
      errors.push(...endpointValidation.errors);
      warnings.push(...endpointValidation.warnings);
      coverage += endpointValidation.coverage;

      // Documentation validation
      const docsValidation = this.validateDocumentation();
      errors.push(...docsValidation.errors);
      warnings.push(...docsValidation.warnings);
      coverage += docsValidation.coverage;

    } catch (error) {
      errors.push(`Failed to validate OpenAPI spec: ${error.message}`);
    }

    // Calculate final coverage
    coverage = Math.min(100, coverage);

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      coverage,
      details: this.getSpecDetails()
    };
  }

  private async loadSpecFile(): Promise<any> {
    const absolutePath = path.resolve(this.specPath);

    if (!fs.existsSync(absolutePath)) {
      throw new Error(`OpenAPI spec file not found: ${absolutePath}`);
    }

    const content = fs.readFileSync(absolutePath, 'utf-8');
    const extension = path.extname(this.specPath).toLowerCase();

    if (extension === '.yaml' || extension === '.yml') {
      return parseYaml(content);
    } else if (extension === '.json') {
      return JSON.parse(content);
    } else {
      throw new Error(`Unsupported file format: ${extension}. Use .yaml, .yml, or .json`);
    }
  }

  private validateBasicStructure(): { errors: string[]; warnings: string[]; coverage: number } {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 0;

    // Required fields
    const requiredFields = ['openapi', 'info', 'paths'];
    for (const field of requiredFields) {
      if (!(field in this.spec)) {
        errors.push(`Missing required field: ${field}`);
      } else {
        coverage += 10;
      }
    }

    // OpenAPI version
    if (this.spec.openapi) {
      const version = this.spec.openapi;
      if (!version.startsWith('3.')) {
        errors.push(`Unsupported OpenAPI version: ${version}. Use 3.x`);
      } else {
        coverage += 5;
      }
    }

    // Info section
    if (this.spec.info) {
      const info = this.spec.info;
      if (!info.title) {
        warnings.push('Missing API title in info section');
      }
      if (!info.version) {
        warnings.push('Missing API version in info section');
      } else {
        coverage += 5;
      }
    }

    // Servers section
    if (!this.spec.servers || this.spec.servers.length === 0) {
      warnings.push('No servers defined. Consider adding server configurations');
    } else {
      coverage += 5;
    }

    return { errors, warnings, coverage };
  }

  private validateSchemas(): { errors: string[]; warnings: string[]; coverage: number } {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 0;

    if (!this.spec.components?.schemas) {
      warnings.push('No schemas defined in components section');
      return { errors, warnings, coverage };
    }

    const schemas = this.spec.components.schemas;
    const schemaCount = Object.keys(schemas).length;

    if (schemaCount === 0) {
      warnings.push('No schemas defined');
    } else {
      coverage += 15;
    }

    // Validate common schemas
    const commonSchemas = ['Error', 'User', 'Tenant', 'Pagination'];
    for (const schemaName of commonSchemas) {
      if (!(schemaName in schemas)) {
        warnings.push(`Common schema missing: ${schemaName}`);
      } else {
        coverage += 5;
      }
    }

    // Validate schema structure
    for (const [schemaName, schema] of Object.entries(schemas)) {
      const schemaErrors = this.validateSchemaStructure(schemaName, schema as any);
      errors.push(...schemaErrors.errors);
      warnings.push(...schemaErrors.warnings);
    }

    return { errors, warnings, coverage };
  }

  private validateSchemaStructure(schemaName: string, schema: any): { errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!schema.type && !schema.$ref && !schema.allOf && !schema.oneOf && !schema.anyOf) {
      warnings.push(`Schema ${schemaName} missing type definition`);
    }

    // Validate required fields for objects
    if (schema.type === 'object' && schema.properties) {
      if (schema.required && Array.isArray(schema.required)) {
        const missingRequired = schema.required.filter((field: string) => !(field in schema.properties));
        if (missingRequired.length > 0) {
          errors.push(`Schema ${schemaName} lists required fields not in properties: ${missingRequired.join(', ')}`);
        }
      }
    }

    return { errors, warnings };
  }

  private validateSecurity(): { errors: string[]; warnings: string[]; coverage: number } {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 0;

    if (!this.spec.components?.securitySchemes) {
      warnings.push('No security schemes defined');
      return { errors, warnings, coverage };
    }

    const securitySchemes = this.spec.components.securitySchemes;
    const schemeCount = Object.keys(securitySchemes).length;

    if (schemeCount === 0) {
      warnings.push('No security schemes defined');
    } else {
      coverage += 10;
    }

    // Check for JWT bearer token
    const hasBearerAuth = Object.values(securitySchemes).some((scheme: any) =>
      scheme.type === 'http' && scheme.scheme === 'bearer'
    );

    if (!hasBearerAuth) {
      warnings.push('No Bearer token authentication defined');
    } else {
      coverage += 10;
    }

    // Validate security scheme structure
    for (const [schemeName, scheme] of Object.entries(securitySchemes)) {
      const schemeErrors = this.validateSecurityScheme(schemeName, scheme as any);
      errors.push(...schemeErrors.errors);
      warnings.push(...schemeErrors.warnings);
    }

    return { errors, warnings, coverage };
  }

  private validateSecurityScheme(schemeName: string, scheme: any): { errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!scheme.type) {
      errors.push(`Security scheme ${schemeName} missing type`);
    }

    if (scheme.type === 'http' && !scheme.scheme) {
      errors.push(`HTTP security scheme ${schemeName} missing scheme`);
    }

    if (scheme.type === 'apiKey' && !scheme.in) {
      errors.push(`API key security scheme ${schemeName} missing 'in' parameter`);
    }

    return { errors, warnings };
  }

  private validateEndpoints(): { errors: string[]; warnings: string[]; coverage: number } {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 0;

    if (!this.spec.paths) {
      errors.push('No paths defined');
      return { errors, warnings, coverage };
    }

    const paths = this.spec.paths;
    const endpointCount = Object.keys(paths).length;

    if (endpointCount === 0) {
      errors.push('No endpoints defined');
    } else {
      coverage += 15;
    }

    // Validate each endpoint
    for (const [path, methods] of Object.entries(paths)) {
      const endpointErrors = this.validateEndpoint(path, methods as any);
      errors.push(...endpointErrors.errors);
      warnings.push(...endpointErrors.warnings);
    }

    // Check for common endpoints
    const requiredEndpoints = ['/auth/login', '/auth/logout', '/users/profile'];
    for (const endpoint of requiredEndpoints) {
      if (!(endpoint in paths)) {
        warnings.push(`Common endpoint missing: ${endpoint}`);
      } else {
        coverage += 5;
      }
    }

    return { errors, warnings, coverage };
  }

  private validateEndpoint(path: string, methods: any): { errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    for (const [method, operation] of Object.entries(methods)) {
      if (method === 'parameters') continue; // Skip path parameters

      const op = operation as any;

      // Check for operationId
      if (!op.operationId) {
        warnings.push(`Endpoint ${method.toUpperCase()} ${path} missing operationId`);
      }

      // Check for summary or description
      if (!op.summary && !op.description) {
        warnings.push(`Endpoint ${method.toUpperCase()} ${path} missing summary or description`);
      }

      // Validate parameters
      if (op.parameters) {
        const paramErrors = this.validateParameters(path, method, op.parameters);
        errors.push(...paramErrors.errors);
        warnings.push(...paramErrors.warnings);
      }

      // Validate request body for applicable methods
      if (['post', 'put', 'patch'].includes(method.toLowerCase())) {
        if (!op.requestBody) {
          warnings.push(`Endpoint ${method.toUpperCase()} ${path} missing request body`);
        }
      }

      // Validate responses
      if (!op.responses) {
        errors.push(`Endpoint ${method.toUpperCase()} ${path} missing responses`);
      } else {
        const responseErrors = this.validateResponses(path, method, op.responses);
        errors.push(...responseErrors.errors);
        warnings.push(...responseErrors.warnings);
      }

      // Validate security
      if (!op.security && !this.spec.security) {
        warnings.push(`Endpoint ${method.toUpperCase()} ${path} missing security definition`);
      }
    }

    return { errors, warnings };
  }

  private validateParameters(path: string, method: string, parameters: any[]): { errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    for (const param of parameters) {
      if (!param.name) {
        errors.push(`Parameter in ${method.toUpperCase()} ${path} missing name`);
      }
      if (!param.in) {
        errors.push(`Parameter ${param.name} in ${method.toUpperCase()} ${path} missing 'in' field`);
      }
      if (!param.schema) {
        warnings.push(`Parameter ${param.name} in ${method.toUpperCase()} ${path} missing schema`);
      }
    }

    return { errors, warnings };
  }

  private validateResponses(path: string, method: string, responses: any): { errors: string[]; warnings: string[] } {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check for success response
    const hasSuccessResponse = Object.keys(responses).some(code => code.startsWith('2'));
    if (!hasSuccessResponse) {
      warnings.push(`Endpoint ${method.toUpperCase()} ${path} missing success response`);
    }

    // Check for error responses
    const hasErrorResponse = Object.keys(responses).some(code => code.startsWith('4') || code.startsWith('5'));
    if (!hasErrorResponse) {
      warnings.push(`Endpoint ${method.toUpperCase()} ${path} missing error responses`);
    }

    // Validate response schemas
    for (const [code, response] of Object.entries(responses)) {
      const resp = response as any;
      if (resp.content) {
        for (const [contentType, content] of Object.entries(resp.content)) {
          if (!content.schema) {
            warnings.push(`Response ${code} in ${method.toUpperCase()} ${path} missing schema for ${contentType}`);
          }
        }
      }
    }

    return { errors, warnings };
  }

  private validateDocumentation(): { errors: string[]; warnings: string[]; coverage: number } {
    const errors: string[] = [];
    const warnings: string[] = [];
    let coverage = 0;

    // Check for tags
    if (this.spec.tags && this.spec.tags.length > 0) {
      coverage += 10;
    } else {
      warnings.push('No tags defined for API organization');
    }

    // Check for external documentation
    if (this.spec.externalDocs) {
      coverage += 5;
    } else {
      warnings.push('Consider adding external documentation links');
    }

    // Validate info section completeness
    if (this.spec.info) {
      const info = this.spec.info;
      if (info.contact) coverage += 5;
      if (info.license) coverage += 5;
      if (info.termsOfService) coverage += 5;
    }

    return { errors, warnings, coverage };
  }

  private getSpecDetails(): { specVersion: string; endpoints: number; schemas: number; securitySchemes: number; tags: number } {
    return {
      specVersion: this.spec?.openapi || 'unknown',
      endpoints: this.spec?.paths ? Object.keys(this.spec.paths).length : 0,
      schemas: this.spec?.components?.schemas ? Object.keys(this.spec.components.schemas).length : 0,
      securitySchemes: this.spec?.components?.securitySchemes ? Object.keys(this.spec.components.securitySchemes).length : 0,
      tags: this.spec?.tags ? this.spec.tags.length : 0
    };
  }
}
