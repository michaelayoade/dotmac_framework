#!/usr/bin/env node

/**
 * DotMac Frontend Build System
 *
 * Comprehensive build, test, and deployment orchestration script
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const chalk = require('chalk');

const PACKAGES = [
  '@dotmac/typescript-config',
  '@dotmac/registry',
  '@dotmac/security',
  '@dotmac/testing',
  '@dotmac/monitoring',
  '@dotmac/eslint-config',
  '@dotmac/primitives',
  '@dotmac/patterns',
  '@dotmac/headless',
  '@dotmac/styled-components',
];

const APPS = ['admin', 'customer', 'reseller'];

class BuildSystem {
  constructor() {
    this.startTime = Date.now();
    this.results = {
      packages: {},
      apps: {},
      tests: {},
      errors: [],
    };
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const colors = {
      info: chalk.blue,
      success: chalk.green,
      warning: chalk.yellow,
      error: chalk.red,
    };

    console.log(`${chalk.gray(timestamp)} ${colors[type]('●')} ${message}`);
  }

  async exec(command, options = {}) {
    return new Promise((resolve, reject) => {
      const child = spawn('sh', ['-c', command], {
        stdio: options.silent ? 'pipe' : 'inherit',
        ...options,
      });

      let stdout = '';
      let stderr = '';

      if (options.silent) {
        child.stdout.on('data', (data) => {
          stdout += data.toString();
        });

        child.stderr.on('data', (data) => {
          stderr += data.toString();
        });
      }

      child.on('close', (code) => {
        if (code === 0) {
          resolve({ stdout, stderr, code });
        } else {
          reject({ stdout, stderr, code });
        }
      });
    });
  }

  async checkPrerequisites() {
    this.log('🔍 Checking prerequisites...');

    const checks = [
      { command: 'node --version', name: 'Node.js' },
      { command: 'pnpm --version', name: 'pnpm' },
      { command: 'turbo --version', name: 'Turbo' },
    ];

    for (const check of checks) {
      try {
        const result = await this.exec(check.command, { silent: true });
        this.log(`✅ ${check.name}: ${result.stdout.trim()}`, 'success');
      } catch (error) {
        this.log(`❌ ${check.name} not found`, 'error');
        throw new Error(`Missing prerequisite: ${check.name}`);
      }
    }
  }

  async installDependencies() {
    this.log('📦 Installing dependencies...');

    try {
      await this.exec('pnpm install --frozen-lockfile');
      this.log('✅ Dependencies installed successfully', 'success');
    } catch (error) {
      this.log('❌ Failed to install dependencies', 'error');
      this.results.errors.push('Dependencies installation failed');
      throw error;
    }
  }

  async typeCheck() {
    this.log('🔍 Running type check...');

    try {
      await this.exec('turbo run type-check');
      this.log('✅ Type check passed', 'success');
    } catch (error) {
      this.log('❌ Type check failed', 'error');
      this.results.errors.push('Type check failed');
      throw error;
    }
  }

  async lint() {
    this.log('🔧 Running linting...');

    try {
      await this.exec('turbo run lint');
      this.log('✅ Linting passed', 'success');
    } catch (error) {
      this.log('❌ Linting failed', 'error');
      this.results.errors.push('Linting failed');
      throw error;
    }
  }

  async runTests(type = 'all') {
    this.log(`🧪 Running ${type} tests...`);

    const testCommands = {
      unit: 'pnpm run test:unit',
      integration: 'pnpm run test:integration',
      e2e: 'pnpm run test:e2e',
      a11y: 'pnpm run test:a11y',
      all: 'pnpm run test:ci',
    };

    try {
      const command = testCommands[type] || testCommands.all;
      await this.exec(command);
      this.log(`✅ ${type} tests passed`, 'success');
      this.results.tests[type] = 'passed';
    } catch (error) {
      this.log(`❌ ${type} tests failed`, 'error');
      this.results.tests[type] = 'failed';
      this.results.errors.push(`${type} tests failed`);

      if (type === 'unit' || type === 'integration') {
        throw error; // Critical tests
      }
    }
  }

  async buildPackages() {
    this.log('🏗️  Building packages...');

    for (const pkg of PACKAGES) {
      try {
        this.log(`Building ${pkg}...`);
        await this.exec(`turbo run build --filter=${pkg}`);
        this.log(`✅ ${pkg} built successfully`, 'success');
        this.results.packages[pkg] = 'success';
      } catch (error) {
        this.log(`❌ ${pkg} build failed`, 'error');
        this.results.packages[pkg] = 'failed';
        this.results.errors.push(`${pkg} build failed`);
        throw error;
      }
    }
  }

  async buildApps() {
    this.log('🏗️  Building applications...');

    for (const app of APPS) {
      try {
        this.log(`Building ${app} app...`);
        await this.exec(`turbo run build --filter=./apps/${app}`);
        this.log(`✅ ${app} app built successfully`, 'success');
        this.results.apps[app] = 'success';
      } catch (error) {
        this.log(`❌ ${app} app build failed`, 'error');
        this.results.apps[app] = 'failed';
        this.results.errors.push(`${app} app build failed`);
        throw error;
      }
    }
  }

  async buildStorybook() {
    this.log('📚 Building Storybook...');

    try {
      await this.exec('turbo run storybook:build');
      this.log('✅ Storybook built successfully', 'success');
    } catch (error) {
      this.log('❌ Storybook build failed', 'error');
      this.results.errors.push('Storybook build failed');
      // Don't throw - Storybook is not critical for deployment
    }
  }

  async runSecurityAudit() {
    this.log('🔒 Running security audit...');

    try {
      await this.exec('pnpm audit --audit-level moderate');
      this.log('✅ Security audit passed', 'success');
    } catch (error) {
      this.log('⚠️  Security vulnerabilities found', 'warning');
      this.results.errors.push('Security vulnerabilities detected');
      // Don't throw - handle based on severity
    }
  }

  async generateBuildReport() {
    const endTime = Date.now();
    const duration = endTime - this.startTime;

    const report = {
      timestamp: new Date().toISOString(),
      duration: `${Math.round(duration / 1000)}s`,
      status: this.results.errors.length === 0 ? 'SUCCESS' : 'FAILED',
      results: this.results,
      environment: {
        node: process.version,
        platform: process.platform,
        architecture: process.arch,
        ci: !!process.env.CI,
      },
    };

    // Write report to file
    const reportPath = path.join(process.cwd(), 'build-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    this.log(`📊 Build report generated: ${reportPath}`);
    return report;
  }

  async printSummary() {
    this.log('\n🎯 Build Summary:', 'info');
    this.log('─'.repeat(50));

    // Packages summary
    const packagesSuccess = Object.values(this.results.packages).filter(
      (r) => r === 'success'
    ).length;
    const packagesTotal = PACKAGES.length;
    this.log(`📦 Packages: ${packagesSuccess}/${packagesTotal} successful`);

    // Apps summary
    const appsSuccess = Object.values(this.results.apps).filter((r) => r === 'success').length;
    const appsTotal = APPS.length;
    this.log(`🚀 Apps: ${appsSuccess}/${appsTotal} successful`);

    // Tests summary
    const testsRun = Object.keys(this.results.tests).length;
    const testsPassed = Object.values(this.results.tests).filter((r) => r === 'passed').length;
    this.log(`🧪 Tests: ${testsPassed}/${testsRun} passed`);

    // Errors
    if (this.results.errors.length > 0) {
      this.log(`❌ Errors: ${this.results.errors.length}`, 'error');
      this.results.errors.forEach((error) => {
        this.log(`   • ${error}`, 'error');
      });
    } else {
      this.log('✅ No errors', 'success');
    }

    this.log('─'.repeat(50));

    const duration = Date.now() - this.startTime;
    const status = this.results.errors.length === 0 ? 'SUCCESS' : 'FAILED';
    const statusColor = status === 'SUCCESS' ? 'success' : 'error';

    this.log(`🏁 Build completed in ${Math.round(duration / 1000)}s - ${status}`, statusColor);
  }

  async run(options = {}) {
    try {
      this.log('🚀 Starting DotMac Frontend Build System');

      if (!options.skipPrerequisites) {
        await this.checkPrerequisites();
      }

      if (!options.skipInstall) {
        await this.installDependencies();
      }

      if (!options.skipTypeCheck) {
        await this.typeCheck();
      }

      if (!options.skipLint) {
        await this.lint();
      }

      if (!options.skipTests) {
        if (options.testType) {
          await this.runTests(options.testType);
        } else {
          await this.runTests('unit');
          await this.runTests('integration');
          await this.runTests('a11y');
        }
      }

      if (!options.skipSecurity) {
        await this.runSecurityAudit();
      }

      if (!options.skipPackages) {
        await this.buildPackages();
      }

      if (!options.skipApps) {
        await this.buildApps();
      }

      if (!options.skipStorybook) {
        await this.buildStorybook();
      }

      const report = await this.generateBuildReport();
      await this.printSummary();

      return report;
    } catch (error) {
      this.log(`💥 Build failed: ${error.message}`, 'error');
      await this.generateBuildReport();
      await this.printSummary();
      process.exit(1);
    }
  }
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  const options = {};

  // Parse command line arguments
  args.forEach((arg) => {
    if (arg.startsWith('--skip-')) {
      const key = arg.replace('--skip-', '').replace(/-([a-z])/g, (g) => g[1].toUpperCase());
      options[`skip${key.charAt(0).toUpperCase() + key.slice(1)}`] = true;
    } else if (arg.startsWith('--test-type=')) {
      options.testType = arg.split('=')[1];
    }
  });

  const buildSystem = new BuildSystem();
  buildSystem.run(options);
}

module.exports = { BuildSystem };
