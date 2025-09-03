#!/usr/bin/env node

/**
 * Performance Monitoring Script
 * Analyzes bundle size, dependencies, and performance metrics
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const config = {
  bundleSizeLimit: 250000, // 250KB
  vendor: {
    limit: 200000, // 200KB
    threshold: 0.4, // 40% of total bundle
  },
  performance: {
    lcp: { good: 2500, poor: 4000 },
    fid: { good: 100, poor: 300 },
    cls: { good: 0.1, poor: 0.25 },
  },
};

// Colors for console output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

// Analyze bundle size
function analyzeBundleSize() {
  log('\n📦 Bundle Size Analysis', colors.blue);
  log('='.repeat(50));

  try {
    // Run size-limit to get current bundle sizes
    const output = execSync('npm run size', { encoding: 'utf8' });
    log(output);

    // Check if .next directory exists
    const nextDir = path.join(process.cwd(), '.next');
    if (!fs.existsSync(nextDir)) {
      log('❌ No build found. Run `npm run build` first.', colors.red);
      return;
    }

    // Analyze individual chunks
    const chunksDir = path.join(nextDir, 'static', 'chunks');
    if (fs.existsSync(chunksDir)) {
      const chunks = fs
        .readdirSync(chunksDir)
        .filter((file) => file.endsWith('.js'))
        .map((file) => {
          const filePath = path.join(chunksDir, file);
          const stats = fs.statSync(filePath);
          return {
            name: file,
            size: stats.size,
            sizeFormatted: formatBytes(stats.size),
          };
        })
        .sort((a, b) => b.size - a.size);

      log('\n📊 Top Chunks by Size:');
      chunks.slice(0, 10).forEach((chunk, index) => {
        const color =
          chunk.size > 100000 ? colors.red : chunk.size > 50000 ? colors.yellow : colors.green;
        log(`${index + 1}. ${chunk.name} - ${chunk.sizeFormatted}`, color);
      });

      // Calculate total size
      const totalSize = chunks.reduce((sum, chunk) => sum + chunk.size, 0);
      log(`\nTotal chunks size: ${formatBytes(totalSize)}`);

      if (totalSize > config.bundleSizeLimit) {
        log(
          `⚠️  Bundle size exceeds limit (${formatBytes(config.bundleSizeLimit)})`,
          colors.yellow
        );
      } else {
        log(`✅ Bundle size within limits`, colors.green);
      }
    }
  } catch (error) {
    log(`❌ Bundle analysis failed: ${error.message}`, colors.red);
  }
}

// Analyze dependencies
function analyzeDependencies() {
  log('\n📚 Dependency Analysis', colors.blue);
  log('='.repeat(50));

  try {
    const packageJson = JSON.parse(
      fs.readFileSync(path.join(process.cwd(), 'package.json'), 'utf8')
    );

    const dependencies = Object.keys(packageJson.dependencies || {});
    const devDependencies = Object.keys(packageJson.devDependencies || {});

    log(`Production dependencies: ${dependencies.length}`);
    log(`Development dependencies: ${devDependencies.length}`);

    // Check for large packages
    const heavyPackages = [
      'lodash',
      'moment',
      'rxjs',
      '@angular/core',
      'bootstrap',
      'jquery',
      'three',
      'fabric',
      'codemirror',
    ];

    const foundHeavyPackages = dependencies.filter((dep) =>
      heavyPackages.some((heavy) => dep.includes(heavy))
    );

    if (foundHeavyPackages.length > 0) {
      log('\n⚠️  Heavy packages detected:', colors.yellow);
      foundHeavyPackages.forEach((pkg) => log(`  - ${pkg}`, colors.yellow));
    }

    // Check for duplicates
    const allDeps = [...dependencies, ...devDependencies];
    const duplicates = allDeps.filter((dep, index) => allDeps.indexOf(dep) !== index);

    if (duplicates.length > 0) {
      log('\n⚠️  Duplicate dependencies:', colors.yellow);
      duplicates.forEach((dep) => log(`  - ${dep}`, colors.yellow));
    } else {
      log('\n✅ No duplicate dependencies found', colors.green);
    }

    // Run npm audit
    log('\n🔒 Security Audit:');
    try {
      execSync('npm audit --audit-level moderate', { stdio: 'inherit' });
      log('✅ No high-severity vulnerabilities found', colors.green);
    } catch (error) {
      log('⚠️  Security vulnerabilities found. Run `npm audit fix`', colors.yellow);
    }
  } catch (error) {
    log(`❌ Dependency analysis failed: ${error.message}`, colors.red);
  }
}

// Check build configuration
function checkBuildConfig() {
  log('\n⚙️  Build Configuration', colors.blue);
  log('='.repeat(50));

  // Check Next.js config
  const nextConfigPath = path.join(process.cwd(), 'next.config.js');
  if (fs.existsSync(nextConfigPath)) {
    log('✅ next.config.js found');

    const config = fs.readFileSync(nextConfigPath, 'utf8');

    // Check for optimizations
    const optimizations = [
      { name: 'Bundle Analyzer', check: /withBundleAnalyzer/ },
      { name: 'SWC Minification', check: /swcMinify.*true/ },
      { name: 'Tree Shaking', check: /usedExports.*true/ },
      { name: 'Code Splitting', check: /splitChunks/ },
      { name: 'Image Optimization', check: /images:/ },
    ];

    log('\n🚀 Enabled Optimizations:');
    optimizations.forEach((opt) => {
      if (opt.check.test(config)) {
        log(`  ✅ ${opt.name}`, colors.green);
      } else {
        log(`  ❌ ${opt.name}`, colors.red);
      }
    });
  } else {
    log('❌ next.config.js not found', colors.red);
  }

  // Check TypeScript config
  const tsconfigPath = path.join(process.cwd(), 'tsconfig.json');
  if (fs.existsSync(tsconfigPath)) {
    log('\n✅ TypeScript configuration found');
  } else {
    log('\n❌ TypeScript configuration not found', colors.red);
  }

  // Check for performance budgets
  const sizeLimitPath = path.join(process.cwd(), '.size-limit.js');
  if (fs.existsSync(sizeLimitPath)) {
    log('✅ Performance budgets configured (.size-limit.js)');
  } else {
    log('❌ No performance budgets configured', colors.red);
  }
}

// Generate recommendations
function generateRecommendations() {
  log('\n💡 Performance Recommendations', colors.blue);
  log('='.repeat(50));

  const recommendations = [
    {
      title: 'Enable Gzip/Brotli Compression',
      description: 'Configure your server to compress static assets',
      impact: 'High',
    },
    {
      title: 'Implement Image Optimization',
      description: 'Use Next.js Image component with WebP/AVIF formats',
      impact: 'High',
    },
    {
      title: 'Add Service Worker for Caching',
      description: 'Implement PWA features for offline functionality',
      impact: 'Medium',
    },
    {
      title: 'Optimize Third-Party Scripts',
      description: 'Load non-critical scripts with next/script',
      impact: 'Medium',
    },
    {
      title: 'Implement Code Splitting',
      description: 'Use dynamic imports for heavy components',
      impact: 'High',
    },
    {
      title: 'Enable React Strict Mode',
      description: 'Catch potential issues during development',
      impact: 'Low',
    },
  ];

  recommendations.forEach((rec, index) => {
    const color =
      rec.impact === 'High' ? colors.red : rec.impact === 'Medium' ? colors.yellow : colors.green;

    log(`${index + 1}. ${rec.title}`, color);
    log(`   ${rec.description}`);
    log(`   Impact: ${rec.impact}\n`);
  });
}

// Utility functions
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Main execution
function main() {
  log('🚀 DotMac Customer Portal - Performance Monitor', colors.blue);
  log('='.repeat(60));

  try {
    analyzeBundleSize();
    analyzeDependencies();
    checkBuildConfig();
    generateRecommendations();

    log('\n✨ Analysis complete!', colors.green);
    log('Run specific commands for detailed analysis:', colors.blue);
    log('  npm run analyze        - Bundle analyzer');
    log('  npm run size           - Size limits check');
    log('  npm run audit:deps     - Security audit');
  } catch (error) {
    log(`❌ Performance monitoring failed: ${error.message}`, colors.red);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = {
  analyzeBundleSize,
  analyzeDependencies,
  checkBuildConfig,
  generateRecommendations,
};
