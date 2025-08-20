#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */

const { chromium } = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;

const fs = require('node:fs').promises;
const path = require('node:path');

const PORTALS = [
  { name: 'admin', url: 'http://localhost:3000', port: 3000 },
  { name: 'customer', url: 'http://localhost:3001', port: 3001 },
  { name: 'reseller', url: 'http://localhost:3002', port: 3002 },
];

const TEST_PAGES = {
  admin: ['/', '/customers', '/network', '/billing', '/support', '/analytics', '/security'],
  customer: ['/', '/billing', '/usage', '/support', '/documents'],
  reseller: ['/', '/commissions'],
};

class AccessibilityTester {
  constructor() {
    this.browser = null;
    this.results = {
      summary: {
        totalTests: 0,
        passed: 0,
        failed: 0,
        warnings: 0,
      },
      portals: {},
    };
  }

  async initialize() {
    console.log('🚀 Starting accessibility tests...\n');
    this.browser = await chromium.launch({ headless: true });
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
    }
  }

  async testPortal(portal) {
    console.log(`📱 Testing ${portal.name} portal...`);

    const context = await this.browser.newContext({
      viewport: { width: 1280, height: 720 },
    });

    const page = await context.newPage();

    const portalResults = {
      name: portal.name,
      url: portal.url,
      pages: {},
      summary: { passed: 0, failed: 0, warnings: 0 },
    };

    const pagesToTest = TEST_PAGES[portal.name] || ['/'];

    for (const pagePath of pagesToTest) {
      try {
        const fullUrl = `${portal.url}${pagePath}`;
        console.log(`  🔍 Testing: ${fullUrl}`);

        // Navigate to page
        await page.goto(fullUrl, { waitUntil: 'networkidle', timeout: 30000 });

        // Wait for content to load
        await page.waitForTimeout(2000);

        // Run axe accessibility tests
        const axeBuilder = new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .exclude(['[data-testid="mock-data-warning"]']); // Exclude dev-only elements

        const axeResults = await axeBuilder.analyze();

        // Process results
        const pageResults = {
          url: fullUrl,
          violations: axeResults.violations.length,
          passes: axeResults.passes.length,
          incomplete: axeResults.incomplete.length,
          inapplicable: axeResults.inapplicable.length,
          details: {
            violations: axeResults.violations,
            incomplete: axeResults.incomplete,
          },
        };

        portalResults.pages[pagePath] = pageResults;

        // Update summary
        if (axeResults.violations.length === 0) {
          portalResults.summary.passed++;
          console.log(`    ✅ Passed - ${axeResults.passes.length} checks`);
        } else {
          portalResults.summary.failed++;
          console.log(`    ❌ Failed - ${axeResults.violations.length} violations`);
        }

        if (axeResults.incomplete.length > 0) {
          portalResults.summary.warnings++;
          console.log(`    ⚠️  Warnings - ${axeResults.incomplete.length} incomplete checks`);
        }

        this.results.summary.totalTests++;
      } catch (error) {
        console.log(`    💥 Error testing ${pagePath}: ${error.message}`);
        portalResults.pages[pagePath] = {
          url: `${portal.url}${pagePath}`,
          error: error.message,
        };
        this.results.summary.failed++;
      }
    }

    await context.close();
    this.results.portals[portal.name] = portalResults;

    // Update global summary
    this.results.summary.passed += portalResults.summary.passed;
    this.results.summary.failed += portalResults.summary.failed;
    this.results.summary.warnings += portalResults.summary.warnings;

    console.log(`✨ ${portal.name} portal complete\n`);
  }

  async generateReport() {
    const timestamp = new Date().toISOString();
    const reportDir = path.join(process.cwd(), 'reports', 'accessibility');

    // Ensure reports directory exists
    await fs.mkdir(reportDir, { recursive: true });

    // Generate JSON report
    const jsonReport = {
      timestamp,
      summary: this.results.summary,
      portals: this.results.portals,
    };

    await fs.writeFile(
      path.join(reportDir, `a11y-report-${timestamp.split('T')[0]}.json`),
      JSON.stringify(jsonReport, null, 2)
    );

    // Generate HTML report
    const htmlReport = this.generateHtmlReport(jsonReport);
    await fs.writeFile(
      path.join(reportDir, `a11y-report-${timestamp.split('T')[0]}.html`),
      htmlReport
    );

    // Generate summary for console
    console.log('📊 ACCESSIBILITY TEST SUMMARY');
    console.log('='.repeat(50));
    console.log(`Total Tests: ${this.results.summary.totalTests}`);
    console.log(`✅ Passed: ${this.results.summary.passed}`);
    console.log(`❌ Failed: ${this.results.summary.failed}`);
    console.log(`⚠️  Warnings: ${this.results.summary.warnings}`);
    console.log(
      `📈 Success Rate: ${((this.results.summary.passed / this.results.summary.totalTests) * 100).toFixed(1)}%\n`
    );

    // Portal breakdown
    for (const [portalName, portal] of Object.entries(this.results.portals)) {
      console.log(`${portalName.toUpperCase()} Portal:`);
      console.log(`  Passed: ${portal.summary.passed}`);
      console.log(`  Failed: ${portal.summary.failed}`);
      console.log(`  Warnings: ${portal.summary.warnings}\n`);
    }

    console.log(`📄 Reports saved to: ${reportDir}`);

    // Exit with error code if any tests failed
    if (this.results.summary.failed > 0) {
      process.exit(1);
    }
  }

  generateHtmlReport(data) {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DotMac Accessibility Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .header { text-align: center; margin-bottom: 30px; }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
    .metric { background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; }
    .metric-value { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
    .passed { color: #28a745; }
    .failed { color: #dc3545; }
    .warning { color: #ffc107; }
    .portal { margin-bottom: 30px; border: 1px solid #dee2e6; border-radius: 6px; overflow: hidden; }
    .portal-header { background: #007bff; color: white; padding: 15px 20px; }
    .portal-content { padding: 20px; }
    .page-result { margin-bottom: 15px; padding: 15px; border-left: 4px solid #dee2e6; background: #f8f9fa; }
    .page-result.passed { border-color: #28a745; }
    .page-result.failed { border-color: #dc3545; }
    .violation { margin: 10px 0; padding: 10px; background: #fff; border-radius: 4px; border-left: 3px solid #dc3545; }
    .violation-title { font-weight: bold; color: #dc3545; }
    .violation-description { margin: 5px 0; font-size: 0.9em; }
    .violation-impact { font-size: 0.8em; color: #666; }
    .timestamp { text-align: center; color: #666; margin-top: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🛡️ DotMac Accessibility Report</h1>
      <p>Generated on ${new Date(data.timestamp).toLocaleString()}</p>
    </div>
    
    <div class="summary">
      <div class="metric">
        <div class="metric-value">${data.summary.totalTests}</div>
        <div>Total Tests</div>
      </div>
      <div class="metric">
        <div class="metric-value passed">${data.summary.passed}</div>
        <div>Passed</div>
      </div>
      <div class="metric">
        <div class="metric-value failed">${data.summary.failed}</div>
        <div>Failed</div>
      </div>
      <div class="metric">
        <div class="metric-value warning">${data.summary.warnings}</div>
        <div>Warnings</div>
      </div>
    </div>
    
    ${Object.values(data.portals)
      .map(
        (portal) => `
      <div class="portal">
        <div class="portal-header">
          <h2>${portal.name.charAt(0).toUpperCase() + portal.name.slice(1)} Portal</h2>
        </div>
        <div class="portal-content">
          ${Object.entries(portal.pages)
            .map(
              ([path, page]) => `
            <div class="page-result ${page.violations === 0 ? 'passed' : 'failed'}">
              <h3>${path === '/' ? 'Dashboard' : path}</h3>
              <p><strong>URL:</strong> ${page.url}</p>
              ${
                page.error
                  ? `<p class="failed"><strong>Error:</strong> ${page.error}</p>`
                  : `
                <p>✅ Passes: ${page.passes} | ❌ Violations: ${page.violations} | ⚠️ Incomplete: ${page.incomplete}</p>
                ${page.details.violations
                  .map(
                    (violation) => `
                  <div class="violation">
                    <div class="violation-title">${violation.id}: ${violation.help}</div>
                    <div class="violation-description">${violation.description}</div>
                    <div class="violation-impact">Impact: ${violation.impact} | Tags: ${violation.tags.join(', ')}</div>
                  </div>
                `
                  )
                  .join('')}
              `
              }
            </div>
          `
            )
            .join('')}
        </div>
      </div>
    `
      )
      .join('')}
    
    <div class="timestamp">
      Report generated by DotMac Accessibility Testing Suite
    </div>
  </div>
</body>
</html>
    `.trim();
  }

  async run() {
    try {
      await this.initialize();

      for (const portal of PORTALS) {
        await this.testPortal(portal);
      }

      await this.generateReport();
    } catch (error) {
      console.error('💥 Test suite failed:', error);
      process.exit(1);
    } finally {
      await this.cleanup();
    }
  }
}

// Command line interface
if (require.main === module) {
  const tester = new AccessibilityTester();
  tester.run().catch(console.error);
}

module.exports = AccessibilityTester;
