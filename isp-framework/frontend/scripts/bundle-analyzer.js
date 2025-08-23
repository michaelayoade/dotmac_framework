#!/usr/bin/env node
/* eslint-disable @typescript-eslint/no-require-imports */

const fs = require('node:fs').promises;
const path = require('node:path');
const { execSync } = require('node:child_process');

const chalk = require('chalk');

const APPS = ['admin', 'customer', 'reseller'];
const SIZE_THRESHOLDS = {
  warning: 1024 * 1024, // 1MB
  error: 2 * 1024 * 1024, // 2MB
};

class BundleAnalyzer {
  constructor() {
    this.results = {
      apps: {},
      summary: {
        totalSize: 0,
        warnings: [],
        errors: [],
      },
    };
  }

  async analyzeBundles() {
    console.log(chalk.blue('🔍 Analyzing bundle sizes...\n'));

    for (const app of APPS) {
      try {
        await this.analyzeApp(app);
      } catch (error) {
        console.error(chalk.red(`❌ Failed to analyze ${app}:`), error.message);
      }
    }

    await this.generateReport();
    this.printSummary();
  }

  async analyzeApp(appName) {
    const appPath = path.join(process.cwd(), 'apps', appName);

    console.log(chalk.cyan(`📊 Analyzing ${appName} app...`));

    // Check if app exists
    try {
      await fs.access(appPath);
    } catch {
      console.log(chalk.yellow(`⚠️  ${appName} app not found, skipping...`));
      return;
    }

    const _buildPath = path.join(appPath, '.next', 'static');
    let stats = null;

    try {
      // Build the app if not already built
      const nextBuildPath = path.join(appPath, '.next');
      try {
        await fs.access(nextBuildPath);
      } catch {
        console.log(chalk.yellow(`📦 Building ${appName} app...`));
        execSync('pnpm build', { cwd: appPath, stdio: 'pipe' });
      }

      stats = await this.getNextJsStats(appPath);
    } catch (error) {
      console.log(chalk.yellow(`⚠️  Could not analyze ${appName}: ${error.message}`));
      return;
    }

    const analysis = {
      name: appName,
      pages: stats.pages || {},
      chunks: stats.chunks || {},
      totalSize: stats.totalSize || 0,
      recommendations: [],
    };

    // Analyze page sizes
    this.analyzePageSizes(analysis);

    // Analyze chunk sizes
    this.analyzeChunkSizes(analysis);

    // Generate recommendations
    this.generateRecommendations(analysis);

    this.results.apps[appName] = analysis;
    this.results.summary.totalSize += analysis.totalSize;

    console.log(chalk.green(`✅ ${appName} analysis complete`));
  }

  async getNextJsStats(appPath) {
    try {
      // Try to read Next.js build stats
      const _buildManifest = path.join(appPath, '.next', 'static', 'chunks', '_buildManifest.js');

      // Alternatively, parse the build output or use webpack-bundle-analyzer
      // For now, we'll use a simpler approach by analyzing the .next directory

      return await this.analyzeNextDir(path.join(appPath, '.next'));
    } catch (_error) {
      // Fallback to directory analysis
      return await this.analyzeDirectory(appPath);
    }
  }

  async analyzeNextDir(nextPath) {
    const stats = {
      pages: {},
      chunks: {},
      totalSize: 0,
    };

    try {
      // Analyze static chunks
      const staticPath = path.join(nextPath, 'static', 'chunks');
      const chunks = await this.getDirectoryFiles(staticPath);

      for (const chunk of chunks) {
        const filePath = path.join(staticPath, chunk);
        const stat = await fs.stat(filePath);
        stats.chunks[chunk] = {
          size: stat.size,
          path: filePath,
        };
        stats.totalSize += stat.size;
      }

      // Analyze server chunks if they exist
      const serverPath = path.join(nextPath, 'server', 'pages');
      try {
        await fs.access(serverPath);
        const serverFiles = await this.getDirectoryFiles(serverPath, true);

        for (const file of serverFiles) {
          const filePath = path.join(serverPath, file);
          const stat = await fs.stat(filePath);
          stats.pages[file] = {
            size: stat.size,
            path: filePath,
          };
          stats.totalSize += stat.size;
        }
      } catch {
        // Server pages might not exist in all builds
      }
    } catch (error) {
      console.log(chalk.yellow(`Could not analyze .next directory: ${error.message}`));
    }

    return stats;
  }

  async getDirectoryFiles(dirPath, recursive = false) {
    try {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      let files = [];

      for (const entry of entries) {
        if (entry.isFile() && (entry.name.endsWith('.js') || entry.name.endsWith('.css'))) {
          files.push(entry.name);
        } else if (recursive && entry.isDirectory()) {
          const subFiles = await this.getDirectoryFiles(path.join(dirPath, entry.name), recursive);
          files = files.concat(subFiles.map((f) => path.join(entry.name, f)));
        }
      }

      return files;
    } catch {
      return [];
    }
  }

