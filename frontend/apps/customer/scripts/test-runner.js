#!/usr/bin/env node

/**
 * Comprehensive Test Runner for Customer App
 * Runs all test types and generates coverage reports
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  reset: '\x1b[0m',
  bold: '\x1b[1m'
};

function log(message, color = 'white') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logHeader(message) {
  console.log(`\n${colors.bold}${colors.blue}${'='.repeat(60)}`);
  console.log(`${colors.bold}${colors.blue} ${message}`);
  console.log(`${colors.bold}${colors.blue}${'='.repeat(60)}${colors.reset}\n`);
}

function runCommand(command, description, options = {}) {
  logHeader(description);
  
  try {
    const startTime = Date.now();
    log(`Running: ${command}`, 'cyan');
    
    const result = execSync(command, {
      stdio: 'inherit',
      cwd: process.cwd(),
      ...options
    });
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    log(`✅ ${description} completed successfully in ${duration}s`, 'green');
    
    return { success: true, duration };
  } catch (error) {
    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    log(`❌ ${description} failed after ${duration}s`, 'red');
    log(`Error: ${error.message}`, 'red');
    
    return { success: false, error: error.message, duration };
  }
}

function generateCoverageReport() {
  logHeader('Generating Combined Coverage Report');
  
  const coveragePath = path.join(process.cwd(), 'coverage');
  
  if (fs.existsSync(path.join(coveragePath, 'coverage-summary.json'))) {
    const summary = JSON.parse(
      fs.readFileSync(path.join(coveragePath, 'coverage-summary.json'), 'utf8')
    );
    
    const { statements, branches, functions, lines } = summary.total;
    
    console.log('\n📊 Coverage Summary:');
    console.log(`${colors.bold}Statements: ${colors.green}${statements.pct}%${colors.reset}`);
    console.log(`${colors.bold}Branches:   ${colors.green}${branches.pct}%${colors.reset}`);
    console.log(`${colors.bold}Functions:  ${colors.green}${functions.pct}%${colors.reset}`);
    console.log(`${colors.bold}Lines:      ${colors.green}${lines.pct}%${colors.reset}`);
    
    // Check thresholds
    const thresholds = {
      statements: 90,
      branches: 85,
      functions: 90,
      lines: 90
    };
    
    let allPassed = true;
    console.log('\n🎯 Coverage Thresholds:');
    
    for (const [metric, threshold] of Object.entries(thresholds)) {
      const actual = summary.total[metric].pct;
      const passed = actual >= threshold;
      allPassed = allPassed && passed;
      
      const status = passed ? '✅' : '❌';
      const color = passed ? 'green' : 'red';
      
      console.log(`${status} ${metric.padEnd(12)}: ${colors[color]}${actual}%${colors.reset} (target: ${threshold}%)`);
    }
    
    if (allPassed) {
      log('\n🎉 All coverage thresholds met! Phase 2 targets achieved.', 'green');
    } else {
      log('\n⚠️  Some coverage thresholds not met. Consider adding more tests.', 'yellow');
    }
    
    // Generate HTML report path
    const htmlReportPath = path.join(coveragePath, 'lcov-report', 'index.html');
    if (fs.existsSync(htmlReportPath)) {
      log(`\n📄 HTML Coverage Report: file://${htmlReportPath}`, 'cyan');
    }
    
    return allPassed;
  } else {
    log('No coverage summary found', 'yellow');
    return false;
  }
}

function checkTestFiles() {
  logHeader('Checking Test File Coverage');
  
  const testPatterns = [
    'src/**/*.test.ts',
    'src/**/*.test.tsx',
    'src/**/__tests__/**/*.ts',
    'src/**/__tests__/**/*.tsx'
  ];
  
  const glob = require('glob');
  const testFiles = [];
  
  testPatterns.forEach(pattern => {
    const files = glob.sync(pattern, { cwd: process.cwd() });
    testFiles.push(...files);
  });
  
  log(`Found ${testFiles.length} test files:`, 'blue');
  testFiles.forEach(file => {
    console.log(`  - ${file}`);
  });
  
  // Check for common components that should have tests
  const srcFiles = glob.sync('src/**/*.{ts,tsx}', { 
    cwd: process.cwd(),
    ignore: ['**/*.test.*', '**/__tests__/**', '**/*.d.ts']
  });
  
  const componentsWithoutTests = srcFiles.filter(srcFile => {
    const baseName = path.basename(srcFile, path.extname(srcFile));
    const dir = path.dirname(srcFile);
    
    // Check for corresponding test file
    const possibleTestFiles = [
      path.join(dir, `${baseName}.test.ts`),
      path.join(dir, `${baseName}.test.tsx`),
      path.join(dir, '__tests__', `${baseName}.test.ts`),
      path.join(dir, '__tests__', `${baseName}.test.tsx`)
    ];
    
    return !possibleTestFiles.some(testFile => 
      fs.existsSync(path.join(process.cwd(), testFile))
    );
  });
  
  if (componentsWithoutTests.length > 0) {
    log(`\n⚠️  Components without tests (${componentsWithoutTests.length}):`, 'yellow');
    componentsWithoutTests.slice(0, 10).forEach(file => {
      console.log(`  - ${file}`);
    });
    if (componentsWithoutTests.length > 10) {
      console.log(`  ... and ${componentsWithoutTests.length - 10} more`);
    }
  } else {
    log('\n✅ All components have corresponding test files!', 'green');
  }
  
  return { testFiles: testFiles.length, untested: componentsWithoutTests.length };
}

