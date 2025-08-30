// Plugin System Types for DotMac Framework
export enum PluginStatus {
  UNINITIALIZED = 'uninitialized',
  INITIALIZING = 'initializing',
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error',
  DISABLED = 'disabled',
  UPDATING = 'updating'
}

export interface PluginMetadata {
  // Core identification
  name: string;
  version: string;
  domain: string;

  // Plugin information
  description?: string;
  author?: string;
  homepage?: string;

  // Dependencies and compatibility
  dependencies: string[];
  optional_dependencies: string[];
  python_requires?: string;
  platform_compatibility: string[];

  // Plugin capabilities
  supports_async: boolean;
  supports_streaming: boolean;
  supports_batching: boolean;
  thread_safe: boolean;

  // Configuration
  config_schema?: Record<string, any>;
  default_config: Record<string, any>;
  required_permissions: string[];

  // Runtime information
  plugin_id: string;
  created_at: string;
  updated_at?: string;

  // Tags for categorization and discovery
  tags: string[];
  categories: string[];
}

export interface Plugin {
  metadata: PluginMetadata;
  config: Record<string, any>;
  status: PluginStatus;

  // Runtime state
  initialized_at?: string;
  last_activity?: string;
  error_count: number;
  success_count: number;
  uptime?: number;

  // Health information
  healthy: boolean;
  is_active: boolean;
}

export interface PluginHealth {
  status: PluginStatus;
  name: string;
  version: string;
  domain: string;
  healthy: boolean;
  uptime_seconds?: number;
  error_count: number;
  success_count: number;
  last_activity?: string;
  plugin_specific?: Record<string, any>;
}

export interface PluginInstallation {
  id: string;
  plugin_key: string;
  tenant_id?: string;
  installed_at: string;
  installed_by: string;
  version: string;
  config: Record<string, any>;
  enabled: boolean;
  auto_update: boolean;
}

export interface PluginRegistry {
  plugins: Plugin[];
  domains: string[];
  total_plugins: number;
  active_plugins: number;
  healthy_plugins: number;
  error_plugins: number;
}

export interface PluginMarketplaceItem {
  id: string;
  name: string;
  display_name: string;
  description: string;
  version: string;
  latest_version: string;
  author: string;
  homepage?: string;
  repository?: string;
  documentation?: string;

  // Marketplace metadata
  category: string;
  tags: string[];
  rating: number;
  download_count: number;
  last_updated: string;

  // Installation information
  installation_url: string;
  install_size: number;
  dependencies: string[];

  // Status
  installed: boolean;
  update_available: boolean;
  compatible: boolean;

  // Pricing (if applicable)
  pricing_model: 'free' | 'paid' | 'freemium';
  price?: number;
  trial_available?: boolean;
}

export interface PluginInstallRequest {
  plugin_id: string;
  version?: string;
  config?: Record<string, any>;
  enable_after_install: boolean;
  auto_update: boolean;
}

export interface PluginUpdateRequest {
  plugin_key: string;
  version?: string;
  config_changes?: Record<string, any>;
  force_update: boolean;
}

export interface PluginUninstallRequest {
  plugin_key: string;
  remove_data: boolean;
  force_removal: boolean;
}

export interface PluginConfigValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PluginSearchFilters {
  category?: string;
  tags?: string[];
  status?: PluginStatus;
  domain?: string;
  installed?: boolean;
  compatible?: boolean;
  name_pattern?: string;
  author?: string;
}

export interface PluginSystemHealth {
  manager: {
    initialized: boolean;
    shutdown: boolean;
    timestamp: string;
  };
  registry: {
    total_plugins: number;
    domains: string[];
  };
  lifecycle: Record<string, any>;
  plugins: {
    total_plugins: number;
    active_plugins: number;
    healthy_plugins: number;
    error_plugins: number;
  };
}

// Hook return types
export interface UsePluginsResult {
  plugins: Plugin[];
  loading: boolean;
  error: string | null;

  // Plugin management
  installPlugin: (request: PluginInstallRequest) => Promise<void>;
  updatePlugin: (request: PluginUpdateRequest) => Promise<void>;
  uninstallPlugin: (request: PluginUninstallRequest) => Promise<void>;

  // Plugin control
  enablePlugin: (pluginKey: string) => Promise<void>;
  disablePlugin: (pluginKey: string) => Promise<void>;
  restartPlugin: (pluginKey: string) => Promise<void>;

  // Plugin information
  getPlugin: (domain: string, name: string) => Plugin | null;
  getPluginHealth: (pluginKey: string) => Promise<PluginHealth>;

  // Filtering and search
  findPlugins: (filters: PluginSearchFilters) => Plugin[];
  getAvailableDomains: () => string[];

