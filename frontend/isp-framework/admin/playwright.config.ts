/**
 * Admin Portal Playwright Configuration
 * Uses unified config with admin-specific overrides
 */

import { createUnifiedConfig } from '../../playwright.config.unified';

export default createUnifiedConfig({
  portal: 'admin',
  testType: 'full',
  apiMocking: true,
});