async function main() {
  const startTime = Date.now();
  const results = {};
  
  logHeader('🚀 DotMac Customer App - Comprehensive Test Suite');
  log('Phase 2: Testing Implementation - Targeting 90%+ Coverage', 'cyan');
  
  // Check test file coverage first
  const testStats = checkTestFiles();
  
  // 1. Type checking
  results.typecheck = runCommand(
    'pnpm type-check',
    '🔍 TypeScript Type Checking'
  );
  
  // 2. Linting
  results.lint = runCommand(
    'pnpm lint',
    '🧹 ESLint Code Quality Check',
    { env: { ...process.env, NODE_ENV: 'test' } }
  );
  
  // 3. Unit tests
  results.unit = runCommand(
    'pnpm test:unit --coverage --verbose',
    '🧪 Unit Tests (Components, Utilities, Hooks)'
  );
  
  // 4. Integration tests
  results.integration = runCommand(
    'pnpm test:integration --coverage --verbose',
    '🔗 Integration Tests (API Layer, Services)'
  );
  
  // 5. Generate coverage report
  const coverageResult = generateCoverageReport();
  
  // 6. E2E tests (optional - can be skipped in CI)
  if (process.env.SKIP_E2E !== 'true') {
    log('\n⚠️  E2E tests require a running application. Starting dev server...', 'yellow');
    results.e2e = runCommand(
      'pnpm test:e2e --headed=false',
      '🌐 End-to-End Tests (Critical User Flows)',
      { timeout: 120000 } // 2 minutes timeout
    );
  } else {
    log('\n⏭️  Skipping E2E tests (SKIP_E2E=true)', 'yellow');
  }
  
  // Final summary
  const totalTime = ((Date.now() - startTime) / 1000).toFixed(2);
  
  logHeader('📊 Test Suite Summary');
  
  const testTypes = ['typecheck', 'lint', 'unit', 'integration', 'e2e'];
  let totalTests = 0;
  let passedTests = 0;
  
  testTypes.forEach(type => {
    if (results[type]) {
      totalTests++;
      if (results[type].success) {
        passedTests++;
        log(`✅ ${type.padEnd(12)}: PASSED (${results[type].duration}s)`, 'green');
      } else {
        log(`❌ ${type.padEnd(12)}: FAILED (${results[type].duration}s)`, 'red');
      }
    }
  });
  
  console.log('');
  log(`📈 Test Statistics:`, 'bold');
  log(`  - Test Files: ${testStats.testFiles}`, 'blue');
  log(`  - Components without tests: ${testStats.untested}`, testStats.untested > 0 ? 'yellow' : 'green');
  log(`  - Test Suites Passed: ${passedTests}/${totalTests}`, passedTests === totalTests ? 'green' : 'red');
  log(`  - Coverage Target Met: ${coverageResult ? 'Yes' : 'No'}`, coverageResult ? 'green' : 'red');
  log(`  - Total Duration: ${totalTime}s`, 'blue');
  
  // Phase 2 completion check
  const phase2Complete = passedTests === totalTests && coverageResult && testStats.untested === 0;
  
  if (phase2Complete) {
    logHeader('🎉 Phase 2 Complete: Testing Implementation SUCCESS!');
    log('✅ All tests passing', 'green');
    log('✅ 90%+ test coverage achieved', 'green');
    log('✅ All components have tests', 'green');
    log('✅ Ready for production deployment', 'green');
  } else {
    logHeader('⚠️  Phase 2 Partial: Some targets not met');
    if (passedTests !== totalTests) log('❌ Some tests are failing', 'red');
    if (!coverageResult) log('❌ Coverage thresholds not met', 'red');
    if (testStats.untested > 0) log(`❌ ${testStats.untested} components without tests`, 'red');
  }
  
  // Exit with appropriate code
  process.exit(phase2Complete ? 0 : 1);
}

// Handle interrupts gracefully
process.on('SIGINT', () => {
  log('\n\n⏹️  Test run interrupted by user', 'yellow');
  process.exit(1);
});

process.on('SIGTERM', () => {
  log('\n\n⏹️  Test run terminated', 'yellow');
  process.exit(1);
});

// Run the test suite
main().catch(error => {
  log(`💥 Test runner crashed: ${error.message}`, 'red');
  console.error(error);
  process.exit(1);
});