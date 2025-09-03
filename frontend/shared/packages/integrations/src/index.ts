/**
 * Integration Components Package
 * Provides standardized integration UI components following DRY patterns
 */

// Main dashboard components
export { default as ApiGatewayDashboard } from './components/ApiGatewayDashboard';

// Integration management components
export { IntegrationHubView } from './components/IntegrationHubView';
export { WebhookManagerView } from './components/WebhookManagerView';
export { ConnectionManagerView } from './components/ConnectionManagerView';

// Hooks for integration management
export { useIntegrationHub } from './hooks/useIntegrationHub';
export { useWebhookManager } from './hooks/useWebhookManager';
export { useConnectionManager } from './hooks/useConnectionManager';

// Types and interfaces
export type {
  GatewayMetrics,
  IntegrationConnection,
  WebhookEndpoint,
  ApiConnection,
} from './types';

// Utilities
export { IntegrationUtils } from './utils/integrationUtils';
