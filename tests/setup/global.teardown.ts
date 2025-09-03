/**
 * Global Teardown for License Enforcement E2E Tests
 * 
 * Cleans up test environment, databases, and generated data
 * after license enforcement testing is complete.
 */

import { FullConfig } from '@playwright/test';
import { execSync } from 'child_process';
import { existsSync, rmSync, readFileSync } from 'fs';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Cleaning up license enforcement test environment...');
  
  try {
    // 1. Generate final test reports
    await generateFinalReports();
    
    // 2. Clean up test databases  
    await cleanupTestDatabases();
    
    // 3. Archive test artifacts if needed
    await archiveTestArtifacts();
    
    // 4. Clean up temporary test data
    await cleanupTestData();
    
    console.log('✅ License enforcement test cleanup complete');
    
  } catch (error) {
    console.error('⚠️  Warning: Cleanup encountered issues:', error);
    // Don't throw - cleanup issues shouldn't fail the overall test run
  }
}

async function generateFinalReports() {
  console.log('📊 Generating final test reports...');
  
  try {
    // Aggregate all test results for final reporting
    const resultsPath = 'test-results/license-test-results.json';
    
    if (existsSync(resultsPath)) {
      const results = JSON.parse(readFileSync(resultsPath, 'utf-8'));
      
      // Generate consolidated report
      const summary = {
        timestamp: new Date().toISOString(),
        totalTests: results.stats?.total || 0,
        passed: results.stats?.expected || 0,
        failed: results.stats?.unexpected || 0,
        skipped: results.stats?.skipped || 0,
        duration: results.stats?.duration || 0,
        licenseCompliance: {
          basicPlanTests: 0,
          premiumPlanTests: 0,
          enterprisePlanTests: 0,
          crossAppTests: 0,
          featureFlagTests: 0
        }
      };
      
      // Save final summary
      const fs = require('fs');
      fs.writeFileSync(
        'test-results/final-license-report.json', 
        JSON.stringify(summary, null, 2)
      );
      
      console.log('  ✓ Final reports generated');
    }
    
  } catch (error) {
    console.error('  ⚠️  Report generation failed:', error);
  }
}

async function cleanupTestDatabases() {
  console.log('🗄️  Cleaning up test databases...');
  
  try {
    // Remove test database files
    const testDbFiles = [
      '../src/dotmac_management/test_license.db',
      'test_license.db'
    ];
    
    for (const dbFile of testDbFiles) {
      if (existsSync(dbFile)) {
        rmSync(dbFile, { force: true });
        console.log(`  ✓ Removed ${dbFile}`);
      }
    }
    
  } catch (error) {
    console.error('  ⚠️  Database cleanup failed:', error);
  }
}

async function archiveTestArtifacts() {
  console.log('📦 Archiving test artifacts...');
  
  const shouldArchive = process.env.ARCHIVE_TEST_ARTIFACTS === 'true' || process.env.CI;
  
  if (!shouldArchive) {
    console.log('  ℹ️  Artifact archiving skipped');
    return;
  }
  
  try {
    // In CI environments, artifacts might be collected by the CI system
    // For now, we'll just ensure they're organized properly
    
    const artifactDirs = [
      'test-results/screenshots',
      'test-results/videos', 
      'test-results/traces'
    ];
    
    let totalArtifacts = 0;
    
    for (const dir of artifactDirs) {
      if (existsSync(dir)) {
        const files = require('fs').readdirSync(dir);
        totalArtifacts += files.length;
      }
    }
    
    if (totalArtifacts > 0) {
      console.log(`  📁 ${totalArtifacts} test artifacts preserved`);
    }
    
  } catch (error) {
    console.error('  ⚠️  Artifact archiving failed:', error);
  }
}

async function cleanupTestData() {
  console.log('🗑️  Cleaning up temporary test data...');
  
  try {
    // Clean up temporary test data but preserve reports
    const tempDataPaths = [
      'test-data/temp',
      'test-data/exports'
    ];
    
    for (const dataPath of tempDataPaths) {
      if (existsSync(dataPath)) {
        rmSync(dataPath, { recursive: true, force: true });
        console.log(`  ✓ Cleaned ${dataPath}`);
      }
    }
    
    // Clean up any leftover lock files or temp files
    const tempFiles = [
      '.playwright-test-state.json',
      'test-state.json'
    ];
    
    for (const tempFile of tempFiles) {
      if (existsSync(tempFile)) {
        rmSync(tempFile, { force: true });
        console.log(`  ✓ Removed ${tempFile}`);
      }
    }
    
  } catch (error) {
    console.error('  ⚠️  Temp data cleanup failed:', error);
  }
}

export default globalTeardown;