/**
 * DotMac Bundle Optimizer
 * Advanced bundle optimization utilities for Next.js applications
 */

export * from './code-splitting';
export * from './tree-shaking';
export * from './dynamic-imports';
export * from './bundle-analyzer';
export * from './performance-monitor';
export * from './size-tracker';

// Main optimization factory
export { createNextOptimizer } from './optimizer';

// Utility functions
export { 
  analyzeBundle,
  generateSizeReport,
  checkSizeLimits,
  optimizeChunks 
} from './utils';