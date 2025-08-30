#!/usr/bin/env node

/**
 * DotMac Architecture Analyzer
 *
 * Provides comprehensive analysis of frontend architecture and suggests improvements
 */

const fs = require('fs-extra');
const path = require('path');
const glob = require('glob');
const chalk = require('chalk');
const ora = require('ora');
const inquirer = require('inquirer');

async function main() {
  console.log(chalk.blue.bold('\n📊 DotMac Architecture Analyzer\n'));

  const { analysisMode } = await inquirer.prompt([
    {
      type: 'list',
      name: 'analysisMode',
      message: 'What would you like to analyze?',
      choices: [
        { name: '🏗️ Architecture - Complete architectural analysis', value: 'architecture' },
        { name: '📦 Dependencies - Package dependency analysis', value: 'dependencies' },
        { name: '🔄 Bundle Impact - Bundle size and duplication analysis', value: 'bundle' },
        { name: '📈 Metrics - Code quality and reusability metrics', value: 'metrics' },
        { name: '🎯 Recommendations - Get actionable recommendations', value: 'recommendations' }
      ]
    }
  ]);

  const projectRoot = process.cwd();
  const frontendPath = path.join(projectRoot, 'frontend');

  if (!fs.existsSync(frontendPath)) {
    console.error(chalk.red('❌ No frontend directory found. Are you in the project root?'));
    process.exit(1);
  }

  switch (analysisMode) {
    case 'architecture':
      await analyzeArchitecture(frontendPath);
      break;
    case 'dependencies':
      await analyzeDependencies(frontendPath);
      break;
    case 'bundle':
      await analyzeBundleImpact(frontendPath);
      break;
    case 'metrics':
      await analyzeMetrics(frontendPath);
      break;
    case 'recommendations':
      await generateRecommendations(frontendPath);
      break;
  }
}

/**
 * Comprehensive architectural analysis
 */
async function analyzeArchitecture(frontendPath) {
  const spinner = ora('🔍 Analyzing architecture...').start();

  const analysis = {
    packages: await analyzePackages(frontendPath),
    components: await analyzeComponents(frontendPath),
    providers: await analyzeProviders(frontendPath),
    dependencies: await analyzeDependencyStructure(frontendPath),
    reusability: await calculateReusabilityScore(frontendPath),
    consistency: await calculateConsistencyScore(frontendPath)
  };

  spinner.succeed('Architecture analysis complete!');

  displayArchitecturalReport(analysis);

  // Save detailed report
  const reportPath = path.join(frontendPath, 'architecture-analysis.json');
  await fs.writeJSON(reportPath, analysis, { spaces: 2 });

  console.log(chalk.green(`\n📄 Detailed report saved to: ${chalk.cyan(reportPath)}`));
}

/**
 * Analyze package structure
 */
async function analyzePackages(frontendPath) {
  const packagesPath = path.join(frontendPath, 'packages');
  const appsPath = path.join(frontendPath, 'apps');

  const packages = [];
  const apps = [];

  if (await fs.pathExists(packagesPath)) {
    const packageDirs = await fs.readdir(packagesPath);
    for (const dir of packageDirs) {
      const packagePath = path.join(packagesPath, dir);
      const packageJsonPath = path.join(packagePath, 'package.json');

      if (await fs.pathExists(packageJsonPath)) {
        const packageJson = await fs.readJSON(packageJsonPath);
        packages.push({
          name: packageJson.name,
          version: packageJson.version,
          type: 'package',
          path: path.relative(frontendPath, packagePath),
          dependencies: Object.keys(packageJson.dependencies || {}),
          devDependencies: Object.keys(packageJson.devDependencies || {}),
          exports: packageJson.exports || packageJson.main || null
        });
      }
    }
  }

  if (await fs.pathExists(appsPath)) {
    const appDirs = await fs.readdir(appsPath);
    for (const dir of appDirs) {
      const appPath = path.join(appsPath, dir);
      const packageJsonPath = path.join(appPath, 'package.json');

      if (await fs.pathExists(packageJsonPath)) {
        const packageJson = await fs.readJSON(packageJsonPath);
        apps.push({
          name: packageJson.name || dir,
          version: packageJson.version,
          type: 'app',
          path: path.relative(frontendPath, appPath),
          dependencies: Object.keys(packageJson.dependencies || {}),
          devDependencies: Object.keys(packageJson.devDependencies || {}),
          framework: detectFramework(packageJson)
        });
      }
    }
  }

  return { packages, apps, totalCount: packages.length + apps.length };
}

