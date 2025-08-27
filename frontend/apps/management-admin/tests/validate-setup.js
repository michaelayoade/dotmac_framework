#!/usr/bin/env node

/**
 * E2E Setup Validation Script
 * Validates that all E2E testing components are properly configured
 */

const fs = require('fs');
const path = require('path');

console.log('🧪 Validating E2E Testing Setup...\n');

// Check required files exist
const requiredFiles = [
  'playwright.config.ts',
  'tests/e2e/auth.spec.ts',
  'tests/e2e/dashboard.spec.ts',
  'tests/e2e/tenants.spec.ts', 
  'tests/e2e/mfa.spec.ts',
  'tests/e2e/realtime.spec.ts',
  'tests/fixtures/test-data.ts',
  'tests/helpers/auth.ts',
  'tests/helpers/api-mocks.ts',
  'tests/setup/global-setup.ts',
  'tests/setup/global-teardown.ts',
  'jest.setup.js'
];

let allFilesExist = true;

console.log('📁 Checking required files...');
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
console.log('\n📦 Checking package.json scripts...');
const packagePath = path.join(process.cwd(), 'package.json');
const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

const requiredScripts = [
  'test:e2e',
  'test:e2e:ui', 
  'test:e2e:debug',
  'test:e2e:headed',
  'test:e2e:report',
  'playwright:install'
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

// Check dependencies
console.log('\n📚 Checking dependencies...');
const requiredDeps = [
  '@playwright/test',
  'jest',
  'jest-environment-jsdom'
];

const requiredProdDeps = [
  'qrcode'
];

let allDepsExist = true;

requiredDeps.forEach(dep => {
  if (pkg.devDependencies && pkg.devDependencies[dep]) {
    console.log(`✅ ${dep}: ${pkg.devDependencies[dep]}`);
  } else {
    console.log(`❌ ${dep} - MISSING from devDependencies`);
    allDepsExist = false;
  }
});

requiredProdDeps.forEach(dep => {
  if (pkg.dependencies && pkg.dependencies[dep]) {
    console.log(`✅ ${dep}: ${pkg.dependencies[dep]}`);
  } else {
    console.log(`❌ ${dep} - MISSING from dependencies`);
    allDepsExist = false;
  }
});

// Validate test file structure
console.log('\n🏗️ Validating test file structure...');

// Check auth test
const authTestPath = path.join(process.cwd(), 'tests/e2e/auth.spec.ts');
if (fs.existsSync(authTestPath)) {
  const authContent = fs.readFileSync(authTestPath, 'utf8');
  if (authContent.includes('Authentication Flow')) {
    console.log('✅ Auth tests properly structured');
  } else {
    console.log('❌ Auth tests missing proper test.describe');
    allFilesExist = false;
  }
}

// Check MFA test
const mfaTestPath = path.join(process.cwd(), 'tests/e2e/mfa.spec.ts');
if (fs.existsSync(mfaTestPath)) {
  const mfaContent = fs.readFileSync(mfaTestPath, 'utf8');
  if (mfaContent.includes('Multi-Factor Authentication')) {
    console.log('✅ MFA tests properly structured');
  } else {
    console.log('❌ MFA tests missing proper structure');
    allFilesExist = false;
  }
}

// Check helper files
const authHelperPath = path.join(process.cwd(), 'tests/helpers/auth.ts');
if (fs.existsSync(authHelperPath)) {
  const authHelperContent = fs.readFileSync(authHelperPath, 'utf8');
  if (authHelperContent.includes('loginAsAdmin')) {
    console.log('✅ Auth helpers properly implemented');
  } else {
    console.log('❌ Auth helpers missing loginAsAdmin function');
    allFilesExist = false;
  }
}

// Summary
console.log('\n📋 Setup Validation Summary');
console.log('='.repeat(40));

if (allFilesExist && allScriptsExist && allDepsExist) {
  console.log('🎉 ALL CHECKS PASSED!');
  console.log('✅ E2E testing setup is complete and ready');
  console.log('\n🚀 Next steps:');
  console.log('  1. Run "npm run playwright:install" to install browser binaries');
  console.log('  2. Start your development server');
  console.log('  3. Run "npm run test:e2e" to execute tests');
  console.log('  4. Run "npm run test:e2e:ui" for interactive test execution');
  process.exit(0);
} else {
  console.log('❌ SOME CHECKS FAILED');
  console.log('Please review the missing components above');
  process.exit(1);
}