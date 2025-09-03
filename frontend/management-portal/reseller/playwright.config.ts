/**
 * Management Reseller Portal Playwright Configuration
 * Uses unified config with management-reseller-specific overrides
 */

import { createUnifiedConfig } from '../../playwright.config.unified';

export default createUnifiedConfig({
  portal: 'management-reseller',
  testType: 'full',
  apiMocking: true,
});
