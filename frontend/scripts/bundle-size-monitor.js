#!/usr/bin/env node

/**
 * Bundle Size Monitor Script
 * Monitors bundle sizes across builds and enforces size budgets
 */

const fs = require('fs');
const path = require('path');
const chalk = require('chalk');
const filesize = require('filesize');
const { execSync } = require('child_process');

// Configuration
const CONFIG = {
  // Size budgets (in bytes)
  budgets: {
    // Framework applications
    'isp-framework/customer': {
      maxBundleSize: 400000,    // 400KB
      maxChunkSize: 200000,     // 200KB
      maxAssetSize: 200000,     // 200KB
    },
    'isp-framework/admin': {
      maxBundleSize: 500000,    // 500KB
      maxChunkSize: 250000,     // 250KB
      maxAssetSize: 250000,     // 250KB
    },
    'isp-framework/reseller': {
      maxBundleSize: 450000,    // 450KB
      maxChunkSize: 225000,     // 225KB
      maxAssetSize: 225000,     // 225KB
    },
    
    // Management portals
    'management-portal/admin': {
      maxBundleSize: 600000,    // 600KB
      maxChunkSize: 300000,     // 300KB
      maxAssetSize: 300000,     // 300KB
    },
    'management-portal/tenant': {
      maxBundleSize: 500000,    // 500KB
      maxChunkSize: 250000,     // 250KB
      maxAssetSize: 250000,     // 250KB
    },
    'management-portal/reseller': {
      maxBundleSize: 550000,    // 550KB
      maxChunkSize: 275000,     // 275KB
      maxAssetSize: 275000,     // 275KB
    },
  },
  
  // Warning thresholds (percentage of budget)
  warningThreshold: 0.8,      // 80%
  errorThreshold: 1.0,        // 100%
  
  // Output paths
  reportsDir: './reports/bundle-analysis',
  historyFile: './reports/bundle-history.json',
  
  // Compression analysis
  analyzeCompression: true,
  
  // CI/CD integration
  failOnBudgetExceeded: process.env.CI === 'true',
  generatePullRequestComment: process.env.CI === 'true',
};

class BundleSizeMonitor {
  constructor() {
    this.history = this.loadHistory();
    this.currentAnalysis = null;
  }
  
  /**
   * Monitor all applications
   */
  async monitorAllApps() {
    console.log(chalk.blue('🔍 Starting bundle size monitoring...\n'));
    
    const apps = Object.keys(CONFIG.budgets);
    const results = [];
    
    for (const app of apps) {
      console.log(chalk.gray(`Analyzing ${app}...`));
      
      try {
        const analysis = await this.analyzeApp(app);
        const budgetCheck = this.checkBudgets(app, analysis);
        
        results.push({
          app,
          analysis,
          budgetCheck,
        });
        
        this.logResults(app, analysis, budgetCheck);
      } catch (error) {
        console.error(chalk.red(`Error analyzing ${app}: ${error.message}`));
        results.push({
          app,
          error: error.message,
        });
      }
    }
    
    // Generate reports
    await this.generateReports(results);
    
    // Check if any budgets were exceeded
    const hasErrors = results.some(r => r.budgetCheck?.hasErrors);
    const hasWarnings = results.some(r => r.budgetCheck?.hasWarnings);
    
    // Summary
    console.log('\n' + '='.repeat(60));
    console.log(chalk.blue('📊 Bundle Size Monitoring Summary'));
    console.log('='.repeat(60));
    
    results.forEach(result => {
      if (result.error) {
        console.log(chalk.red(`❌ ${result.app}: Error`));
      } else if (result.budgetCheck.hasErrors) {
        console.log(chalk.red(`❌ ${result.app}: Budget exceeded`));
      } else if (result.budgetCheck.hasWarnings) {
        console.log(chalk.yellow(`⚠️  ${result.app}: Near budget limit`));
      } else {
        console.log(chalk.green(`✅ ${result.app}: Within budget`));
      }
    });
    
    if (hasErrors && CONFIG.failOnBudgetExceeded) {
      console.log(chalk.red('\n💥 Bundle size budgets exceeded! Failing build.'));
      process.exit(1);
    } else if (hasWarnings) {
      console.log(chalk.yellow('\n⚠️  Some bundles are approaching size limits.'));
    } else {
      console.log(chalk.green('\n🎉 All bundles are within size budgets!'));
    }
  }
  
