/**
 * Main Bundle Optimizer Factory
 * Central configuration and optimization orchestrator
 */

import type { Configuration } from 'webpack';
import { createOptimizedWebpackConfig } from '../configs/next-bundle-optimizer.js';
import { createTreeShakingConfig, type TreeShakingOptions } from './tree-shaking';
import { createHybridSplittingConfig, type CodeSplittingOptions } from './code-splitting';
import { createBundleAnalyzer, type BundleAnalysisOptions } from './bundle-analyzer';
import { createDynamicComponent, type ComponentImportConfig } from './dynamic-imports';

export interface NextOptimizerOptions {
  // Environment settings
  isDevelopment?: boolean;
  isProduction?: boolean;
  analyze?: boolean;
  
  // Optimization strategies
  codeSplitting?: CodeSplittingOptions;
  treeShaking?: TreeShakingOptions;
  bundleAnalysis?: BundleAnalysisOptions;
  
  // Dynamic imports
  dynamicComponents?: ComponentImportConfig[];
  
  // Performance budgets
  performanceBudgets?: PerformanceBudgetConfig;
  
  // Custom webpack optimizations
  customOptimizations?: CustomOptimizationConfig;
}

export interface PerformanceBudgetConfig {
  maxBundleSize: number;
  maxChunkSize: number;
  maxAssetSize: number;
  gzipThreshold: number;
}

export interface CustomOptimizationConfig {
  externals?: Record<string, string>;
  aliases?: Record<string, string>;
  additionalPlugins?: any[];
  moduleRules?: any[];
}

/**
 * Main optimizer factory
 */
export const createNextOptimizer = (options: NextOptimizerOptions = {}) => {
  const {
    isDevelopment = process.env.NODE_ENV === 'development',
    isProduction = process.env.NODE_ENV === 'production',
    analyze = process.env.ANALYZE === 'true',
  } = options;
  
  return {
    // Next.js configuration enhancer
    withOptimization: (nextConfig: any = {}) => {
      return {
        ...nextConfig,
        
        // Experimental features
        experimental: {
          ...nextConfig.experimental,
          // Optimize package imports
          optimizePackageImports: [
            '@dotmac/primitives',
            '@dotmac/headless',
            '@dotmac/styled-components',
            'lucide-react',
            '@radix-ui/react-icons',
            'react-hook-form',
            'date-fns',
            'lodash-es',
            ...(nextConfig.experimental?.optimizePackageImports || []),
          ],
          
          // Server components optimization
          serverComponentsExternalPackages: [
            'sharp',
            'onnxruntime-node',
            ...(nextConfig.experimental?.serverComponentsExternalPackages || []),
          ],
          
          // Enable turbo optimizations
          turbo: {
            rules: {
              '*.svg': {
                loaders: ['@svgr/webpack'],
                as: '*.js',
              },
              ...nextConfig.experimental?.turbo?.rules,
            },
          },
        },
        
        // Compiler optimizations
        compiler: {
          ...nextConfig.compiler,
          // Remove console logs in production
          removeConsole: isProduction,
          // Remove React dev tools in production
          reactRemoveProperties: isProduction,
        },
        
        // Performance optimizations
        swcMinify: true,
        compress: true,
        poweredByHeader: false,
        
        // Webpack configuration
        webpack: (config: Configuration, context: any) => {
          // Apply custom webpack optimizations
          const optimizedConfig = applyWebpackOptimizations(config, {
            ...context,
            options,
            isDevelopment,
            isProduction,
            analyze,
          });
          
          // Apply user's custom webpack config
          if (nextConfig.webpack) {
            return nextConfig.webpack(optimizedConfig, context);
          }
          
          return optimizedConfig;
        },
      };
    },
    
    // Webpack plugin factory
    createWebpackPlugins: () => createWebpackPlugins(options),
    
    // Component factory for dynamic imports
    createDynamicComponents: () => {
      if (!options.dynamicComponents) return {};
      
      return options.dynamicComponents.reduce((components, config) => {
        components[config.name] = createDynamicComponent(config);
        return components;
      }, {} as Record<string, any>);
    },
    
    // Performance monitor
    createPerformanceMonitor: () => createPerformanceMonitor(options),
    
    // Bundle analyzer
    createAnalyzer: () => {
      if (!options.bundleAnalysis) return null;
      return createBundleAnalyzer(options.bundleAnalysis);
    },
  };
};

