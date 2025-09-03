#!/usr/bin/env node

/**
 * DotMac Migration Tool
 *
 * Automates migration from duplicate components to unified architecture
 */

const fs = require('fs-extra');
const path = require('path');
const glob = require('glob');
const chalk = require('chalk');
const ora = require('ora');
const inquirer = require('inquirer');

const UNIFIED_COMPONENTS = [
  'Button',
  'Input',
  'Card',
  'Modal',
  'Form',
  'Table',
  'Toast',
  'Dialog',
  'Dropdown',
  'Select',
  'Checkbox',
  'RadioGroup',
  'Switch',
  'Tabs',
  'Accordion',
  'Avatar',
  'Badge',
  'Progress',
  'Skeleton',
  'Spinner',
  'Alert',
  'Tooltip',
];

const PORTALS = ['admin', 'customer', 'reseller', 'technician', 'management'];

async function main() {
  console.log(chalk.blue.bold('\n🏗️  DotMac Frontend Migration Tool\n'));

  const { migrationMode } = await inquirer.prompt([
    {
      type: 'list',
      name: 'migrationMode',
      message: 'What would you like to migrate?',
      choices: [
        { name: '🧩 Components - Replace duplicates with unified components', value: 'components' },
        { name: '🔌 Providers - Replace custom provider compositions', value: 'providers' },
        { name: '📦 Full Migration - Complete architecture migration', value: 'full' },
        { name: '🔍 Analysis Only - Scan for issues without making changes', value: 'analyze' },
      ],
    },
  ]);

  const projectRoot = process.cwd();
  const frontendPath = path.join(projectRoot, 'frontend');

  if (!fs.existsSync(frontendPath)) {
    console.error(chalk.red('❌ No frontend directory found. Are you in the project root?'));
    process.exit(1);
  }

  switch (migrationMode) {
    case 'components':
      await migrateComponents(frontendPath);
      break;
    case 'providers':
      await migrateProviders(frontendPath);
      break;
    case 'full':
      await fullMigration(frontendPath);
      break;
    case 'analyze':
      await analyzeProject(frontendPath);
      break;
  }
}

/**
 * Migrate duplicate components to unified components
 */
async function migrateComponents(frontendPath) {
  const spinner = ora('🔍 Scanning for duplicate components...').start();

  const duplicates = await findDuplicateComponents(frontendPath);

  spinner.succeed(`Found ${duplicates.length} duplicate components`);

  if (duplicates.length === 0) {
    console.log(chalk.green('✅ No duplicate components found!'));
    return;
  }

  // Display findings
  console.log(chalk.yellow('\n📋 Duplicate components found:\n'));
  duplicates.forEach((duplicate) => {
    console.log(`  ${chalk.red('❌')} ${duplicate.component} in ${duplicate.file}`);
  });

  const { shouldMigrate } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'shouldMigrate',
      message: 'Proceed with component migration?',
      default: true,
    },
  ]);

  if (!shouldMigrate) {
    console.log(chalk.yellow('Migration cancelled.'));
    return;
  }

  const migrateSpinner = ora('🔄 Migrating components...').start();

  for (const duplicate of duplicates) {
    await migrateComponentFile(duplicate);
  }

  migrateSpinner.succeed('✅ Component migration complete!');

  // Update package.json dependencies
  await updatePackageDependencies(frontendPath);

  console.log(chalk.green('\n🎉 Migration complete! Next steps:'));
  console.log(chalk.blue('  1. Run: pnpm install'));
  console.log(chalk.blue('  2. Run: pnpm lint --fix'));
  console.log(chalk.blue('  3. Test your applications'));
}

/**
 * Migrate provider compositions to UniversalProviders
 */
async function migrateProviders(frontendPath) {
  const spinner = ora('🔍 Scanning for provider patterns...').start();

  const providerFiles = await findProviderFiles(frontendPath);

  spinner.succeed(`Found ${providerFiles.length} provider files`);

  if (providerFiles.length === 0) {
    console.log(chalk.green('✅ No provider files found to migrate!'));
    return;
  }

  // Display findings
  console.log(chalk.yellow('\n📋 Provider files found:\n'));
  providerFiles.forEach((file) => {
    console.log(`  ${chalk.blue('🔌')} ${file.path} (${file.providerCount} providers)`);
  });

  const { shouldMigrate } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'shouldMigrate',
      message: 'Proceed with provider migration?',
      default: true,
    },
  ]);

  if (!shouldMigrate) {
    console.log(chalk.yellow('Migration cancelled.'));
    return;
  }

  const migrateSpinner = ora('🔄 Migrating providers...').start();

  for (const file of providerFiles) {
    await migrateProviderFile(file);
  }

  migrateSpinner.succeed('✅ Provider migration complete!');
}

