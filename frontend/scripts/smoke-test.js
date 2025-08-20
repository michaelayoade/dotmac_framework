#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */

const { execSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const chalk = require('chalk');

class FrontendSmokeTest {
  constructor() {
    this.results = {
      passed: 0,
      failed: 0,
      warnings: 0,
      tests: [],
    };
  }

  log(level, message, details = '') {
    const _timestamp = new Date().toISOString();
    const prefix = {
      info: chalk.blue('ℹ️'),
      success: chalk.green('✅'),
      warning: chalk.yellow('⚠️'),
      error: chalk.red('❌'),
    }[level];

    console.log(`${prefix} ${message}`);
    if (details) {
      console.log(`   ${chalk.gray(details)}`);
    }
  }

  async runTest(name, testFn) {
    this.log('info', `Running ${name}...`);
    const startTime = Date.now();

    try {
      await testFn();
      const duration = Date.now() - startTime;
      this.log('success', `${name} passed (${duration}ms)`);
      this.results.passed++;
      this.results.tests.push({ name, status: 'passed', duration });
    } catch (error) {
      const duration = Date.now() - startTime;
      this.log('error', `${name} failed (${duration}ms)`, error.message);
      this.results.failed++;
      this.results.tests.push({
        name,
        status: 'failed',
        duration,
        error: error.message,
      });
    }
  }

  async runWarningTest(name, testFn) {
    this.log('info', `Running ${name}...`);
    const startTime = Date.now();

    try {
      await testFn();
      const duration = Date.now() - startTime;
      this.log('success', `${name} passed (${duration}ms)`);
      this.results.passed++;
      this.results.tests.push({ name, status: 'passed', duration });
    } catch (error) {
      const duration = Date.now() - startTime;
      this.log('warning', `${name} has warnings (${duration}ms)`, error.message);
      this.results.warnings++;
      this.results.tests.push({
        name,
        status: 'warning',
        duration,
        error: error.message,
      });
    }
  }

  execCommand(command, options = {}) {
    try {
      const result = execSync(command, {
        encoding: 'utf8',
        cwd: process.cwd(),
        ...options,
      });
      return result.toString().trim();
    } catch (error) {
      throw new Error(`Command failed: ${command}\n${error.message}`);
    }
  }

  checkFileExists(filePath) {
    if (!fs.existsSync(filePath)) {
      throw new Error(`Required file not found: ${filePath}`);
    }
  }

  checkPackageJson() {
    this.checkFileExists('package.json');
    const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));

    const requiredScripts = [
      'test',
      'test:unit',
      'test:integration',
      'test:e2e',
      'lint',
      'type-check',
      'build',
      'dev',
    ];

    const missingScripts = requiredScripts.filter((script) => !pkg.scripts[script]);
    if (missingScripts.length > 0) {
      throw new Error(`Missing required scripts: ${missingScripts.join(', ')}`);
    }
  }

  checkTsConfig() {
    this.checkFileExists('tsconfig.json');
    const tsconfig = JSON.parse(fs.readFileSync('tsconfig.json', 'utf8'));

    if (!tsconfig.compilerOptions?.strict) {
      throw new Error('TypeScript strict mode is not enabled');
    }

    const strictRules = [
      'noUnusedLocals',
      'noUnusedParameters',
      'noImplicitReturns',
      'noFallthroughCasesInSwitch',
    ];

    const missingRules = strictRules.filter((rule) => !tsconfig.compilerOptions[rule]);
    if (missingRules.length > 0) {
      throw new Error(`Missing strict TypeScript rules: ${missingRules.join(', ')}`);
    }
  }

  checkEslintConfig() {
    const configFiles = ['.eslintrc.js', '.eslintrc.json', 'eslint.config.js'];
    const hasConfig = configFiles.some((file) => fs.existsSync(file));

    if (!hasConfig) {
      throw new Error('No ESLint configuration found');
    }
  }

  checkPrettierConfig() {
    const configFiles = ['.prettierrc.js', '.prettierrc.json', 'prettier.config.js'];
    const hasConfig = configFiles.some((file) => fs.existsSync(file));

    if (!hasConfig) {
      throw new Error('No Prettier configuration found');
    }
  }

  checkTestConfig() {
    const _configFiles = ['jest.config.js', 'jest.config.json', 'playwright.config.ts'];
    const hasJest = fs.existsSync('jest.config.js') || fs.existsSync('jest.config.json');
    const hasPlaywright = fs.existsSync('playwright.config.ts');

    if (!hasJest) {
      throw new Error('No Jest configuration found');
    }

    if (!hasPlaywright) {
      throw new Error('No Playwright configuration found');
    }
  }

  checkWorkspaceStructure() {
    const requiredDirs = ['packages', 'apps', 'tests', '__mocks__', 'test-utils'];
    const missingDirs = requiredDirs.filter((dir) => !fs.existsSync(dir));

    if (missingDirs.length > 0) {
      throw new Error(`Missing required directories: ${missingDirs.join(', ')}`);
    }

    // Check package structure
    const packagesDir = 'packages';
    const expectedPackages = ['headless', 'primitives', 'styled-components'];
    const actualPackages = fs
      .readdirSync(packagesDir)
      .filter((item) => fs.statSync(path.join(packagesDir, item)).isDirectory());

    const missingPackages = expectedPackages.filter((pkg) => !actualPackages.includes(pkg));
    if (missingPackages.length > 0) {
      throw new Error(`Missing required packages: ${missingPackages.join(', ')}`);
    }
  }

  checkImportPaths() {
    // Check for common import issues
    const result = this.execCommand(
      'grep -r "from.*@dotmac" packages apps tests --include="*.ts" --include="*.tsx" | head -10 || true'
    );

    if (result.includes('@dotmac/headless/src') || result.includes('@dotmac/primitives/src')) {
      throw new Error('Found imports using src paths instead of package root');
    }

    // Check for relative imports crossing package boundaries
    const relativeImports = this.execCommand(
      'grep -r "from.*\\.\\./" packages --include="*.ts" --include="*.tsx" | grep -v node_modules || true'
    );

    if (relativeImports.includes('../packages/')) {
      throw new Error('Found relative imports crossing package boundaries');
    }
  }

  testTypeScript() {
    this.execCommand('pnpm type-check', { stdio: 'pipe' });
  }

  testLinting() {
    this.execCommand('pnpm lint', { stdio: 'pipe' });
  }

  testPrettier() {
    this.execCommand('pnpm format --check', { stdio: 'pipe' });
  }

  testUnitTests() {
    this.execCommand('pnpm test:unit --passWithNoTests --watchAll=false', {
      stdio: 'pipe',
      env: { ...process.env, CI: 'true' },
    });
  }

  testBuild() {
    // Test that packages can be built
    this.execCommand('pnpm build', { stdio: 'pipe' });
  }

  generateReport() {
    const total = this.results.passed + this.results.failed + this.results.warnings;

    console.log(`\n${'='.repeat(60)}`);
    console.log(chalk.bold.blue('🔍 Frontend Smoke Test Results'));
    console.log('='.repeat(60));

    console.log(`Total Tests: ${total}`);
    console.log(chalk.green(`✅ Passed: ${this.results.passed}`));
    console.log(chalk.yellow(`⚠️  Warnings: ${this.results.warnings}`));
    console.log(chalk.red(`❌ Failed: ${this.results.failed}`));

    if (this.results.failed > 0) {
      console.log(`\n${chalk.red.bold('Failed Tests:')}`);
      this.results.tests
        .filter((test) => test.status === 'failed')
        .forEach((test) => {
          console.log(chalk.red(`  ❌ ${test.name}: ${test.error}`));
        });
    }

    if (this.results.warnings > 0) {
      console.log(`\n${chalk.yellow.bold('Warnings:')}`);
      this.results.tests
        .filter((test) => test.status === 'warning')
        .forEach((test) => {
          console.log(chalk.yellow(`  ⚠️  ${test.name}: ${test.error}`));
        });
    }

    const success = this.results.failed === 0;
    console.log(`\n${'='.repeat(60)}`);
    console.log(
      success
        ? chalk.green.bold('🎉 All smoke tests passed!')
        : chalk.red.bold('💥 Smoke tests failed!')
    );
    console.log('='.repeat(60));

    return success;
  }

  async run() {
    console.log(chalk.blue.bold('🚀 Running Frontend Smoke Tests...\n'));

    // Configuration checks
    await this.runTest('Package.json validation', () => this.checkPackageJson());
    await this.runTest('TypeScript configuration', () => this.checkTsConfig());
    await this.runTest('ESLint configuration', () => this.checkEslintConfig());
    await this.runTest('Prettier configuration', () => this.checkPrettierConfig());
    await this.runTest('Test configuration', () => this.checkTestConfig());

    // Structure checks
    await this.runTest('Workspace structure', () => this.checkWorkspaceStructure());
    await this.runTest('Import path validation', () => this.checkImportPaths());

    // Code quality checks
    await this.runTest('TypeScript type checking', () => this.testTypeScript());
    await this.runTest('ESLint validation', () => this.testLinting());
    await this.runWarningTest('Code formatting', () => this.testPrettier());

    // Functionality checks
    await this.runTest('Unit tests', () => this.testUnitTests());
    await this.runTest('Build process', () => this.testBuild());

    const success = this.generateReport();
    process.exit(success ? 0 : 1);
  }
}

// Run smoke tests
if (require.main === module) {
  const smokeTest = new FrontendSmokeTest();
  smokeTest.run().catch((error) => {
    console.error(chalk.red('Smoke test runner failed:'), error);
    process.exit(1);
  });
}

module.exports = FrontendSmokeTest;
