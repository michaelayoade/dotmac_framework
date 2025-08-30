/**
 * Plugin Management Components
 * Exports all plugin-related components using existing DRY ErrorBoundary system
 */

import { withErrorBoundary } from '@dotmac/providers';
import { PluginManagement as PluginManagementBase } from './PluginManagement';
import { PluginMarketplace as PluginMarketplaceBase } from './PluginMarketplace';
import { InstalledPlugins as InstalledPluginsBase } from './InstalledPlugins';
import { PluginInstallationWizard as PluginInstallationWizardBase } from './PluginInstallationWizard';

// Wrap components with existing error boundary system
export const PluginManagement = withErrorBoundary(PluginManagementBase, {
  portal: 'management',
  onError: (error, errorInfo) => {
    // Use existing error reporting instead of console.error
    // This will integrate with gtag and monitoring service automatically
  }
});

export const PluginMarketplace = withErrorBoundary(PluginMarketplaceBase, {
  portal: 'management',
  onError: (error, errorInfo) => {
    // Existing system handles logging automatically
  }
});

export const InstalledPlugins = withErrorBoundary(InstalledPluginsBase, {
  portal: 'management'
});

export const PluginInstallationWizard = withErrorBoundary(PluginInstallationWizardBase, {
  portal: 'management'
});

// Export base components for testing
export {
  PluginManagementBase,
  PluginMarketplaceBase,
  InstalledPluginsBase,
  PluginInstallationWizardBase
};
