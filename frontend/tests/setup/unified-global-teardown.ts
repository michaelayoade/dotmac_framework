/**
 * Unified Global Teardown for E2E Tests
 * Comprehensive cleanup of test artifacts and state
 */

import { type FullConfig } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting unified E2E test environment cleanup...');
  
  try {
    // Clean authentication artifacts
    await cleanupAuthArtifacts();
    
    // Clean temporary test data
    await cleanupTestData();
    
    // Clean browser storage artifacts
    await cleanupBrowserStorage();
    
    // Clean API mock state
    await cleanupApiMocks();
    
    // Clean test result artifacts (keep reports)
    await cleanupTestArtifacts();
    
    console.log('✅ Unified E2E test environment cleanup complete');
    
  } catch (error) {
    console.error('❌ Error during teardown:', error);
    // Don't fail the test suite on teardown errors
  }
}

async function cleanupAuthArtifacts() {
  console.log('🔐 Cleaning authentication artifacts...');
  
  const authDir = path.resolve(__dirname, '../auth');
  
  try {
    const authFiles = await fs.readdir(authDir);
    
    for (const file of authFiles) {
      if (file.endsWith('-auth.json')) {
        await fs.unlink(path.join(authDir, file));
        console.log(`   Removed ${file}`);
      }
    }
  } catch (error) {
    // Auth directory might not exist, that's okay
    console.log('   No auth artifacts to clean');
  }
}

async function cleanupTestData() {
  console.log('📋 Cleaning test data artifacts...');
  
  const testDataPaths = [
    path.resolve(__dirname, '../fixtures/temp'),
    path.resolve(__dirname, '../downloads'),
    path.resolve(__dirname, '../uploads'),
    path.resolve(__dirname, '../cache')
  ];
  
  for (const testPath of testDataPaths) {
    try {
      await fs.rm(testPath, { recursive: true, force: true });
      console.log(`   Removed ${path.basename(testPath)}`);
    } catch (error) {
      // Directory might not exist, that's okay
    }
  }
}

async function cleanupBrowserStorage() {
  console.log('🌐 Cleaning browser storage artifacts...');
  
  // Clean up any browser profile directories created during testing
  const tempDirs = [
    path.resolve(__dirname, '../.browsers'),
    path.resolve(__dirname, '../.profiles')
  ];
  
  for (const dir of tempDirs) {
    try {
      await fs.rm(dir, { recursive: true, force: true });
      console.log(`   Removed browser artifacts: ${path.basename(dir)}`);
    } catch (error) {
      // Directory might not exist, that's okay
    }
  }
}

async function cleanupApiMocks() {
  console.log('🔄 Cleaning API mock state...');
  
  const mockPaths = [
    path.resolve(__dirname, '../fixtures/api-mocks.json'),
    path.resolve(__dirname, '../fixtures/mock-state.json'),
    path.resolve(__dirname, '../mocks/runtime-state.json')
  ];
  
  for (const mockPath of mockPaths) {
    try {
      await fs.unlink(mockPath);
      console.log(`   Removed mock file: ${path.basename(mockPath)}`);
    } catch (error) {
      // File might not exist, that's okay
    }
  }
  
  // Reset any persistent mock server state
  try {
    // Send shutdown signal to mock servers if running
    const mockServers = [3100, 3101, 3102, 3103]; // Mock API ports
    
    for (const port of mockServers) {
      try {
        await fetch(`http://localhost:${port}/test/shutdown`, {
          method: 'POST',
          timeout: 1000
        });
      } catch {
        // Mock server not running, that's okay
      }
    }
  } catch (error) {
    // Mock servers might not be running, that's okay
  }
}

async function cleanupTestArtifacts() {
  console.log('🗃️  Cleaning temporary test artifacts...');
  
  // Clean temp files but preserve test reports
  const artifactPaths = [
    path.resolve(__dirname, '../../test-results/temp'),
    path.resolve(__dirname, '../../test-results/screenshots/temp'),
    path.resolve(__dirname, '../../test-results/videos/temp'),
    path.resolve(__dirname, '../../test-results/traces/temp')
  ];
  
  for (const artifactPath of artifactPaths) {
    try {
      await fs.rm(artifactPath, { recursive: true, force: true });
      console.log(`   Removed temp artifacts: ${path.basename(artifactPath)}`);
    } catch (error) {
      // Directory might not exist, that's okay
    }
  }
  
  // Clean old test result files (keep last 5 runs)
  try {
    const resultsDir = path.resolve(__dirname, '../../test-results');
    const files = await fs.readdir(resultsDir);
    
    const resultFiles = files
      .filter(file => file.endsWith('-results.json'))
      .map(file => ({
        name: file,
        path: path.join(resultsDir, file),
        stat: fs.stat(path.join(resultsDir, file))
      }));
    
    const sortedFiles = (await Promise.all(
      resultFiles.map(async file => ({
        ...file,
        stat: await file.stat
      }))
    )).sort((a, b) => b.stat.mtime.getTime() - a.stat.mtime.getTime());
    
    // Keep only the 5 most recent result files
    for (const file of sortedFiles.slice(5)) {
      await fs.unlink(file.path);
      console.log(`   Removed old result: ${file.name}`);
    }
    
  } catch (error) {
    // Results directory might not exist or be accessible
    console.log('   No old results to clean');
  }
}

export default globalTeardown;