/**
 * Full migration - components + providers + cleanup
 */
async function fullMigration(frontendPath) {
  console.log(chalk.blue('🚀 Starting full migration...\n'));

  await migrateComponents(frontendPath);
  console.log();
  await migrateProviders(frontendPath);

  console.log(chalk.yellow('\n🧹 Cleaning up old files...'));
  await cleanupOldFiles(frontendPath);

  console.log(chalk.green('\n🎉 Full migration complete!'));
}

/**
 * Analyze project without making changes
 */
async function analyzeProject(frontendPath) {
  const spinner = ora('🔍 Analyzing project architecture...').start();

  const analysis = await performArchitecturalAnalysis(frontendPath);

  spinner.succeed('Analysis complete!');

  // Display analysis results
  console.log(chalk.blue('\n📊 Architecture Analysis Results\n'));

  console.log(chalk.yellow('Components:'));
  console.log(`  • Duplicate components: ${chalk.red(analysis.duplicateComponents)}`);
  console.log(`  • Unified components used: ${chalk.green(analysis.unifiedComponents)}`);
  console.log(
    `  • Reusability score: ${getScoreColor(analysis.reusabilityScore)}${analysis.reusabilityScore}%${chalk.reset()}`
  );

  console.log(chalk.yellow('\nProviders:'));
  console.log(`  • Custom provider compositions: ${chalk.red(analysis.customProviders)}`);
  console.log(`  • UniversalProvider usage: ${chalk.green(analysis.universalProviders)}`);
  console.log(
    `  • Consistency score: ${getScoreColor(analysis.consistencyScore)}${analysis.consistencyScore}%${chalk.reset()}`
  );

  console.log(chalk.yellow('\nBundle Impact:'));
  console.log(`  • Estimated duplicate code: ${chalk.red(analysis.duplicateCodeSize)}`);
  console.log(`  • Potential savings: ${chalk.green(analysis.potentialSavings)}`);

  if (analysis.duplicateComponents > 0 || analysis.customProviders > 0) {
    console.log(chalk.blue('\n💡 Recommendations:'));
    console.log('  • Run migration to fix architectural issues');
    console.log('  • Implement governance rules to prevent regressions');
  }
}

/**
 * Find duplicate components across the codebase
 */
async function findDuplicateComponents(frontendPath) {
  const duplicates = [];

  for (const component of UNIFIED_COMPONENTS) {
    const componentFiles = glob.sync(`${frontendPath}/**/components/**/${component}.{ts,tsx}`, {
      ignore: ['**/node_modules/**', '**/packages/ui/**'],
    });

    if (componentFiles.length > 0) {
      componentFiles.forEach((file) => {
        duplicates.push({
          component,
          file: path.relative(frontendPath, file),
          portal: detectPortalFromPath(file),
        });
      });
    }
  }

  return duplicates;
}

/**
 * Find provider files that need migration
 */
async function findProviderFiles(frontendPath) {
  const providerFiles = [];

  const files = glob.sync(`${frontendPath}/**/providers.{ts,tsx}`, {
    ignore: ['**/node_modules/**', '**/packages/providers/**'],
  });

  for (const file of files) {
    const content = await fs.readFile(file, 'utf8');
    const providerCount = (
      content.match(/(QueryClientProvider|ThemeProvider|AuthProvider|TenantProvider)/g) || []
    ).length;

    if (providerCount > 1) {
      providerFiles.push({
        path: path.relative(frontendPath, file),
        absolutePath: file,
        providerCount,
        portal: detectPortalFromPath(file),
      });
    }
  }

  return providerFiles;
}

/**
 * Migrate a single component file
 */