/**
 * Analyze component structure and duplication
 */
async function analyzeComponents(frontendPath) {
  const componentFiles = glob.sync(`${frontendPath}/**/components/**/*.{ts,tsx}`, {
    ignore: ['**/node_modules/**', '**/dist/**', '**/.next/**']
  });

  const componentMap = new Map();
  const duplicates = [];

  for (const file of componentFiles) {
    const fileName = path.basename(file, path.extname(file));
    const relativePath = path.relative(frontendPath, file);

    if (componentMap.has(fileName)) {
      componentMap.get(fileName).push(relativePath);
    } else {
      componentMap.set(fileName, [relativePath]);
    }
  }

  // Find duplicates
  for (const [name, files] of componentMap.entries()) {
    if (files.length > 1) {
      duplicates.push({
        name,
        count: files.length,
        files,
        locations: files.map(f => detectLocation(f))
      });
    }
  }

  return {
    totalComponents: componentFiles.length,
    uniqueComponents: componentMap.size,
    duplicateComponents: duplicates.length,
    duplicates: duplicates.sort((a, b) => b.count - a.count)
  };
}

/**
 * Analyze provider patterns
 */
async function analyzeProviders(frontendPath) {
  const providerFiles = glob.sync(`${frontendPath}/**/providers/**/*.{ts,tsx}`, {
    ignore: ['**/node_modules/**', '**/dist/**']
  });

  const appProviders = glob.sync(`${frontendPath}/apps/*/src/app/providers.{ts,tsx}`);
  const layoutProviders = glob.sync(`${frontendPath}/apps/*/src/app/layout.{ts,tsx}`);

  const patterns = [];
  const inconsistencies = [];

  const allProviderFiles = [...providerFiles, ...appProviders, ...layoutProviders];

  for (const file of allProviderFiles) {
    const content = await fs.readFile(file, 'utf8');
    const relativePath = path.relative(frontendPath, file);

    const providers = extractProviderUsage(content);
    const pattern = {
      file: relativePath,
      location: detectLocation(relativePath),
      providers: providers,
      hasUniversalProvider: content.includes('UniversalProviders'),
      hasCustomComposition: providers.length > 1 && !content.includes('UniversalProviders')
    };

    patterns.push(pattern);

    if (pattern.hasCustomComposition) {
      inconsistencies.push({
        file: relativePath,
        issue: 'Custom provider composition',
        providers: providers
      });
    }
  }

  return {
    totalProviderFiles: allProviderFiles.length,
    universalProviderUsage: patterns.filter(p => p.hasUniversalProvider).length,
    customCompositions: patterns.filter(p => p.hasCustomComposition).length,
    patterns,
    inconsistencies
  };
}

/**
 * Analyze dependency structure
 */