  /**
   * Analyze specific application
   */
  async analyzeApp(appPath) {
    const buildDir = path.join(appPath, '.next');
    const statsFile = path.join(buildDir, 'build-manifest.json');
    
    if (!fs.existsSync(buildDir)) {
      throw new Error(`Build directory not found: ${buildDir}`);
    }
    
    // Get bundle files
    const bundleFiles = this.getBundleFiles(buildDir);
    
    // Calculate sizes
    const analysis = {
      app: appPath,
      timestamp: new Date().toISOString(),
      totalSize: 0,
      assets: [],
      chunks: [],
    };
    
    // Analyze JavaScript files
    const jsFiles = bundleFiles.filter(f => f.endsWith('.js') && !f.includes('_buildManifest'));
    for (const file of jsFiles) {
      const filePath = path.join(buildDir, 'static', file);
      if (fs.existsSync(filePath)) {
        const size = fs.statSync(filePath).size;
        analysis.totalSize += size;
        
        analysis.assets.push({
          name: file,
          size,
          type: 'js',
          compressed: CONFIG.analyzeCompression ? await this.getCompressedSize(filePath) : null,
        });
      }
    }
    
    // Analyze CSS files
    const cssFiles = bundleFiles.filter(f => f.endsWith('.css'));
    for (const file of cssFiles) {
      const filePath = path.join(buildDir, 'static', file);
      if (fs.existsSync(filePath)) {
        const size = fs.statSync(filePath).size;
        analysis.totalSize += size;
        
        analysis.assets.push({
          name: file,
          size,
          type: 'css',
          compressed: CONFIG.analyzeCompression ? await this.getCompressedSize(filePath) : null,
        });
      }
    }
    
    // Sort assets by size
    analysis.assets.sort((a, b) => b.size - a.size);
    
    return analysis;
  }
  
  /**
   * Get bundle files from build manifest
   */
  getBundleFiles(buildDir) {
    const manifestPath = path.join(buildDir, 'build-manifest.json');
    const staticDir = path.join(buildDir, 'static');
    
    let files = [];
    
    // Try to read build manifest
    if (fs.existsSync(manifestPath)) {
      try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        
        // Extract files from manifest
        Object.values(manifest.pages || {}).forEach(pageFiles => {
          if (Array.isArray(pageFiles)) {
            files.push(...pageFiles);
          }
        });
        
        // Add main app files
        if (manifest.files) {
          files.push(...manifest.files);
        }
      } catch (error) {
        console.warn(`Could not parse build manifest: ${error.message}`);
      }
    }
    
    // Fallback: scan static directory
    if (files.length === 0 && fs.existsSync(staticDir)) {
      const scanDir = (dir, prefix = '') => {
        const entries = fs.readdirSync(dir);
        
        entries.forEach(entry => {
          const fullPath = path.join(dir, entry);
          const relativePath = path.join(prefix, entry);
          
          if (fs.statSync(fullPath).isDirectory()) {
            scanDir(fullPath, relativePath);
          } else if (entry.endsWith('.js') || entry.endsWith('.css')) {
            files.push(relativePath);
          }
        });
      };
      
      scanDir(staticDir);
    }
    