  async analyzeDirectory(dirPath) {
    const stats = {
      pages: {},
      chunks: {},
      totalSize: 0,
    };

    try {
      const files = await this.getDirectoryFiles(dirPath, true);

      for (const file of files) {
        const filePath = path.join(dirPath, file);
        try {
          const stat = await fs.stat(filePath);
          stats.chunks[file] = {
            size: stat.size,
            path: filePath,
          };
          stats.totalSize += stat.size;
        } catch {
          // Skip files that can't be read
        }
      }
    } catch {
      // Directory doesn't exist or can't be read
    }

    return stats;
  }

  analyzePageSizes(analysis) {
    for (const [pageName, pageInfo] of Object.entries(analysis.pages)) {
      if (pageInfo.size > SIZE_THRESHOLDS.error) {
        analysis.recommendations.push({
          type: 'error',
          message: `Page ${pageName} is ${this.formatSize(pageInfo.size)} (> ${this.formatSize(SIZE_THRESHOLDS.error)})`,
          suggestion: 'Consider code splitting or reducing bundle size',
        });
        this.results.summary.errors.push(`${analysis.name}: ${pageName} too large`);
      } else if (pageInfo.size > SIZE_THRESHOLDS.warning) {
        analysis.recommendations.push({
          type: 'warning',
          message: `Page ${pageName} is ${this.formatSize(pageInfo.size)} (> ${this.formatSize(SIZE_THRESHOLDS.warning)})`,
          suggestion: 'Consider optimizing this page',
        });
        this.results.summary.warnings.push(`${analysis.name}: ${pageName} large`);
      }
    }
  }

  analyzeChunkSizes(analysis) {
    const largeChunks = Object.entries(analysis.chunks)
      .filter(([, info]) => info.size > SIZE_THRESHOLDS.warning)
      .sort((a, b) => b[1].size - a[1].size);

    if (largeChunks.length > 0) {
      analysis.recommendations.push({
        type: 'info',
        message: `Found ${largeChunks.length} large chunks`,
        suggestion:
          'Review largest chunks: ' +
          largeChunks
            .slice(0, 3)
            .map(([name]) => name)
            .join(', '),
      });
    }
  }

  generateRecommendations(analysis) {
    const totalChunks = Object.keys(analysis.chunks).length;
    const _totalPages = Object.keys(analysis.pages).length;

    // General recommendations based on bundle composition
    if (totalChunks > 50) {
      analysis.recommendations.push({
        type: 'info',
        message: `High number of chunks (${totalChunks})`,
        suggestion: 'Consider chunk optimization strategies',
      });
    }

    if (analysis.totalSize > SIZE_THRESHOLDS.error * 3) {
      analysis.recommendations.push({
        type: 'error',
        message: `Total bundle size is very large (${this.formatSize(analysis.totalSize)})`,
        suggestion: 'Implement aggressive code splitting and tree shaking',
      });
    }

    // Specific recommendations
    analysis.recommendations.push({
      type: 'info',
      message: 'Optimization opportunities',
      suggestion: [
        'Enable gzip/brotli compression',
        'Implement dynamic imports for large components',
        'Use Next.js Image optimization',
        'Consider removing unused dependencies',
        'Enable tree shaking',
      ].join('; '),
    });
  }

  async generateReport() {
    const timestamp = new Date().toISOString();
    const reportDir = path.join(process.cwd(), 'reports', 'bundle-analysis');

    await fs.mkdir(reportDir, { recursive: true });

    // Generate JSON report
    const jsonReport = {
      timestamp,
      summary: this.results.summary,
      apps: this.results.apps,
      thresholds: SIZE_THRESHOLDS,
    };

    await fs.writeFile(
      path.join(reportDir, `bundle-analysis-${timestamp.split('T')[0]}.json`),
      JSON.stringify(jsonReport, null, 2)
    );

    // Generate HTML report
    const htmlReport = this.generateHtmlReport(jsonReport);
    await fs.writeFile(
      path.join(reportDir, `bundle-analysis-${timestamp.split('T')[0]}.html`),
      htmlReport
    );

    console.log(chalk.green(`📄 Reports saved to: ${reportDir}`));
  }

