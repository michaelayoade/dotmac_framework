# Bundle Optimizer Package

Comprehensive bundle optimization system for the DotMac Framework frontend applications.

## Features

- **Code Splitting**: Advanced chunking strategies (routes, components, features, hybrid)
- **Tree Shaking**: Dead code elimination with side effects configuration
- **Dynamic Imports**: Smart lazy loading with preload strategies
- **Bundle Analysis**: Comprehensive size tracking and reporting
- **Performance Budgets**: Configurable size limits with CI/CD enforcement
- **Historical Tracking**: Bundle size trends over time

## Installation

```bash
# Install dependencies
pnpm install

# Build the package
pnpm run build
```

## Usage

### Next.js Integration

```typescript
// next.config.js
const { createNextOptimizer } = require('@dotmac/bundle-optimizer');

const optimizer = createNextOptimizer({
  isProduction: process.env.NODE_ENV === 'production',
  codeSplitting: {
    strategy: 'hybrid',
    chunkSizeThresholds: {
      minSize: 20000,
      maxSize: 244000,
    },
  },
  treeShaking: {
    packages: [
      { name: 'lodash-es', sideEffects: false },
      { name: '@dotmac/primitives', sideEffects: false },
    ],
    aggressiveMode: true,
  },
  performanceBudgets: {
    maxBundleSize: 400000,  // 400KB
    maxChunkSize: 200000,   // 200KB
    maxAssetSize: 200000,   // 200KB
  },
});

module.exports = optimizer.withOptimization({
  // Your existing Next.js config
});
```

### Bundle Analysis

```typescript
import { analyzeBundle, generateSizeReport } from '@dotmac/bundle-optimizer/utils';

// Analyze webpack stats
const analysis = await analyzeBundle('./path/to/stats.json');

// Generate human-readable report
const report = generateSizeReport(analysis);
console.log(report);

// Check size limits
const { passed, violations } = checkSizeLimits(analysis, {
  maxTotalSize: 500000,
  maxChunkSize: 200000,
});
```

### Dynamic Components

```typescript
import { createDynamicComponent, withDynamicLoading } from '@dotmac/bundle-optimizer/dynamic-imports';

// Basic dynamic component
const LazyComponent = createDynamicComponent({
  name: 'MyComponent',
  path: './MyComponent',
  preload: 'viewport',
});

// Advanced with error boundary
const AdvancedComponent = withDynamicLoading({
  name: 'AdvancedComponent',
  path: './AdvancedComponent',
  preload: 'interaction',
  fallback: LoadingSpinner,
  errorBoundary: ErrorBoundary,
});
```

## Configuration Presets

### Production Preset
```typescript
const optimizer = createNextOptimizer(optimizerPresets.production());
```

- Aggressive code splitting
- Maximum tree shaking
- Strict performance budgets
- Compression analysis enabled

### Development Preset
```typescript
const optimizer = createNextOptimizer(optimizerPresets.development());
```

- Faster builds
- Larger chunk sizes
- Bundle analysis on demand
- Relaxed budgets

### Staging Preset
```typescript
const optimizer = createNextOptimizer(optimizerPresets.staging());
```

- Balanced optimization
- Bundle analysis enabled
- Moderate performance budgets
- Historical tracking

## Bundle Size Monitoring

The package includes a comprehensive monitoring script for CI/CD integration:

```bash
# Monitor all applications
node scripts/bundle-size-monitor.js --all-apps

# Monitor specific application
node scripts/bundle-size-monitor.js --app=customer

# Generate markdown report
node scripts/bundle-size-monitor.js --generate-markdown

# CI mode (fails on budget exceeded)
node scripts/bundle-size-monitor.js --ci
```

### Size Budgets

Default budgets are configured per application:

```javascript
const budgets = {
  'customer': {
    maxBundleSize: 400000,    // 400KB
    maxChunkSize: 200000,     // 200KB
    maxAssetSize: 200000,     // 200KB
  },
  'admin': {
    maxBundleSize: 500000,    // 500KB
    maxChunkSize: 250000,     // 250KB
    maxAssetSize: 250000,     // 250KB
  },
};
```

## CI/CD Integration

The bundle optimizer integrates with GitHub Actions to enforce size budgets:

```yaml
- name: Bundle Size Gate
  run: |
    node scripts/bundle-size-monitor.js --app=${{ matrix.app }} --ci
  env:
    CI: true
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

This will:
- Analyze bundle sizes after build
- Compare against configured budgets
- Generate reports and PR comments
- Fail the build if budgets are exceeded

## Architecture

```
bundle-optimizer/
├── src/
│   ├── optimizer.ts        # Main optimizer factory
│   ├── code-splitting.ts   # Code splitting strategies
│   ├── tree-shaking.ts     # Tree shaking configuration
│   ├── dynamic-imports.ts  # Dynamic import utilities
│   ├── bundle-analyzer.ts  # Bundle analysis and monitoring
│   └── utils.ts           # Analysis utilities
├── configs/
│   └── next-bundle-optimizer.js  # Next.js configuration
└── scripts/
    └── bundle-size-monitor.js    # CLI monitoring tool
```

## Optimization Strategies

### 1. Code Splitting

- **Route-based**: Split by pages/routes
- **Component-based**: Split large components
- **Feature-based**: Split by application features
- **Hybrid**: Intelligent combination of strategies

### 2. Tree Shaking

- Dead code elimination
- Side effects configuration
- Package-specific optimization
- Import path rewriting

### 3. Dynamic Imports

- Preload strategies: critical, interaction, viewport, idle
- Error boundaries and fallbacks
- Smart loading based on device capabilities
- Intersection Observer integration

### 4. Bundle Analysis

- Size tracking and reporting
- Compression analysis (gzip, brotli)
- Historical trend analysis
- Performance regression detection

## Performance Impact

Expected improvements with full optimization:

- **Bundle Size**: 30-50% reduction
- **First Load**: 20-40% improvement
- **Code Coverage**: 15-25% increase
- **Cache Efficiency**: 40-60% improvement

## Monitoring and Alerts

The system provides comprehensive monitoring:

- Real-time bundle size tracking
- Historical size trends
- Performance budget alerts
- PR comment integration
- CI/CD gate enforcement

## Contributing

1. Follow existing code patterns
2. Add tests for new features
3. Update documentation
4. Ensure performance budgets pass
5. Add TypeScript types for APIs