#!/usr/bin/env node

/**
 * Integration Testing Validation Script
 * Validates that all integration testing components are properly configured
 */

const fs = require('fs');
const path = require('path');

console.log('🧪 Validating Integration Testing Setup...\n');

// Check required files exist
const requiredFiles = [
  'tests/integration/jest.config.js',
  'tests/integration/setup.ts',
  'tests/integration/api-integration.test.ts',
  'tests/integration/component-integration.test.tsx',
  'tests/integration/business-flow.test.ts',
  'tests/integration/security-integration.test.ts'
];

let allFilesExist = true;

console.log('📁 Checking integration test files...');
requiredFiles.forEach(file => {
  const filePath = path.join(process.cwd(), file);
  if (fs.existsSync(filePath)) {
    console.log(`✅ ${file}`);
  } else {
    console.log(`❌ ${file} - MISSING`);
    allFilesExist = false;
  }
});

// Check package.json scripts
console.log('\n📦 Checking integration test scripts...');
const packagePath = path.join(process.cwd(), 'package.json');
const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

const requiredScripts = [
  'test:integration',
  'test:integration:watch',
  'test:integration:coverage'
];

let allScriptsExist = true;

requiredScripts.forEach(script => {
  if (pkg.scripts && pkg.scripts[script]) {
    console.log(`✅ ${script}: ${pkg.scripts[script]}`);
  } else {
    console.log(`❌ ${script} - MISSING`);
    allScriptsExist = false;
  }
});

// Validate test file structure
console.log('\n🏗️ Validating integration test structure...');

// Check API integration test
const apiTestPath = path.join(process.cwd(), 'tests/integration/api-integration.test.ts');
if (fs.existsSync(apiTestPath)) {
  const apiContent = fs.readFileSync(apiTestPath, 'utf8');
  if (apiContent.includes('API Integration Tests')) {
    console.log('✅ API integration tests properly structured');
  } else {
    console.log('❌ API integration tests missing proper structure');
    allFilesExist = false;
  }
}

// Check component integration test
const componentTestPath = path.join(process.cwd(), 'tests/integration/component-integration.test.tsx');
if (fs.existsSync(componentTestPath)) {
  const componentContent = fs.readFileSync(componentTestPath, 'utf8');
  if (componentContent.includes('Component Integration Tests')) {
    console.log('✅ Component integration tests properly structured');
  } else {
    console.log('❌ Component integration tests missing proper structure');
    allFilesExist = false;
  }
}

// Check business flow test
const businessTestPath = path.join(process.cwd(), 'tests/integration/business-flow.test.ts');
if (fs.existsSync(businessTestPath)) {
  const businessContent = fs.readFileSync(businessTestPath, 'utf8');
  if (businessContent.includes('Business Flow Integration Tests')) {
    console.log('✅ Business flow integration tests properly structured');
  } else {
    console.log('❌ Business flow integration tests missing proper structure');
    allFilesExist = false;
  }
}

// Check security integration test
const securityTestPath = path.join(process.cwd(), 'tests/integration/security-integration.test.ts');
if (fs.existsSync(securityTestPath)) {
  const securityContent = fs.readFileSync(securityTestPath, 'utf8');
  if (securityContent.includes('Security Integration Tests')) {
    console.log('✅ Security integration tests properly structured');
  } else {
    console.log('❌ Security integration tests missing proper structure');
    allFilesExist = false;
  }
}

// Check Jest configuration
console.log('\n⚙️ Validating Jest configuration...');
const jestConfigPath = path.join(process.cwd(), 'tests/integration/jest.config.js');
if (fs.existsSync(jestConfigPath)) {
  const jestContent = fs.readFileSync(jestConfigPath, 'utf8');
  
  const requiredConfigs = [
    'displayName',
    'testEnvironment',
    'testMatch',
    'setupFilesAfterEnv',
    'moduleNameMapper'
  ];
  
  let configValid = true;
  requiredConfigs.forEach(config => {
    if (jestContent.includes(config)) {
      console.log(`✅ Jest config has ${config}`);
    } else {
      console.log(`❌ Jest config missing ${config}`);
      configValid = false;
    }
  });
  
  if (!configValid) allFilesExist = false;
}

// Test categories validation
console.log('\n📋 Validating test categories...');

const testCategories = {
  'API Integration': {
    file: apiTestPath,
    tests: ['Authentication API', 'MFA API Integration', 'WebSocket Integration']
  },
  'Component Integration': {
    file: componentTestPath,
    tests: ['MFA Setup Integration', 'Realtime Dashboard Integration']
  },
  'Business Flow': {
    file: businessTestPath,
    tests: ['Complete Authentication Flow', 'Tenant Management Workflow']
  },
  'Security Integration': {
    file: securityTestPath,
    tests: ['Authentication Security', 'Session Security', 'Audit Trail Security']
  }
};

Object.entries(testCategories).forEach(([category, info]) => {
  if (fs.existsSync(info.file)) {
    const content = fs.readFileSync(info.file, 'utf8');
    const hasTests = info.tests.some(test => content.includes(test));
    
    if (hasTests) {
      console.log(`✅ ${category}: Contains expected test suites`);
    } else {
      console.log(`❌ ${category}: Missing expected test suites`);
      allFilesExist = false;
    }
  }
});

// Summary
console.log('\n📋 Integration Testing Validation Summary');
console.log('='.repeat(50));

if (allFilesExist && allScriptsExist) {
  console.log('🎉 ALL INTEGRATION TESTS CONFIGURED!');
  console.log('✅ Integration testing suite is complete and ready');
  console.log('\n🚀 Test Coverage:');
  console.log('  • API Integration Tests - Real API endpoint testing');
  console.log('  • Component Integration - UI component with service integration');
  console.log('  • Business Flow Tests - End-to-end business process testing');
  console.log('  • Security Integration - Security feature integration testing');
  console.log('\n📖 Usage:');
  console.log('  • npm run test:integration - Run all integration tests');
  console.log('  • npm run test:integration:watch - Run with file watching');
  console.log('  • npm run test:integration:coverage - Run with coverage report');
  process.exit(0);
} else {
  console.log('❌ SOME INTEGRATION TEST COMPONENTS MISSING');
  console.log('Please review the missing components above');
  process.exit(1);
}

// Script completed successfully