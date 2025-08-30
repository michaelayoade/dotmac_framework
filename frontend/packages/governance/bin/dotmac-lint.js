#!/usr/bin/env node

/**
 * DotMac Architectural Linting Tool
 *
 * Provides specialized linting for DotMac architecture compliance
 */

const { ESLint } = require('eslint');
const path = require('path');
const fs = require('fs-extra');
const chalk = require('chalk');
const ora = require('ora');
const inquirer = require('inquirer');

const GOVERNANCE_RULES = [
  '@dotmac/governance/no-duplicate-components',
  '@dotmac/governance/enforce-provider-pattern'
];

async function main() {
  console.log(chalk.blue.bold('\n🔍 DotMac Architectural Linter\n'));

  const { lintMode } = await inquirer.prompt([
    {
      type: 'list',
      name: 'lintMode',
      message: 'What would you like to lint?',
      choices: [
        { name: '🧩 Components - Check for duplicate components', value: 'components' },
        { name: '🔌 Providers - Check provider patterns', value: 'providers' },
        { name: '📦 Full Architecture - Check all architectural rules', value: 'full' },
        { name: '🔧 Setup - Install governance rules in projects', value: 'setup' }
      ]
    }
  ]);

  const projectRoot = process.cwd();
  const frontendPath = path.join(projectRoot, 'frontend');

  if (!fs.existsSync(frontendPath)) {
    console.error(chalk.red('❌ No frontend directory found. Are you in the project root?'));
    process.exit(1);
  }

  switch (lintMode) {
    case 'components':
      await lintComponents(frontendPath);
      break;
    case 'providers':
      await lintProviders(frontendPath);
      break;
    case 'full':
      await fullArchitecturalLint(frontendPath);
      break;
    case 'setup':
      await setupGovernanceRules(frontendPath);
      break;
  }
}

/**
 * Lint components for architectural compliance
 */
async function lintComponents(frontendPath) {
  const spinner = ora('🔍 Linting components...').start();

  const eslint = new ESLint({
    baseConfig: {
      plugins: ['@dotmac/governance'],
      rules: {
        '@dotmac/governance/no-duplicate-components': 'error'
      }
    },
    useEslintrc: false
  });

  try {
    const results = await eslint.lintFiles([
      `${frontendPath}/apps/*/src/components/**/*.{ts,tsx}`,
      `${frontendPath}/apps/*/src/pages/**/*.{ts,tsx}`
    ]);

    spinner.succeed('Component linting complete!');

    await displayLintResults(results, 'Components');

  } catch (error) {
    spinner.fail('Component linting failed');
    console.error(chalk.red(error.message));
  }
}

/**
 * Lint providers for pattern compliance
 */
async function lintProviders(frontendPath) {
  const spinner = ora('🔍 Linting providers...').start();

  const eslint = new ESLint({
    baseConfig: {
      plugins: ['@dotmac/governance'],
      rules: {
        '@dotmac/governance/enforce-provider-pattern': 'error'
      }
    },
    useEslintrc: false
  });

  try {
    const results = await eslint.lintFiles([
      `${frontendPath}/apps/*/src/app/providers.tsx`,
      `${frontendPath}/apps/*/src/app/layout.tsx`,
      `${frontendPath}/apps/*/src/pages/_app.tsx`,
      `${frontendPath}/apps/*/src/providers/**/*.{ts,tsx}`
    ]);

    spinner.succeed('Provider linting complete!');

    await displayLintResults(results, 'Providers');

  } catch (error) {
    spinner.fail('Provider linting failed');
    console.error(chalk.red(error.message));
  }
}

/**
 * Full architectural linting
 */
