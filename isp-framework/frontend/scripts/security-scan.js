#!/usr/bin/env node

/**
 * Security Testing and Vulnerability Scanner
 * Comprehensive security analysis for DotMac Frontend
 * Includes CSP, SRI, dependency scanning, and code analysis
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawn } = require('child_process');
const chalk = require('chalk');

class SecurityScanner {
  constructor() {
    this.results = {
      csp: { violations: [], warnings: [], score: 0 },
      sri: { missing: [], present: [], score: 0 },
      dependencies: { vulnerabilities: [], outdated: [], score: 0 },
      code: { issues: [], patterns: [], score: 0 },
      permissions: { issues: [], score: 0 },
      overall: { score: 0, grade: 'F' },
    };

    this.weightings = {
      csp: 0.25,
      sri: 0.2,
      dependencies: 0.3,
      code: 0.2,
      permissions: 0.05,
    };
  }

  async runSecurityScan() {
    console.log(chalk.blue('🔒 Starting Security Vulnerability Scan...\\n'));

    try {
      await this.scanCSP();
      await this.scanSRI();
      await this.scanDependencies();
      await this.scanCode();
      await this.scanPermissions();
      await this.calculateOverallScore();
      await this.generateSecurityReport();

      if (this.results.overall.score < 80) {
        console.error(chalk.red('❌ Security scan failed! Score below threshold.'));
        process.exit(1);
      } else {
        console.log(
          chalk.green(`✅ Security scan passed! Score: ${this.results.overall.score}/100`)
        );
      }
    } catch (error) {
      console.error(chalk.red(`💥 Security scan failed: ${error.message}`));
      process.exit(1);
    }
  }

  async scanCSP() {
    console.log(chalk.yellow('🛡️  Scanning Content Security Policy...'));

    const cspFiles = this.findCSPFiles();

    if (cspFiles.length === 0) {
      this.results.csp.violations.push('No CSP configuration files found');
      this.results.csp.score = 0;
      return;
    }

    let totalScore = 0;
    let fileCount = 0;

    for (const file of cspFiles) {
      const content = fs.readFileSync(file, 'utf8');
      const cspAnalysis = this.analyzeCSP(content, file);

      totalScore += cspAnalysis.score;
      fileCount++;

      this.results.csp.violations.push(...cspAnalysis.violations);
      this.results.csp.warnings.push(...cspAnalysis.warnings);
    }

    this.results.csp.score = fileCount > 0 ? totalScore / fileCount : 0;
    console.log(
      chalk.green(`  ✓ CSP Analysis complete. Score: ${this.results.csp.score.toFixed(1)}/100`)
    );
  }

  findCSPFiles() {
    const files = [];
    const searchPaths = [
      'next.config.js',
      'apps/*/next.config.js',
      'middleware.ts',
      'apps/*/middleware.ts',
      'apps/*/src/middleware.ts',
    ];

    for (const pattern of searchPaths) {
      const matches = this.glob(pattern);
      files.push(...matches);
    }

    return files.filter((file) => fs.existsSync(file));
  }

  glob(pattern) {
    // Simple glob implementation for CSP file patterns
    if (pattern.includes('*')) {
      const basePath = pattern.split('*')[0];
      const suffix = pattern.split('*')[1];

      try {
        if (fs.existsSync(basePath.slice(0, -1))) {
          const dirs = fs.readdirSync(basePath.slice(0, -1), { withFileTypes: true });
          return dirs
            .filter((d) => d.isDirectory())
            .map((d) => path.join(basePath.slice(0, -1), d.name, suffix))
            .filter((f) => fs.existsSync(f));
        }
      } catch (e) {
        // Ignore errors
      }
    }

    return fs.existsSync(pattern) ? [pattern] : [];
  }

  analyzeCSP(content, filename) {
    const analysis = {
      score: 100,
      violations: [],
      warnings: [],
    };

    // Check for basic CSP directives
    const requiredDirectives = [
      'default-src',
      'script-src',
      'style-src',
      'img-src',
      'connect-src',
      'font-src',
      'object-src',
      'media-src',
      'frame-src',
    ];

    const hasCSP =
      content.includes('contentSecurityPolicy') || content.includes('Content-Security-Policy');

    if (!hasCSP) {
      analysis.violations.push(`${filename}: No CSP configuration found`);
      analysis.score = 0;
      return analysis;
    }

    // Check for unsafe directives
    const unsafePatterns = ['unsafe-inline', 'unsafe-eval', 'data:', '*', 'http://'];

    for (const pattern of unsafePatterns) {
      if (content.includes(pattern)) {
        analysis.violations.push(`${filename}: Unsafe CSP directive found: ${pattern}`);
        analysis.score -= 20;
      }
    }

    // Check for missing directives
    let foundDirectives = 0;
    for (const directive of requiredDirectives) {
      if (content.includes(directive)) {
        foundDirectives++;
      } else {
        analysis.warnings.push(`${filename}: Missing CSP directive: ${directive}`);
      }
    }

    const directiveScore = (foundDirectives / requiredDirectives.length) * 30;
    analysis.score = Math.min(analysis.score, Math.max(0, analysis.score - (30 - directiveScore)));

    return analysis;
  }

  async scanSRI() {
    console.log(chalk.yellow('🔐 Scanning Subresource Integrity...'));

    // Find HTML and configuration files
    const htmlFiles = this.findHTMLFiles();
    const configFiles = this.findSRIConfigFiles();

    if (htmlFiles.length === 0 && configFiles.length === 0) {
      this.results.sri.missing.push('No HTML or SRI configuration files found');
      this.results.sri.score = 0;
      return;
    }

    let totalExternalResources = 0;
    let resourcesWithSRI = 0;

    // Check HTML files for external resources
    for (const file of htmlFiles) {
      const content = fs.readFileSync(file, 'utf8');
      const analysis = this.analyzeSRI(content, file);

      totalExternalResources += analysis.externalResources;
      resourcesWithSRI += analysis.resourcesWithSRI;

      this.results.sri.missing.push(...analysis.missing);
      this.results.sri.present.push(...analysis.present);
    }

    // Check if SRI generation is configured
    const hasSRIGeneration = this.checkSRIGeneration();

    if (hasSRIGeneration) {
      this.results.sri.present.push('SRI hash generation configured');
      resourcesWithSRI += 10; // Bonus points
    }

    this.results.sri.score =
      totalExternalResources > 0
        ? Math.min(100, (resourcesWithSRI / totalExternalResources) * 100)
        : hasSRIGeneration
          ? 100
          : 0;

    console.log(
      chalk.green(`  ✓ SRI Analysis complete. Score: ${this.results.sri.score.toFixed(1)}/100`)
    );
  }

  findHTMLFiles() {
    const files = [];
    const extensions = ['.html', '.htm'];

    this.findFilesRecursive('.', extensions, files, ['node_modules', '.next', 'dist', 'coverage']);

    return files;
  }

  findSRIConfigFiles() {
    return ['scripts/generate-sri-hashes.js', 'next.config.js'].filter((f) => fs.existsSync(f));
  }

  findFilesRecursive(dir, extensions, files, excludeDirs = []) {
    if (!fs.existsSync(dir)) return;

    const items = fs.readdirSync(dir, { withFileTypes: true });

    for (const item of items) {
      const fullPath = path.join(dir, item.name);

      if (item.isDirectory()) {
        if (!excludeDirs.some((exclude) => item.name.includes(exclude))) {
          this.findFilesRecursive(fullPath, extensions, files, excludeDirs);
        }
      } else {
        if (extensions.some((ext) => item.name.endsWith(ext))) {
          files.push(fullPath);
        }
      }
    }
  }

  analyzeSRI(content, filename) {
    const analysis = {
      externalResources: 0,
      resourcesWithSRI: 0,
      missing: [],
      present: [],
    };

    // Find external script and link tags
    const scriptRegex = /<script[^>]*src=["']https?:\/\/[^"']*["'][^>]*>/g;
    const linkRegex = /<link[^>]*href=["']https?:\/\/[^"']*["'][^>]*>/g;

    const scripts = content.match(scriptRegex) || [];
    const links = content.match(linkRegex) || [];

    analysis.externalResources = scripts.length + links.length;

    // Check for integrity attributes
    for (const script of scripts) {
      if (script.includes('integrity=')) {
        analysis.resourcesWithSRI++;
        analysis.present.push(`${filename}: Script with SRI found`);
      } else {
        analysis.missing.push(`${filename}: External script without SRI`);
      }
    }

    for (const link of links) {
      if (link.includes('integrity=')) {
        analysis.resourcesWithSRI++;
        analysis.present.push(`${filename}: Link with SRI found`);
      } else if (link.includes('stylesheet')) {
        analysis.missing.push(`${filename}: External stylesheet without SRI`);
      }
    }

    return analysis;
  }

  checkSRIGeneration() {
    const sriScript = path.join(__dirname, 'generate-sri-hashes.js');
    const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));

    return (
      fs.existsSync(sriScript) &&
      packageJson.scripts &&
      (packageJson.scripts['generate:sri'] || packageJson.scripts['prebuild'])
    );
  }

  async scanDependencies() {
    console.log(chalk.yellow('📦 Scanning Dependencies for Vulnerabilities...'));

    try {
      // Use npm audit
      const auditResult = execSync('npm audit --json', {
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      const audit = JSON.parse(auditResult);
      this.analyzeDependencyAudit(audit);
    } catch (error) {
      // npm audit returns non-zero exit code when vulnerabilities found
      if (error.stdout) {
        try {
          const audit = JSON.parse(error.stdout);
          this.analyzeDependencyAudit(audit);
        } catch (parseError) {
          this.results.dependencies.vulnerabilities.push('Failed to parse audit results');
          this.results.dependencies.score = 0;
        }
      } else {
        this.results.dependencies.vulnerabilities.push('Failed to run dependency audit');
        this.results.dependencies.score = 0;
      }
    }

    // Check for outdated packages
    try {
      const outdatedResult = execSync('npm outdated --json', {
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      if (outdatedResult.trim()) {
        const outdated = JSON.parse(outdatedResult);
        this.analyzeOutdatedPackages(outdated);
      }
    } catch (error) {
      // npm outdated returns non-zero when packages are outdated
      if (error.stdout && error.stdout.trim()) {
        try {
          const outdated = JSON.parse(error.stdout);
          this.analyzeOutdatedPackages(outdated);
        } catch (parseError) {
          // Ignore parse errors for outdated check
        }
      }
    }

    console.log(
      chalk.green(
        `  ✓ Dependency scan complete. Score: ${this.results.dependencies.score.toFixed(1)}/100`
      )
    );
  }

  analyzeDependencyAudit(audit) {
    if (!audit.vulnerabilities) {
      this.results.dependencies.score = 100;
      return;
    }

    let criticalCount = 0;
    let highCount = 0;
    let moderateCount = 0;
    let lowCount = 0;

    for (const [packageName, vulnerability] of Object.entries(audit.vulnerabilities)) {
      const severity = vulnerability.severity;

      this.results.dependencies.vulnerabilities.push({
        package: packageName,
        severity: severity,
        title: vulnerability.via[0]?.title || 'Unknown vulnerability',
        url: vulnerability.via[0]?.url,
      });

      switch (severity) {
        case 'critical':
          criticalCount++;
          break;
        case 'high':
          highCount++;
          break;
        case 'moderate':
          moderateCount++;
          break;
        case 'low':
          lowCount++;
          break;
      }
    }

    // Calculate score based on vulnerability severity
    const totalVulns = criticalCount + highCount + moderateCount + lowCount;
    const weightedScore =
      criticalCount * 0 + // Critical = 0 points
      highCount * 20 + // High = 20 points
      moderateCount * 60 + // Moderate = 60 points
      lowCount * 80; // Low = 80 points

    this.results.dependencies.score = totalVulns > 0 ? weightedScore / totalVulns : 100;
  }

  analyzeOutdatedPackages(outdated) {
    for (const [packageName, info] of Object.entries(outdated)) {
      this.results.dependencies.outdated.push({
        package: packageName,
        current: info.current,
        wanted: info.wanted,
        latest: info.latest,
      });
    }

    // Reduce score for many outdated packages
    const outdatedCount = Object.keys(outdated).length;
    const penalty = Math.min(20, outdatedCount * 2);
    this.results.dependencies.score = Math.max(0, this.results.dependencies.score - penalty);
  }

  async scanCode() {
    console.log(chalk.yellow('🔍 Scanning Code for Security Issues...'));

    // Find all TypeScript/JavaScript files
    const codeFiles = [];
    this.findFilesRecursive('.', ['.ts', '.tsx', '.js', '.jsx'], codeFiles, [
      'node_modules',
      '.next',
      'dist',
      'coverage',
      'test-results',
    ]);

    let totalIssues = 0;
    let totalFiles = codeFiles.length;

    for (const file of codeFiles) {
      const issues = this.analyzeCodeFile(file);
      totalIssues += issues.length;
      this.results.code.issues.push(...issues);
    }

    // Calculate score
    const issueRate = totalFiles > 0 ? totalIssues / totalFiles : 0;
    this.results.code.score = Math.max(0, 100 - issueRate * 10);

    console.log(
      chalk.green(`  ✓ Code scan complete. Score: ${this.results.code.score.toFixed(1)}/100`)
    );
  }

  analyzeCodeFile(filename) {
    const issues = [];
    const content = fs.readFileSync(filename, 'utf8');

    // Security patterns to detect
    const securityPatterns = [
      {
        pattern: /eval\(/g,
        message: 'Use of eval() detected - potential XSS vulnerability',
        severity: 'critical',
      },
      {
        pattern: /innerHTML\s*=/g,
        message: 'Use of innerHTML - potential XSS vulnerability',
        severity: 'high',
      },
      {
        pattern: /document\.write\(/g,
        message: 'Use of document.write() - potential XSS vulnerability',
        severity: 'high',
      },
      {
        pattern: /localStorage\./g,
        message: 'Direct localStorage access - use secure storage utility',
        severity: 'medium',
      },
      {
        pattern: /sessionStorage\./g,
        message: 'Direct sessionStorage access - use secure storage utility',
        severity: 'medium',
      },
      {
        pattern: /target=["']_blank["'][^>]*(?!rel=["']noopener)/g,
        message: 'target="_blank" without rel="noopener" - security risk',
        severity: 'medium',
      },
      {
        pattern: /console\.log\(/g,
        message: 'Console.log() found - potential information disclosure',
        severity: 'low',
      },
      {
        pattern: /Math\.random\(\)/g,
        message: 'Math.random() is not cryptographically secure',
        severity: 'low',
      },
    ];

    for (const { pattern, message, severity } of securityPatterns) {
      const matches = content.match(pattern);
      if (matches) {
        issues.push({
          file: filename,
          message: message,
          severity: severity,
          count: matches.length,
        });
      }
    }

    return issues;
  }

  async scanPermissions() {
    console.log(chalk.yellow('🔐 Scanning File Permissions...'));

    let score = 100;
    const issues = [];

    // Check for overly permissive files
    const sensitiveFiles = ['package.json', '.env*', 'next.config.js', 'middleware.ts'];

    for (const pattern of sensitiveFiles) {
      const files = pattern.includes('*') ? this.glob(pattern) : [pattern];

      for (const file of files) {
        if (fs.existsSync(file)) {
          try {
            const stats = fs.statSync(file);
            const mode = stats.mode & parseInt('777', 8);

            if (mode & parseInt('006', 8)) {
              // World writable
              issues.push(`${file}: World writable permissions detected`);
              score -= 20;
            } else if (mode & parseInt('004', 8)) {
              // World readable for sensitive files
              issues.push(`${file}: World readable permissions for sensitive file`);
              score -= 10;
            }
          } catch (error) {
            // Ignore permission check errors
          }
        }
      }
    }

    this.results.permissions.issues = issues;
    this.results.permissions.score = Math.max(0, score);

    console.log(
      chalk.green(
        `  ✓ Permissions scan complete. Score: ${this.results.permissions.score.toFixed(1)}/100`
      )
    );
  }

  async calculateOverallScore() {
    const weightedScore =
      this.results.csp.score * this.weightings.csp +
      this.results.sri.score * this.weightings.sri +
      this.results.dependencies.score * this.weightings.dependencies +
      this.results.code.score * this.weightings.code +
      this.results.permissions.score * this.weightings.permissions;

    this.results.overall.score = Math.round(weightedScore);

    // Assign letter grade
    if (this.results.overall.score >= 90) {
      this.results.overall.grade = 'A';
    } else if (this.results.overall.score >= 80) {
      this.results.overall.grade = 'B';
    } else if (this.results.overall.score >= 70) {
      this.results.overall.grade = 'C';
    } else if (this.results.overall.score >= 60) {
      this.results.overall.grade = 'D';
    } else {
      this.results.overall.grade = 'F';
    }
  }

  async generateSecurityReport() {
    console.log(chalk.yellow('\\n📊 Generating Security Report...'));

    const report = {
      timestamp: new Date().toISOString(),
      overall: this.results.overall,
      details: this.results,
      recommendations: this.generateRecommendations(),
    };

    // Write report to file
    const reportPath = path.join(__dirname, '../test-results/security-report.json');
    const reportDir = path.dirname(reportPath);

    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true });
    }

    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    // Print summary
    console.log(chalk.blue('\\n🔒 Security Analysis Summary:'));
    console.log(
      `  Overall Score: ${this.getScoreColor(this.results.overall.score)}${this.results.overall.score}/100 (${this.results.overall.grade})${chalk.reset()}`
    );
    console.log(
      `  CSP Score: ${this.getScoreColor(this.results.csp.score)}${this.results.csp.score.toFixed(1)}/100${chalk.reset()}`
    );
    console.log(
      `  SRI Score: ${this.getScoreColor(this.results.sri.score)}${this.results.sri.score.toFixed(1)}/100${chalk.reset()}`
    );
    console.log(
      `  Dependencies: ${this.getScoreColor(this.results.dependencies.score)}${this.results.dependencies.score.toFixed(1)}/100${chalk.reset()}`
    );
    console.log(
      `  Code Security: ${this.getScoreColor(this.results.code.score)}${this.results.code.score.toFixed(1)}/100${chalk.reset()}`
    );
    console.log(
      `  Permissions: ${this.getScoreColor(this.results.permissions.score)}${this.results.permissions.score.toFixed(1)}/100${chalk.reset()}`
    );
    console.log(`\\n  Report saved to: ${reportPath}`);

    // Print key issues
    this.printSecurityIssues();
  }

  getScoreColor(score) {
    if (score >= 90) return chalk.green;
    if (score >= 80) return chalk.yellow;
    if (score >= 60) return chalk.orange;
    return chalk.red;
  }

  printSecurityIssues() {
    // Print critical issues
    console.log(chalk.red('\\n🚨 Critical Issues:'));
    let hasIssues = false;

    for (const violation of this.results.csp.violations) {
      console.log(`  ${chalk.red('❌')} ${violation}`);
      hasIssues = true;
    }

    for (const vuln of this.results.dependencies.vulnerabilities) {
      if (vuln.severity === 'critical' || vuln.severity === 'high') {
        console.log(`  ${chalk.red('❌')} ${vuln.package}: ${vuln.title} (${vuln.severity})`);
        hasIssues = true;
      }
    }

    for (const issue of this.results.code.issues) {
      if (issue.severity === 'critical' || issue.severity === 'high') {
        console.log(`  ${chalk.red('❌')} ${issue.file}: ${issue.message}`);
        hasIssues = true;
      }
    }

    if (!hasIssues) {
      console.log(`  ${chalk.green('✅ No critical security issues found!')}`);
    }
  }

  generateRecommendations() {
    const recommendations = [];

    if (this.results.csp.score < 80) {
      recommendations.push({
        category: 'CSP',
        priority: 'high',
        action: 'Implement comprehensive Content Security Policy with strict directives',
      });
    }

    if (this.results.sri.score < 80) {
      recommendations.push({
        category: 'SRI',
        priority: 'medium',
        action: 'Add Subresource Integrity hashes to all external resources',
      });
    }

    if (this.results.dependencies.vulnerabilities.length > 0) {
      recommendations.push({
        category: 'Dependencies',
        priority: 'high',
        action: 'Update vulnerable dependencies and establish regular security audits',
      });
    }

    if (this.results.code.score < 80) {
      recommendations.push({
        category: 'Code',
        priority: 'medium',
        action: 'Address code security issues and implement secure coding practices',
      });
    }

    return recommendations;
  }
}

// Run security scan if called directly
if (require.main === module) {
  const scanner = new SecurityScanner();
  scanner.runSecurityScan().catch((error) => {
    console.error(chalk.red(`Fatal error: ${error.message}`));
    process.exit(1);
  });
}

module.exports = SecurityScanner;
