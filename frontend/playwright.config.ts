import { createUnifiedConfig } from './playwright.config.unified';

// Delegate to the unified config to eliminate duplication and keep
// portal setups and webServer strategy consistent.
export default createUnifiedConfig();
