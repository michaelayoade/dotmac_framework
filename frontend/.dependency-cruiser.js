/**
 * Dependency Cruiser Configuration for DotMac Frontend
 * Enforces import restrictions, detects circular dependencies, and validates architecture
 */

module.exports = {
  forbidden: [
    // Prevent circular dependencies
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular dependencies are not allowed',
      from: {},
      to: {
        circular: true,
      },
    },

    // Cross-team import restrictions
    {
      name: 'no-admin-in-customer',
      severity: 'error',
      comment: 'Customer portal cannot import from Admin portal',
      from: {
        path: '^isp-framework/customer/',
      },
      to: {
        path: '^isp-framework/admin/',
      },
    },
    {
      name: 'no-customer-in-admin',
      severity: 'error',
      comment: 'Admin portal cannot import from Customer portal',
      from: {
        path: '^isp-framework/admin/',
      },
      to: {
        path: '^isp-framework/customer/',
      },
    },
    {
      name: 'no-reseller-in-others',
      severity: 'error',
      comment: 'Other portals cannot import from Reseller portal',
      from: {
        pathNot: '^isp-framework/reseller/',
      },
      to: {
        path: '^isp-framework/reseller/',
      },
    },

    // Prevent direct database access from components
    {
      name: 'no-direct-db-access',
      severity: 'error',
      comment: 'Components cannot directly access database modules',
      from: {
        path: '(components|pages)/',
      },
      to: {
        path: '(database|db|prisma|sequelize|mongoose)/',
      },
    },

    // Enforce API layer usage
    {
      name: 'use-api-layer',
      severity: 'warn',
      comment: 'Components should use API layer instead of direct service calls',
      from: {
        path: '^(isp-framework|management-portal)/.*/src/components/',
      },
      to: {
        path: '^(isp-framework|management-portal)/.*/src/services/',
        pathNot: '^(isp-framework|management-portal)/.*/src/services/api/',
      },
    },

    // Prevent utils from importing components
    {
      name: 'utils-no-components',
      severity: 'error',
      comment: 'Utility functions should not import components',
      from: {
        path: '(utils|lib|helpers)/',
      },
      to: {
        path: 'components/',
      },
    },

    // Prevent shared components from importing app-specific code
    {
      name: 'shared-components-isolation',
      severity: 'error',
      comment: 'Shared components cannot import app-specific code',
      from: {
        path: '^packages/',
      },
      to: {
        path: '^(isp-framework|management-portal)/',
      },
    },

    // Prevent importing development dependencies in production code
    {
      name: 'no-dev-deps-in-prod',
      severity: 'error',
      comment: 'Production code cannot import development dependencies',
      from: {
        path: '^(isp-framework|management-portal|packages)/.*/src/',
        pathNot: '\\.(test|spec|stories)\\.[jt]sx?$',
      },
      to: {
        dependencyTypes: ['dev'],
      },
    },

    // Prevent test files from being imported in production
    {
      name: 'no-test-imports',
      severity: 'error',
      comment: 'Test files cannot be imported in production code',
      from: {
        pathNot: '\\.(test|spec)\\.([jt]sx?|mdx)$',
      },
      to: {
        path: '\\.(test|spec)\\.([jt]sx?|mdx)$',
      },
    },

    // Prevent importing internal Next.js modules
    {
      name: 'no-internal-nextjs',
      severity: 'error',
      comment: 'Cannot import internal Next.js modules',
      from: {},
      to: {
        path: '^next/dist/',
      },
    },

    // Prevent relative imports going up more than 2 levels
    {
      name: 'no-deep-relative-imports',
      severity: 'warn',
      comment: 'Avoid deep relative imports (more than 2 levels up)',
      from: {},
      to: {
        path: '^(\\.\\./){{3,}}',
      },
    },

    // Enforce TypeScript usage
    {
      name: 'prefer-typescript',
      severity: 'warn',
      comment: 'Prefer TypeScript files over JavaScript',
      from: {
        path: '\\.[jt]sx?$',
      },
      to: {
        path: '\\.jsx?$',
        pathNot: '(jest|webpack|babel)\\.config\\.js$',
      },
    },

    // Security restrictions
    {
      name: 'no-eval-imports',
      severity: 'error',
      comment: 'Cannot import modules that use eval()',
      from: {},
      to: {
        path: '(eval|vm|function-constructor)',
      },
    },

    // Performance restrictions
    {
      name: 'no-heavy-imports-in-components',
      severity: 'warn',
      comment: 'Avoid importing heavy libraries directly in components',
      from: {
        path: 'components/',
      },
      to: {
        path: '(lodash|moment|jquery|bootstrap)$',
      },
    },
  ],

  allowed: [
    // Allow imports within the same app
    {
      from: {
        path: '^(isp-framework|management-portal)/([^/]+)/',
      },
      to: {
        path: '^$1/$2/',
      },
    },

    // Allow shared package imports from apps
    {
      from: {
        path: '^(isp-framework|management-portal)/',
      },
      to: {
        path: '^packages/',
      },
    },

    // Allow Next.js framework imports
    {
      from: {},
      to: {
        path: '^next(/|$)',
      },
    },

    // Allow React and React-related imports
    {
      from: {},
      to: {
        path: '^react(-|/|$)',
      },
    },

    // Allow standard Node.js modules
    {
      from: {},
      to: {
        path: '^(path|fs|util|os|crypto|http|https)$',
      },
    },

    // Allow testing utilities in test files
    {
      from: {
        path: '\\.(test|spec)\\.[jt]sx?$',
      },
      to: {
        path: '^(@testing-library|jest|vitest|playwright)/',
      },
    },
  ],

  options: {
    doNotFollow: {
      path: 'node_modules',
    },

    includeOnly: {
      path: '^(isp-framework|management-portal|packages)/',
    },

    exclude: {
      path: [
        'node_modules',
        '\\.d\\.ts$',
        'coverage',
        'dist',
        '.next',
        'test-results',
        'playwright-report',
      ],
    },

    // Module systems to support
    moduleSystems: ['cjs', 'es6', 'amd'],

    // File extensions to analyze
    extensions: ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'],

    // Dependency types to include
    dependencyTypes: ['local', 'npm', 'npm-dev', 'npm-optional', 'npm-peer', 'npm-bundled'],

    // Enhanced reporting
    reporterOptions: {
      archi: {
        collapsePattern: '^(isp-framework|management-portal|packages)/[^/]+',
        theme: {
          graph: {
            splines: 'ortho',
          },
        },
      },
      dot: {
        theme: {
          graph: {
            bgcolor: 'transparent',
            splines: 'ortho',
          },
          modules: [
            {
              criteria: { source: '^isp-framework/admin' },
              attributes: { fillcolor: '#ffcccc', style: 'filled' },
            },
            {
              criteria: { source: '^isp-framework/customer' },
              attributes: { fillcolor: '#ccffcc', style: 'filled' },
            },
            {
              criteria: { source: '^isp-framework/reseller' },
              attributes: { fillcolor: '#ccccff', style: 'filled' },
            },
            {
              criteria: { source: '^management-portal' },
              attributes: { fillcolor: '#ffccff', style: 'filled' },
            },
            {
              criteria: { source: '^packages' },
              attributes: { fillcolor: '#ffffcc', style: 'filled' },
            },
          ],
        },
      },
    },

    // Progress indication
    progress: {
      type: 'cli-feedback',
    },
  },
};
