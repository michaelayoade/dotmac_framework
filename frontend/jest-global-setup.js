/**
 * Global Jest setup - runs once before all tests
 * Follows backend pattern for comprehensive test environment setup
 */

module.exports = async () => {
  // Set test environment variables
  process.env.NODE_ENV = 'test';
  process.env.NEXT_PUBLIC_API_URL = 'http://localhost:3001/api/v1';
  process.env.NEXT_PUBLIC_APP_ENV = 'test';

  // Disable analytics in tests
  process.env.NEXT_PUBLIC_ANALYTICS_ENABLED = 'false';

  // Mock external services
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = 'pk_test_mock';

  // Setup global test utilities
  global.TEST_CONFIG = {
    apiUrl: 'http://localhost:3001/api/v1',
    timeout: 10000,
    retries: 2,
  };

  console.log('🧪 Global test setup complete');
};
