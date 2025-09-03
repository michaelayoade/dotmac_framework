/**
 * Reseller Portal Playwright Configuration
 * Uses unified config with reseller-specific overrides
 */

import { createUnifiedConfig } from '../../playwright.config.unified';

export default createUnifiedConfig({
  portal: 'reseller',
  testType: 'full',
  apiMocking: true,
});
