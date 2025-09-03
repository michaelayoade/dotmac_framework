/**
 * Advanced Tree Shaking Configuration
 * Optimize dead code elimination and reduce bundle size
 */

import type { Configuration } from 'webpack';

export interface TreeShakingOptions {
  packages: PackageTreeShakingConfig[];
  sideEffectsFree: string[];
  customAnalyzer?: boolean;
  aggressiveMode?: boolean;
}

export interface PackageTreeShakingConfig {
  name: string;
  sideEffects: boolean | string[];
  exports?: string[];
  usedExports?: string[];
  customShaking?: TreeShakingStrategy;
}

export type TreeShakingStrategy = 'conservative' | 'aggressive' | 'custom';

/**
 * Create optimized tree shaking configuration
 */
export const createTreeShakingConfig = (options: TreeShakingOptions): Configuration['optimization'] => {
  const { packages, sideEffectsFree, aggressiveMode = false } = options;
  
  return {
    // Enable tree shaking
    usedExports: true,
    sideEffects: false,
    
    // Module concatenation for better tree shaking
    concatenateModules: true,
    
    // Provide side effects configuration
    providedExports: true,
    
    // Mark packages as side-effect free
    sideEffects: createSideEffectsConfig(packages, sideEffectsFree),
    
    // Minimize in production with tree shaking
    minimize: process.env.NODE_ENV === 'production',
    
    // Inner graph optimization
    innerGraph: aggressiveMode,
  };
};

/**
 * Create side effects configuration
 */
const createSideEffectsConfig = (
  packages: PackageTreeShakingConfig[], 
  additionalSideEffectsFree: string[]
): boolean | string[] => {
  const sideEffectsFreePatterns = [
    // Always safe patterns
    '*.css',
    '*.scss',
    '*.sass',
    '*.less',
    '*.styl',
    
    // DotMac packages (designed to be side-effect free)
    '@dotmac/primitives',
    '@dotmac/primitives/**',
    '@dotmac/headless',
    '@dotmac/headless/**',
    '@dotmac/styled-components',
    '@dotmac/styled-components/**',
    
    // UI libraries known to be side-effect free
    'lucide-react',
    'lucide-react/**',
    '@radix-ui/**',
    'class-variance-authority',
    'clsx',
    'tailwind-merge',
    
    // Utility libraries
    'lodash-es',
    'lodash-es/**',
    'date-fns',
    'date-fns/**',
    'ramda',
    'ramda/**',
    
    // Form libraries (mostly pure)
    'yup',
    'joi',
    'superstruct',
    
    // Add custom side-effect free packages
    ...additionalSideEffectsFree,
    
    // Add package-specific configurations
    ...packages
      .filter(pkg => pkg.sideEffects === false)
      .map(pkg => pkg.name),
  ];
  
  return sideEffectsFreePatterns;
};

/**
 * Advanced tree shaking for specific packages
 */
export const createPackageTreeShakingConfig = (packages: PackageTreeShakingConfig[]) => {
  const rules: Configuration['module']['rules'] = [];
  
  packages.forEach(pkg => {
    if (pkg.customShaking) {
      rules.push({
        test: new RegExp(`node_modules[\\\\/]${pkg.name.replace('/', '[\\\\/]')}`),
        sideEffects: pkg.sideEffects,
        use: {
          loader: 'webpack-tree-shaking-loader',
          options: {
            strategy: pkg.customShaking,
            exports: pkg.exports,
            usedExports: pkg.usedExports,
          },
        },
      });
    }
  });
  
  return rules;
};

/**
 * Dead code elimination configuration
 */
export const createDeadCodeEliminationConfig = () => ({
  // Enable dead code elimination
  useDeadCodeElimination: true,
  
  // Webpack module rules for better DCE
  moduleRules: [
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
  ],
  
  // Terser configuration for dead code removal
  terserOptions: {
    compress: {
      // Remove unused code
      dead_code: true,
      // Remove unused variables
      unused: true,
      // Drop unreachable code
      conditionals: true,
      // Remove console.* in production
      drop_console: process.env.NODE_ENV === 'production',
      // Remove debugger statements
      drop_debugger: true,
      // Evaluate constant expressions
      evaluate: true,
      // Inline single-use variables
      inline: 2,
      // Join consecutive var statements
      join_vars: true,
      // Optimize loops
      loops: true,
      // Remove unreferenced functions
      pure_funcs: [
        'console.log',
        'console.warn',
        'console.info',
        'console.debug',
        'assert',
      ],
    },
    mangle: {
      // Mangle variable names for smaller size
      toplevel: true,
    },
  },
});

/**
 * Import optimization configuration
 */
