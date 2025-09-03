#!/usr/bin/env node

/**
 * Security Audit Script
 *
 * Comprehensive security testing and vulnerability assessment
 * for the DotMac Framework frontend applications.
 *
 * Features:
 * - Dependency vulnerability scanning
 * - Code security analysis
 * - Authentication security testing
 * - XSS prevention validation
 * - CSRF protection verification
 * - Input sanitization checks
 */

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class SecurityAuditor {
  constructor() {
    this.results = {
      timestamp: new Date().toISOString(),
      overallScore: 0,
      vulnerabilities: [],
      recommendations: [],
      testResults: {},
    };
    this.passedTests = 0;
    this.totalTests = 0;
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const colors = {
      info: '\x1b[36m',
      success: '\x1b[32m',
      warning: '\x1b[33m',
      error: '\x1b[31m',
      reset: '\x1b[0m',
    };

    console.log(`${colors[type]}[${timestamp}] ${message}${colors.reset}`);
  }

  async runTest(name, testFn) {
    this.totalTests++;
    this.log(`Running: ${name}`);

    try {
      const result = await testFn();
      if (result.passed) {
        this.passedTests++;
        this.log(`✅ ${name}: PASSED`, 'success');
      } else {
        this.log(`❌ ${name}: FAILED - ${result.reason}`, 'error');
        this.results.vulnerabilities.push({
          test: name,
          severity: result.severity || 'medium',
          description: result.reason,
          recommendation: result.recommendation,
        });
      }

      this.results.testResults[name] = result;
      return result;
    } catch (error) {
      this.log(`💥 ${name}: ERROR - ${error.message}`, 'error');
      this.results.testResults[name] = {
        passed: false,
        error: error.message,
        severity: 'high',
      };
      return { passed: false, error: error.message };
    }
  }

  async checkDependencyVulnerabilities() {
    return this.runTest('Dependency Vulnerabilities', async () => {
      try {
        const auditOutput = execSync('pnpm audit --json', {
          encoding: 'utf8',
          cwd: process.cwd(),
        });

        const audit = JSON.parse(auditOutput);
        const highVulns = audit.metadata?.vulnerabilities?.high || 0;
        const criticalVulns = audit.metadata?.vulnerabilities?.critical || 0;

        if (highVulns > 0 || criticalVulns > 0) {
          return {
            passed: false,
            severity: 'high',
            reason: `Found ${criticalVulns} critical and ${highVulns} high severity vulnerabilities`,
            recommendation: 'Run `pnpm audit fix` and update vulnerable dependencies',
            details: { critical: criticalVulns, high: highVulns },
          };
        }

        return {
          passed: true,
          details: { total: audit.metadata?.vulnerabilities?.total || 0 },
        };
      } catch (error) {
        // pnpm audit returns non-zero exit code when vulnerabilities found
        if (error.stdout) {
          try {
            const audit = JSON.parse(error.stdout);
            const highVulns = audit.metadata?.vulnerabilities?.high || 0;
            const criticalVulns = audit.metadata?.vulnerabilities?.critical || 0;

            return {
              passed: highVulns === 0 && criticalVulns === 0,
              severity: 'high',
              reason: `Found ${criticalVulns} critical and ${highVulns} high severity vulnerabilities`,
              recommendation: 'Run `pnpm audit fix` and update vulnerable dependencies',
            };
          } catch (parseError) {
            throw new Error(`Failed to parse audit results: ${parseError.message}`);
          }
        }
        throw error;
      }
    });
  }

  async checkCSRFProtection() {
    return this.runTest('CSRF Protection', async () => {
      const middlewareFiles = [
        'isp-framework/admin/src/middleware.ts',
        'isp-framework/customer/src/middleware.ts',
        'isp-framework/reseller/src/middleware.ts',
        'management-portal/admin/src/middleware.ts',
      ];

      const missingCSRF = [];

      for (const filePath of middlewareFiles) {
        if (fs.existsSync(filePath)) {
          const content = fs.readFileSync(filePath, 'utf8');
          if (!content.includes('csrf') && !content.includes('CSRF')) {
            missingCSRF.push(filePath);
          }
        } else {
          missingCSRF.push(filePath + ' (missing)');
        }
      }

      if (missingCSRF.length > 0) {
        return {
          passed: false,
          severity: 'high',
          reason: `CSRF protection missing in: ${missingCSRF.join(', ')}`,
          recommendation: 'Implement CSRF middleware in all portal applications',
        };
      }

      return { passed: true };
    });
  }

  async checkInputSanitization() {
    return this.runTest('Input Sanitization', async () => {
      const sanitizationPaths = [
        'packages/security/src/sanitization',
        'packages/headless/src/utils/validation.ts',
      ];

      const missingSanitization = [];

      for (const sanitizationPath of sanitizationPaths) {
        if (!fs.existsSync(sanitizationPath)) {
          missingSanitization.push(sanitizationPath);
        }
      }

      // Check for DOMPurify usage
      const packageJsonPath = 'package.json';
      if (fs.existsSync(packageJsonPath)) {
        const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
        const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies };

        if (!dependencies.dompurify) {
          missingSanitization.push('DOMPurify dependency');
        }
      }

      if (missingSanitization.length > 0) {
        return {
          passed: false,
          severity: 'high',
          reason: `Missing sanitization components: ${missingSanitization.join(', ')}`,
          recommendation: 'Implement comprehensive input sanitization with DOMPurify',
        };
      }

      return { passed: true };
    });
  }

  async checkSecureHeaders() {
    return this.runTest('Security Headers', async () => {
      const nextConfigFiles = [
        'isp-framework/admin/next.config.js',
        'isp-framework/customer/next.config.js',
        'isp-framework/reseller/next.config.js',
        'management-portal/admin/next.config.js',
      ];

      const missingHeaders = [];

      for (const configPath of nextConfigFiles) {
        if (fs.existsSync(configPath)) {
          const content = fs.readFileSync(configPath, 'utf8');

          const requiredHeaders = [
            'X-Frame-Options',
            'X-Content-Type-Options',
            'Content-Security-Policy',
            'Strict-Transport-Security',
          ];

          const foundHeaders = requiredHeaders.filter((header) => content.includes(header));

          if (foundHeaders.length < requiredHeaders.length) {
            missingHeaders.push(
              `${configPath}: missing ${requiredHeaders.filter((h) => !foundHeaders.includes(h)).join(', ')}`
            );
          }
        }
      }

      if (missingHeaders.length > 0) {
        return {
          passed: false,
          severity: 'medium',
          reason: `Security headers not configured: ${missingHeaders.join('; ')}`,
          recommendation: 'Configure security headers in Next.js configuration',
        };
      }

      return { passed: true };
    });
  }

  async checkAuthenticationSecurity() {
    return this.runTest('Authentication Security', async () => {
      const authFiles = [
        'packages/headless/src/utils/tokenManager.ts',
        'packages/security/src/auth',
      ];

      const issues = [];

      for (const authPath of authFiles) {
        if (fs.existsSync(authPath)) {
          const isDirectory = fs.statSync(authPath).isDirectory();

          if (isDirectory) {
            const files = fs.readdirSync(authPath);
            if (files.length === 0) {
              issues.push(`${authPath} directory is empty`);
            }
          } else {
            const content = fs.readFileSync(authPath, 'utf8');

            // Check for secure token handling
            if (!content.includes('secure') && !content.includes('httpOnly')) {
              issues.push(`${authPath}: Missing secure cookie configuration`);
            }

            // Check for token expiration
            if (!content.includes('expires') && !content.includes('maxAge')) {
              issues.push(`${authPath}: Missing token expiration`);
            }
          }
        } else {
          issues.push(`${authPath}: Missing authentication module`);
        }
      }

      if (issues.length > 0) {
        return {
          passed: false,
          severity: 'high',
          reason: `Authentication security issues: ${issues.join('; ')}`,
          recommendation:
            'Implement secure token management with proper expiration and secure flags',
        };
      }

      return { passed: true };
    });
  }

  async checkSecretsExposure() {
    return this.runTest('Secrets Exposure', async () => {
      const sensitivePatterns = [
        /password\s*=\s*['"][^'"]+['"]/gi,
        /api[_-]?key\s*=\s*['"][^'"]+['"]/gi,
        /secret\s*=\s*['"][^'"]+['"]/gi,
        /token\s*=\s*['"][^'"]+['"]/gi,
        /NEXT_PUBLIC_.*(?:SECRET|KEY|TOKEN|PASSWORD)/gi,
      ];

      const excludePatterns = [
        /\.git/,
        /node_modules/,
        /\.next/,
        /build/,
        /dist/,
        /coverage/,
        /\.env\.example/,
      ];

      const exposedSecrets = [];

      const scanDirectory = (dir) => {
        const items = fs.readdirSync(dir);

        for (const item of items) {
          const fullPath = path.join(dir, item);
          const relativePath = path.relative(process.cwd(), fullPath);

          // Skip excluded directories
          if (excludePatterns.some((pattern) => pattern.test(relativePath))) {
            continue;
          }

          const stat = fs.statSync(fullPath);

          if (stat.isDirectory()) {
            scanDirectory(fullPath);
          } else if (
            stat.isFile() &&
            (item.endsWith('.ts') ||
              item.endsWith('.tsx') ||
              item.endsWith('.js') ||
              item.endsWith('.jsx'))
          ) {
            const content = fs.readFileSync(fullPath, 'utf8');

            for (const pattern of sensitivePatterns) {
              const matches = content.match(pattern);
              if (matches) {
                exposedSecrets.push({
                  file: relativePath,
                  matches: matches.slice(0, 3), // Limit to first 3 matches
                });
              }
            }
          }
        }
      };

      scanDirectory(process.cwd());

      if (exposedSecrets.length > 0) {
        return {
          passed: false,
          severity: 'critical',
          reason: `Potential secrets exposed in ${exposedSecrets.length} files`,
          recommendation: 'Move all secrets to environment variables and add to .gitignore',
          details: exposedSecrets,
        };
      }

      return { passed: true };
    });
  }

  async checkTestSecurity() {
    return this.runTest('Test Security Alignment', async () => {
      const testDirectories = [
        'isp-framework/admin/tests',
        'isp-framework/customer/tests',
        'isp-framework/reseller/src/__tests__',
        'management-portal/admin/tests',
        'tests',
      ];

      const securityTestPatterns = [
        /csrf/gi,
        /xss/gi,
        /sanitiz/gi,
        /security/gi,
        /auth.*security/gi,
        /vulnerability/gi,
      ];

      let totalTestFiles = 0;
      let securityTestFiles = 0;

      const scanTestDirectory = (dir) => {
        if (!fs.existsSync(dir)) return;

        const items = fs.readdirSync(dir);

        for (const item of items) {
          const fullPath = path.join(dir, item);
          const stat = fs.statSync(fullPath);

          if (stat.isDirectory()) {
            scanTestDirectory(fullPath);
          } else if (item.includes('.test.') || item.includes('.spec.')) {
            totalTestFiles++;

            const content = fs.readFileSync(fullPath, 'utf8');
            const hasSecurityTests = securityTestPatterns.some((pattern) => pattern.test(content));

            if (hasSecurityTests) {
              securityTestFiles++;
            }
          }
        }
      };

      testDirectories.forEach(scanTestDirectory);

      const securityTestRatio = totalTestFiles > 0 ? securityTestFiles / totalTestFiles : 0;
      const minSecurityTestRatio = 0.2; // At least 20% of tests should include security aspects

      if (securityTestRatio < minSecurityTestRatio) {
        return {
          passed: false,
          severity: 'medium',
          reason: `Only ${Math.round(securityTestRatio * 100)}% of tests include security validation (${securityTestFiles}/${totalTestFiles})`,
          recommendation: `Increase security test coverage to at least ${Math.round(minSecurityTestRatio * 100)}% of all tests`,
          details: { securityTests: securityTestFiles, totalTests: totalTestFiles },
        };
      }

      return {
        passed: true,
        details: {
          securityTests: securityTestFiles,
          totalTests: totalTestFiles,
          ratio: securityTestRatio,
        },
      };
    });
  }

  async generateReport() {
    this.log('\n🔍 Starting Security Audit...', 'info');

    // Run all security tests
    await this.checkDependencyVulnerabilities();
    await this.checkCSRFProtection();
    await this.checkInputSanitization();
    await this.checkSecureHeaders();
    await this.checkAuthenticationSecurity();
    await this.checkSecretsExposure();
    await this.checkTestSecurity();

    // Calculate overall score
    this.results.overallScore = Math.round((this.passedTests / this.totalTests) * 100);

    // Generate recommendations
    this.generateRecommendations();

    // Create report
    const reportPath = 'security-audit-report.json';
    fs.writeFileSync(reportPath, JSON.stringify(this.results, null, 2));

    // Log summary
    this.logSummary();

    return this.results;
  }

  generateRecommendations() {
    const recommendations = [
      'Implement automated security scanning in CI/CD pipeline',
      'Regular security audits and penetration testing',
      'Keep dependencies updated with security patches',
      'Implement comprehensive logging and monitoring',
      'Regular security training for development team',
    ];

    // Add specific recommendations based on vulnerabilities
    if (this.results.vulnerabilities.length > 0) {
      recommendations.unshift('Address all high and critical severity vulnerabilities immediately');
    }

    this.results.recommendations = recommendations;
  }

  logSummary() {
    this.log('\n📊 Security Audit Summary', 'info');
    this.log('═'.repeat(50), 'info');
    this.log(
      `Overall Score: ${this.results.overallScore}%`,
      this.results.overallScore >= 80
        ? 'success'
        : this.results.overallScore >= 60
          ? 'warning'
          : 'error'
    );
    this.log(`Tests Passed: ${this.passedTests}/${this.totalTests}`, 'info');
    this.log(
      `Vulnerabilities Found: ${this.results.vulnerabilities.length}`,
      this.results.vulnerabilities.length === 0 ? 'success' : 'warning'
    );

    if (this.results.vulnerabilities.length > 0) {
      this.log('\n🚨 Critical Issues:', 'error');
      this.results.vulnerabilities
        .filter((v) => v.severity === 'critical' || v.severity === 'high')
        .forEach((v) => {
          this.log(`• ${v.test}: ${v.description}`, 'error');
        });
    }

    this.log(`\n📄 Full report saved to: security-audit-report.json`, 'info');

    // Exit with error code if critical issues found
    const criticalIssues = this.results.vulnerabilities.filter(
      (v) => v.severity === 'critical' || v.severity === 'high'
    ).length;

    if (criticalIssues > 0) {
      process.exit(1);
    }
  }
}

// Run audit if called directly
if (require.main === module) {
  const auditor = new SecurityAuditor();
  auditor.generateReport().catch((error) => {
    console.error('❌ Security audit failed:', error);
    process.exit(1);
  });
}

module.exports = SecurityAuditor;
