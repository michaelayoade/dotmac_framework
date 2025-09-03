import type { PluginConfigValidation } from '../types';

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export function validatePluginName(name: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!name || name.trim().length === 0) {
    errors.push('Plugin name is required');
  } else {
    if (name.length < 3) {
      errors.push('Plugin name must be at least 3 characters long');
    }

    if (name.length > 100) {
      errors.push('Plugin name cannot exceed 100 characters');
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      errors.push('Plugin name can only contain letters, numbers, hyphens, and underscores');
    }

    if (/^[_-]|[_-]$/.test(name)) {
      warnings.push('Plugin name should not start or end with hyphens or underscores');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginVersion(version: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!version || version.trim().length === 0) {
    errors.push('Plugin version is required');
  } else {
    // Semantic versioning pattern: major.minor.patch with optional pre-release/build
    const semverPattern =
      /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$/;

    if (!semverPattern.test(version)) {
      errors.push('Plugin version must follow semantic versioning (e.g., 1.0.0, 1.2.3-alpha.1)');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginDomain(domain: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!domain || domain.trim().length === 0) {
    errors.push('Plugin domain is required');
  } else {
    if (domain.length < 2) {
      errors.push('Plugin domain must be at least 2 characters long');
    }

    if (domain.length > 50) {
      errors.push('Plugin domain cannot exceed 50 characters');
    }

    if (!/^[a-zA-Z0-9_.-]+$/.test(domain)) {
      errors.push(
        'Plugin domain can only contain letters, numbers, dots, hyphens, and underscores'
      );
    }

    if (/^[._-]|[._-]$/.test(domain)) {
      warnings.push('Plugin domain should not start or end with special characters');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginDescription(description?: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (description) {
    if (description.length > 500) {
      errors.push('Plugin description cannot exceed 500 characters');
    }

    if (description.trim().length < 10) {
      warnings.push(
        'Plugin description should be at least 10 characters for better discoverability'
      );
    }

    // Check for common issues
    if (description.toLowerCase().includes('todo') || description.toLowerCase().includes('fixme')) {
      warnings.push('Plugin description contains placeholder text');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginDependencies(dependencies: string[]): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!Array.isArray(dependencies)) {
    errors.push('Dependencies must be an array');
    return { isValid: false, errors, warnings };
  }

  const uniqueDeps = new Set(dependencies);
  if (uniqueDeps.size !== dependencies.length) {
    warnings.push('Duplicate dependencies found');
  }

  for (const dep of dependencies) {
    if (typeof dep !== 'string') {
      errors.push('Each dependency must be a string');
      continue;
    }

    if (!dep.trim()) {
      errors.push('Empty dependency found');
      continue;
    }

    // Basic plugin key validation (domain.name)
    if (!/^[a-zA-Z0-9_.-]+\.[a-zA-Z0-9_-]+$/.test(dep)) {
      errors.push(`Invalid dependency format: ${dep}. Expected format: domain.name`);
    }
  }

  if (dependencies.length > 20) {
    warnings.push('Plugin has many dependencies, consider reducing coupling');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginTags(tags: string[]): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!Array.isArray(tags)) {
    errors.push('Tags must be an array');
    return { isValid: false, errors, warnings };
  }

  const uniqueTags = new Set(tags.map((tag) => tag.toLowerCase()));
  if (uniqueTags.size !== tags.length) {
    warnings.push('Duplicate tags found (case-insensitive)');
  }

  for (const tag of tags) {
    if (typeof tag !== 'string') {
      errors.push('Each tag must be a string');
      continue;
    }

    if (!tag.trim()) {
      errors.push('Empty tag found');
      continue;
    }

    if (tag.length > 30) {
      errors.push(`Tag too long: ${tag}. Maximum 30 characters`);
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(tag)) {
      errors.push(
        `Invalid tag format: ${tag}. Only letters, numbers, hyphens, and underscores allowed`
      );
    }
  }

  if (tags.length === 0) {
    warnings.push('Consider adding tags for better discoverability');
  } else if (tags.length > 10) {
    warnings.push('Too many tags, consider using only the most relevant ones');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginCategories(categories: string[]): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!Array.isArray(categories)) {
    errors.push('Categories must be an array');
    return { isValid: false, errors, warnings };
  }

  const validCategories = [
    'authentication',
    'billing',
    'communication',
    'analytics',
    'monitoring',
    'network',
    'security',
    'integration',
    'workflow',
    'reporting',
    'data-processing',
    'ai-ml',
    'automation',
    'ui-extension',
    'system',
  ];

  for (const category of categories) {
    if (typeof category !== 'string') {
      errors.push('Each category must be a string');
      continue;
    }

    if (!validCategories.includes(category.toLowerCase())) {
      warnings.push(`Unknown category: ${category}. Consider using standard categories`);
    }
  }

  if (categories.length === 0) {
    warnings.push('Consider adding at least one category');
  } else if (categories.length > 3) {
    warnings.push('Too many categories, consider focusing on primary categories');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginConfig(
  config: Record<string, any>,
  schema?: Record<string, any>
): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!config || typeof config !== 'object') {
    errors.push('Plugin configuration must be an object');
    return { isValid: false, errors, warnings };
  }

  // If schema is provided, validate against it
  if (schema) {
    for (const [key, schemaRule] of Object.entries(schema)) {
      const value = config[key];

      // Check required fields
      if (schemaRule.required && (value === undefined || value === null)) {
        errors.push(`Required configuration field missing: ${key}`);
        continue;
      }

      // Check data types
      if (value !== undefined && schemaRule.type) {
        const expectedType = schemaRule.type;
        const actualType = Array.isArray(value) ? 'array' : typeof value;

        if (expectedType !== actualType) {
          errors.push(
            `Configuration field ${key} should be of type ${expectedType}, got ${actualType}`
          );
        }
      }

      // Check value constraints
      if (value !== undefined && schemaRule.enum && !schemaRule.enum.includes(value)) {
        errors.push(`Configuration field ${key} must be one of: ${schemaRule.enum.join(', ')}`);
      }

      if (
        typeof value === 'string' &&
        schemaRule.minLength &&
        value.length < schemaRule.minLength
      ) {
        errors.push(
          `Configuration field ${key} must be at least ${schemaRule.minLength} characters`
        );
      }

      if (
        typeof value === 'string' &&
        schemaRule.maxLength &&
        value.length > schemaRule.maxLength
      ) {
        errors.push(`Configuration field ${key} cannot exceed ${schemaRule.maxLength} characters`);
      }

      if (
        typeof value === 'number' &&
        schemaRule.minimum !== undefined &&
        value < schemaRule.minimum
      ) {
        errors.push(`Configuration field ${key} must be at least ${schemaRule.minimum}`);
      }

      if (
        typeof value === 'number' &&
        schemaRule.maximum !== undefined &&
        value > schemaRule.maximum
      ) {
        errors.push(`Configuration field ${key} cannot exceed ${schemaRule.maximum}`);
      }
    }
  }

  // Check for common configuration issues
  const configKeys = Object.keys(config);
  if (configKeys.length === 0) {
    warnings.push('Plugin configuration is empty');
  }

  // Check for sensitive data in config
  const sensitiveKeys = ['password', 'secret', 'key', 'token', 'credential', 'api_key'];
  for (const key of configKeys) {
    if (sensitiveKeys.some((sensitive) => key.toLowerCase().includes(sensitive))) {
      warnings.push(`Configuration contains potentially sensitive field: ${key}`);
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function validatePluginInstallRequest(request: {
  plugin_id?: string;
  version?: string;
  config?: Record<string, any>;
  enable_after_install?: boolean;
  auto_update?: boolean;
}): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!request.plugin_id || request.plugin_id.trim() === '') {
    errors.push('Plugin ID is required');
  }

  if (request.version) {
    const versionValidation = validatePluginVersion(request.version);
    errors.push(...versionValidation.errors);
    warnings.push(...versionValidation.warnings);
  }

  if (request.config) {
    const configValidation = validatePluginConfig(request.config);
    errors.push(...configValidation.errors);
    warnings.push(...configValidation.warnings);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

// Comprehensive plugin metadata validation
export function validatePluginMetadata(metadata: {
  name?: string;
  version?: string;
  domain?: string;
  description?: string;
  dependencies?: string[];
  tags?: string[];
  categories?: string[];
}): ValidationResult {
  const allErrors: string[] = [];
  const allWarnings: string[] = [];

  // Validate each field
  const validations = [
    validatePluginName(metadata.name || ''),
    validatePluginVersion(metadata.version || ''),
    validatePluginDomain(metadata.domain || ''),
    validatePluginDescription(metadata.description),
    validatePluginDependencies(metadata.dependencies || []),
    validatePluginTags(metadata.tags || []),
    validatePluginCategories(metadata.categories || []),
  ];

  for (const validation of validations) {
    allErrors.push(...validation.errors);
    allWarnings.push(...validation.warnings);
  }

  return {
    isValid: allErrors.length === 0,
    errors: allErrors,
    warnings: allWarnings,
  };
}