  // Bulk operations
  enableMultiplePlugins: (pluginKeys: string[]) => Promise<Record<string, boolean>>;
  disableMultiplePlugins: (pluginKeys: string[]) => Promise<Record<string, boolean>>;

  // System operations
  getSystemHealth: () => Promise<PluginSystemHealth>;
  refreshPlugins: () => Promise<void>;
}

export interface UsePluginMarketplaceResult {
  items: PluginMarketplaceItem[];
  loading: boolean;
  error: string | null;

  // Search and filtering
  searchPlugins: (query: string, filters?: PluginSearchFilters) => Promise<void>;
  filterByCategory: (category: string) => void;
  filterByTag: (tag: string) => void;
  clearFilters: () => void;

  // Installation
  installFromMarketplace: (item: PluginMarketplaceItem) => Promise<void>;

  // Information
  getPluginDetails: (pluginId: string) => Promise<PluginMarketplaceItem | null>;
  getCategories: () => string[];
  getPopularTags: () => string[];

  // Management
  refreshMarketplace: () => Promise<void>;
  checkForUpdates: () => Promise<void>;
}

export interface UsePluginLifecycleResult {
  // Lifecycle operations
  initializePlugin: (pluginKey: string) => Promise<boolean>;
  shutdownPlugin: (pluginKey: string) => Promise<boolean>;
  restartPlugin: (pluginKey: string) => Promise<boolean>;

  // Health monitoring
  performHealthCheck: (pluginKey: string) => Promise<PluginHealth>;
  startHealthMonitoring: () => Promise<void>;
  stopHealthMonitoring: () => Promise<void>;

  // Configuration
  updatePluginConfig: (pluginKey: string, config: Record<string, any>) => Promise<void>;
  validatePluginConfig: (pluginKey: string, config: Record<string, any>) => Promise<PluginConfigValidation>;

  // Bulk operations
  initializePluginsByDomain: (domain: string) => Promise<Record<string, boolean>>;
  shutdownPluginsByDomain: (domain: string) => Promise<Record<string, boolean>>;

  // Monitoring state
  healthMonitoringActive: boolean;
  lastHealthCheck: string | null;
}

// Component props types
export interface PluginDashboardProps {
  showSystemMetrics?: boolean;
  showRecentActivity?: boolean;
  showHealthAlerts?: boolean;
  refreshInterval?: number;
}

export interface PluginMarketplaceProps {
  defaultCategory?: string;
  showInstalledOnly?: boolean;
  showFilters?: boolean;
  allowInstallation?: boolean;
}

export interface PluginManagerProps {
  domain?: string;
  allowBulkOperations?: boolean;
  showAdvancedFeatures?: boolean;
  refreshInterval?: number;
}

export interface PluginCardProps {
  plugin: Plugin;
  showActions?: boolean;
  showHealth?: boolean;
  onEnable?: (pluginKey: string) => void;
  onDisable?: (pluginKey: string) => void;
  onRestart?: (pluginKey: string) => void;
  onConfigure?: (pluginKey: string) => void;
}

export interface PluginInstallWizardProps {
  marketplaceItem: PluginMarketplaceItem;
  onInstall: (request: PluginInstallRequest) => Promise<void>;
  onCancel: () => void;
}

// API types
export interface PluginsAPI {
  // Plugin management
  getPlugins: (domain?: string) => Promise<Plugin[]>;
  getPlugin: (domain: string, name: string) => Promise<Plugin>;
  installPlugin: (request: PluginInstallRequest) => Promise<void>;
  updatePlugin: (request: PluginUpdateRequest) => Promise<void>;
  uninstallPlugin: (request: PluginUninstallRequest) => Promise<void>;

  // Plugin control
  enablePlugin: (pluginKey: string) => Promise<void>;
  disablePlugin: (pluginKey: string) => Promise<void>;
  restartPlugin: (pluginKey: string) => Promise<void>;

  // Health and monitoring
  getPluginHealth: (pluginKey: string) => Promise<PluginHealth>;
  getSystemHealth: () => Promise<PluginSystemHealth>;

  // Marketplace
  getMarketplaceItems: (filters?: PluginSearchFilters) => Promise<PluginMarketplaceItem[]>;
  searchMarketplace: (query: string, filters?: PluginSearchFilters) => Promise<PluginMarketplaceItem[]>;
  getMarketplaceItem: (pluginId: string) => Promise<PluginMarketplaceItem>;

  // Configuration
  updatePluginConfig: (pluginKey: string, config: Record<string, any>) => Promise<void>;
  validatePluginConfig: (pluginKey: string, config: Record<string, any>) => Promise<PluginConfigValidation>;

  // System operations
  refreshPluginRegistry: () => Promise<void>;
}