  generateHtmlReport(data) {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DotMac Bundle Analysis Report</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    .header { text-align: center; margin-bottom: 30px; }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
    .metric { background: #f8f9fa; padding: 20px; border-radius: 6px; text-align: center; }
    .metric-value { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
    .app-analysis { margin-bottom: 30px; border: 1px solid #dee2e6; border-radius: 6px; overflow: hidden; }
    .app-header { background: #007bff; color: white; padding: 15px 20px; }
    .app-content { padding: 20px; }
    .recommendations { margin-top: 20px; }
    .recommendation { margin: 10px 0; padding: 10px; border-radius: 4px; }
    .recommendation.error { background: #f8d7da; border-left: 4px solid #dc3545; }
    .recommendation.warning { background: #fff3cd; border-left: 4px solid #ffc107; }
    .recommendation.info { background: #d1ecf1; border-left: 4px solid #17a2b8; }
    .chart-container { margin: 20px 0; height: 300px; }
    canvas { max-height: 300px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📊 DotMac Bundle Analysis Report</h1>
      <p>Generated on ${new Date(data.timestamp).toLocaleString()}</p>
    </div>
    
    <div class="summary">
      <div class="metric">
        <div class="metric-value">${Object.keys(data.apps).length}</div>
        <div>Apps Analyzed</div>
      </div>
      <div class="metric">
        <div class="metric-value">${this.formatSize(data.summary.totalSize)}</div>
        <div>Total Bundle Size</div>
      </div>
      <div class="metric">
        <div class="metric-value">${data.summary.warnings.length}</div>
        <div>Warnings</div>
      </div>
      <div class="metric">
        <div class="metric-value">${data.summary.errors.length}</div>
        <div>Errors</div>
      </div>
    </div>
    
    <div class="chart-container">
      <canvas id="bundleSizeChart"></canvas>
    </div>
    
    ${Object.entries(data.apps)
      .map(
        ([appName, appData]) => `
      <div class="app-analysis">
        <div class="app-header">
          <h2>${appName.charAt(0).toUpperCase() + appName.slice(1)} App</h2>
        </div>
        <div class="app-content">
          <p><strong>Total Size:</strong> ${this.formatSize(appData.totalSize)}</p>
          <p><strong>Pages:</strong> ${Object.keys(appData.pages).length}</p>
          <p><strong>Chunks:</strong> ${Object.keys(appData.chunks).length}</p>
          
          ${
            appData.recommendations.length > 0
              ? `
            <div class="recommendations">
              <h3>Recommendations</h3>
              ${appData.recommendations
                .map(
                  (rec) => `
                <div class="recommendation ${rec.type}">
                  <strong>${rec.message}</strong><br>
                  <small>${rec.suggestion}</small>
                </div>
              `
                )
                .join('')}
            </div>
          `
              : ''
          }
          
          ${
            Object.keys(appData.chunks).length > 0
              ? `
            <h4>Largest Chunks</h4>
            <ul>
              ${Object.entries(appData.chunks)
                .sort((a, b) => b[1].size - a[1].size)
                .slice(0, 5)
                .map(([name, info]) => `<li>${name}: ${this.formatSize(info.size)}</li>`)
                .join('')}
            </ul>
          `
              : ''
          }
        </div>
      </div>
    `
      )
      .join('')}
  </div>
  
  <script>
    const ctx = document.getElementById('bundleSizeChart').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ${JSON.stringify(Object.keys(data.apps))},
        datasets: [{
          label: 'Bundle Size (MB)',
          data: ${JSON.stringify(Object.values(data.apps).map((app) => (app.totalSize / 1024 / 1024).toFixed(2)))},
          backgroundColor: ['#007bff', '#28a745', '#ffc107'],
          borderColor: ['#0056b3', '#1e7e34', '#d39e00'],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Size (MB)'
            }
          }
        }
      }
    });
  </script>
</body>
</html>
    `.trim();
  }

  printSummary() {
    console.log(`\n${chalk.blue('📊 BUNDLE ANALYSIS SUMMARY')}`);
    console.log('='.repeat(50));

    console.log(`Total Apps Analyzed: ${Object.keys(this.results.apps).length}`);
    console.log(
      `Total Bundle Size: ${chalk.bold(this.formatSize(this.results.summary.totalSize))}`
    );
    console.log(`Warnings: ${chalk.yellow(this.results.summary.warnings.length)}`);
    console.log(`Errors: ${chalk.red(this.results.summary.errors.length)}`);

    // App breakdown
    for (const [appName, appData] of Object.entries(this.results.apps)) {
      console.log(`\n${chalk.cyan(appName.toUpperCase())} App:`);
      console.log(`  Size: ${this.formatSize(appData.totalSize)}`);
      console.log(`  Pages: ${Object.keys(appData.pages).length}`);
      console.log(`  Chunks: ${Object.keys(appData.chunks).length}`);
      console.log(
        `  Issues: ${appData.recommendations.filter((r) => r.type === 'error').length} errors, ${appData.recommendations.filter((r) => r.type === 'warning').length} warnings`
      );
    }

    // Recommendations
    if (this.results.summary.errors.length > 0) {
      console.log(`\n${chalk.red('❌ CRITICAL ISSUES:')}`);
      this.results.summary.errors.forEach((error) => {
        console.log(`  - ${error}`);
      });
    }

    if (this.results.summary.warnings.length > 0) {
      console.log(`\n${chalk.yellow('⚠️  WARNINGS:')}`);
      this.results.summary.warnings.forEach((warning) => {
        console.log(`  - ${warning}`);
      });
    }

    // Exit with error if critical issues found
    if (this.results.summary.errors.length > 0) {
      console.log(
        `\n${chalk.red('Bundle analysis found critical issues. Please address them before deploying.')}`
      );
      process.exit(1);
    }

    console.log(`\n${chalk.green('✅ Bundle analysis complete!')}`);
  }

  formatSize(bytes) {
    if (bytes === 0) {
      return '0 B';
    }
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
  }
}

// CLI interface
if (require.main === module) {
  const analyzer = new BundleAnalyzer();
  analyzer.analyzeBundles().catch(console.error);
}

module.exports = BundleAnalyzer;
