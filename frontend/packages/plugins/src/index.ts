// Export types
export type * from './types';

// Export hooks
export * from './hooks';

// Export components
export * from './components';

// Export utilities
export * from './utils';

// API endpoints for integration
export const API_ENDPOINTS = {
  PLUGINS: '/api/plugins',
  PLUGIN_INSTALL: '/api/plugins/install',
  PLUGIN_UPDATE: '/api/plugins/update',
  PLUGIN_UNINSTALL: '/api/plugins/uninstall',
  PLUGIN_ENABLE: '/api/plugins/enable',
  PLUGIN_DISABLE: '/api/plugins/disable',
  PLUGIN_RESTART: '/api/plugins/restart',
  PLUGIN_HEALTH: '/api/plugins/health',
  SYSTEM_HEALTH: '/api/plugins/system/health',
  MARKETPLACE: '/api/plugins/marketplace',
  MARKETPLACE_SEARCH: '/api/plugins/marketplace/search',
  LIFECYCLE: '/api/plugins/lifecycle'
} as const;