    return [...new Set(files)]; // Remove duplicates
  }
  
  /**
   * Get compressed file size
   */
  async getCompressedSize(filePath) {
    try {
      const { gzipSize } = require('gzip-size');
      const content = fs.readFileSync(filePath);
      
      return {
        gzip: await gzipSize(content),
      };
    } catch (error) {
      console.warn(`Could not calculate compressed size for ${filePath}: ${error.message}`);
      return null;
    }
  }
  
  /**
   * Check budgets for application
   */
  checkBudgets(app, analysis) {
    const budget = CONFIG.budgets[app];
    if (!budget) {
      return { hasWarnings: false, hasErrors: false, violations: [] };
    }
    
    const violations = [];
    let hasWarnings = false;
    let hasErrors = false;
    
    // Check total bundle size
    if (analysis.totalSize > budget.maxBundleSize * CONFIG.errorThreshold) {
      violations.push({
        type: 'error',
        category: 'total',
        message: `Total bundle size (${filesize(analysis.totalSize)}) exceeds budget (${filesize(budget.maxBundleSize)})`,
        actual: analysis.totalSize,
        budget: budget.maxBundleSize,
      });
      hasErrors = true;
    } else if (analysis.totalSize > budget.maxBundleSize * CONFIG.warningThreshold) {
      violations.push({
        type: 'warning',
        category: 'total',
        message: `Total bundle size (${filesize(analysis.totalSize)}) approaching budget (${filesize(budget.maxBundleSize)})`,
        actual: analysis.totalSize,
        budget: budget.maxBundleSize,
      });
      hasWarnings = true;
    }
    
    // Check individual assets
    analysis.assets.forEach(asset => {
      if (asset.size > budget.maxAssetSize * CONFIG.errorThreshold) {
        violations.push({
          type: 'error',
          category: 'asset',
          message: `Asset ${asset.name} (${filesize(asset.size)}) exceeds budget (${filesize(budget.maxAssetSize)})`,
          actual: asset.size,
          budget: budget.maxAssetSize,
          asset: asset.name,
        });
        hasErrors = true;
      } else if (asset.size > budget.maxAssetSize * CONFIG.warningThreshold) {
        violations.push({
          type: 'warning',
          category: 'asset',
          message: `Asset ${asset.name} (${filesize(asset.size)}) approaching budget (${filesize(budget.maxAssetSize)})`,
          actual: asset.size,
          budget: budget.maxAssetSize,
          asset: asset.name,
        });
        hasWarnings = true;
      }
    });
    
    return {
      hasWarnings,
      hasErrors,
      violations,
    };
  }
  
  /**
   * Log results to console
   */
  logResults(app, analysis, budgetCheck) {
    const budget = CONFIG.budgets[app];
    
    console.log(`\n📦 ${chalk.bold(app)}`);
    console.log(`   Total Size: ${filesize(analysis.totalSize)} / ${filesize(budget.maxBundleSize)} (${Math.round((analysis.totalSize / budget.maxBundleSize) * 100)}%)`);
    console.log(`   Assets: ${analysis.assets.length}`);
    
    // Show largest assets
    if (analysis.assets.length > 0) {
      console.log('   Largest assets:');
      analysis.assets.slice(0, 3).forEach(asset => {
        const compressed = asset.compressed?.gzip ? ` (gzipped: ${filesize(asset.compressed.gzip)})` : '';
        console.log(`     • ${asset.name}: ${filesize(asset.size)}${compressed}`);
      });
    }
    
    // Show violations
    if (budgetCheck.violations.length > 0) {
      console.log('   Issues:');
      budgetCheck.violations.forEach(violation => {
        const color = violation.type === 'error' ? chalk.red : chalk.yellow;
        const icon = violation.type === 'error' ? '❌' : '⚠️';
        console.log(`     ${icon} ${color(violation.message)}`);
      });
    } else {
      console.log(chalk.green('   ✅ All checks passed'));
    }
  }
  
  /**
   * Generate reports
   */
  async generateReports(results) {
    // Ensure reports directory exists
    if (!fs.existsSync(CONFIG.reportsDir)) {
      fs.mkdirSync(CONFIG.reportsDir, { recursive: true });
    }
    
    // Generate JSON report
    const jsonReport = {
      timestamp: new Date().toISOString(),
      results,
      budgets: CONFIG.budgets,
    };
    
    fs.writeFileSync(
      path.join(CONFIG.reportsDir, 'bundle-analysis.json'),
      JSON.stringify(jsonReport, null, 2)
    );
    
    // Generate markdown report
    const markdownReport = this.generateMarkdownReport(results);
    fs.writeFileSync(
      path.join(CONFIG.reportsDir, 'bundle-analysis.md'),
      markdownReport
    );
    
    // Update history
    this.updateHistory(results);
    
    // Generate CI comment if needed
    if (CONFIG.generatePullRequestComment) {
      const comment = this.generatePullRequestComment(results);
      fs.writeFileSync(
        path.join(CONFIG.reportsDir, 'pr-comment.md'),
        comment
      );
    }
    
    console.log(chalk.gray(`\n📊 Reports generated in ${CONFIG.reportsDir}`));
  }
  
  /**
   * Generate markdown report
   */
  generateMarkdownReport(results) {
    const lines = [
      '# Bundle Size Analysis Report',
      '',
      `Generated: ${new Date().toISOString()}`,
      '',
      '## Summary',
      '',
    ];
    
    results.forEach(result => {
      if (result.error) {
        lines.push(`### ❌ ${result.app}`);
        lines.push(`Error: ${result.error}`);
      } else {
        const { analysis, budgetCheck } = result;
        const budget = CONFIG.budgets[result.app];
        const status = budgetCheck.hasErrors ? '❌' : budgetCheck.hasWarnings ? '⚠️' : '✅';
        
        lines.push(`### ${status} ${result.app}`);
        lines.push(`- Total Size: ${filesize(analysis.totalSize)} / ${filesize(budget.maxBundleSize)} (${Math.round((analysis.totalSize / budget.maxBundleSize) * 100)}%)`);
        lines.push(`- Assets: ${analysis.assets.length}`);
        
        if (analysis.assets.length > 0) {
          lines.push('- Largest assets:');
          analysis.assets.slice(0, 5).forEach(asset => {
            lines.push(`  - ${asset.name}: ${filesize(asset.size)}`);
          });
        }
        
        if (budgetCheck.violations.length > 0) {
          lines.push('- Issues:');
          budgetCheck.violations.forEach(violation => {
            lines.push(`  - ${violation.type === 'error' ? '❌' : '⚠️'} ${violation.message}`);
          });
        }
      }
      
      lines.push('');
    });
    
    return lines.join('\n');
  }
  
  /**
   * Generate pull request comment
   */
  generatePullRequestComment(results) {
    const hasErrors = results.some(r => r.budgetCheck?.hasErrors);
    const hasWarnings = results.some(r => r.budgetCheck?.hasWarnings);
    
    const title = hasErrors ? '🚨 Bundle Size Budget Exceeded' :
                 hasWarnings ? '⚠️ Bundle Size Warning' :
                 '✅ Bundle Size Check Passed';
    
    const lines = [
      `## ${title}`,
      '',
      '| App | Size | Budget | Status |',
      '|-----|------|--------|--------|',
    ];
    
    results.forEach(result => {
      if (!result.error && result.analysis) {
        const { analysis, budgetCheck } = result;
        const budget = CONFIG.budgets[result.app];
        const percentage = Math.round((analysis.totalSize / budget.maxBundleSize) * 100);
        const status = budgetCheck.hasErrors ? '❌ Over' : budgetCheck.hasWarnings ? '⚠️ Near' : '✅ OK';
        
        lines.push(`| ${result.app} | ${filesize(analysis.totalSize)} | ${filesize(budget.maxBundleSize)} (${percentage}%) | ${status} |`);
      }
    });
    
    if (hasErrors || hasWarnings) {
      lines.push('');
      lines.push('### Issues:');
      
      results.forEach(result => {
        if (result.budgetCheck?.violations.length > 0) {
          lines.push(`\n**${result.app}:**`);
          result.budgetCheck.violations.forEach(violation => {
            lines.push(`- ${violation.type === 'error' ? '❌' : '⚠️'} ${violation.message}`);
          });
        }
      });
    }
    
    return lines.join('\n');
  }
  
  /**
   * Load historical data
   */
  loadHistory() {
    if (fs.existsSync(CONFIG.historyFile)) {
      try {
        return JSON.parse(fs.readFileSync(CONFIG.historyFile, 'utf8'));
      } catch (error) {
        console.warn(`Could not load history: ${error.message}`);
      }
    }
    
    return [];
  }
  
  /**
   * Update historical data
   */
  updateHistory(results) {
    const entry = {
      timestamp: new Date().toISOString(),
      results: results.map(r => ({
        app: r.app,
        totalSize: r.analysis?.totalSize || 0,
        assetCount: r.analysis?.assets?.length || 0,
        hasErrors: r.budgetCheck?.hasErrors || false,
        hasWarnings: r.budgetCheck?.hasWarnings || false,
      })),
    };
    
    this.history.push(entry);
    
    // Keep only last 50 entries
    if (this.history.length > 50) {
      this.history = this.history.slice(-50);
    }
    
    // Ensure history directory exists
    const historyDir = path.dirname(CONFIG.historyFile);
    if (!fs.existsSync(historyDir)) {
      fs.mkdirSync(historyDir, { recursive: true });
    }
    
    fs.writeFileSync(CONFIG.historyFile, JSON.stringify(this.history, null, 2));
  }
}

