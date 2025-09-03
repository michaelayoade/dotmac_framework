/**
 * Management Page Factory
 * Creates pages using ManagementPageTemplate with configuration
 */

import React from 'react';
import { ManagementPageTemplate } from '../templates/ManagementPageTemplate';
import type { ManagementPageConfig } from '../types/templates';

export interface CreateManagementPageOptions {
  config: ManagementPageConfig;
  portal?: 'admin' | 'customer' | 'reseller' | 'technician' | 'management';
  className?: string;
  wrapperProps?: Record<string, any>;
}

/**
 * Factory function to create a management page component
 */
export function createManagementPage(options: CreateManagementPageOptions) {
  const { config, className, wrapperProps } = options;

  const ManagementPage: React.FC = () => {
    return React.createElement(ManagementPageTemplate, { config, className, ...wrapperProps });
  };

  // Set display name for debugging
  ManagementPage.displayName = `ManagementPage(${config.title})`;

  return ManagementPage;
}

/**
 * Hook for runtime configuration updates
 */
export function useManagementPageConfig(
  baseConfig: ManagementPageConfig,
  overrides?: Partial<ManagementPageConfig>
): ManagementPageConfig {
  return React.useMemo(
    () => ({
      ...baseConfig,
      ...overrides,
      metrics: overrides?.metrics || baseConfig.metrics,
      tableColumns: overrides?.tableColumns || baseConfig.tableColumns,
      actions: overrides?.actions || baseConfig.actions,
      filters: overrides?.filters || baseConfig.filters,
    }),
    [baseConfig, overrides]
  );
}

/**
 * Validation for management page configurations
 */
export function validateManagementConfig(config: ManagementPageConfig): string[] {
  const errors: string[] = [];

  if (!config.title) errors.push('title is required');
  if (!Array.isArray(config.metrics)) errors.push('metrics must be an array');
  if (!Array.isArray(config.filters)) errors.push('filters must be an array');
  if (!Array.isArray(config.actions)) errors.push('actions must be an array');

  return errors;
}
