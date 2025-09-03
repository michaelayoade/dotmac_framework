import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global E2E test setup...');

  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Check if the application is running
  const baseURL = config.projects[0]?.use?.baseURL || 'http://localhost:3003';

  try {
    console.log(`🔍 Checking if application is running at ${baseURL}`);
    await page.goto(`${baseURL}/api/health`);
    const response = await page.textContent('body');
    console.log('✅ Application health check passed');
  } catch (error) {
    console.error('❌ Application health check failed:', error);
    throw new Error(
      `Application is not running at ${baseURL}. Please start the development server first.`
    );
  }

  // Set up test data
  console.log('🔧 Setting up test data...');

  // Store authentication tokens and test data in global state
  process.env.PLAYWRIGHT_TEST_BASE_URL = baseURL;
  process.env.PLAYWRIGHT_TEST_READY = 'true';

  await browser.close();
  console.log('✅ Global setup completed successfully');
}

export default globalSetup;