/**
 * Apply webpack optimizations
 */
const applyWebpackOptimizations = (
  config: Configuration,
  context: {
    options: NextOptimizerOptions;
    isDevelopment: boolean;
    isProduction: boolean;
    analyze: boolean;
    dev: boolean;
    isServer: boolean;
    buildId: string;
  }
) => {
  const { options, isDevelopment, isProduction, analyze, dev, isServer } = context;
  
  // Apply tree shaking
  if (options.treeShaking && isProduction) {
    const treeShakingConfig = createTreeShakingConfig(options.treeShaking);
    config.optimization = {
      ...config.optimization,
      ...treeShakingConfig,
    };
  }
  
  // Apply code splitting
  if (options.codeSplitting) {
    const codeSplittingConfig = createHybridSplittingConfig(options.codeSplitting);
    config.optimization = {
      ...config.optimization,
      ...codeSplittingConfig,
    };
  }
  
  // Apply custom optimizations
  if (options.customOptimizations) {
    applyCustomOptimizations(config, options.customOptimizations);
  }
  
  // Add performance budgets
  if (options.performanceBudgets && isProduction) {
    config.performance = {
      hints: 'error',
      maxAssetSize: options.performanceBudgets.maxAssetSize,
      maxEntrypointSize: options.performanceBudgets.maxBundleSize,
      assetFilter: (assetFilename) => {
        return !assetFilename.includes('.map') &&
               !assetFilename.includes('sw.js') &&
               !assetFilename.includes('workbox-');
      },
    };
  }
  
  // Add bundle analyzer
  if (options.bundleAnalysis && (analyze || options.bundleAnalysis.enabled)) {
    const analyzer = createBundleAnalyzer(options.bundleAnalysis);
    if (analyzer) {
      config.plugins = config.plugins || [];
      config.plugins.push(analyzer);
    }
  }
  
  // Optimize module resolution
  config.resolve = {
    ...config.resolve,
    alias: {
      ...config.resolve?.alias,
      // Optimize lodash imports
      'lodash': 'lodash-es',
      // Optimize date-fns imports
      'date-fns': 'date-fns/esm',
      // Custom aliases
      ...options.customOptimizations?.aliases,
    },
    mainFields: ['es2015', 'module', 'main'],
    extensions: ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json'],
  };
  
  // Add module rules for better optimization
  config.module = config.module || { rules: [] };
  config.module.rules.push(
    {
      test: /\.js$/,
      include: /node_modules\/(lodash|ramda)/,
      sideEffects: false,
    },
    {
      test: /\.js$/,
      include: /@dotmac/,
      sideEffects: false,
    },
    ...(options.customOptimizations?.moduleRules || [])
  );
  
  return config;
};

/**
 * Apply custom optimizations
 */
const applyCustomOptimizations = (
  config: Configuration,
  customOptimizations: CustomOptimizationConfig
) => {
  // Apply externals
  if (customOptimizations.externals) {
    config.externals = {
      ...config.externals,
      ...customOptimizations.externals,
    };
  }
  
  // Add additional plugins
  if (customOptimizations.additionalPlugins) {
    config.plugins = config.plugins || [];
    config.plugins.push(...customOptimizations.additionalPlugins);
  }
};

/**
 * Create webpack plugins for optimization
 */
const createWebpackPlugins = (options: NextOptimizerOptions) => {
  const plugins: any[] = [];
  
  // Bundle analyzer plugin
  if (options.bundleAnalysis?.enabled) {
    const analyzer = createBundleAnalyzer(options.bundleAnalysis);
    if (analyzer) plugins.push(analyzer);
  }
  
  // Ignore plugin for reducing bundle size
  const { IgnorePlugin } = require('webpack');
  plugins.push(
    new IgnorePlugin({
      resourceRegExp: /^\.\/locale$/,
      contextRegExp: /moment$/,
    }),
    new IgnorePlugin({
      resourceRegExp: /^\.\/locales$/,
      contextRegExp: /date-fns$/,
    })
  );
  
  // Define plugin for feature flags
  const { DefinePlugin } = require('webpack');
  plugins.push(
    new DefinePlugin({
      __DEV__: JSON.stringify(process.env.NODE_ENV === 'development'),
      __PROD__: JSON.stringify(process.env.NODE_ENV === 'production'),
      __ANALYZE__: JSON.stringify(process.env.ANALYZE === 'true'),
    })
  );
  
  return plugins;
};

