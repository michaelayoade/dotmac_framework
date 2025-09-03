#!/usr/bin/env node

/**
 * Web Vitals Gating Script
 * Enforces performance budgets and fails CI if thresholds are exceeded
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// Performance Budgets (in milliseconds, or score for ratios)
const BUDGETS = {
  fcp: 1800,    // First Contentful Paint
  lcp: 2500,    // Largest Contentful Paint  
  fid: 100,     // First Input Delay
  cls: 0.1,     // Cumulative Layout Shift
  tbt: 200,     // Total Blocking Time
  si: 3400,     // Speed Index
  tti: 3800,    // Time to Interactive
  performanceScore: 90,
  accessibilityScore: 95,
  bestPracticesScore: 95,
  seoScore: 90,
  bundleSize: 800000,      // Total bundle size in bytes
  jsSize: 250000,          // JavaScript bundle size in bytes  
  cssSize: 50000,          // CSS bundle size in bytes
  unusedJs: 20000,         // Unused JavaScript in bytes
  unusedCss: 20000,        // Unused CSS in bytes
  domNodes: 1500           // Maximum DOM nodes
};

class WebVitalsGate {
  constructor() {
    this.violations = [];
    this.warnings = [];
    this.results = {};
  }

  async run() {
    console.log('🔍 Running Web Vitals Performance Gate...\n');

    try {
      // Run Lighthouse CI
      await this.runLighthouseCI();
      
      // Parse Lighthouse results
      await this.parseLighthouseResults();
      
      // Check bundle sizes
      await this.checkBundleSizes();
      
      // Generate report
      this.generateReport();
      
      // Exit with appropriate code
      this.exitWithResults();
      
    } catch (error) {
      console.error('❌ Web Vitals Gate failed:', error.message);
      process.exit(1);
    }
  }

  async runLighthouseCI() {
    console.log('📊 Running Lighthouse CI...');
    
    return new Promise((resolve, reject) => {
      const lhci = spawn('lhci', ['autorun'], { stdio: 'inherit' });
      
      lhci.on('close', (code) => {
        if (code === 0) {
          console.log('✅ Lighthouse CI completed\n');
          resolve();
        } else {
          // Don't reject immediately - we'll analyze the results
          console.log('⚠️  Lighthouse CI finished with warnings\n');
          resolve();
        }
      });
      
      lhci.on('error', (err) => {
        reject(new Error(`Failed to run Lighthouse CI: ${err.message}`));
      });
    });
  }

  async parseLighthouseResults() {
    console.log('📈 Parsing Lighthouse results...');
    
    const lhciDir = '.lighthouseci';
    if (!fs.existsSync(lhciDir)) {
      throw new Error('Lighthouse CI results not found');
    }

    // Find the latest results
    const manifestPath = path.join(lhciDir, 'manifest.json');
    if (!fs.existsSync(manifestPath)) {
      throw new Error('Lighthouse CI manifest not found');
    }

    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    
    // Process each URL's results
    for (const result of manifest) {
      const reportPath = path.join(lhciDir, result.jsonPath);
      if (fs.existsSync(reportPath)) {
        const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
        this.analyzeReport(report, result.url);
      }
    }
  }

  analyzeReport(report, url) {
    const audits = report.audits;
    const categories = report.categories;
    
    console.log(`\n🌐 Analyzing ${url}:`);

    // Core Web Vitals
    this.checkMetric('FCP', audits['first-contentful-paint']?.numericValue, BUDGETS.fcp, url);
    this.checkMetric('LCP', audits['largest-contentful-paint']?.numericValue, BUDGETS.lcp, url);
    this.checkMetric('FID', audits['first-input-delay']?.numericValue, BUDGETS.fid, url);
    this.checkMetric('CLS', audits['cumulative-layout-shift']?.numericValue, BUDGETS.cls, url);
    this.checkMetric('TBT', audits['total-blocking-time']?.numericValue, BUDGETS.tbt, url);
    this.checkMetric('SI', audits['speed-index']?.numericValue, BUDGETS.si, url);
    this.checkMetric('TTI', audits['interactive']?.numericValue, BUDGETS.tti, url);

    // Category Scores (0-100)
    this.checkScore('Performance', categories.performance?.score * 100, BUDGETS.performanceScore, url);
    this.checkScore('Accessibility', categories.accessibility?.score * 100, BUDGETS.accessibilityScore, url);
    this.checkScore('Best Practices', categories['best-practices']?.score * 100, BUDGETS.bestPracticesScore, url);
    this.checkScore('SEO', categories.seo?.score * 100, BUDGETS.seoScore, url);

    // Resource sizes
    this.checkMetric('Total Bundle Size', audits['total-byte-weight']?.numericValue, BUDGETS.bundleSize, url);
    this.checkMetric('JavaScript Size', audits['resource-summary']?.details?.items?.find(i => i.resourceType === 'script')?.size, BUDGETS.jsSize, url);
    this.checkMetric('CSS Size', audits['resource-summary']?.details?.items?.find(i => i.resourceType === 'stylesheet')?.size, BUDGETS.cssSize, url);
    
    // Unused resources (warnings only)
    this.checkMetric('Unused JavaScript', audits['unused-javascript']?.numericValue, BUDGETS.unusedJs, url, true);
    this.checkMetric('Unused CSS', audits['unused-css-rules']?.numericValue, BUDGETS.unusedCss, url, true);
    
    // DOM complexity
    this.checkMetric('DOM Nodes', audits['dom-size']?.numericValue, BUDGETS.domNodes, url);
  }

  checkMetric(name, value, budget, url, warningOnly = false) {
    if (value === undefined || value === null) {
      console.log(`   ⚠️  ${name}: No data available`);
      return;
    }

    const passed = value <= budget;
    const severity = warningOnly ? 'warning' : 'error';
    
    if (passed) {
      console.log(`   ✅ ${name}: ${this.formatValue(value)} (budget: ${this.formatValue(budget)})`);
    } else {
      const message = `${name} exceeded budget: ${this.formatValue(value)} > ${this.formatValue(budget)} (${url})`;
      console.log(`   ❌ ${name}: ${this.formatValue(value)} (budget: ${this.formatValue(budget)})`);
      
      if (warningOnly) {
        this.warnings.push(message);
      } else {
        this.violations.push(message);
      }
    }
  }

  checkScore(name, score, budget, url) {
    if (score === undefined || score === null) {
      console.log(`   ⚠️  ${name}: No data available`);
      return;
    }

    const passed = score >= budget;
    
    if (passed) {
      console.log(`   ✅ ${name}: ${score.toFixed(1)} (budget: ${budget})`);
    } else {
      const message = `${name} below budget: ${score.toFixed(1)} < ${budget} (${url})`;
      console.log(`   ❌ ${name}: ${score.toFixed(1)} (budget: ${budget})`);
      this.violations.push(message);
    }
  }

  formatValue(value) {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(2)}MB`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}KB`;
    } else if (value < 1) {
      return value.toFixed(3);
    } else {
      return Math.round(value).toString();
    }
  }

  async checkBundleSizes() {
    console.log('\n📦 Checking bundle sizes...');
    
    // Look for bundle analysis files
    const buildDirs = ['dist', 'build', '.next'];
    
    for (const dir of buildDirs) {
      if (fs.existsSync(dir)) {
        await this.analyzeBundleSize(dir);
        break;
      }
    }
  }

  async analyzeBundleSize(buildDir) {
    // This is a simplified bundle analysis
    // In a real implementation, you'd use tools like webpack-bundle-analyzer
    try {
      const stats = this.getDirSize(buildDir);
      console.log(`   📊 Build directory size: ${this.formatValue(stats)}`);
      
      if (stats > BUDGETS.bundleSize) {
        this.violations.push(`Build size exceeded budget: ${this.formatValue(stats)} > ${this.formatValue(BUDGETS.bundleSize)}`);
      }
    } catch (error) {
      console.log(`   ⚠️  Could not analyze bundle size: ${error.message}`);
    }
  }

  getDirSize(dir) {
    let size = 0;
    
    const walk = (currentPath) => {
      const files = fs.readdirSync(currentPath);
      
      for (const file of files) {
        const filePath = path.join(currentPath, file);
        const stat = fs.statSync(filePath);
        
        if (stat.isDirectory()) {
          walk(filePath);
        } else {
          size += stat.size;
        }
      }
    };
    
    walk(dir);
    return size;
  }

  generateReport() {
    console.log('\n📋 Performance Gate Report:');
    console.log('================================');
    
    if (this.violations.length === 0 && this.warnings.length === 0) {
      console.log('🎉 All performance budgets met!');
      return;
    }

    if (this.violations.length > 0) {
      console.log('\n❌ VIOLATIONS (Build will fail):');
      this.violations.forEach((violation, i) => {
        console.log(`   ${i + 1}. ${violation}`);
      });
    }

    if (this.warnings.length > 0) {
      console.log('\n⚠️  WARNINGS (Consider optimizing):');
      this.warnings.forEach((warning, i) => {
        console.log(`   ${i + 1}. ${warning}`);
      });
    }

    console.log('\n💡 Performance Optimization Tips:');
    console.log('   • Use code splitting to reduce bundle sizes');
    console.log('   • Optimize images (WebP, proper sizing)');
    console.log('   • Remove unused CSS and JavaScript');
    console.log('   • Use lazy loading for non-critical resources');
    console.log('   • Implement proper caching strategies');
    console.log('   • Consider using a CDN for static assets');
  }

  exitWithResults() {
    console.log('\n================================');
    
    if (this.violations.length > 0) {
      console.log(`❌ Performance gate FAILED with ${this.violations.length} violations`);
      console.log('Build will not proceed until performance issues are resolved.');
      process.exit(1);
    } else {
      console.log(`✅ Performance gate PASSED${this.warnings.length > 0 ? ` (${this.warnings.length} warnings)` : ''}`);
      process.exit(0);
    }
  }
}

// Run the gate
if (require.main === module) {
  const gate = new WebVitalsGate();
  gate.run().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = WebVitalsGate;