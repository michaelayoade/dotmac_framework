/**
 * Global Test Teardown
 * Runs once after all tests
 */

export default async function globalTeardown() {
  console.log('🧹 Cleaning up global test environment...');

  // Clean up any global resources
  // This is where you might close database connections, 
  // stop test servers, clean up temp files, etc.

  console.log('✅ Global test environment cleanup complete');
}