/**
 * Create performance monitor
 */
const createPerformanceMonitor = (options: NextOptimizerOptions) => {
  const budgets = options.performanceBudgets;
  if (!budgets) return null;
  
  return {
    // Monitor bundle sizes
    checkBundleSizes: (stats: any) => {
      const assets = stats.compilation.assets;
      const warnings: string[] = [];
      const errors: string[] = [];
      
      Object.keys(assets).forEach(assetName => {
        const asset = assets[assetName];
        const size = asset.size();
        
        if (size > budgets.maxAssetSize) {
          errors.push(`Asset ${assetName} (${size} bytes) exceeds maximum size (${budgets.maxAssetSize} bytes)`);
        }
      });
      
      return { warnings, errors };
    },
    
    // Monitor chunk sizes
    checkChunkSizes: (stats: any) => {
      const chunks = stats.compilation.chunks;
      const warnings: string[] = [];
      const errors: string[] = [];
      
      chunks.forEach((chunk: any) => {
        const size = chunk.size();
        
        if (size > budgets.maxChunkSize) {
          warnings.push(`Chunk ${chunk.name || chunk.id} (${size} bytes) exceeds maximum size (${budgets.maxChunkSize} bytes)`);
        }
      });
      
      return { warnings, errors };
    },
  };
};

/**
 * Preset configurations for common scenarios
 */
export const optimizerPresets = {
  // Aggressive optimization for production
  production: (): NextOptimizerOptions => ({
    isProduction: true,
    codeSplitting: {
      strategy: 'hybrid',
      chunkSizeThresholds: {
        minSize: 30000,
        maxSize: 200000,
        maxAsyncRequests: 20,
        maxInitialRequests: 20,
      },
    },
    treeShaking: {
      packages: [
        { name: 'lodash-es', sideEffects: false },
        { name: '@dotmac/primitives', sideEffects: false },
        { name: 'lucide-react', sideEffects: false },
      ],
      sideEffectsFree: ['**/*.css', '**/*.scss'],
      aggressiveMode: true,
    },
    performanceBudgets: {
      maxBundleSize: 400000,  // 400KB
      maxChunkSize: 200000,   // 200KB
      maxAssetSize: 200000,   // 200KB
      gzipThreshold: 10240,   // 10KB
    },
  }),
  
  // Balanced optimization for staging
  staging: (): NextOptimizerOptions => ({
    codeSplitting: {
      strategy: 'hybrid',
      chunkSizeThresholds: {
        minSize: 20000,
        maxSize: 250000,
        maxAsyncRequests: 25,
        maxInitialRequests: 25,
      },
    },
    treeShaking: {
      packages: [
        { name: '@dotmac/primitives', sideEffects: false },
        { name: 'lucide-react', sideEffects: false },
      ],
      sideEffectsFree: ['**/*.css'],
      aggressiveMode: false,
    },
    bundleAnalysis: {
      enabled: true,
      mode: 'static',
      openAnalyzer: false,
      reportPath: './reports',
      generateStats: true,
    },
  }),
  
  // Development optimization
  development: (): NextOptimizerOptions => ({
    isDevelopment: true,
    codeSplitting: {
      strategy: 'routes',
      chunkSizeThresholds: {
        minSize: 10000,
        maxSize: 500000,
        maxAsyncRequests: 50,
        maxInitialRequests: 50,
      },
    },
    bundleAnalysis: {
      enabled: process.env.ANALYZE === 'true',
      mode: 'server',
      openAnalyzer: true,
      reportPath: './reports',
      generateStats: false,
    },
  }),
};