/**
 * Customer Portal Playwright Configuration
 * Uses unified config with customer-specific overrides
 */

import { createUnifiedConfig } from '../../playwright.config.unified';

export default createUnifiedConfig({ 
  portal: 'customer',
  testType: 'full',
  apiMocking: true 
});