// CLI interface
if (require.main === module) {
  const monitor = new BundleSizeMonitor();
  
  // Parse command line arguments
  const args = process.argv.slice(2);
  let command = 'all';
  let specificApp = null;
  let generateMarkdown = false;
  let generateReports = false;
  let isCi = false;
  
  // Parse arguments
  args.forEach(arg => {
    if (arg.startsWith('--app=')) {
      specificApp = arg.split('=')[1];
      command = 'app';
    } else if (arg === '--all-apps') {
      command = 'all';
    } else if (arg === '--generate-markdown') {
      generateMarkdown = true;
    } else if (arg === '--generate-reports') {
      generateReports = true;
    } else if (arg === '--ci') {
      isCi = true;
      CONFIG.failOnBudgetExceeded = true;
    } else if (arg === 'all') {
      command = 'all';
    } else if (arg === 'app') {
      command = 'app';
      specificApp = args[args.indexOf(arg) + 1];
    }
  });
  
  switch (command) {
    case 'all':
      monitor.monitorAllApps().then(results => {
        if (generateMarkdown) {
          const markdown = monitor.generateMarkdownReport(results);
          console.log(markdown);
        }
        
        if (generateReports) {
          console.log(chalk.gray(`📊 Reports generated in ${CONFIG.reportsDir}`));
        }
        
        const hasErrors = results.some(r => r.budgetCheck?.hasErrors);
        if (hasErrors && CONFIG.failOnBudgetExceeded) {
          process.exit(1);
        }
      }).catch(error => {
        console.error(chalk.red(`Monitoring failed: ${error.message}`));
        process.exit(1);
      });
      break;
      
    case 'app':
      if (!specificApp) {
        console.error(chalk.red('Please specify an app to analyze'));
        process.exit(1);
      }
      
      monitor.analyzeApp(specificApp).then(analysis => {
        const budgetCheck = monitor.checkBudgets(specificApp, analysis);
        monitor.logResults(specificApp, analysis, budgetCheck);
        
        if (budgetCheck.hasErrors && CONFIG.failOnBudgetExceeded) {
          process.exit(1);
        }
      }).catch(error => {
        console.error(chalk.red(`Analysis failed: ${error.message}`));
        process.exit(1);
      });
      break;
      
    default:
      console.log('Usage:');
      console.log('  node bundle-size-monitor.js                    - Monitor all applications');
      console.log('  node bundle-size-monitor.js --all-apps         - Monitor all applications');
      console.log('  node bundle-size-monitor.js --app=<name>       - Monitor specific application');
      console.log('  node bundle-size-monitor.js --generate-markdown - Output markdown report');
      console.log('  node bundle-size-monitor.js --generate-reports - Generate report files');
      console.log('  node bundle-size-monitor.js --ci               - CI mode (fail on errors)');
      break;
  }
}

module.exports = { BundleSizeMonitor, CONFIG };