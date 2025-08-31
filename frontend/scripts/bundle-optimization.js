/**
 * Bundle Optimization Script for DotMac ISP Platform
 * Analyzes and optimizes bundle sizes across all portal applications
 */

const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const APPS_DIR = path.join(__dirname, '../apps');
const PACKAGES_DIR = path.join(__dirname, '../packages');

async function runCommand(command, cwd = process.cwd()) {
  return new Promise((resolve, reject) => {
    exec(command, { cwd, maxBuffer: 1024 * 1024 * 10 }, (error, stdout, stderr) => {
      if (error) {
        reject(error);
      } else {
        resolve({ stdout, stderr });
      }
    });
  });
}

async function analyzeBundles() {
  console.log('🔍 Starting Bundle Analysis...\n');
  
  const apps = fs.readdirSync(APPS_DIR).filter(dir => 
    fs.statSync(path.join(APPS_DIR, dir)).isDirectory() && 
    fs.existsSync(path.join(APPS_DIR, dir, 'package.json'))
  );

  const results = {};

  for (const app of apps) {
    const appPath = path.join(APPS_DIR, app);
    console.log(`📊 Analyzing ${app}...`);

    try {
      // Check if app has Next.js
      const packageJson = JSON.parse(fs.readFileSync(path.join(appPath, 'package.json'), 'utf8'));
      
      if (packageJson.dependencies?.next || packageJson.devDependencies?.next) {
        console.log(`  ✅ Next.js app detected - analyzing bundle`);
        
        // Build with bundle analyzer
        process.env.ANALYZE = 'true';
        
        try {
          await runCommand('npm run build', appPath);
          
          // Check for bundle report
          const buildDirs = ['.next/analyze', '.next/static', 'dist'];
          let bundleSize = 0;
          
          for (const buildDir of buildDirs) {
            const fullPath = path.join(appPath, buildDir);
            if (fs.existsSync(fullPath)) {
              bundleSize += await getDirSize(fullPath);
            }
          }
          
          results[app] = {
            type: 'next.js',
            bundleSize: Math.round(bundleSize / 1024 / 1024 * 100) / 100, // MB
            optimizations: []
          };
          
          // Suggest optimizations
          if (bundleSize > 10 * 1024 * 1024) { // > 10MB
            results[app].optimizations.push('Bundle size large - consider code splitting');
          }
          
          if (packageJson.dependencies && Object.keys(packageJson.dependencies).length > 50) {
            results[app].optimizations.push('Many dependencies - audit for unused packages');
          }
          
        } catch (buildError) {
          console.log(`  ⚠️  Build failed: ${buildError.message}`);
          results[app] = {
            type: 'next.js',
            error: buildError.message
          };
        }
      } else {
        console.log(`  📦 Package library detected`);
        
        // Check for dist folder
        const distPath = path.join(appPath, 'dist');
        if (fs.existsSync(distPath)) {
          const distSize = await getDirSize(distPath);
          results[app] = {
            type: 'library',
            distSize: Math.round(distSize / 1024 * 100) / 100, // KB
            optimizations: []
          };
        } else {
          results[app] = {
            type: 'library',
            status: 'no build output'
          };
        }
      }
      
    } catch (error) {
      console.log(`  ❌ Error analyzing ${app}: ${error.message}`);
      results[app] = { error: error.message };
    }
    
    console.log(`  ✅ ${app} analysis complete\n`);
  }

  return results;
}

async function getDirSize(dirPath) {
  let totalSize = 0;
  
  try {
    const items = fs.readdirSync(dirPath);
    
    for (const item of items) {
      const itemPath = path.join(dirPath, item);
      const stats = fs.statSync(itemPath);
      
      if (stats.isDirectory()) {
        totalSize += await getDirSize(itemPath);
      } else {
        totalSize += stats.size;
      }
    }
  } catch (error) {
    // Directory might not exist or be accessible
    return 0;
  }
  
  return totalSize;
}

function generateOptimizationReport(results) {
  console.log('\n📈 BUNDLE OPTIMIZATION REPORT\n');
  console.log('=' .repeat(60));
  
  const apps = Object.keys(results);
  let totalBundleSize = 0;
  let totalOptimizations = 0;
  
  apps.forEach(app => {
    const result = results[app];
    console.log(`\n🎯 ${app.toUpperCase()}`);
    
    if (result.error) {
      console.log(`   ❌ Error: ${result.error}`);
      return;
    }
    
    if (result.type === 'next.js') {
      if (result.bundleSize) {
        console.log(`   📦 Bundle Size: ${result.bundleSize}MB`);
        totalBundleSize += result.bundleSize;
        
        if (result.optimizations.length > 0) {
          console.log(`   🔧 Optimizations:`);
          result.optimizations.forEach(opt => {
            console.log(`      - ${opt}`);
            totalOptimizations++;
          });
        } else {
          console.log(`   ✅ Bundle optimized`);
        }
      } else {
        console.log(`   ⚠️  Bundle size could not be determined`);
      }
    } else if (result.type === 'library') {
      if (result.distSize) {
        console.log(`   📚 Library Size: ${result.distSize}KB`);
        if (result.optimizations.length > 0) {
          console.log(`   🔧 Optimizations:`);
          result.optimizations.forEach(opt => {
            console.log(`      - ${opt}`);
            totalOptimizations++;
          });
        }
      } else {
        console.log(`   📚 Library: ${result.status || 'No build output'}`);
      }
    }
  });
  
  console.log('\n' + '=' .repeat(60));
  console.log(`📊 SUMMARY:`);
  console.log(`   Total Applications: ${apps.length}`);
  console.log(`   Total Bundle Size: ${totalBundleSize.toFixed(2)}MB`);
  console.log(`   Optimization Opportunities: ${totalOptimizations}`);
  
  if (totalBundleSize > 100) {
    console.log(`   ⚠️  Large total bundle size - consider micro-frontend architecture`);
  }
  
  if (totalOptimizations === 0) {
    console.log(`   ✅ All bundles are well optimized!`);
  }
  
  console.log('\n🚀 Optimization Recommendations:');
  console.log('   1. Implement dynamic imports for large components');
  console.log('   2. Use Next.js bundle analyzer to identify heavy dependencies'); 
  console.log('   3. Enable tree shaking for unused code elimination');
  console.log('   4. Consider lazy loading for non-critical components');
  console.log('   5. Optimize images and assets with Next.js Image component');
  
  return {
    totalApps: apps.length,
    totalBundleSize,
    totalOptimizations,
    results
  };
}

async function main() {
  try {
    const results = await analyzeBundles();
    const report = generateOptimizationReport(results);
    
    // Save report to file
    const reportPath = path.join(__dirname, '../bundle-analysis-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`\n💾 Report saved to: ${reportPath}`);
    
  } catch (error) {
    console.error('❌ Bundle analysis failed:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { analyzeBundles, generateOptimizationReport };