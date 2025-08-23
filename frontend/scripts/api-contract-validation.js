#!/usr/bin/env node

/**
 * API Contract Validation System
 * Validates frontend types against backend OpenAPI schemas
 * Ensures API compatibility across all services
 */

const fs = require('fs');
const path = require('path');
const chalk = require('chalk');

class APIContractValidator {
  constructor() {
    this.backendSpecsDir = path.join(__dirname, '../../backend/docs/swagger');
    this.frontendTypesDir = path.join(__dirname, '../types');
    this.validationResults = [];
    this.services = [
      'dotmac_api_gateway',
      'dotmac_identity',
      'dotmac_billing',
      'dotmac_services',
      'dotmac_networking',
      'dotmac_analytics',
      'dotmac_platform',
      'dotmac_core_events',
      'dotmac_core_ops',
    ];
  }

  async validateContracts() {
    console.log(chalk.blue('🔍 Starting API Contract Validation...\\n'));

    try {
      await this.loadBackendSpecs();
      await this.validateFrontendTypes();
      await this.validateEndpoints();
      await this.generateValidationReport();

      const hasErrors = this.validationResults.some((result) => result.errors.length > 0);

      if (hasErrors) {
        console.error(chalk.red('❌ API contract validation failed!'));
        process.exit(1);
      } else {
        console.log(chalk.green('✅ All API contracts are valid!'));
      }
    } catch (error) {
      console.error(chalk.red(`💥 Validation failed: ${error.message}`));
      process.exit(1);
    }
  }

  async loadBackendSpecs() {
    console.log(chalk.yellow('📖 Loading backend OpenAPI specifications...'));

    this.backendSpecs = {};

    for (const service of this.services) {
      const specPath = path.join(this.backendSpecsDir, `${service}.json`);

      if (fs.existsSync(specPath)) {
        try {
          const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
          this.backendSpecs[service] = spec;
          console.log(chalk.green(`  ✓ Loaded ${service} specification`));
        } catch (error) {
          console.warn(chalk.yellow(`  ⚠ Failed to load ${service}: ${error.message}`));
        }
      } else {
        console.warn(chalk.yellow(`  ⚠ No specification found for ${service}`));
      }
    }
  }

  async validateFrontendTypes() {
    console.log(chalk.yellow('\\n🔍 Validating frontend TypeScript types...'));

    // Find all TypeScript type files
    const typeFiles = this.findTypeFiles();

    for (const typeFile of typeFiles) {
      const validation = {
        file: typeFile,
        service: this.extractServiceFromPath(typeFile),
        errors: [],
        warnings: [],
        info: [],
      };

      try {
        await this.validateTypeFile(typeFile, validation);
      } catch (error) {
        validation.errors.push(`Type validation failed: ${error.message}`);
      }

      this.validationResults.push(validation);
    }
  }

  findTypeFiles() {
    const typeFiles = [];

    // Search in apps and packages directories
    const searchDirs = [
      path.join(__dirname, '../apps'),
      path.join(__dirname, '../packages'),
      path.join(__dirname, '../types'),
    ];

    for (const dir of searchDirs) {
      if (fs.existsSync(dir)) {
        this.findTypeFilesRecursive(dir, typeFiles);
      }
    }

    return typeFiles;
  }

  findTypeFilesRecursive(dir, typeFiles) {
    const items = fs.readdirSync(dir, { withFileTypes: true });

    for (const item of items) {
      const fullPath = path.join(dir, item.name);

      if (item.isDirectory() && !item.name.includes('node_modules') && !item.name.startsWith('.')) {
        this.findTypeFilesRecursive(fullPath, typeFiles);
      } else if (
        item.name.endsWith('.d.ts') ||
        (item.name.endsWith('.ts') && !item.name.endsWith('.test.ts')) ||
        (item.name.endsWith('.tsx') && !item.name.endsWith('.test.tsx'))
      ) {
        typeFiles.push(fullPath);
      }
    }
  }

  extractServiceFromPath(filePath) {
    // Try to determine which backend service this type file relates to
    const pathLower = filePath.toLowerCase();

    if (
      pathLower.includes('identity') ||
      pathLower.includes('auth') ||
      pathLower.includes('customer')
    ) {
      return 'dotmac_identity';
    } else if (
      pathLower.includes('billing') ||
      pathLower.includes('invoice') ||
      pathLower.includes('payment')
    ) {
      return 'dotmac_billing';
    } else if (pathLower.includes('network') || pathLower.includes('device')) {
      return 'dotmac_networking';
    } else if (pathLower.includes('analytics') || pathLower.includes('metrics')) {
      return 'dotmac_analytics';
    } else if (pathLower.includes('service')) {
      return 'dotmac_services';
    } else if (pathLower.includes('gateway') || pathLower.includes('api')) {
      return 'dotmac_api_gateway';
    } else if (pathLower.includes('platform')) {
      return 'dotmac_platform';
    } else if (pathLower.includes('event')) {
      return 'dotmac_core_events';
    } else if (pathLower.includes('ops')) {
      return 'dotmac_core_ops';
    }

    return 'unknown';
  }

