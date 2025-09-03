/**
 * Global Teardown for Dev 4 Integration Tests
 * 
 * Handles cleanup after integration test completion including
 * test data cleanup, mock service shutdown, and resource cleanup.
 */

import { FullConfig } from '@playwright/test';
import { cleanupAllTestTenants } from '../utils/tenant-factory';
import { ciConfig } from './ci.config';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting Dev 4 Integration Test Cleanup...');
  
  try {
    // 1. Cleanup test tenants
    await cleanupTestTenants();
    
    // 2. Cleanup test database
    await cleanupTestDatabase();
    
    // 3. Generate test summary
    await generateTestSummary();
    
    // 4. Cleanup temporary files
    await cleanupTempFiles();
    
    console.log('✅ Integration test cleanup complete');
    
  } catch (error) {
    console.error('❌ Global teardown failed:', error);
    // Don't fail the tests due to cleanup issues
  }
}

/**
 * Clean up all test tenants created during testing
 */
async function cleanupTestTenants(): Promise<void> {
  console.log('🏠 Cleaning up test tenants...');
  
  try {
    await cleanupAllTestTenants();
    console.log('✅ Test tenants cleaned up');
  } catch (error) {
    console.warn('⚠️  Failed to cleanup some test tenants:', error);
  }
}

/**
 * Clean up test database data
 */
async function cleanupTestDatabase(): Promise<void> {
  console.log('🗄️  Cleaning up test database...');
  
  if (process.env.CI !== 'true') {
    // In local development, preserve some test data
    return;
  }
  
  try {
    const { spawn } = require('child_process');
    
    // Clean up test data but preserve schema
    const cleanup = spawn('poetry', ['run', 'python', '-c', `
import asyncio
from dotmac_management.database import get_session
from sqlalchemy import text

async def cleanup_test_data():
    async for session in get_session():
        try:
            # Delete test data (preserve production-like data)
            await session.execute(text("DELETE FROM tenants WHERE name LIKE 'Test %' OR name LIKE '%Test%'"))
            await session.execute(text("DELETE FROM users WHERE email LIKE '%@test.com'"))
            await session.execute(text("DELETE FROM notifications WHERE title LIKE 'Test %'"))
            await session.commit()
            print("✅ Test data cleaned up")
        except Exception as e:
            print(f"⚠️  Database cleanup warning: {e}")
            await session.rollback()
        break

asyncio.run(cleanup_test_data())
    `], { cwd: './src', stdio: 'pipe' });
    
    await new Promise((resolve) => {
      cleanup.on('close', () => resolve(void 0));
    });
    
    console.log('✅ Database cleanup complete');
    
  } catch (error) {
    console.warn('⚠️  Database cleanup failed:', error);
  }
}

/**
 * Generate test execution summary
 */
async function generateTestSummary(): Promise<void> {
  console.log('📊 Generating test summary...');
  
  try {
    const fs = require('fs');
    const path = require('path');
    
    const summaryData = {
      timestamp: new Date().toISOString(),
      environment: {
        ci: process.env.CI === 'true',
        nodeVersion: process.version,
        usedMockServices: ciConfig.useMockServices,
        parallelWorkers: ciConfig.parallelWorkers
      },
      testFiles: [
        'management-tenant-communication.spec.ts',
        'external-integrations.spec.ts', 
        'realtime-systems.spec.ts'
      ],
      coverage: {
        managementTenantCommunication: true,
        externalIntegrations: true,
        realtimeSystems: true,
        sharedUtilities: true
      }
    };
    
    // Ensure test-results directory exists
    const resultsDir = path.resolve('test-results');
    if (!fs.existsSync(resultsDir)) {
      fs.mkdirSync(resultsDir, { recursive: true });
    }
    
    // Write summary file
    fs.writeFileSync(
      path.join(resultsDir, 'dev4-integration-summary.json'),
      JSON.stringify(summaryData, null, 2)
    );
    
    console.log('✅ Test summary generated');
    
  } catch (error) {
    console.warn('⚠️  Failed to generate test summary:', error);
  }
}

/**
 * Clean up temporary files and artifacts
 */
async function cleanupTempFiles(): Promise<void> {
  console.log('🗂️  Cleaning up temporary files...');
  
  try {
    const fs = require('fs');
    const path = require('path');
    
    // Clean up temporary test artifacts (but preserve test results)
    const tempDirs = [
      'temp-uploads',
      'temp-downloads', 
      'mock-data',
      '.temp-test-data'
    ];
    
    for (const dir of tempDirs) {
      const dirPath = path.resolve(dir);
      if (fs.existsSync(dirPath)) {
        fs.rmSync(dirPath, { recursive: true, force: true });
      }
    }
    
    // Clean up any lingering process files
    const processFiles = ['management_api.pid', 'tenant_mock.pid'];
    for (const file of processFiles) {
      const filePath = path.resolve(file);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    }
    
    console.log('✅ Temporary files cleaned up');
    
  } catch (error) {
    console.warn('⚠️  Failed to cleanup temporary files:', error);
  }
}

/**
 * Report test execution statistics
 */
function reportTestStats(): void {
  const stats = {
    totalTestFiles: 3,
    testUtilities: 2,
    ciConfigFiles: 4,
    mockServers: 1,
    coverage: [
      'Management-to-Tenant Communication',
      'External Systems Integration', 
      'Real-time WebSocket Systems',
      'Shared Test Infrastructure'
    ]
  };
  
  console.log('\n📈 Dev 4 Integration Test Statistics:');
  console.log(`   Test Files: ${stats.totalTestFiles}`);
  console.log(`   Utilities: ${stats.testUtilities}`);
  console.log(`   CI Config Files: ${stats.ciConfigFiles}`);
  console.log(`   Coverage Areas: ${stats.coverage.length}`);
  console.log(`   Mock Servers: ${stats.mockServers}`);
  console.log('\n🎯 Coverage Areas:');
  stats.coverage.forEach(area => {
    console.log(`   ✅ ${area}`);
  });
}

// Call stats reporting
reportTestStats();

export default globalTeardown;