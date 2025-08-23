/**
 * Global Jest teardown - runs once after all tests
 */

module.exports = async () => {
  console.log('🧹 Starting global test cleanup...');

  // Ensure MSW server is properly closed
  try {
    const { server } = require('./__mocks__/server.js');
    if (server && typeof server.close === 'function') {
      await server.close();
      console.log('✅ MSW server closed');
    }
  } catch (error) {
    // MSW server might not be available or already closed
    console.log('ℹ️ MSW server cleanup skipped (not available)');
  }

  // Close any other global resources
  if (global.gc) {
    global.gc();
  }

  console.log('🧹 Global test cleanup complete');
};