async function analyzeDependencyStructure(frontendPath) {
  const packageJsonFiles = glob.sync(`${frontendPath}/**/package.json`, {
    ignore: ['**/node_modules/**']
  });

  const dependencies = new Map();
  const devDependencies = new Map();
  const workspaceDependencies = new Map();

  for (const file of packageJsonFiles) {
    const packageJson = await fs.readJSON(file);
    const location = detectLocation(path.relative(frontendPath, file));

    // Regular dependencies
    for (const [dep, version] of Object.entries(packageJson.dependencies || {})) {
      if (!dependencies.has(dep)) {
        dependencies.set(dep, []);
      }
      dependencies.get(dep).push({ location, version, file: path.relative(frontendPath, file) });
    }

    // Dev dependencies
    for (const [dep, version] of Object.entries(packageJson.devDependencies || {})) {
      if (!devDependencies.has(dep)) {
        devDependencies.set(dep, []);
      }
      devDependencies.get(dep).push({ location, version, file: path.relative(frontendPath, file) });
    }

    // Workspace dependencies
    for (const [dep, version] of Object.entries(packageJson.dependencies || {})) {
      if (version.startsWith('workspace:')) {
        if (!workspaceDependencies.has(dep)) {
          workspaceDependencies.set(dep, []);
        }
        workspaceDependencies.get(dep).push({ location, version, file: path.relative(frontendPath, file) });
      }
    }
  }

  // Find version conflicts
  const conflicts = [];
  for (const [dep, usages] of dependencies.entries()) {
    const versions = [...new Set(usages.map(u => u.version))];
    if (versions.length > 1) {
      conflicts.push({ dependency: dep, versions, usages });
    }
  }

  return {
    totalDependencies: dependencies.size,
    totalDevDependencies: devDependencies.size,
    workspaceDependencies: workspaceDependencies.size,
    versionConflicts: conflicts.length,
    conflicts,
    mostUsedDependencies: [...dependencies.entries()]
      .sort((a, b) => b[1].length - a[1].length)
      .slice(0, 10)
      .map(([name, usages]) => ({ name, count: usages.length }))
  };
}

/**
 * Calculate reusability score
 */
async function calculateReusabilityScore(frontendPath) {
  const components = await analyzeComponents(frontendPath);
  const packages = await analyzePackages(frontendPath);

  const sharedComponents = packages.packages.filter(p =>
    p.name.includes('ui') || p.name.includes('components')
  ).length;

  const duplicateRatio = components.duplicateComponents / components.uniqueComponents;
  const packageRatio = sharedComponents / packages.totalCount;

  // Score out of 100
  const baseScore = 100;
  const duplicatePenalty = duplicateRatio * 50;
  const packageBonus = packageRatio * 20;

  const score = Math.max(0, Math.min(100, baseScore - duplicatePenalty + packageBonus));

  return {
    score: Math.round(score),
    factors: {
      duplicateRatio: Math.round(duplicateRatio * 100) / 100,
      packageRatio: Math.round(packageRatio * 100) / 100,
      sharedComponents,
      totalPackages: packages.totalCount
    }
  };
}

/**
 * Calculate consistency score
 */
async function calculateConsistencyScore(frontendPath) {
  const providers = await analyzeProviders(frontendPath);
  const components = await analyzeComponents(frontendPath);

  const providerConsistency = providers.universalProviderUsage / providers.totalProviderFiles;
  const componentConsistency = 1 - (components.duplicateComponents / components.uniqueComponents);

  const overallScore = (providerConsistency + componentConsistency) / 2 * 100;

  return {
    score: Math.round(overallScore),
    factors: {
      providerConsistency: Math.round(providerConsistency * 100),
      componentConsistency: Math.round(componentConsistency * 100),
      universalProviderUsage: providers.universalProviderUsage,
      totalProviderFiles: providers.totalProviderFiles
    }
  };
}

/**
 * Display architectural report
 */
