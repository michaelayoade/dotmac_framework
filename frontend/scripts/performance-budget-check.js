#!/usr/bin/env node

/**
 * Performance Budget Check
 * Enforce performance budgets in CI with configurable thresholds
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Performance budget thresholds
const PERFORMANCE_BUDGETS = {
  // Bundle size limits (in KB)
  bundleSize: {
    admin: 800, // Admin portal bundle
    customer: 600, // Customer portal bundle
    reseller: 700, // Reseller portal bundle
    technician: 500, // Technician portal bundle
    shared: 200, // Shared packages
  },

  // Lighthouse scores (0-100)
  lighthouse: {
    performance: 90,
    accessibility: 95,
    bestPractices: 90,
    seo: 85,
    pwa: 80,
  },

  // Core Web Vitals
  webVitals: {
    lcp: 2500, // Largest Contentful Paint (ms)
    fid: 100, // First Input Delay (ms)
    cls: 0.1, // Cumulative Layout Shift
    fcp: 1800, // First Contentful Paint (ms)
    ttfb: 600, // Time to First Byte (ms)
  },

  // Resource counts
  resources: {
    totalRequests: 50,
    cssFiles: 5,
    jsFiles: 10,
    images: 20,
    fonts: 4,
  },
};

class PerformanceBudgetChecker {
  constructor() {
    this.results = {
      passed: [],
      failed: [],
      warnings: [],
    };

    this.outputPath = process.env.PERFORMANCE_OUTPUT_PATH || './performance-results';
    this.isCI = process.env.CI === 'true';
    this.verbose = process.env.VERBOSE === 'true';
  }

  log(message, level = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = this.isCI ? `::${level}::` : `[${level.toUpperCase()}]`;
    console.log(`${prefix} ${timestamp} ${message}`);
  }

  async checkBundleSizes() {
    this.log('Checking bundle sizes...');

    const distPath = path.join(process.cwd(), 'dist');
    if (!fs.existsSync(distPath)) {
      this.results.warnings.push('No dist directory found, skipping bundle size check');
      return;
    }

    const apps = ['admin', 'customer', 'reseller', 'technician'];

    for (const app of apps) {
      const appPath = path.join(distPath, app);
      if (!fs.existsSync(appPath)) {
        this.results.warnings.push(`No build found for ${app} app`);
        continue;
      }

      try {
        // Find main JS bundle
        const jsFiles = this.findFiles(appPath, /\.js$/).filter(
          (f) => f.includes('chunk') || f.includes('main') || f.includes('index')
        );

        let totalSize = 0;
        jsFiles.forEach((file) => {
          const stats = fs.statSync(file);
          totalSize += stats.size;
        });

        const sizeKB = Math.round(totalSize / 1024);
        const budget = PERFORMANCE_BUDGETS.bundleSize[app];

        if (sizeKB <= budget) {
          this.results.passed.push({
            check: 'Bundle Size',
            app,
            value: `${sizeKB}KB`,
            threshold: `${budget}KB`,
            status: 'PASS',
          });
        } else {
          this.results.failed.push({
            check: 'Bundle Size',
            app,
            value: `${sizeKB}KB`,
            threshold: `${budget}KB`,
            status: 'FAIL',
            message: `Bundle size exceeds budget by ${sizeKB - budget}KB`,
          });
        }

        this.log(
          `${app}: ${sizeKB}KB (budget: ${budget}KB) - ${sizeKB <= budget ? 'PASS' : 'FAIL'}`
        );
      } catch (error) {
        this.results.failed.push({
          check: 'Bundle Size',
          app,
          status: 'ERROR',
          message: `Failed to check bundle size: ${error.message}`,
        });
      }
    }
  }

  async checkLighthouseScores() {
    this.log('Checking Lighthouse scores...');

    const lighthouseResultsPath = path.join(this.outputPath, 'lighthouse');
    if (!fs.existsSync(lighthouseResultsPath)) {
      this.results.warnings.push('No Lighthouse results found');
      return;
    }

    try {
      const reportFiles = this.findFiles(lighthouseResultsPath, /\.json$/).filter(
        (f) => f.includes('lighthouse') || f.includes('report')
      );

      for (const reportFile of reportFiles) {
        const report = JSON.parse(fs.readFileSync(reportFile, 'utf8'));
        const url = report.requestedUrl || report.finalUrl;
        const app = this.extractAppFromUrl(url);

        const scores = {
          performance: Math.round(report.categories.performance?.score * 100) || 0,
          accessibility: Math.round(report.categories.accessibility?.score * 100) || 0,
          bestPractices: Math.round(report.categories['best-practices']?.score * 100) || 0,
          seo: Math.round(report.categories.seo?.score * 100) || 0,
          pwa: report.categories.pwa ? Math.round(report.categories.pwa?.score * 100) : null,
        };

        // Check each score against budget
        Object.entries(scores).forEach(([category, score]) => {
          if (score === null) return;

          const threshold = PERFORMANCE_BUDGETS.lighthouse[category];
          const result = {
            check: 'Lighthouse',
            app,
            category,
            value: score,
            threshold,
            url,
          };

          if (score >= threshold) {
            this.results.passed.push({ ...result, status: 'PASS' });
          } else {
            this.results.failed.push({
              ...result,
              status: 'FAIL',
              message: `${category} score ${score} below threshold ${threshold}`,
            });
          }
        });

        this.log(
          `${app} Lighthouse: Performance ${scores.performance}, Accessibility ${scores.accessibility}, Best Practices ${scores.bestPractices}, SEO ${scores.seo}${scores.pwa ? `, PWA ${scores.pwa}` : ''}`
        );
      }
    } catch (error) {
      this.results.failed.push({
        check: 'Lighthouse',
        status: 'ERROR',
        message: `Failed to process Lighthouse reports: ${error.message}`,
      });
    }
  }

  async checkWebVitals() {
    this.log('Checking Core Web Vitals...');

    // Look for web vitals data from Real User Monitoring or lab data
    const webVitalsPath = path.join(this.outputPath, 'web-vitals.json');
    if (!fs.existsSync(webVitalsPath)) {
      this.results.warnings.push('No Web Vitals data found');
      return;
    }

    try {
      const webVitalsData = JSON.parse(fs.readFileSync(webVitalsPath, 'utf8'));

      Object.entries(webVitalsData).forEach(([url, metrics]) => {
        const app = this.extractAppFromUrl(url);

        Object.entries(PERFORMANCE_BUDGETS.webVitals).forEach(([metric, threshold]) => {
          const value = metrics[metric];
          if (value === undefined) return;

          const result = {
            check: 'Web Vitals',
            app,
            metric: metric.toUpperCase(),
            value,
            threshold,
            url,
          };

          if (value <= threshold) {
            this.results.passed.push({ ...result, status: 'PASS' });
          } else {
            this.results.failed.push({
              ...result,
              status: 'FAIL',
              message: `${metric.toUpperCase()} ${value}ms exceeds threshold ${threshold}ms`,
            });
          }
        });
      });
    } catch (error) {
      this.results.failed.push({
        check: 'Web Vitals',
        status: 'ERROR',
        message: `Failed to process Web Vitals data: ${error.message}`,
      });
    }
  }

  async checkResourceCounts() {
    this.log('Checking resource counts...');

    // This would typically come from HAR files or network analysis
    const harPath = path.join(this.outputPath, 'network.har');
    if (!fs.existsSync(harPath)) {
      this.results.warnings.push('No network HAR file found');
      return;
    }

    try {
      const harData = JSON.parse(fs.readFileSync(harPath, 'utf8'));
      const entries = harData.log.entries;

      const resourceCounts = {
        totalRequests: entries.length,
        cssFiles: entries.filter((e) => e.request.url.endsWith('.css')).length,
        jsFiles: entries.filter((e) => e.request.url.endsWith('.js')).length,
        images: entries.filter((e) => e.response.content.mimeType?.startsWith('image/')).length,
        fonts: entries.filter((e) => e.response.content.mimeType?.includes('font')).length,
      };

      Object.entries(resourceCounts).forEach(([resource, count]) => {
        const threshold = PERFORMANCE_BUDGETS.resources[resource];
        const result = {
          check: 'Resource Count',
          resource,
          value: count,
          threshold,
        };

        if (count <= threshold) {
          this.results.passed.push({ ...result, status: 'PASS' });
        } else {
          this.results.failed.push({
            ...result,
            status: 'FAIL',
            message: `${resource} count ${count} exceeds threshold ${threshold}`,
          });
        }
      });

      this.log(
        `Resources: ${resourceCounts.totalRequests} total, ${resourceCounts.jsFiles} JS, ${resourceCounts.cssFiles} CSS, ${resourceCounts.images} images, ${resourceCounts.fonts} fonts`
      );
    } catch (error) {
      this.results.failed.push({
        check: 'Resource Count',
        status: 'ERROR',
        message: `Failed to process HAR file: ${error.message}`,
      });
    }
  }

  async generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        total: this.results.passed.length + this.results.failed.length,
        passed: this.results.passed.length,
        failed: this.results.failed.length,
        warnings: this.results.warnings.length,
      },
      results: this.results,
      budgets: PERFORMANCE_BUDGETS,
    };

    // Save JSON report
    const reportPath = path.join(this.outputPath, 'performance-budget-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    // Generate HTML report
    this.generateHTMLReport(report);

    return report;
  }

  generateHTMLReport(report) {
    const html = `
<!DOCTYPE html>
<html>
<head>
    <title>Performance Budget Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .passed { color: #22c55e; }
        .failed { color: #ef4444; }
        .warning { color: #f59e0b; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; }
        .status-pass { background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; }
        .status-fail { background: #fecaca; color: #991b1b; padding: 4px 8px; border-radius: 4px; }
        .status-error { background: #fed7d7; color: #991b1b; padding: 4px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Performance Budget Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Checks:</strong> ${report.summary.total}</p>
        <p><strong class="passed">Passed:</strong> ${report.summary.passed}</p>
        <p><strong class="failed">Failed:</strong> ${report.summary.failed}</p>
        <p><strong class="warning">Warnings:</strong> ${report.summary.warnings}</p>
        <p><strong>Generated:</strong> ${report.timestamp}</p>
    </div>

    ${
      this.results.failed.length > 0
        ? `
    <h2>Failed Checks</h2>
    <table>
        <thead>
            <tr>
                <th>Check</th>
                <th>App/Resource</th>
                <th>Value</th>
                <th>Threshold</th>
                <th>Status</th>
                <th>Message</th>
            </tr>
        </thead>
        <tbody>
            ${this.results.failed
              .map(
                (result) => `
            <tr>
                <td>${result.check}</td>
                <td>${result.app || result.resource || '-'}</td>
                <td>${result.value}</td>
                <td>${result.threshold || '-'}</td>
                <td><span class="status-fail">${result.status}</span></td>
                <td>${result.message || '-'}</td>
            </tr>
            `
              )
              .join('')}
        </tbody>
    </table>
    `
        : ''
    }

    <h2>All Results</h2>
    <table>
        <thead>
            <tr>
                <th>Check</th>
                <th>App/Resource</th>
                <th>Value</th>
                <th>Threshold</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            ${[...this.results.passed, ...this.results.failed]
              .map(
                (result) => `
            <tr>
                <td>${result.check}</td>
                <td>${result.app || result.resource || '-'}</td>
                <td>${result.value}</td>
                <td>${result.threshold || '-'}</td>
                <td><span class="status-${result.status.toLowerCase()}">${result.status}</span></td>
            </tr>
            `
              )
              .join('')}
        </tbody>
    </table>

    ${
      this.results.warnings.length > 0
        ? `
    <h2>Warnings</h2>
    <ul>
        ${this.results.warnings.map((warning) => `<li class="warning">${warning}</li>`).join('')}
    </ul>
    `
        : ''
    }
</body>
</html>`;

    const htmlPath = path.join(this.outputPath, 'performance-budget-report.html');
    fs.writeFileSync(htmlPath, html);
    this.log(`HTML report saved to ${htmlPath}`);
  }

  findFiles(dir, pattern) {
    const files = [];
    const items = fs.readdirSync(dir);

    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        files.push(...this.findFiles(fullPath, pattern));
      } else if (pattern.test(item)) {
        files.push(fullPath);
      }
    }

    return files;
  }

  extractAppFromUrl(url) {
    if (url.includes('admin')) return 'admin';
    if (url.includes('customer')) return 'customer';
    if (url.includes('reseller')) return 'reseller';
    if (url.includes('technician')) return 'technician';
    return 'unknown';
  }

  async run() {
    this.log('Starting performance budget checks...');

    // Ensure output directory exists
    if (!fs.existsSync(this.outputPath)) {
      fs.mkdirSync(this.outputPath, { recursive: true });
    }

    // Run all checks
    await this.checkBundleSizes();
    await this.checkLighthouseScores();
    await this.checkWebVitals();
    await this.checkResourceCounts();

    // Generate report
    const report = await this.generateReport();

    // Output summary
    this.log(`Performance budget check completed:`);
    this.log(`  Total checks: ${report.summary.total}`);
    this.log(`  Passed: ${report.summary.passed}`, 'info');
    this.log(`  Failed: ${report.summary.failed}`, report.summary.failed > 0 ? 'error' : 'info');
    this.log(
      `  Warnings: ${report.summary.warnings}`,
      report.summary.warnings > 0 ? 'warning' : 'info'
    );

    // Set GitHub Actions outputs if running in CI
    if (this.isCI) {
      console.log(`::set-output name=total::${report.summary.total}`);
      console.log(`::set-output name=passed::${report.summary.passed}`);
      console.log(`::set-output name=failed::${report.summary.failed}`);
      console.log(`::set-output name=warnings::${report.summary.warnings}`);
    }

    // Exit with error code if any checks failed
    if (report.summary.failed > 0) {
      this.log(`Performance budget checks failed!`, 'error');
      process.exit(1);
    } else {
      this.log(`All performance budget checks passed!`, 'info');
      process.exit(0);
    }
  }
}

// Run if called directly
if (require.main === module) {
  const checker = new PerformanceBudgetChecker();
  checker.run().catch((error) => {
    console.error('Performance budget check failed:', error);
    process.exit(1);
  });
}

module.exports = PerformanceBudgetChecker;
