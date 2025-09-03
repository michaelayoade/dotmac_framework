/**
 * Advanced Code Splitting Strategies
 * Intelligent route and component-based code splitting
 */

import type { Configuration } from 'webpack';

export interface CodeSplittingOptions {
  strategy: 'routes' | 'components' | 'features' | 'hybrid';
  routes?: RouteConfig[];
  components?: ComponentConfig[];
  features?: FeatureConfig[];
  chunkSizeThresholds?: ChunkSizeThresholds;
}

export interface RouteConfig {
  name: string;
  pattern: RegExp;
  priority: number;
  preload?: boolean;
  chunks?: string[];
}

export interface ComponentConfig {
  name: string;
  path: string;
  lazy: boolean;
  preload?: 'critical' | 'interaction' | 'viewport';
  dependencies?: string[];
}

export interface FeatureConfig {
  name: string;
  modules: string[];
  async: boolean;
  priority: number;
}

export interface ChunkSizeThresholds {
  minSize: number;
  maxSize: number;
  maxAsyncRequests: number;
  maxInitialRequests: number;
}

/**
 * Route-based code splitting configuration
 */
export const createRouteSplittingConfig = (routes: RouteConfig[]): Configuration['optimization'] => {
  const cacheGroups: Record<string, any> = {};
  
  routes.forEach(route => {
    cacheGroups[route.name] = {
      name: route.name,
      test: route.pattern,
      priority: route.priority,
      chunks: 'async',
      enforce: true,
    };
  });
  
  return {
    splitChunks: {
      chunks: 'all',
      cacheGroups,
    },
  };
};

/**
 * Component-based code splitting
 */
export const createComponentSplittingConfig = (components: ComponentConfig[]) => {
  const lazyComponents = components.filter(c => c.lazy);
  const criticalComponents = components.filter(c => c.preload === 'critical');
  
  return {
    // Generate dynamic import helpers
    generateLazyComponents: () => {
      return lazyComponents.map(component => ({
        name: component.name,
        path: component.path,
        importStatement: `React.lazy(() => import('${component.path}'))`,
        preloadStatement: component.preload 
          ? `import('${component.path}')` 
          : undefined,
      }));
    },
    
    // Critical component preloading
    preloadCritical: criticalComponents.map(c => c.path),
  };
};

/**
 * Feature-based code splitting
 */
export const createFeatureSplittingConfig = (features: FeatureConfig[]): Configuration['optimization'] => {
  const cacheGroups: Record<string, any> = {};
  
  features.forEach(feature => {
    cacheGroups[feature.name] = {
      name: feature.name,
      test: new RegExp(feature.modules.join('|')),
      priority: feature.priority,
      chunks: feature.async ? 'async' : 'all',
      enforce: true,
    };
  });
  
  return {
    splitChunks: {
      chunks: 'all',
      cacheGroups,
    },
  };
};

/**
 * Hybrid splitting strategy combining multiple approaches
 */
export const createHybridSplittingConfig = (options: CodeSplittingOptions): Configuration['optimization'] => {
  const { chunkSizeThresholds = defaultChunkSizeThresholds } = options;
  
  const cacheGroups: Record<string, any> = {
    // Framework (React, Next.js)
    framework: {
      name: 'framework',
      test: /[\\/]node_modules[\\/](react|react-dom|next)[\\/]/,
      priority: 50,
      chunks: 'all',
      enforce: true,
    },
    
    // DotMac shared packages
    dotmacShared: {
      name: 'dotmac-shared',
      test: /[\\/]node_modules[\\/]@dotmac[\\/]/,
      priority: 45,
      chunks: 'all',
      enforce: true,
    },
    
    // UI libraries
    uiLibs: {
      name: 'ui-libs',
      test: /[\\/]node_modules[\\/](@radix-ui|lucide-react|framer-motion)[\\/]/,
      priority: 40,
      chunks: 'all',
      minSize: chunkSizeThresholds.minSize,
    },
    
    // Data visualization (often large)
    dataViz: {
      name: 'data-viz',
      test: /[\\/]node_modules[\\/](recharts|d3|@visx|chart\.js)[\\/]/,
      priority: 35,
      chunks: 'async', // Load on demand
      enforce: true,
    },
    
    // Form libraries
    forms: {
      name: 'forms',
      test: /[\\/]node_modules[\\/](react-hook-form|@hookform|formik|yup|zod)[\\/]/,
      priority: 30,
      chunks: 'all',
    },
    
    // Utility libraries
    utils: {
      name: 'utils',
      test: /[\\/]node_modules[\\/](lodash|date-fns|ramda|clsx)[\\/]/,
      priority: 25,
      chunks: 'all',
    },
    
    // Vendor libraries
    vendor: {
      name: 'vendors',
      test: /[\\/]node_modules[\\/]/,
      priority: 10,
      chunks: 'all',
      minChunks: 2,
    },
    
    // Common application code
    common: {
      name: 'common',
      minChunks: 2,
      priority: 5,
      chunks: 'all',
      reuseExistingChunk: true,
    },
  };
  
  // Add route-specific cache groups
  if (options.routes) {
    options.routes.forEach(route => {
      cacheGroups[`route-${route.name}`] = {
        name: `route-${route.name}`,
        test: route.pattern,
        priority: route.priority + 20, // Higher than vendor
        chunks: 'async',
      };
    });
  }
  
  // Add feature-specific cache groups
  if (options.features) {
    options.features.forEach(feature => {
      cacheGroups[`feature-${feature.name}`] = {
        name: `feature-${feature.name}`,
        test: new RegExp(feature.modules.join('|')),
        priority: feature.priority + 15, // Between routes and vendor
        chunks: feature.async ? 'async' : 'all',
      };
    });
  }
  
  return {
    splitChunks: {
      chunks: 'all',
      minSize: chunkSizeThresholds.minSize,
      maxSize: chunkSizeThresholds.maxSize,
      maxAsyncRequests: chunkSizeThresholds.maxAsyncRequests,
      maxInitialRequests: chunkSizeThresholds.maxInitialRequests,
      cacheGroups,
    },
  };
};