export const createImportOptimizationConfig = () => ({
  // Babel plugin configurations for better tree shaking
  babelPlugins: [
    // Transform imports for better tree shaking
    [
      'babel-plugin-import',
      {
        libraryName: '@dotmac/primitives',
        libraryDirectory: 'src/components',
        camel2DashComponentName: false,
      },
      'dotmac-primitives',
    ],
    [
      'babel-plugin-import',
      {
        libraryName: 'lodash',
        libraryDirectory: '',
        camel2DashComponentName: false,
      },
      'lodash',
    ],
    [
      'babel-plugin-import',
      {
        libraryName: 'date-fns',
        libraryDirectory: '',
        camel2DashComponentName: false,
      },
      'date-fns',
    ],
    [
      'babel-plugin-import',
      {
        libraryName: 'lucide-react',
        libraryDirectory: 'icons',
        camel2DashComponentName: false,
      },
      'lucide-react',
    ],
  ],
  
  // Webpack resolve configuration for better tree shaking
  resolve: {
    // Use ES modules when available
    mainFields: ['es2015', 'module', 'main'],
    // Resolve to source when possible
    aliasFields: ['browser', 'browser:module'],
    // Extensions in order of preference
    extensions: ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json'],
  },
});

/**
 * Analyze and optimize specific library imports
 */
export const createLibraryOptimizationConfig = () => ({
  libraries: [
    {
      name: 'lodash',
      optimization: {
        // Use lodash-es for better tree shaking
        alias: 'lodash-es',
        // Import only used functions
        importStrategy: 'named',
        // Babel transform
        babelPlugin: ['lodash', { id: ['lodash'] }],
      },
    },
    {
      name: 'date-fns',
      optimization: {
        // Import only used functions
        importStrategy: 'named',
        // Use ESM build
        resolve: 'date-fns/esm',
        // No side effects
        sideEffects: false,
      },
    },
    {
      name: 'lucide-react',
      optimization: {
        // Import icons individually
        importStrategy: 'named',
        // Tree shake unused icons
        treeShake: true,
        // Use ESM build
        resolve: 'lucide-react/dist/esm',
      },
    },
    {
      name: '@radix-ui/react-icons',
      optimization: {
        // Import icons individually
        importStrategy: 'named',
        // Tree shake unused icons
        treeShake: true,
        // No side effects
        sideEffects: false,
      },
    },
    {
      name: 'recharts',
      optimization: {
        // Import only used components
        importStrategy: 'named',
        // Some components have side effects
        sideEffects: ['recharts/es6/cartesian/ReferenceLine'],
        // Use ESM build when available
        resolve: 'recharts/es6',
      },
    },
  ],
});

/**
 * Create module federation tree shaking config
 */
export const createModuleFederationTreeShaking = () => ({
  // Shared modules configuration
  shared: {
    react: {
      singleton: true,
      eager: false,
      // Only load what's needed
      import: 'react/index',
      shareKey: 'react',
      shareScope: 'default',
      version: '^18.0.0',
    },
    'react-dom': {
      singleton: true,
      eager: false,
      import: 'react-dom/client',
      shareKey: 'react-dom',
      shareScope: 'default',
      version: '^18.0.0',
    },
    '@dotmac/primitives': {
      singleton: true,
      eager: false,
      // Tree shake primitives
      import: false, // Don't auto-import, let tree shaking work
      shareKey: '@dotmac/primitives',
      shareScope: 'default',
    },
  },
});

/**
 * Custom tree shaking analyzer
 */
export const createTreeShakingAnalyzer = () => ({
  analyze: (compilation: any) => {
    const unusedExports = new Map<string, string[]>();
    const sideEffectModules = new Set<string>();
    
    // Analyze modules for unused exports
    compilation.modules.forEach((module: any) => {
      if (module.buildInfo?.exportsType === 'namespace') {
        const usedExports = module.usedExports;
        const providedExports = module.buildMeta?.providedExports;
        
        if (providedExports && usedExports) {
          const unused = providedExports.filter((exp: string) => !usedExports.has(exp));
          if (unused.length > 0) {
            unusedExports.set(module.identifier(), unused);
          }
        }
      }
      
      // Check for side effects
      if (module.factoryMeta?.sideEffectFree === false) {
        sideEffectModules.add(module.identifier());
      }
    });
    
    return {
      unusedExports,
      sideEffectModules,
      recommendations: generateOptimizationRecommendations(unusedExports, sideEffectModules),
    };
  },
});

/**
 * Generate optimization recommendations
 */
const generateOptimizationRecommendations = (
  unusedExports: Map<string, string[]>,
  sideEffectModules: Set<string>
) => {
  const recommendations: string[] = [];
  
  if (unusedExports.size > 0) {
    recommendations.push(
      `Found ${unusedExports.size} modules with unused exports. Consider using named imports.`
    );
  }
  
  if (sideEffectModules.size > 0) {
    recommendations.push(
      `Found ${sideEffectModules.size} modules with side effects. Review if they can be marked as side-effect free.`
    );
  }
  
  return recommendations;
};