/**
 * @dotmac/governance - Architectural Governance Tools
 *
 * Provides ESLint rules, migration tools, and analysis utilities
 * to enforce and maintain architectural standards across DotMac frontend.
 */

// ESLint Rules
export { default as noDuplicateComponents } from '../eslint-rules/no-duplicate-components';
export { default as enforceProviderPattern } from '../eslint-rules/enforce-provider-pattern';

// Migration Tools
export {
  migrateComponents,
  migrateProviders,
  analyzeProject
} from '../bin/dotmac-migrate';

// Linting Tools
export {
  lintComponents,
  lintProviders,
  fullArchitecturalLint,
  setupGovernanceRules
} from '../bin/dotmac-lint';

// Analysis Tools
export {
  analyzeArchitecture,
  analyzeDependencies,
  analyzeBundleImpact,
  generateRecommendations
} from '../bin/dotmac-analyze';

// Types and Interfaces
export interface GovernanceConfig {
  rules: {
    'no-duplicate-components': 'error' | 'warn' | 'off';
    'enforce-provider-pattern': 'error' | 'warn' | 'off';
  };
  allowedFiles?: string[];
  allowedComponents?: string[];
  allowedPrefixes?: string[];
  forbiddenProviders?: string[];
}

export interface ArchitecturalAnalysis {
  packages: {
    packages: PackageInfo[];
    apps: AppInfo[];
    totalCount: number;
  };
  components: {
    totalComponents: number;
    uniqueComponents: number;
    duplicateComponents: number;
    duplicates: ComponentDuplicate[];
  };
  providers: {
    totalProviderFiles: number;
    universalProviderUsage: number;
    customCompositions: number;
    inconsistencies: ProviderInconsistency[];
  };
  dependencies: {
    totalDependencies: number;
    versionConflicts: number;
    conflicts: DependencyConflict[];
    mostUsedDependencies: DependencyUsage[];
  };
  reusability: {
    score: number;
    factors: ReusabilityFactors;
  };
  consistency: {
    score: number;
    factors: ConsistencyFactors;
  };
}

export interface PackageInfo {
  name: string;
  version: string;
  type: 'package' | 'app';
  path: string;
  dependencies: string[];
  devDependencies: string[];
  exports?: string | null;
  framework?: string;
}

export interface AppInfo extends PackageInfo {
  type: 'app';
  framework: string;
}

export interface ComponentDuplicate {
  name: string;
  count: number;
  files: string[];
  locations: string[];
}

export interface ProviderInconsistency {
  file: string;
  issue: string;
  providers: string[];
}

export interface DependencyConflict {
  dependency: string;
  versions: string[];
  usages: Array<{
    location: string;
    version: string;
    file: string;
  }>;
}

export interface DependencyUsage {
  name: string;
  count: number;
}

export interface ReusabilityFactors {
  duplicateRatio: number;
  packageRatio: number;
  sharedComponents: number;
  totalPackages: number;
}

export interface ConsistencyFactors {
  providerConsistency: number;
  componentConsistency: number;
  universalProviderUsage: number;
  totalProviderFiles: number;
}

export interface MigrationResult {
  success: boolean;
  filesChanged: number;
  componentsFixed: number;
  providersFixed: number;
  errors: Array<{
    file: string;
    error: string;
  }>;
}

export interface LintResult {
  totalFiles: number;
  errorCount: number;
  warningCount: number;
  fixableCount: number;
  ruleViolations: Record<string, number>;
  files: Array<{
    filePath: string;
    errorCount: number;
    warningCount: number;
    messages: Array<{
      ruleId: string;
      severity: 'error' | 'warning';
      message: string;
      line: number;
      column: number;
    }>;
  }>;
}

export interface Recommendation {
  title: string;
  priority: 'high' | 'medium' | 'low';
  description: string;
  actions: string[];
  impact: string;
}

// Constants
export const UNIFIED_COMPONENTS = [
  'Button', 'Input', 'Card', 'Modal', 'Form', 'Table',
  'Toast', 'Dialog', 'Dropdown', 'Select', 'Checkbox',
  'RadioGroup', 'Switch', 'Tabs', 'Accordion', 'Avatar',
  'Badge', 'Progress', 'Skeleton', 'Spinner', 'Alert', 'Tooltip'
] as const;

export const FORBIDDEN_DIRECT_PROVIDERS = [
  'QueryClientProvider',
  'ThemeProvider',
  'AuthProvider',
  'TenantProvider',
  'NotificationProvider',
  'ErrorBoundary'
] as const;

export const ALLOWED_LOCAL_PREFIXES = [
  'Portal',
  'Admin',
  'Customer',
  'Reseller',
  'Technician',
  'Management',
  'Local',
  'Custom'
] as const;

export const PORTALS = [
  'admin',
  'customer',
  'reseller',
  'technician',
  'management'
] as const;

// Default configurations
export const defaultGovernanceConfig: GovernanceConfig = {
  rules: {
    'no-duplicate-components': 'error',
    'enforce-provider-pattern': 'error'
  },
  allowedFiles: [
    'UniversalProviders.tsx',
    'providers/index.ts',
    'providers/UniversalProviders.tsx'
  ],
  allowedComponents: [],
  allowedPrefixes: [...ALLOWED_LOCAL_PREFIXES],
  forbiddenProviders: [...FORBIDDEN_DIRECT_PROVIDERS]
};

// Utility functions
export function detectPortalFromPath(filePath: string): string {
  for (const portal of PORTALS) {
    if (filePath.includes(`/apps/${portal}/`) || filePath.includes(`apps/${portal}/`)) {
      return portal;
    }
  }
  return 'default';
}

export function isUnifiedComponent(componentName: string): boolean {
  return UNIFIED_COMPONENTS.includes(componentName as any);
}

export function isForbiddenProvider(providerName: string): boolean {
  return FORBIDDEN_DIRECT_PROVIDERS.includes(providerName as any);
}

export function hasAllowedPrefix(componentName: string, allowedPrefixes: string[] = [...ALLOWED_LOCAL_PREFIXES]): boolean {
  return allowedPrefixes.some(prefix => componentName.startsWith(prefix));
}

// Version
export const version = '1.0.0';
