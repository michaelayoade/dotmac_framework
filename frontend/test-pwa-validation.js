#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

console.log('🔍 DotMac PWA Validation Test\n');

// Test configuration
const testConfig = {
  resellerApp: {
    path: './isp-framework/reseller',
    port: 3002,
    name: 'Reseller Portal',
  },
  technicianApp: {
    path: './isp-framework/field-ops',
    port: 3003,
    name: 'Technician Mobile Portal',
  },
};

// Validation functions
function validateManifest(appPath, appName) {
  const manifestPath = path.join(appPath, 'public', 'manifest.json');

  try {
    if (!fs.existsSync(manifestPath)) {
      console.log(`❌ ${appName}: manifest.json not found`);
      return false;
    }

    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    const requiredFields = [
      'name',
      'short_name',
      'start_url',
      'display',
      'theme_color',
      'background_color',
      'icons',
    ];

    const missingFields = requiredFields.filter((field) => !manifest[field]);

    if (missingFields.length > 0) {
      console.log(`❌ ${appName}: Missing required manifest fields: ${missingFields.join(', ')}`);
      return false;
    }

    // Check icons
    if (!manifest.icons || manifest.icons.length === 0) {
      console.log(`❌ ${appName}: No icons defined in manifest`);
      return false;
    }

    const hasRequiredSizes = manifest.icons.some(
      (icon) => icon.sizes === '192x192' || icon.sizes === '512x512'
    );

    if (!hasRequiredSizes) {
      console.log(`❌ ${appName}: Missing required icon sizes (192x192 or 512x512)`);
      return false;
    }

    console.log(`✅ ${appName}: Valid PWA manifest`);
    return true;
  } catch (error) {
    console.log(`❌ ${appName}: Invalid manifest.json - ${error.message}`);
    return false;
  }
}

function validateServiceWorker(appPath, appName) {
  const swPath = path.join(appPath, 'public', 'sw.js');

  if (!fs.existsSync(swPath)) {
    console.log(`❌ ${appName}: Service Worker not found`);
    return false;
  }

  try {
    const swContent = fs.readFileSync(swPath, 'utf8');

    // Check for essential SW features
    const requiredFeatures = [
      'install',
      'activate',
      'fetch',
      'caches.open',
      'cache.addAll',
      'cache.put',
      'caches.match',
    ];

    const missingFeatures = requiredFeatures.filter((feature) => !swContent.includes(feature));

    if (missingFeatures.length > 0) {
      console.log(`⚠️  ${appName}: Service Worker missing features: ${missingFeatures.join(', ')}`);
    }

    // Check for offline support
    if (!swContent.includes('offline') && !swContent.includes('cache')) {
      console.log(`⚠️  ${appName}: Service Worker may not support offline functionality`);
    }

    console.log(`✅ ${appName}: Service Worker found and contains basic functionality`);
    return true;
  } catch (error) {
    console.log(`❌ ${appName}: Error reading Service Worker - ${error.message}`);
    return false;
  }
}

function validateOfflineSupport(appPath, appName) {
  // Check for offline database implementation
  const dbPath = path.join(appPath, 'src', 'lib', 'offline-db.ts');
  const offlinePage = path.join(appPath, 'src', 'app', 'offline', 'page.tsx');

  let score = 0;
  let maxScore = 4;

  if (fs.existsSync(dbPath)) {
    score++;
    console.log(`✅ ${appName}: Offline database implementation found`);
  } else {
    console.log(`❌ ${appName}: No offline database implementation`);
  }

  if (fs.existsSync(offlinePage)) {
    score++;
    console.log(`✅ ${appName}: Offline fallback page found`);
  } else {
    console.log(`❌ ${appName}: No offline fallback page`);
  }

  // Check for PWA hooks
  const hooksPath = path.join(appPath, 'src', 'hooks');
  if (fs.existsSync(hooksPath)) {
    const hooks = fs.readdirSync(hooksPath);
    if (hooks.some((hook) => hook.includes('PWA') || hook.includes('offline'))) {
      score++;
      console.log(`✅ ${appName}: PWA/Offline hooks found`);
    } else {
      console.log(`⚠️  ${appName}: No PWA-specific hooks found`);
    }
  }

  // Check for sync functionality
  const syncHook = path.join(hooksPath, 'useOfflineSync.ts');
  if (fs.existsSync(syncHook)) {
    score++;
    console.log(`✅ ${appName}: Offline sync functionality found`);
  } else {
    console.log(`❌ ${appName}: No offline sync functionality`);
  }

  const percentage = Math.round((score / maxScore) * 100);
  console.log(`📊 ${appName}: Offline support score: ${score}/${maxScore} (${percentage}%)`);

  return score >= 3; // At least 75% for passing
}

