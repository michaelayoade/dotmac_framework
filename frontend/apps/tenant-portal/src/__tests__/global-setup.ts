/**
 * Global Test Setup
 * Runs once before all tests
 */

export default async function globalSetup() {
  console.log('🧪 Setting up global test environment...');

  // Set timezone for consistent test results
  process.env.TZ = 'UTC';

  // Suppress console warnings during tests
  const originalWarn = console.warn;
  console.warn = (message: string, ...args: any[]) => {
    // Suppress specific warnings that are expected during testing
    const suppressedWarnings = [
      'Warning: ReactDOM.render is no longer supported',
      'Warning: Each child in a list should have a unique "key" prop',
      'act(...) is not supported in production builds',
      'Warning: componentWillReceiveProps has been renamed',
      'Warning: componentWillUpdate has been renamed',
    ];

    const shouldSuppress = suppressedWarnings.some(warning => 
      message.includes(warning)
    );

    if (!shouldSuppress) {
      originalWarn.call(console, message, ...args);
    }
  };

  // Initialize test database or other global resources if needed
  // This is where you might set up test databases, external services, etc.

  console.log('✅ Global test environment setup complete');
}