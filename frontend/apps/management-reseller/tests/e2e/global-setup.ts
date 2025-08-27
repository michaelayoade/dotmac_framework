import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  // Create a browser instance for setup
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Set up test environment
    console.log('Setting up E2E test environment...');
    
    // Wait for the dev server to be ready
    const baseURL = config.webServer?.url || 'http://localhost:3004';
    console.log(`Waiting for server at ${baseURL}`);
    
    // Try to access the application
    await page.goto(baseURL);
    await page.waitForLoadState('networkidle');
    
    // Set up test data if needed
    // For example, you could seed the database or create test users here
    
    // Store authentication state for tests that need it
    await setupAuthenticationState(page, baseURL);
    
    console.log('E2E test environment setup complete');
  } catch (error) {
    console.error('Failed to set up E2E test environment:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

async function setupAuthenticationState(page: any, baseURL: string) {
  try {
    // Create authenticated session for tests that need it
    await page.goto(`${baseURL}/login`);
    
    // Fill in test credentials (these would be test-specific credentials)
    await page.fill('[data-testid="email-input"]', 'test-admin@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');
    
    // Wait for successful login
    await page.waitForURL(`${baseURL}/dashboard`);
    
    // Save authenticated state
    await page.context().storageState({ path: 'tests/e2e/fixtures/auth-state.json' });
    
    console.log('Authentication state saved for E2E tests');
  } catch (error) {
    console.warn('Could not set up authentication state:', error);
    // This is not a critical error - tests can still run without pre-authentication
  }
}

export default globalSetup;