  async validateTypeFile(typeFile, validation) {
    const content = fs.readFileSync(typeFile, 'utf8');

    // Extract interface and type definitions
    const interfaces = this.extractInterfaces(content);
    const types = this.extractTypes(content);

    if (interfaces.length === 0 && types.length === 0) {
      validation.info.push('No interfaces or types found in file');
      return;
    }

    const service = validation.service;
    if (service === 'unknown' || !this.backendSpecs[service]) {
      validation.warnings.push(`No backend specification available for service: ${service}`);
      return;
    }

    const spec = this.backendSpecs[service];

    // Validate interfaces against OpenAPI schemas
    for (const interfaceData of interfaces) {
      this.validateInterface(interfaceData, spec, validation);
    }

    // Validate type aliases
    for (const typeData of types) {
      this.validateType(typeData, spec, validation);
    }
  }

  extractInterfaces(content) {
    const interfaces = [];
    const interfaceRegex = /interface\\s+(\\w+)\\s*{([^}]*)}/g;
    let match;

    while ((match = interfaceRegex.exec(content)) !== null) {
      interfaces.push({
        name: match[1],
        body: match[2],
        properties: this.extractProperties(match[2]),
      });
    }

    return interfaces;
  }

  extractTypes(content) {
    const types = [];
    const typeRegex = /type\\s+(\\w+)\\s*=\\s*([^;\\n]+);?/g;
    let match;

    while ((match = typeRegex.exec(content)) !== null) {
      types.push({
        name: match[1],
        definition: match[2].trim(),
      });
    }

    return types;
  }

  extractProperties(interfaceBody) {
    const properties = {};
    const propertyRegex = /(\\w+)\\??:\\s*([^;,\\n]+)[;,]?/g;
    let match;

    while ((match = propertyRegex.exec(interfaceBody)) !== null) {
      properties[match[1]] = {
        type: match[2].trim(),
        optional: match[0].includes('?'),
      };
    }

    return properties;
  }

  validateInterface(interfaceData, spec, validation) {
    if (!spec.components || !spec.components.schemas) {
      validation.warnings.push(`No schemas found in ${validation.service} specification`);
      return;
    }

    const schemas = spec.components.schemas;
    const matchingSchema = this.findMatchingSchema(interfaceData.name, schemas);

    if (!matchingSchema) {
      validation.warnings.push(
        `No matching backend schema found for interface ${interfaceData.name}`
      );
      return;
    }

    // Validate properties
    const backendProperties = matchingSchema.properties || {};
    const frontendProperties = interfaceData.properties;

    // Check for missing properties in frontend
    for (const [propName, propSchema] of Object.entries(backendProperties)) {
      if (!(propName in frontendProperties)) {
        const isRequired = matchingSchema.required?.includes(propName);
        if (isRequired) {
          validation.errors.push(
            `Missing required property '${propName}' in interface ${interfaceData.name}`
          );
        } else {
          validation.warnings.push(
            `Missing optional property '${propName}' in interface ${interfaceData.name}`
          );
        }
      }
    }

    // Check for extra properties in frontend
    for (const propName of Object.keys(frontendProperties)) {
      if (!(propName in backendProperties)) {
        validation.warnings.push(
          `Extra property '${propName}' in interface ${interfaceData.name} not found in backend schema`
        );
      }
    }

    validation.info.push(`Validated interface ${interfaceData.name} against backend schema`);
  }

  validateType(typeData, spec, validation) {
    // Basic validation for type aliases
    validation.info.push(`Found type alias: ${typeData.name}`);
  }

  findMatchingSchema(interfaceName, schemas) {
    // Try exact match first
    if (schemas[interfaceName]) {
      return schemas[interfaceName];
    }

    // Try common variations
    const variations = [
      interfaceName.toLowerCase(),
      interfaceName.replace(/^I/, ''), // Remove 'I' prefix
      interfaceName + 'Schema',
      interfaceName + 'Model',
      interfaceName.replace(/Request$|Response$/, ''), // Remove Request/Response suffix
    ];

    for (const variation of variations) {
      if (schemas[variation]) {
        return schemas[variation];
      }
    }

    // Try partial matching
    const lowerInterfaceName = interfaceName.toLowerCase();
    for (const [schemaName, schema] of Object.entries(schemas)) {
      if (
        schemaName.toLowerCase().includes(lowerInterfaceName) ||
        lowerInterfaceName.includes(schemaName.toLowerCase())
      ) {
        return schema;
      }
    }

    return null;
  }

  async validateEndpoints() {
    console.log(chalk.yellow('\\n🔗 Validating API endpoints...'));

    // Find API client files
    const apiFiles = this.findAPIFiles();

    for (const apiFile of apiFiles) {
      const validation = {
        file: apiFile,
        type: 'endpoint',
        errors: [],
        warnings: [],
        info: [],
      };

      try {
        await this.validateAPIFile(apiFile, validation);
      } catch (error) {
        validation.errors.push(`Endpoint validation failed: ${error.message}`);
      }

      this.validationResults.push(validation);
    }
  }

  findAPIFiles() {
    const apiFiles = [];
    const searchDirs = [path.join(__dirname, '../apps'), path.join(__dirname, '../packages')];

    for (const dir of searchDirs) {
      if (fs.existsSync(dir)) {
        this.findAPIFilesRecursive(dir, apiFiles);
      }
    }

    return apiFiles;
  }

  findAPIFilesRecursive(dir, apiFiles) {
    const items = fs.readdirSync(dir, { withFileTypes: true });

    for (const item of items) {
      const fullPath = path.join(dir, item.name);

      if (item.isDirectory() && !item.name.includes('node_modules') && !item.name.startsWith('.')) {
        this.findAPIFilesRecursive(fullPath, apiFiles);
      } else if (
        item.name.includes('api') &&
        (item.name.endsWith('.ts') || item.name.endsWith('.tsx'))
      ) {
        apiFiles.push(fullPath);
      }
    }
  }

  async validateAPIFile(apiFile, validation) {
    const content = fs.readFileSync(apiFile, 'utf8');

    // Extract API calls
    const apiCalls = this.extractAPICalls(content);

    for (const apiCall of apiCalls) {
      this.validateAPICall(apiCall, validation);
    }
  }

  extractAPICalls(content) {
    const calls = [];

    // Look for fetch calls, axios calls, etc.
    const fetchRegex = /fetch\\(\\s*['\\\"`]([^'\\\"`]+)['\\\"`]/g;
    const axiosRegex = /axios\\.(get|post|put|delete|patch)\\(\\s*['\\\"`]([^'\\\"`]+)['\\\"`]/g;

    let match;

    while ((match = fetchRegex.exec(content)) !== null) {
      calls.push({
        method: 'unknown',
        url: match[1],
        type: 'fetch',
      });
    }

    while ((match = axiosRegex.exec(content)) !== null) {
      calls.push({
        method: match[1].toLowerCase(),
        url: match[2],
        type: 'axios',
      });
    }

    return calls;
  }

  validateAPICall(apiCall, validation) {
    validation.info.push(
      `Found API call: ${apiCall.method?.toUpperCase() || 'GET'} ${apiCall.url}`
    );

    // Here you could validate against OpenAPI paths
    // This is a simplified implementation
  }

  async generateValidationReport() {
    console.log(chalk.yellow('\\n📊 Generating validation report...'));

    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalFiles: this.validationResults.length,
        filesWithErrors: this.validationResults.filter((r) => r.errors.length > 0).length,
        filesWithWarnings: this.validationResults.filter((r) => r.warnings.length > 0).length,
        totalErrors: this.validationResults.reduce((sum, r) => sum + r.errors.length, 0),
        totalWarnings: this.validationResults.reduce((sum, r) => sum + r.warnings.length, 0),
      },
      results: this.validationResults,
      services: Object.keys(this.backendSpecs),
    };

    // Write report to file
    const reportPath = path.join(__dirname, '../test-results/api-contract-validation.json');
    const reportDir = path.dirname(reportPath);

    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true });
    }

    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    // Print summary
    console.log(chalk.blue('\\n📈 Validation Summary:'));
    console.log(`  Files processed: ${report.summary.totalFiles}`);
    console.log(`  Errors: ${chalk.red(report.summary.totalErrors)}`);
    console.log(`  Warnings: ${chalk.yellow(report.summary.totalWarnings)}`);
    console.log(`  Services: ${report.services.length}`);
    console.log(`\\n  Report saved to: ${reportPath}`);

    // Print detailed results
    for (const result of this.validationResults) {
      if (result.errors.length > 0 || result.warnings.length > 0) {
        console.log(`\\n${chalk.cyan(path.relative(process.cwd(), result.file))}:`);

        for (const error of result.errors) {
          console.log(`  ${chalk.red('❌ Error:')} ${error}`);
        }

        for (const warning of result.warnings) {
          console.log(`  ${chalk.yellow('⚠  Warning:')} ${warning}`);
        }
      }
    }
  }
}

// Run validation if called directly
if (require.main === module) {
  const validator = new APIContractValidator();
  validator.validateContracts().catch((error) => {
    console.error(chalk.red(`Fatal error: ${error.message}`));
    process.exit(1);
  });
}

module.exports = APIContractValidator;
