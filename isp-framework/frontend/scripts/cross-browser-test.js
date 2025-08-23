#!/usr/bin/env node
/**
 * Cross-Browser Testing Management
 * 
 * Orchestrates testing across different browser configurations and provides
 * comprehensive compatibility reports
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Browser test configurations
const BROWSER_CONFIGS = {
  // Essential browsers (always run)
  essential: [
    'Desktop Chrome Latest',
    'Desktop Firefox Latest',
    'Desktop Safari',
    'iPhone 14 Pro Safari',
    'Samsung Galaxy S22 Chrome'
  ],
  
  // Extended testing (CI/comprehensive testing)
  extended: [
    'Desktop Chrome Beta',
    'Microsoft Edge Latest',
    'iPhone 13 Safari',
    'iPhone SE Safari',
    'Pixel 7 Chrome',
    'iPad Pro 12.9"',
    'iPad Air',
    'Samsung Galaxy Tab'
  ],
  
  // Accessibility focused
  accessibility: [
    'Chrome High Contrast',
    'Firefox Screen Reader Mode'
  ],
  
  // Performance/Network testing
  performance: [
    'Chrome Slow 3G',
    'Mobile Slow Connection'
  ],
  
  // Legacy support
  legacy: [
    'Chrome 100 Legacy'
  ],
  
  // Portal-specific
  portals: [
    'Admin Portal Desktop',
    'Customer Portal Mobile',
    'Reseller Portal Tablet',
    'Technician Portal PWA'
  ]
};

// Browser compatibility matrix
const COMPATIBILITY_MATRIX = {
  'Desktop Chrome Latest': {
    css: {
      flexbox: 'full',
      grid: 'full',
      customProperties: 'full',
      containerQueries: 'full'
    },
    js: {
      es2022: 'full',
      modules: 'full',
      asyncAwait: 'full',
      webComponents: 'full'
    },
    apis: {
      webgl: 'full',
      serviceWorker: 'full',
      webAssembly: 'full',
      intersectionObserver: 'full'
    }
  },
  'Desktop Firefox Latest': {
    css: {
      flexbox: 'full',
      grid: 'full',
      customProperties: 'full',
      containerQueries: 'partial'
    },
    js: {
      es2022: 'full',
      modules: 'full',
      asyncAwait: 'full',
      webComponents: 'full'
    },
    apis: {
      webgl: 'full',
      serviceWorker: 'full',
      webAssembly: 'full',
      intersectionObserver: 'full'
    }
  },
  'Desktop Safari': {
    css: {
      flexbox: 'full',
      grid: 'full',
      customProperties: 'full',
      containerQueries: 'none'
    },
    js: {
      es2022: 'partial',
      modules: 'full',
      asyncAwait: 'full',
      webComponents: 'partial'
    },
    apis: {
      webgl: 'full',
      serviceWorker: 'full',
      webAssembly: 'full',
      intersectionObserver: 'full'
    }
  }
};

class CrossBrowserTester {
  constructor(options = {}) {
    this.options = {
      testSuite: options.testSuite || 'essential',
      parallel: options.parallel !== false,
      reporters: options.reporters || ['html', 'json'],
      outputDir: options.outputDir || 'cross-browser-results',
      maxRetries: options.maxRetries || 2,
      timeout: options.timeout || 60000,
      ...options
    };
    
    this.results = {
      timestamp: new Date().toISOString(),
      testSuite: this.options.testSuite,
      browsers: {},
      summary: {
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0
      },
      compatibility: {}
    };
  }

  async runCrossBrowserTests() {
    console.log('🌐 Starting cross-browser testing...');
    console.log(`📋 Test Suite: ${this.options.testSuite}`);
    
    const browsers = BROWSER_CONFIGS[this.options.testSuite] || BROWSER_CONFIGS.essential;
    console.log(`🔧 Testing ${browsers.length} browser configurations`);
    
    // Create output directory
    if (!fs.existsSync(this.options.outputDir)) {
      fs.mkdirSync(this.options.outputDir, { recursive: true });
    }

    if (this.options.parallel) {
      await this.runTestsInParallel(browsers);
    } else {
      await this.runTestsSequentially(browsers);
    }

    await this.generateCompatibilityReport();
    await this.generateSummaryReport();
    
    console.log('\n🎯 Cross-browser testing completed!');
    console.log(`📊 Results: ${this.results.summary.passed}/${this.results.summary.total} browsers passed`);
    console.log(`📁 Reports: ${this.options.outputDir}/`);
    
    return this.results;
  }

  async runTestsInParallel(browsers) {
    console.log('⚡ Running tests in parallel...');
    
    const chunks = this.chunkArray(browsers, 4); // Run 4 browsers at a time
    
    for (const chunk of chunks) {
      const promises = chunk.map(browser => this.runBrowserTest(browser));
      await Promise.allSettled(promises);
    }
  }

  async runTestsSequentially(browsers) {
    console.log('🔄 Running tests sequentially...');
    
    for (const browser of browsers) {
      await this.runBrowserTest(browser);
    }
  }

  async runBrowserTest(browser) {
    console.log(`\n🔍 Testing: ${browser}`);
    
    const startTime = Date.now();
    
    try {
      const result = await this.executePlaywrightTest(browser);
      const duration = Date.now() - startTime;
      
      this.results.browsers[browser] = {
        status: result.success ? 'passed' : 'failed',
        duration,
        tests: result.tests,
        errors: result.errors,
        screenshots: result.screenshots,
        compatibility: COMPATIBILITY_MATRIX[browser] || {}
      };
      
      if (result.success) {
        this.results.summary.passed++;
        console.log(`  ✅ ${browser} - ${result.tests.passed}/${result.tests.total} tests passed`);
      } else {
        this.results.summary.failed++;
        console.log(`  ❌ ${browser} - ${result.errors.length} errors`);
      }
      
    } catch (error) {
      console.log(`  💥 ${browser} - Test execution failed: ${error.message}`);
      
      this.results.browsers[browser] = {
        status: 'error',
        duration: Date.now() - startTime,
        error: error.message,
        compatibility: {}
      };
      
      this.results.summary.failed++;
    }
    
    this.results.summary.total++;
  }

  async executePlaywrightTest(browser) {
    return new Promise((resolve, reject) => {
      const cmd = 'npx';
      const args = [
        'playwright', 'test',
        '--project', browser,
        '--reporter=json',
        `--output-dir=${this.options.outputDir}/${this.sanitizeName(browser)}`,
        `--timeout=${this.options.timeout}`,
        `--retries=${this.options.maxRetries}`
      ];

      const testProcess = spawn(cmd, args, {
        stdio: 'pipe',
        cwd: process.cwd()
      });

      let stdout = '';
      let stderr = '';

      testProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      testProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      testProcess.on('close', (code) => {
        try {
          const result = this.parsePlaywrightOutput(stdout, stderr, code);
          resolve(result);
        } catch (error) {
          reject(new Error(`Failed to parse test output: ${error.message}`));
        }
      });

      testProcess.on('error', (error) => {
        reject(error);
      });
    });
  }

  parsePlaywrightOutput(stdout, stderr, exitCode) {
    const result = {
      success: exitCode === 0,
      tests: { total: 0, passed: 0, failed: 0, skipped: 0 },
      errors: [],
      screenshots: []
    };

    // Try to parse JSON output
    try {
      const lines = stdout.split('\n').filter(line => line.trim());
      const jsonLine = lines.find(line => line.startsWith('{') && line.includes('"tests"'));
      
      if (jsonLine) {
        const testResults = JSON.parse(jsonLine);
        result.tests = {
          total: testResults.stats?.total || 0,
          passed: testResults.stats?.passed || 0,
          failed: testResults.stats?.failed || 0,
          skipped: testResults.stats?.skipped || 0
        };
      }
    } catch (error) {
      // Fallback to basic parsing
      const passedMatch = stdout.match(/(\d+) passed/);
      const failedMatch = stdout.match(/(\d+) failed/);
      
      if (passedMatch) result.tests.passed = parseInt(passedMatch[1]);
      if (failedMatch) result.tests.failed = parseInt(failedMatch[1]);
      result.tests.total = result.tests.passed + result.tests.failed;
    }

    // Extract errors from stderr
    if (stderr) {
      result.errors = stderr.split('\n')
        .filter(line => line.includes('Error:') || line.includes('Failed:'))
        .slice(0, 10); // Limit to first 10 errors
    }

    return result;
  }

  async generateCompatibilityReport() {
    console.log('\n📊 Generating compatibility report...');
    
    const compatibility = {
      summary: {
        fullSupport: [],
        partialSupport: [],
        noSupport: [],
        unknown: []
      },
      features: {
        css: {},
        javascript: {},
        apis: {}
      }
    };

    // Analyze compatibility across browsers
    const features = ['flexbox', 'grid', 'customProperties', 'es2022', 'serviceWorker'];
    
    for (const feature of features) {
      compatibility.features[feature] = {};
      
      for (const [browser, data] of Object.entries(this.results.browsers)) {
        if (data.compatibility) {
          const support = this.getFeatureSupport(data.compatibility, feature);
          compatibility.features[feature][browser] = support;
        }
      }
    }

    this.results.compatibility = compatibility;
    
    // Write compatibility report
    fs.writeFileSync(
      path.join(this.options.outputDir, 'compatibility-report.json'),
      JSON.stringify(compatibility, null, 2)
    );
  }

  getFeatureSupport(browserCompat, feature) {
    // Check across CSS, JS, and APIs
    for (const category of ['css', 'js', 'apis']) {
      if (browserCompat[category] && browserCompat[category][feature]) {
        return browserCompat[category][feature];
      }
    }
    return 'unknown';
  }

  async generateSummaryReport() {
    console.log('📋 Generating summary report...');
    
    const summaryHtml = this.generateHtmlReport();
    fs.writeFileSync(
      path.join(this.options.outputDir, 'cross-browser-summary.html'),
      summaryHtml
    );

    // Write JSON summary
    fs.writeFileSync(
      path.join(this.options.outputDir, 'cross-browser-results.json'),
      JSON.stringify(this.results, null, 2)
    );
  }

  generateHtmlReport() {
    const passRate = ((this.results.summary.passed / this.results.summary.total) * 100).toFixed(1);
    
    return `
<!DOCTYPE html>
<html>
<head>
  <title>Cross-Browser Testing Report - DotMac Frontend</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f8f9fa; }
    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .header { background: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
    .metric { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .metric-value { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
    .passed { color: #28a745; }
    .failed { color: #dc3545; }
    .browser-results { background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .browser-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; margin: 10px 0; border-radius: 6px; background: #f8f9fa; }
    .browser-passed { border-left: 4px solid #28a745; }
    .browser-failed { border-left: 4px solid #dc3545; }
    .browser-error { border-left: 4px solid #ffc107; }
    .status-badge { padding: 4px 12px; border-radius: 16px; font-size: 0.9em; font-weight: 500; }
    .badge-passed { background: #d4edda; color: #155724; }
    .badge-failed { background: #f8d7da; color: #721c24; }
    .badge-error { background: #fff3cd; color: #856404; }
    .progress-bar { width: 100%; height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden; margin: 20px 0; }
    .progress-fill { height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🌐 Cross-Browser Testing Report</h1>
      <p><strong>Test Suite:</strong> ${this.results.testSuite}</p>
      <p><strong>Generated:</strong> ${this.results.timestamp}</p>
      
      <div class="progress-bar">
        <div class="progress-fill" style="width: ${passRate}%"></div>
      </div>
      <p style="text-align: center; margin: 10px 0;"><strong>${passRate}% Browser Compatibility</strong></p>
    </div>

    <div class="summary">
      <div class="metric">
        <div class="metric-value">${this.results.summary.total}</div>
        <div>Total Browsers</div>
      </div>
      <div class="metric">
        <div class="metric-value passed">${this.results.summary.passed}</div>
        <div>Passed</div>
      </div>
      <div class="metric">
        <div class="metric-value failed">${this.results.summary.failed}</div>
        <div>Failed</div>
      </div>
      <div class="metric">
        <div class="metric-value">${passRate}%</div>
        <div>Success Rate</div>
      </div>
    </div>

    <div class="browser-results">
      <h3>📱 Browser Results</h3>
      ${Object.entries(this.results.browsers).map(([browser, result]) => `
        <div class="browser-item browser-${result.status}">
          <div>
            <strong>${browser}</strong>
            <div style="font-size: 0.9em; color: #666; margin-top: 4px;">
              ${result.tests ? `${result.tests.passed}/${result.tests.total} tests passed` : ''}
              ${result.duration ? `• ${(result.duration / 1000).toFixed(1)}s` : ''}
            </div>
            ${result.errors && result.errors.length > 0 ? `
              <div style="font-size: 0.8em; color: #721c24; margin-top: 8px;">
                ${result.errors.slice(0, 2).join('<br>')}
              </div>
            ` : ''}
          </div>
          <div class="status-badge badge-${result.status}">
            ${result.status.toUpperCase()}
          </div>
        </div>
      `).join('')}
    </div>
  </div>
</body>
</html>`;
  }

  chunkArray(array, size) {
    const chunks = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  }

  sanitizeName(name) {
    return name.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
  }
}

// CLI Interface
async function main() {
  const args = process.argv.slice(2);
  const options = {};

  // Parse command line arguments
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--suite':
      case '-s':
        options.testSuite = args[++i];
        break;
      case '--sequential':
        options.parallel = false;
        break;
      case '--output':
      case '-o':
        options.outputDir = args[++i];
        break;
      case '--timeout':
      case '-t':
        options.timeout = parseInt(args[++i]);
        break;
      case '--help':
      case '-h':
        console.log(`
Cross-Browser Testing Tool

Usage: node scripts/cross-browser-test.js [options]

Options:
  -s, --suite <suite>     Test suite: essential, extended, accessibility, performance, legacy, portals
  --sequential            Run tests sequentially instead of parallel
  -o, --output <dir>      Output directory for results
  -t, --timeout <ms>      Test timeout in milliseconds
  -h, --help              Show this help message

Examples:
  node scripts/cross-browser-test.js --suite essential
  node scripts/cross-browser-test.js --suite accessibility --sequential
  node scripts/cross-browser-test.js --suite extended --output ./results
`);
        process.exit(0);
        break;
    }
  }

  console.log('🚀 DotMac Cross-Browser Testing');
  console.log(`Available test suites: ${Object.keys(BROWSER_CONFIGS).join(', ')}`);
  
  const tester = new CrossBrowserTester(options);
  
  try {
    const results = await tester.runCrossBrowserTests();
    
    // Exit with error code if any tests failed
    if (results.summary.failed > 0) {
      process.exit(1);
    }
    
  } catch (error) {
    console.error('❌ Cross-browser testing failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = { CrossBrowserTester, BROWSER_CONFIGS };