/**
 * Smart chunk splitting based on usage patterns
 */
export const createSmartSplittingConfig = (usageData?: ChunkUsageData): Configuration['optimization'] => {
  // Analyze which chunks are loaded together frequently
  const correlatedChunks = analyzeChunkCorrelation(usageData);
  
  // Create optimized cache groups based on usage patterns
  const cacheGroups: Record<string, any> = {};
  
  correlatedChunks.forEach((group, index) => {
    cacheGroups[`smart-group-${index}`] = {
      name: `smart-group-${index}`,
      test: new RegExp(group.modules.join('|')),
      priority: 30 - index, // Higher priority for more correlated groups
      chunks: group.loadTogether ? 'initial' : 'async',
      minChunks: group.minUsage,
    };
  });
  
  return {
    splitChunks: {
      chunks: 'all',
      cacheGroups,
    },
  };
};

/**
 * Dynamic import optimization helpers
 */
export const createDynamicImportOptimizer = (components: ComponentConfig[]) => {
  return {
    // Generate optimized dynamic imports
    generateImports: () => {
      return components.map(component => {
        const importCode = `const ${component.name} = React.lazy(() => 
          import(/* webpackChunkName: "${component.name}" */ '${component.path}')
        );`;
        
        const preloadCode = component.preload 
          ? `const preload${component.name} = () => import('${component.path}');`
          : undefined;
        
        return {
          component: component.name,
          importCode,
          preloadCode,
          strategy: component.preload,
        };
      });
    },
    
    // Generate preload strategies
    generatePreloadStrategies: () => {
      const criticalComponents = components.filter(c => c.preload === 'critical');
      const interactionComponents = components.filter(c => c.preload === 'interaction');
      const viewportComponents = components.filter(c => c.preload === 'viewport');
      
      return {
        critical: criticalComponents.map(c => c.path),
        interaction: interactionComponents.map(c => c.path),
        viewport: viewportComponents.map(c => c.path),
      };
    },
  };
};

/**
 * Default chunk size thresholds
 */
const defaultChunkSizeThresholds: ChunkSizeThresholds = {
  minSize: 20000,      // 20KB
  maxSize: 244000,     // 244KB
  maxAsyncRequests: 30,
  maxInitialRequests: 30,
};

/**
 * Chunk usage analysis types
 */
interface ChunkUsageData {
  correlations: ChunkCorrelation[];
  loadTimes: Record<string, number>;
  frequency: Record<string, number>;
}

interface ChunkCorrelation {
  modules: string[];
  loadTogether: boolean;
  minUsage: number;
}

/**
 * Analyze chunk correlation patterns (placeholder for real implementation)
 */
const analyzeChunkCorrelation = (usageData?: ChunkUsageData): ChunkCorrelation[] => {
  // In a real implementation, this would analyze actual usage data
  // For now, return sensible defaults
  return [
    {
      modules: ['@dotmac/primitives', '@dotmac/headless'],
      loadTogether: true,
      minUsage: 2,
    },
    {
      modules: ['recharts', 'd3'],
      loadTogether: false,
      minUsage: 1,
    },
  ];
};