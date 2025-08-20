// Main API exports
export * from './client';
// Re-export for convenience
export { getApiClient } from './client';
export * from './config';
export { checkApiHealth, initializeApi, requireApiClient } from './config';
