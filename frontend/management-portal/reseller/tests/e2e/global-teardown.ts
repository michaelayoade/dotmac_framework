import { FullConfig } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

async function globalTeardown(config: FullConfig) {
  console.log('Cleaning up E2E test environment...');

  try {
    // Clean up test artifacts if needed
    await cleanupTestData();

    // Clean up authentication state
    const authStatePath = 'tests/e2e/fixtures/auth-state.json';
    try {
      await fs.unlink(authStatePath);
      console.log('Authentication state cleaned up');
    } catch (error) {
      // File might not exist, which is fine
    }

    // Additional cleanup tasks
    await cleanupTempFiles();

    console.log('E2E test environment cleanup complete');
  } catch (error) {
    console.error('Error during E2E test cleanup:', error);
    // Don't throw the error as cleanup failures shouldn't fail the tests
  }
}

async function cleanupTestData() {
  // Clean up any test data that was created during tests
  // This could include database records, uploaded files, etc.
  console.log('Cleaning up test data...');

  // Example: Clear test uploads directory
  try {
    const testUploadsPath = path.join(process.cwd(), 'test-uploads');
    await fs.rmdir(testUploadsPath, { recursive: true });
  } catch (error) {
    // Directory might not exist
  }
}

async function cleanupTempFiles() {
  // Clean up temporary files created during tests
  console.log('Cleaning up temporary files...');

  try {
    const tempPaths = ['test-results/screenshots', 'test-results/videos', 'test-results/traces'];

    for (const tempPath of tempPaths) {
      try {
        const fullPath = path.join(process.cwd(), tempPath);
        const stats = await fs.stat(fullPath);
        if (stats.isDirectory()) {
          const files = await fs.readdir(fullPath);
          // Keep only the most recent 5 test artifacts for debugging
          if (files.length > 5) {
            const sortedFiles = files
              .map((file) => ({
                name: file,
                time: fs.stat(path.join(fullPath, file)).then((s) => s.mtime),
              }))
              .sort((a, b) => b.time.valueOf() - a.time.valueOf());

            const filesToDelete = sortedFiles.slice(5);
            for (const file of filesToDelete) {
              await fs.unlink(path.join(fullPath, file.name));
            }
          }
        }
      } catch (error) {
        // Path might not exist
      }
    }
  } catch (error) {
    console.warn('Could not clean up all temporary files:', error);
  }
}

export default globalTeardown;