async function fullArchitecturalLint(frontendPath) {
  const spinner = ora('🔍 Running full architectural lint...').start();

  const eslint = new ESLint({
    baseConfig: {
      plugins: ['@dotmac/governance'],
      rules: {
        '@dotmac/governance/no-duplicate-components': 'error',
        '@dotmac/governance/enforce-provider-pattern': 'error'
      }
    },
    useEslintrc: false
  });

  try {
    const results = await eslint.lintFiles([
      `${frontendPath}/apps/**/*.{ts,tsx}`,
      `${frontendPath}/packages/**/*.{ts,tsx}`
    ]);

    spinner.succeed('Full architectural lint complete!');

    await displayLintResults(results, 'Architecture');

    // Generate governance report
    await generateGovernanceReport(results, frontendPath);

  } catch (error) {
    spinner.fail('Architectural linting failed');
    console.error(chalk.red(error.message));
  }
}

/**
 * Setup governance rules in existing projects
 */
async function setupGovernanceRules(frontendPath) {
  const spinner = ora('🔧 Setting up governance rules...').start();

  const apps = await fs.readdir(path.join(frontendPath, 'apps'));
  const validApps = [];

  for (const app of apps) {
    const appPath = path.join(frontendPath, 'apps', app);
    const packageJsonPath = path.join(appPath, 'package.json');

    if (await fs.pathExists(packageJsonPath)) {
      validApps.push({ name: app, path: appPath });
    }
  }

  spinner.succeed(`Found ${validApps.length} apps to configure`);

  console.log(chalk.yellow('\n📋 Apps found:\n'));
  validApps.forEach(app => {
    console.log(`  ${chalk.blue('📱')} ${app.name}`);
  });

  const { shouldSetup } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'shouldSetup',
      message: 'Setup governance rules for these apps?',
      default: true
    }
  ]);

  if (!shouldSetup) {
    console.log(chalk.yellow('Setup cancelled.'));
    return;
  }

  const setupSpinner = ora('🔧 Installing governance rules...').start();

  for (const app of validApps) {
    await setupAppGovernance(app);
  }

  setupSpinner.succeed('✅ Governance rules setup complete!');

  console.log(chalk.green('\n🎉 Setup complete! Next steps:'));
  console.log(chalk.blue('  1. Run: pnpm install'));
  console.log(chalk.blue('  2. Run: pnpm lint'));
  console.log(chalk.blue('  3. Configure pre-commit hooks'));
}

/**
 * Setup governance for individual app
 */
async function setupAppGovernance(app) {
  const packageJsonPath = path.join(app.path, 'package.json');
  const packageJson = await fs.readJSON(packageJsonPath);

  // Add governance dependencies
  packageJson.devDependencies = packageJson.devDependencies || {};
  packageJson.devDependencies['@dotmac/governance'] = 'workspace:*';

  // Update ESLint config
  const eslintrcPath = path.join(app.path, '.eslintrc.json');
  let eslintConfig;

  if (await fs.pathExists(eslintrcPath)) {
    eslintConfig = await fs.readJSON(eslintrcPath);
  } else {
    eslintConfig = {
      extends: ['next/core-web-vitals']
    };
  }

  // Add governance plugin
  eslintConfig.plugins = eslintConfig.plugins || [];
  if (!eslintConfig.plugins.includes('@dotmac/governance')) {
    eslintConfig.plugins.push('@dotmac/governance');
  }

  // Add governance rules
  eslintConfig.rules = eslintConfig.rules || {};
  eslintConfig.rules['@dotmac/governance/no-duplicate-components'] = 'error';
  eslintConfig.rules['@dotmac/governance/enforce-provider-pattern'] = 'error';

  // Write updated files
  await fs.writeJSON(packageJsonPath, packageJson, { spaces: 2 });
  await fs.writeJSON(eslintrcPath, eslintConfig, { spaces: 2 });
}

/**
 * Display lint results with formatting
 */
