import { type FullConfig } from '@playwright/test';
import fs from 'fs';
import path from 'path';

/**
 * Global teardown for Playwright tests
 * Runs once after all tests complete
 */
async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting global teardown...');
  
  try {
    // Clean up authentication state files
    await cleanupAuthStates();
    
    // Clean up test artifacts
    await cleanupTestArtifacts();
    
    // Generate test summary
    await generateTestSummary();
    
    console.log('✅ Global teardown completed successfully');
  } catch (error) {
    console.error('❌ Global teardown failed:', error);
  }
}

async function cleanupAuthStates(): Promise<void> {
  const authStatesDir = path.join(__dirname, '../auth-states');
  
  if (fs.existsSync(authStatesDir)) {
    const files = fs.readdirSync(authStatesDir);
    
    for (const file of files) {
      if (file.endsWith('-auth.json')) {
        const filePath = path.join(authStatesDir, file);
        try {
          fs.unlinkSync(filePath);
          console.log(`🗑️ Cleaned up auth state: ${file}`);
        } catch (error) {
          console.warn(`⚠️ Failed to delete ${file}:`, error);
        }
      }
    }
  }
}

async function cleanupTestArtifacts(): Promise<void> {
  const artifactDirs = [
    path.join(process.cwd(), 'test-results'),
    path.join(process.cwd(), 'playwright-report'),
    path.join(process.cwd(), 'screenshots'),
    path.join(process.cwd(), 'videos')
  ];
  
  for (const dir of artifactDirs) {
    if (fs.existsSync(dir)) {
      try {
        // Only clean up old artifacts (older than 7 days)
        const stats = fs.statSync(dir);
        const daysSinceModified = (Date.now() - stats.mtime.getTime()) / (1000 * 60 * 60 * 24);
        
        if (daysSinceModified > 7) {
          fs.rmSync(dir, { recursive: true, force: true });
          console.log(`🗑️ Cleaned up old artifacts: ${dir}`);
        }
      } catch (error) {
        console.warn(`⚠️ Failed to clean up ${dir}:`, error);
      }
    }
  }
}

async function generateTestSummary(): Promise<void> {
  const summaryPath = path.join(process.cwd(), 'test-results', 'summary.json');
  
  try {
    if (fs.existsSync(summaryPath)) {
      const summary = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));
      
      console.log('\n📊 Test Summary:');
      console.log(`   Total tests: ${summary.total || 'N/A'}`);
      console.log(`   Passed: ${summary.passed || 'N/A'}`);
      console.log(`   Failed: ${summary.failed || 'N/A'}`);
      console.log(`   Skipped: ${summary.skipped || 'N/A'}`);
      console.log(`   Duration: ${summary.duration || 'N/A'}`);
      
      if (summary.failed && summary.failed > 0) {
        console.log('\n❌ Failed tests:');
        (summary.failures || []).forEach((failure: any) => {
          console.log(`   - ${failure.test}: ${failure.error}`);
        });
      }
    }
  } catch (error) {
    console.warn('⚠️ Could not generate test summary:', error);
  }
}

export default globalTeardown;