function displayArchitecturalReport(analysis) {
  console.log(chalk.blue('\n📊 Architectural Analysis Report\n'));

  // Overview
  console.log(chalk.yellow('📋 Overview:'));
  console.log(`  • Total packages: ${chalk.cyan(analysis.packages.packages.length)}`);
  console.log(`  • Total apps: ${chalk.cyan(analysis.packages.apps.length)}`);
  console.log(`  • Total components: ${chalk.cyan(analysis.components.totalComponents)}`);
  console.log(`  • Unique components: ${chalk.cyan(analysis.components.uniqueComponents)}`);

  // Scores
  console.log(chalk.yellow('\n📈 Scores:'));
  console.log(`  • Reusability: ${getScoreColor(analysis.reusability.score)}${analysis.reusability.score}%${chalk.reset()}`);
  console.log(`  • Consistency: ${getScoreColor(analysis.consistency.score)}${analysis.consistency.score}%${chalk.reset()}`);

  // Issues
  console.log(chalk.yellow('\n⚠️ Issues Found:'));
  console.log(`  • Duplicate components: ${chalk.red(analysis.components.duplicateComponents)}`);
  console.log(`  • Custom provider compositions: ${chalk.red(analysis.providers.customCompositions)}`);
  console.log(`  • Dependency version conflicts: ${chalk.red(analysis.dependencies.versionConflicts)}`);

  // Top duplicates
  if (analysis.components.duplicates.length > 0) {
    console.log(chalk.yellow('\n🔄 Most Duplicated Components:'));
    analysis.components.duplicates.slice(0, 5).forEach(duplicate => {
      console.log(`  • ${chalk.cyan(duplicate.name)}: ${chalk.red(duplicate.count)} instances`);
      duplicate.locations.forEach(location => {
        console.log(`    - ${chalk.gray(location)}`);
      });
    });
  }

  // Recommendations
  console.log(chalk.yellow('\n💡 Quick Recommendations:'));
  if (analysis.components.duplicateComponents > 0) {
    console.log('  • Use unified component library (@dotmac/ui)');
  }
  if (analysis.providers.customCompositions > 0) {
    console.log('  • Migrate to UniversalProviders pattern');
  }
  if (analysis.dependencies.versionConflicts > 0) {
    console.log('  • Resolve dependency version conflicts');
  }
  if (analysis.reusability.score < 70) {
    console.log('  • Increase component reusability');
  }
}

/**
 * Generate comprehensive recommendations
 */
async function generateRecommendations(frontendPath) {
  const spinner = ora('🎯 Generating recommendations...').start();

  const analysis = {
    components: await analyzeComponents(frontendPath),
    providers: await analyzeProviders(frontendPath),
    dependencies: await analyzeDependencyStructure(frontendPath),
    reusability: await calculateReusabilityScore(frontendPath),
    consistency: await calculateConsistencyScore(frontendPath)
  };

  spinner.succeed('Recommendations generated!');

  const recommendations = generateActionableRecommendations(analysis);

  console.log(chalk.blue('\n🎯 Actionable Recommendations\n'));

  recommendations.forEach((rec, index) => {
    const priority = rec.priority === 'high' ? chalk.red('HIGH') :
                    rec.priority === 'medium' ? chalk.yellow('MEDIUM') : chalk.green('LOW');

    console.log(`${index + 1}. ${chalk.cyan(rec.title)} [${priority}]`);
    console.log(`   ${rec.description}`);

    if (rec.actions && rec.actions.length > 0) {
      console.log(`   ${chalk.gray('Actions:')}`);
      rec.actions.forEach(action => {
        console.log(`   • ${action}`);
      });
    }

    if (rec.impact) {
      console.log(`   ${chalk.gray(`Expected impact: ${rec.impact}`)}`);
    }
    console.log();
  });
}

/**
 * Generate actionable recommendations based on analysis
 */