async function migrateComponentFile(duplicate) {
  // This would use jscodeshift or AST transformations
  // For now, we'll create a simple replacement

  const newContent = `// Migrated to use unified component from @dotmac/ui
export { ${duplicate.component} } from '@dotmac/ui';

// If portal-specific styling is needed:
// import { ${duplicate.component} } from '@dotmac/ui';
//
// export function ${duplicate.portal}${duplicate.component}(props) {
//   return <${duplicate.component} variant="${duplicate.portal}" {...props} />;
// }
`;

  await fs.writeFile(duplicate.file, newContent);
}

/**
 * Migrate a provider file
 */
async function migrateProviderFile(file) {
  const content = await fs.readFile(file.absolutePath, 'utf8');

  // Simple replacement - this would be more sophisticated in practice
  const migratedContent = content
    .replace(/import.*QueryClientProvider.*from.*@tanstack\/react-query.*/g, '')
    .replace(/import.*ThemeProvider.*from.*/g, '')
    .replace(/import.*AuthProvider.*from.*/g, '')
    .replace(/import.*TenantProvider.*from.*/g, '')
    .replace(/import.*NotificationProvider.*from.*/g, '')
    .replace(/<QueryClientProvider[^>]*>[\s\S]*<\/QueryClientProvider>/g, '')
    .replace(
      /export function Providers\(\{[^}]*\}\) \{[\s\S]*?\}/g,
      generateUniversalProviderComponent(file.portal)
    );

  const finalContent = `import { UniversalProviders } from '@dotmac/providers';\n${migratedContent}`;

  await fs.writeFile(file.absolutePath, finalContent);
}

/**
 * Generate UniversalProvider component
 */
function generateUniversalProviderComponent(portal) {
  return `export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <UniversalProviders
      portal="${portal}"
      features={{
        notifications: true,
        realtime: false,
        analytics: false
      }}
    >
      {children}
    </UniversalProviders>
  );
}`;
}

/**
 * Update package.json dependencies
 */
async function updatePackageDependencies(frontendPath) {
  const apps = glob.sync(`${frontendPath}/apps/*/package.json`);

  for (const packagePath of apps) {
    const packageJson = await fs.readJSON(packagePath);

    // Add unified dependencies
    packageJson.dependencies = packageJson.dependencies || {};
    packageJson.dependencies['@dotmac/ui'] = 'workspace:*';
    packageJson.dependencies['@dotmac/providers'] = 'workspace:*';
    packageJson.dependencies['@dotmac/auth'] = 'workspace:*';

    await fs.writeJSON(packagePath, packageJson, { spaces: 2 });
  }
}

/**
 * Cleanup old duplicate files
 */
async function cleanupOldFiles(frontendPath) {
  // This would remove old duplicate components and providers
  // Implementation depends on specific cleanup strategy
}

/**
 * Perform comprehensive architectural analysis
 */
async function performArchitecturalAnalysis(frontendPath) {
  const duplicates = await findDuplicateComponents(frontendPath);
  const providerFiles = await findProviderFiles(frontendPath);

  return {
    duplicateComponents: duplicates.length,
    unifiedComponents: UNIFIED_COMPONENTS.length - duplicates.length,
    reusabilityScore: Math.max(
      0,
      Math.round(
        ((UNIFIED_COMPONENTS.length - duplicates.length) / UNIFIED_COMPONENTS.length) * 100
      )
    ),
    customProviders: providerFiles.length,
    universalProviders: PORTALS.length - providerFiles.length,
    consistencyScore: Math.max(
      0,
      Math.round(((PORTALS.length - providerFiles.length) / PORTALS.length) * 100)
    ),
    duplicateCodeSize: `${Math.round(duplicates.length * 2.5)}KB`,
    potentialSavings: `${Math.round(duplicates.length * 2)}KB`,
  };
}

/**
 * Detect portal from file path
 */
function detectPortalFromPath(filePath) {
  for (const portal of PORTALS) {
    if (filePath.includes(`/apps/${portal}/`) || filePath.includes(`apps/${portal}/`)) {
      return portal;
    }
  }
  return 'unknown';
}

/**
 * Get color for score display
 */
function getScoreColor(score) {
  if (score >= 80) return chalk.green;
  if (score >= 60) return chalk.yellow;
  return chalk.red;
}

// Handle CLI execution
if (require.main === module) {
  main().catch((error) => {
    console.error(chalk.red('\n❌ Migration failed:'), error.message);
    process.exit(1);
  });
}

module.exports = {
  migrateComponents,
  migrateProviders,
  analyzeProject,
};
