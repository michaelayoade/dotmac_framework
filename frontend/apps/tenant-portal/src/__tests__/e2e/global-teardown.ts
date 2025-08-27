/**
 * Playwright Global Teardown
 * Runs once after all E2E tests
 */

async function globalTeardown() {
  console.log('🧹 Cleaning up Playwright E2E environment...');

  // Clean up test data
  // You can add code here to:
  // - Remove test users
  // - Clean up test databases
  // - Reset external services
  // - Remove test files

  console.log('✅ Playwright E2E environment cleanup complete');
}

export default globalTeardown;