function generateActionableRecommendations(analysis) {
  const recommendations = [];

  // Component duplication recommendations
  if (analysis.components.duplicateComponents > 0) {
    recommendations.push({
      title: 'Eliminate Component Duplication',
      priority: 'high',
      description: `Found ${analysis.components.duplicateComponents} duplicate components. This increases bundle size and maintenance overhead.`,
      actions: [
        'Run: dotmac-migrate components',
        'Implement unified @dotmac/ui components',
        'Setup governance rules to prevent future duplication'
      ],
      impact: `Reduce bundle size by ~${Math.round(analysis.components.duplicateComponents * 2)}KB`
    });
  }

  // Provider pattern recommendations
  if (analysis.providers.customCompositions > 0) {
    recommendations.push({
      title: 'Standardize Provider Patterns',
      priority: 'high',
      description: `Found ${analysis.providers.customCompositions} custom provider compositions. This creates inconsistency across apps.`,
      actions: [
        'Run: dotmac-migrate providers',
        'Implement UniversalProviders pattern',
        'Remove custom provider compositions'
      ],
      impact: 'Improve consistency and reduce maintenance overhead'
    });
  }

  // Dependency conflict recommendations
  if (analysis.dependencies.versionConflicts > 0) {
    recommendations.push({
      title: 'Resolve Dependency Conflicts',
      priority: 'medium',
      description: `Found ${analysis.dependencies.versionConflicts} dependency version conflicts that may cause runtime issues.`,
      actions: [
        'Review conflicting dependencies',
        'Standardize versions across packages',
        'Use workspace protocol for internal dependencies'
      ],
      impact: 'Prevent runtime issues and improve stability'
    });
  }

  // Reusability recommendations
  if (analysis.reusability.score < 70) {
    recommendations.push({
      title: 'Improve Component Reusability',
      priority: 'medium',
      description: `Reusability score is ${analysis.reusability.score}%. Low reusability leads to duplicated effort.`,
      actions: [
        'Extract common components to shared packages',
        'Implement variant-based component design',
        'Create component library documentation'
      ],
      impact: 'Reduce development time and improve consistency'
    });
  }

  // Consistency recommendations
  if (analysis.consistency.score < 70) {
    recommendations.push({
      title: 'Improve Architectural Consistency',
      priority: 'medium',
      description: `Consistency score is ${analysis.consistency.score}%. Inconsistent patterns increase cognitive load.`,
      actions: [
        'Implement architectural governance rules',
        'Create development guidelines',
        'Setup automated consistency checks'
      ],
      impact: 'Improve developer experience and code quality'
    });
  }

  return recommendations.sort((a, b) => {
    const priorityOrder = { high: 3, medium: 2, low: 1 };
    return priorityOrder[b.priority] - priorityOrder[a.priority];
  });
}

// Helper functions
function detectFramework(packageJson) {
  if (packageJson.dependencies?.next) return 'Next.js';
  if (packageJson.dependencies?.['@remix-run/react']) return 'Remix';
  if (packageJson.dependencies?.react) return 'React';
  return 'Unknown';
}

function detectLocation(filePath) {
  if (filePath.includes('/apps/')) {
    const match = filePath.match(/\/apps\/([^\/]+)/);
    return match ? `app:${match[1]}` : 'app:unknown';
  }
  if (filePath.includes('/packages/')) {
    const match = filePath.match(/\/packages\/([^\/]+)/);
    return match ? `package:${match[1]}` : 'package:unknown';
  }
  return 'root';
}

function extractProviderUsage(content) {
  const providers = [];
  const providerPatterns = [
    'QueryClientProvider',
    'ThemeProvider',
    'AuthProvider',
    'TenantProvider',
    'NotificationProvider',
    'ErrorBoundary',
    'UniversalProviders'
  ];

  for (const provider of providerPatterns) {
    if (content.includes(`<${provider}`)) {
      providers.push(provider);
    }
  }

  return providers;
}

function getScoreColor(score) {
  if (score >= 80) return chalk.green;
  if (score >= 60) return chalk.yellow;
  return chalk.red;
}

// Handle CLI execution
if (require.main === module) {
  main().catch(error => {
    console.error(chalk.red('\n❌ Analysis failed:'), error.message);
    process.exit(1);
  });
}

module.exports = {
  analyzeArchitecture,
  analyzeDependencies,
  analyzeBundleImpact: analyzeComponents, // Reuse component analysis
  analyzeMetrics,
  generateRecommendations
};