function validateMobileOptimization(appPath, appName) {
  const layoutPath = path.join(appPath, 'src', 'app', 'layout.tsx');
  const globalCssPath = path.join(appPath, 'src', 'app', 'globals.css');

  let mobileFeatures = 0;

  if (fs.existsSync(layoutPath)) {
    const layoutContent = fs.readFileSync(layoutPath, 'utf8');

    // Check viewport configuration
    if (layoutContent.includes('viewport') && layoutContent.includes('width=device-width')) {
      mobileFeatures++;
      console.log(`✅ ${appName}: Proper viewport configuration`);
    } else {
      console.log(`❌ ${appName}: Missing or improper viewport configuration`);
    }

    // Check for PWA meta tags
    if (
      layoutContent.includes('apple-mobile-web-app') ||
      layoutContent.includes('mobile-web-app')
    ) {
      mobileFeatures++;
      console.log(`✅ ${appName}: Mobile web app meta tags found`);
    } else {
      console.log(`❌ ${appName}: Missing mobile web app meta tags`);
    }
  }

  if (fs.existsSync(globalCssPath)) {
    const cssContent = fs.readFileSync(globalCssPath, 'utf8');

    // Check for safe area support
    if (cssContent.includes('safe-area') || cssContent.includes('env(')) {
      mobileFeatures++;
      console.log(`✅ ${appName}: Safe area support found`);
    } else {
      console.log(`⚠️  ${appName}: No safe area support (for notched devices)`);
    }

    // Check for touch-friendly styles
    if (
      cssContent.includes('touch') ||
      cssContent.includes('44px') ||
      cssContent.includes('tap-highlight')
    ) {
      mobileFeatures++;
      console.log(`✅ ${appName}: Touch-friendly styles found`);
    } else {
      console.log(`⚠️  ${appName}: May not have touch-friendly styles`);
    }
  }

  return mobileFeatures >= 3;
}

function validatePackageJson(appPath, appName) {
  const packagePath = path.join(appPath, 'package.json');

  if (!fs.existsSync(packagePath)) {
    console.log(`❌ ${appName}: package.json not found`);
    return false;
  }

  try {
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));

    // Check for PWA-related dependencies
    const dependencies = { ...pkg.dependencies, ...pkg.devDependencies };
    const pwaDepCount = Object.keys(dependencies).filter(
      (dep) =>
        dep.includes('workbox') ||
        dep.includes('pwa') ||
        dep.includes('dexie') ||
        dep.includes('idb') ||
        dep.includes('capacitor') ||
        dep.includes('framer-motion')
    ).length;

    if (pwaDepCount >= 2) {
      console.log(`✅ ${appName}: PWA-related dependencies found (${pwaDepCount})`);
      return true;
    } else {
      console.log(`⚠️  ${appName}: Limited PWA dependencies (${pwaDepCount})`);
      return false;
    }
  } catch (error) {
    console.log(`❌ ${appName}: Invalid package.json - ${error.message}`);
    return false;
  }
}

function generatePWAReport(appName, results) {
  const totalTests = Object.keys(results).length;
  const passedTests = Object.values(results).filter(Boolean).length;
  const score = Math.round((passedTests / totalTests) * 100);

  console.log(`\n📊 ${appName} PWA Score: ${passedTests}/${totalTests} (${score}%)`);

  if (score >= 80) {
    console.log(`🎉 ${appName}: Excellent PWA implementation!`);
  } else if (score >= 60) {
    console.log(`👍 ${appName}: Good PWA implementation with room for improvement`);
  } else if (score >= 40) {
    console.log(`⚠️  ${appName}: Basic PWA implementation, needs improvement`);
  } else {
    console.log(`❌ ${appName}: Poor PWA implementation, major improvements needed`);
  }

  return { score, passed: passedTests, total: totalTests };
}

// Main validation function
function validatePWA(appConfig) {
  console.log(`\n🔍 Testing ${appConfig.name} (${appConfig.path})\n`);

  const results = {
    manifest: validateManifest(appConfig.path, appConfig.name),
    serviceWorker: validateServiceWorker(appConfig.path, appConfig.name),
    offlineSupport: validateOfflineSupport(appConfig.path, appConfig.name),
    mobileOptimization: validateMobileOptimization(appConfig.path, appConfig.name),
    dependencies: validatePackageJson(appConfig.path, appConfig.name),
  };

  return generatePWAReport(appConfig.name, results);
}

// Run validation
console.log('Starting PWA validation tests...\n');

const results = {};

// Test Reseller Portal
results.reseller = validatePWA(testConfig.resellerApp);

// Test Technician Portal
results.technician = validatePWA(testConfig.technicianApp);

// Overall summary
console.log('\n' + '='.repeat(60));
console.log('📋 OVERALL PWA VALIDATION SUMMARY');
console.log('='.repeat(60));

const totalScore = (results.reseller.score + results.technician.score) / 2;
const totalPassed = results.reseller.passed + results.technician.passed;
const totalTests = results.reseller.total + results.technician.total;

console.log(
  `\nReseller Portal: ${results.reseller.score}% (${results.reseller.passed}/${results.reseller.total})`
);
console.log(
  `Technician Portal: ${results.technician.score}% (${results.technician.passed}/${results.technician.total})`
);
console.log(`\nOverall Score: ${Math.round(totalScore)}% (${totalPassed}/${totalTests})`);

if (totalScore >= 80) {
  console.log('\n🏆 Excellent! Both portals have strong PWA implementations.');
} else if (totalScore >= 60) {
  console.log('\n👍 Good progress! PWA features are well implemented.');
} else {
  console.log('\n⚠️  PWA implementation needs improvement.');
}

console.log('\n📝 Recommendations:');
if (results.reseller.score < 80) {
  console.log('- Enhance Reseller Portal PWA features');
}
if (results.technician.score < 80) {
  console.log('- Enhance Technician Portal PWA features');
}
console.log('- Test offline functionality manually');
console.log('- Test installation on mobile devices');
console.log('- Validate performance with Lighthouse');
console.log('- Test background sync capabilities');

console.log('\n✅ PWA validation complete!');