async function displayLintResults(results, category) {
  const errorCount = results.reduce((sum, result) => sum + result.errorCount, 0);
  const warningCount = results.reduce((sum, result) => sum + result.warningCount, 0);

  console.log(chalk.blue(`\n📊 ${category} Lint Results\n`));

  if (errorCount === 0 && warningCount === 0) {
    console.log(chalk.green('✅ No architectural violations found!'));
    return;
  }

  console.log(chalk.red(`❌ ${errorCount} errors`));
  console.log(chalk.yellow(`⚠️  ${warningCount} warnings`));
  console.log();

  // Display detailed results
  for (const result of results) {
    if (result.messages.length > 0) {
      console.log(chalk.cyan(`📄 ${path.relative(process.cwd(), result.filePath)}`));

      for (const message of result.messages) {
        const severity = message.severity === 2 ? chalk.red('ERROR') : chalk.yellow('WARN');
        const location = chalk.gray(`${message.line}:${message.column}`);

        console.log(`  ${location} ${severity} ${message.message}`);
        if (message.ruleId) {
          console.log(`    ${chalk.gray(`Rule: ${message.ruleId}`)}`);
        }
        console.log();
      }
    }
  }

  // Show fixable suggestions
  const fixableCount = results.reduce((sum, result) => {
    return sum + result.messages.filter(msg => msg.fix || msg.suggestions?.length > 0).length;
  }, 0);

  if (fixableCount > 0) {
    console.log(chalk.blue(`💡 ${fixableCount} issues can be auto-fixed`));

    const { shouldFix } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'shouldFix',
        message: 'Apply automatic fixes?',
        default: false
      }
    ]);

    if (shouldFix) {
      await applyAutoFixes(results);
    }
  }
}

/**
 * Apply automatic fixes from ESLint
 */
async function applyAutoFixes(results) {
  const fixSpinner = ora('🔧 Applying fixes...').start();

  try {
    const eslint = new ESLint({
      fix: true,
      baseConfig: {
        plugins: ['@dotmac/governance'],
        rules: {
          '@dotmac/governance/no-duplicate-components': 'error',
          '@dotmac/governance/enforce-provider-pattern': 'error'
        }
      },
      useEslintrc: false
    });

    const fixedResults = await eslint.lintFiles(results.map(r => r.filePath));
    await ESLint.outputFixes(fixedResults);

    fixSpinner.succeed('✅ Fixes applied successfully!');

  } catch (error) {
    fixSpinner.fail('Failed to apply fixes');
    console.error(chalk.red(error.message));
  }
}

/**
 * Generate comprehensive governance report
 */
async function generateGovernanceReport(results, frontendPath) {
  const reportPath = path.join(frontendPath, 'governance-report.json');

  const report = {
    timestamp: new Date().toISOString(),
    summary: {
      totalFiles: results.length,
      errorCount: results.reduce((sum, result) => sum + result.errorCount, 0),
      warningCount: results.reduce((sum, result) => sum + result.warningCount, 0),
      fixableCount: results.reduce((sum, result) => {
        return sum + result.messages.filter(msg => msg.fix || msg.suggestions?.length > 0).length;
      }, 0)
    },
    ruleViolations: {},
    files: results.filter(result => result.messages.length > 0).map(result => ({
      filePath: path.relative(frontendPath, result.filePath),
      errorCount: result.errorCount,
      warningCount: result.warningCount,
      messages: result.messages.map(msg => ({
        ruleId: msg.ruleId,
        severity: msg.severity === 2 ? 'error' : 'warning',
        message: msg.message,
        line: msg.line,
        column: msg.column
      }))
    }))
  };

  // Count rule violations
  for (const result of results) {
    for (const message of result.messages) {
      if (message.ruleId) {
        report.ruleViolations[message.ruleId] = (report.ruleViolations[message.ruleId] || 0) + 1;
      }
    }
  }

  await fs.writeJSON(reportPath, report, { spaces: 2 });

  console.log(chalk.green(`📄 Governance report saved to: ${chalk.cyan(reportPath)}`));
}

// Handle CLI execution
if (require.main === module) {
  main().catch(error => {
    console.error(chalk.red('\n❌ Linting failed:'), error.message);
    process.exit(1);
  });
}

module.exports = {
  lintComponents,
  lintProviders,
  fullArchitecturalLint,
  setupGovernanceRules
};
