import {
  validatePluginName,
  validatePluginVersion,
  validatePluginDomain,
  validatePluginDescription,
  validatePluginDependencies,
  validatePluginTags,
  validatePluginCategories,
  validatePluginConfig,
  validatePluginMetadata,
} from '../../utils/validation';

describe('Plugin Validation Utils', () => {
  describe('validatePluginName', () => {
    it('should validate correct plugin name', () => {
      const result = validatePluginName('my-plugin');
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should require plugin name', () => {
      const result = validatePluginName('');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin name is required');
    });

    it('should validate minimum length', () => {
      const result = validatePluginName('ab');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin name must be at least 3 characters long');
    });

    it('should validate maximum length', () => {
      const result = validatePluginName('a'.repeat(101));
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin name cannot exceed 100 characters');
    });

    it('should validate character format', () => {
      const result = validatePluginName('my plugin!');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Plugin name can only contain letters, numbers, hyphens, and underscores'
      );
    });

    it('should warn about leading/trailing special characters', () => {
      const result = validatePluginName('-my-plugin-');
      expect(result.isValid).toBe(true);
      expect(result.warnings).toContain(
        'Plugin name should not start or end with hyphens or underscores'
      );
    });
  });

  describe('validatePluginVersion', () => {
    it('should validate semantic versioning', () => {
      const result = validatePluginVersion('1.0.0');
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should validate pre-release versions', () => {
      const result = validatePluginVersion('1.0.0-alpha.1');
      expect(result.isValid).toBe(true);
    });

    it('should require version', () => {
      const result = validatePluginVersion('');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin version is required');
    });

    it('should validate semantic versioning format', () => {
      const result = validatePluginVersion('1.0');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Plugin version must follow semantic versioning (e.g., 1.0.0, 1.2.3-alpha.1)'
      );
    });
  });

  describe('validatePluginDomain', () => {
    it('should validate correct domain', () => {
      const result = validatePluginDomain('com.example');
      expect(result.isValid).toBe(true);
    });

    it('should require domain', () => {
      const result = validatePluginDomain('');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin domain is required');
    });

    it('should validate minimum length', () => {
      const result = validatePluginDomain('a');
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin domain must be at least 2 characters long');
    });
  });

  describe('validatePluginDescription', () => {
    it('should validate correct description', () => {
      const result = validatePluginDescription('This is a good plugin description');
      expect(result.isValid).toBe(true);
    });

    it('should validate maximum length', () => {
      const result = validatePluginDescription('a'.repeat(501));
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin description cannot exceed 500 characters');
    });

    it('should warn about short descriptions', () => {
      const result = validatePluginDescription('Short');
      expect(result.warnings).toContain(
        'Plugin description should be at least 10 characters for better discoverability'
      );
    });

    it('should warn about placeholder text', () => {
      const result = validatePluginDescription('TODO: write description');
      expect(result.warnings).toContain('Plugin description contains placeholder text');
    });
  });

  describe('validatePluginDependencies', () => {
    it('should validate correct dependencies', () => {
      const result = validatePluginDependencies(['com.example.plugin1', 'com.example.plugin2']);
      expect(result.isValid).toBe(true);
    });

    it('should require array format', () => {
      const result = validatePluginDependencies('not-an-array' as any);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Dependencies must be an array');
    });

    it('should validate dependency format', () => {
      const result = validatePluginDependencies(['invalid-format']);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Invalid dependency format: invalid-format. Expected format: domain.name'
      );
    });

    it('should warn about many dependencies', () => {
      const deps = Array.from({ length: 25 }, (_, i) => `domain.plugin${i}`);
      const result = validatePluginDependencies(deps);
      expect(result.warnings).toContain('Plugin has many dependencies, consider reducing coupling');
    });
  });

  describe('validatePluginTags', () => {
    it('should validate correct tags', () => {
      const result = validatePluginTags(['web', 'api', 'integration']);
      expect(result.isValid).toBe(true);
    });

    it('should warn about no tags', () => {
      const result = validatePluginTags([]);
      expect(result.warnings).toContain('Consider adding tags for better discoverability');
    });

    it('should warn about too many tags', () => {
      const tags = Array.from({ length: 15 }, (_, i) => `tag${i}`);
      const result = validatePluginTags(tags);
      expect(result.warnings).toContain(
        'Too many tags, consider using only the most relevant ones'
      );
    });
  });

  describe('validatePluginCategories', () => {
    it('should validate standard categories', () => {
      const result = validatePluginCategories(['authentication', 'security']);
      expect(result.isValid).toBe(true);
    });

    it('should warn about unknown categories', () => {
      const result = validatePluginCategories(['unknown-category']);
      expect(result.warnings).toContain(
        'Unknown category: unknown-category. Consider using standard categories'
      );
    });
  });

  describe('validatePluginConfig', () => {
    it('should validate basic config object', () => {
      const result = validatePluginConfig({ key: 'value' });
      expect(result.isValid).toBe(true);
    });

    it('should require object format', () => {
      const result = validatePluginConfig('not-an-object' as any);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Plugin configuration must be an object');
    });

    it('should validate against schema', () => {
      const schema = {
        required_field: { required: true, type: 'string' },
      };
      const config = {};

      const result = validatePluginConfig(config, schema);
      expect(result.isValid).toBe(false);
      expect(result.errors).toContain('Required configuration field missing: required_field');
    });
  });

  describe('validatePluginMetadata', () => {
    const validMetadata = {
      name: 'test-plugin',
      version: '1.0.0',
      domain: 'com.example',
      description: 'A test plugin description',
      dependencies: [],
      tags: ['test'],
      categories: ['system'],
    };

    it('should validate complete metadata', () => {
      const result = validatePluginMetadata(validMetadata);
      expect(result.isValid).toBe(true);
    });

    it('should collect all validation errors', () => {
      const result = validatePluginMetadata({
        name: '',
        version: 'invalid',
        domain: '',
        dependencies: ['invalid'],
        tags: [],
        categories: [],
      });

      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(3);
    });
  });
});
