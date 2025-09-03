/**
 * Bundle Optimizer Utilities
 * Helper functions for bundle analysis and optimization
 */

import fs from 'fs';
import path from 'path';
import { gzipSize } from 'gzip-size';
import { brotliSize } from 'brotli-size';
import filesize from 'filesize';
import type { BundleStats } from './bundle-analyzer';

export interface BundleAnalysisResult {
  totalSize: number;
  gzippedSize: number;
  brotliSize: number;
  chunks: ChunkAnalysis[];
  recommendations: string[];
}

export interface ChunkAnalysis {
  name: string;
  size: number;
  gzippedSize: number;
  modules: ModuleAnalysis[];
  duplicates: string[];
}

export interface ModuleAnalysis {
  name: string;
  size: number;
  reasons: string[];
  chunks: string[];
}

/**
 * Analyze bundle from webpack stats
 */
export const analyzeBundle = async (statsPath: string): Promise<BundleAnalysisResult> => {
  if (!fs.existsSync(statsPath)) {
    throw new Error(`Stats file not found: ${statsPath}`);
  }
  
  const stats = JSON.parse(fs.readFileSync(statsPath, 'utf8'));
  
  const chunks = await Promise.all(
    stats.chunks.map(async (chunk: any) => analyzeChunk(chunk, stats))
  );
  
  const totalSize = chunks.reduce((sum, chunk) => sum + chunk.size, 0);
  const gzippedSize = chunks.reduce((sum, chunk) => sum + chunk.gzippedSize, 0);
  
  // Calculate brotli size (approximate from gzip)
  const brotliSizeApprox = Math.round(gzippedSize * 0.85);
  
  const recommendations = generateRecommendations(chunks);
  
  return {
    totalSize,
    gzippedSize,
    brotliSize: brotliSizeApprox,
    chunks,
    recommendations,
  };
};

/**
 * Analyze individual chunk
 */
const analyzeChunk = async (chunk: any, stats: any): Promise<ChunkAnalysis> => {
  const modules = chunk.modules.map((module: any) => ({
    name: module.name,
    size: module.size,
    reasons: module.reasons.map((r: any) => r.moduleName),
    chunks: module.chunks,
  }));
  
  // Find duplicate modules across chunks
  const duplicates = findDuplicateModules(chunk, stats);
  
  // Estimate gzipped size (rough approximation)
  const gzippedSize = Math.round(chunk.size * 0.3);
  
  return {
    name: chunk.names[0] || chunk.id,
    size: chunk.size,
    gzippedSize,
    modules,
    duplicates,
  };
};

/**
 * Find duplicate modules across chunks
 */
const findDuplicateModules = (chunk: any, stats: any): string[] => {
  const chunkModules = new Set(chunk.modules.map((m: any) => m.name));
  const duplicates: string[] = [];
  
  stats.chunks.forEach((otherChunk: any) => {
    if (otherChunk.id === chunk.id) return;
    
    otherChunk.modules.forEach((module: any) => {
      if (chunkModules.has(module.name)) {
        duplicates.push(module.name);
      }
    });
  });
  
  return [...new Set(duplicates)];
};

/**
 * Generate optimization recommendations
 */
const generateRecommendations = (chunks: ChunkAnalysis[]): string[] => {
  const recommendations: string[] = [];
  
  // Check for large chunks
  const largeChunks = chunks.filter(chunk => chunk.size > 250000);
  if (largeChunks.length > 0) {
    recommendations.push(
      `Found ${largeChunks.length} large chunks (>250KB). Consider code splitting: ${
        largeChunks.map(c => c.name).join(', ')
      }`
    );
  }
  
  // Check for duplicate modules
  const chunksWithDuplicates = chunks.filter(chunk => chunk.duplicates.length > 0);
  if (chunksWithDuplicates.length > 0) {
    recommendations.push(
      `Found duplicate modules in ${chunksWithDuplicates.length} chunks. Consider extracting common modules.`
    );
  }
  
  // Check for large individual modules
  const allModules = chunks.flatMap(chunk => chunk.modules);
  const largeModules = allModules.filter(module => module.size > 100000);
  if (largeModules.length > 0) {
    recommendations.push(
      `Found ${largeModules.length} large modules (>100KB). Consider dynamic imports: ${
        largeModules.slice(0, 3).map(m => path.basename(m.name)).join(', ')
      }`
    );
  }
  
  // Check for many small chunks
  const smallChunks = chunks.filter(chunk => chunk.size < 10000);
  if (smallChunks.length > 10) {
    recommendations.push(
      `Found ${smallChunks.length} small chunks (<10KB). Consider merging some chunks.`
    );
  }
  
  return recommendations;
};

/**
 * Generate size report
 */
export const generateSizeReport = (analysis: BundleAnalysisResult): string => {
  const report = [
    '# Bundle Size Report',
    '',
    '## Summary',
    `Total Size: ${filesize(analysis.totalSize)}`,
    `Gzipped: ${filesize(analysis.gzippedSize)} (${Math.round((analysis.gzippedSize / analysis.totalSize) * 100)}%)`,
    `Brotli: ${filesize(analysis.brotliSize)} (${Math.round((analysis.brotliSize / analysis.totalSize) * 100)}%)`,
    '',
    '## Chunks',
    ...analysis.chunks
      .sort((a, b) => b.size - a.size)
      .map(chunk => `- ${chunk.name}: ${filesize(chunk.size)} (gzipped: ${filesize(chunk.gzippedSize)})`),
    '',
    '## Recommendations',
    ...analysis.recommendations.map(rec => `- ${rec}`),
    '',
    '## Largest Modules',
    ...analysis.chunks
      .flatMap(chunk => chunk.modules)
      .sort((a, b) => b.size - a.size)
      .slice(0, 10)
      .map(module => `- ${path.basename(module.name)}: ${filesize(module.size)}`),
  ];
  
  return report.join('\n');
};

/**
 * Check if bundle sizes are within limits
 */
export const checkSizeLimits = (
  analysis: BundleAnalysisResult,
  limits: {
    maxTotalSize?: number;
    maxChunkSize?: number;
    maxGzippedSize?: number;
  }
): { passed: boolean; violations: string[] } => {
  const violations: string[] = [];
  
  if (limits.maxTotalSize && analysis.totalSize > limits.maxTotalSize) {
    violations.push(
      `Total bundle size (${filesize(analysis.totalSize)}) exceeds limit (${filesize(limits.maxTotalSize)})`
    );
  }
  
  if (limits.maxGzippedSize && analysis.gzippedSize > limits.maxGzippedSize) {
    violations.push(
      `Gzipped size (${filesize(analysis.gzippedSize)}) exceeds limit (${filesize(limits.maxGzippedSize)})`
    );
  }
  
  if (limits.maxChunkSize) {
    const largeChunks = analysis.chunks.filter(chunk => chunk.size > limits.maxChunkSize!);
    if (largeChunks.length > 0) {
      violations.push(
        `${largeChunks.length} chunks exceed size limit (${filesize(limits.maxChunkSize)}): ${
          largeChunks.map(c => `${c.name} (${filesize(c.size)})`).join(', ')
        }`
      );
    }
  }
  
  return {
    passed: violations.length === 0,
    violations,
  };
};

/**
 * Optimize chunk configuration based on analysis
 */
export const optimizeChunks = (analysis: BundleAnalysisResult): any => {
  const optimization: any = {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {},
    },
  };
  
  // Extract common modules into vendor chunks
  const commonModules = findCommonModules(analysis.chunks);
  if (commonModules.length > 0) {
    optimization.splitChunks.cacheGroups.vendor = {
      test: new RegExp(commonModules.join('|')),
      name: 'vendor',
      chunks: 'all',
      priority: 10,
    };
  }
  
  // Create specific chunks for large modules
  const largeModules = analysis.chunks
    .flatMap(chunk => chunk.modules)
    .filter(module => module.size > 50000)
    .map(module => module.name);
  
  largeModules.forEach((moduleName, index) => {
    const chunkName = `large-module-${index}`;
    optimization.splitChunks.cacheGroups[chunkName] = {
      test: new RegExp(moduleName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')),
      name: chunkName,
      chunks: 'async',
      priority: 20,
    };
  });
  
  return optimization;
};

/**
 * Find modules common across chunks
 */
const findCommonModules = (chunks: ChunkAnalysis[]): string[] => {
  const moduleChunkCount: Record<string, number> = {};
  
  chunks.forEach(chunk => {
    chunk.modules.forEach(module => {
      moduleChunkCount[module.name] = (moduleChunkCount[module.name] || 0) + 1;
    });
  });
  
  // Return modules that appear in more than one chunk
  return Object.entries(moduleChunkCount)
    .filter(([, count]) => count > 1)
    .map(([moduleName]) => moduleName);
};

/**
 * Calculate actual file sizes with compression
 */
export const calculateFileSizes = async (filePaths: string[]): Promise<{
  path: string;
  size: number;
  gzippedSize: number;
  brotliSize: number;
}[]> => {
  const results = await Promise.all(
    filePaths.map(async (filePath) => {
      if (!fs.existsSync(filePath)) {
        return {
          path: filePath,
          size: 0,
          gzippedSize: 0,
          brotliSize: 0,
        };
      }
      
      const content = fs.readFileSync(filePath);
      const size = content.length;
      const gzippedSize = await gzipSize(content);
      const brotliSizeValue = await brotliSize(content);
      
      return {
        path: filePath,
        size,
        gzippedSize,
        brotliSize: brotliSizeValue,
      };
    })
  );
  
  return results;
};

/**
 * Compare bundle sizes between builds
 */
export const compareBundles = (
  current: BundleAnalysisResult,
  previous: BundleAnalysisResult
): {
  totalSizeChange: number;
  gzippedSizeChange: number;
  chunkChanges: Array<{
    name: string;
    sizeChange: number;
    status: 'added' | 'removed' | 'changed' | 'unchanged';
  }>;
} => {
  const totalSizeChange = current.totalSize - previous.totalSize;
  const gzippedSizeChange = current.gzippedSize - previous.gzippedSize;
  
  const currentChunks = new Map(current.chunks.map(c => [c.name, c]));
  const previousChunks = new Map(previous.chunks.map(c => [c.name, c]));
  
  const chunkChanges: Array<{
    name: string;
    sizeChange: number;
    status: 'added' | 'removed' | 'changed' | 'unchanged';
  }> = [];
  
  // Check current chunks
  currentChunks.forEach((currentChunk, name) => {
    const previousChunk = previousChunks.get(name);
    
    if (!previousChunk) {
      chunkChanges.push({
        name,
        sizeChange: currentChunk.size,
        status: 'added',
      });
    } else {
      const sizeChange = currentChunk.size - previousChunk.size;
      chunkChanges.push({
        name,
        sizeChange,
        status: sizeChange === 0 ? 'unchanged' : 'changed',
      });
    }
  });
  
  // Check for removed chunks
  previousChunks.forEach((previousChunk, name) => {
    if (!currentChunks.has(name)) {
      chunkChanges.push({
        name,
        sizeChange: -previousChunk.size,
        status: 'removed',
      });
    }
  });
  
  return {
    totalSizeChange,
    gzippedSizeChange,
    chunkChanges,
  };
};

/**
 * Generate bundle comparison report
 */
export const generateComparisonReport = (comparison: ReturnType<typeof compareBundles>): string => {
  const formatSizeChange = (change: number) => {
    const sign = change > 0 ? '+' : '';
    return `${sign}${filesize(change)}`;
  };
  
  const report = [
    '# Bundle Comparison Report',
    '',
    '## Size Changes',
    `Total Size: ${formatSizeChange(comparison.totalSizeChange)}`,
    `Gzipped: ${formatSizeChange(comparison.gzippedSizeChange)}`,
    '',
    '## Chunk Changes',
  ];
  
  const addedChunks = comparison.chunkChanges.filter(c => c.status === 'added');
  const removedChunks = comparison.chunkChanges.filter(c => c.status === 'removed');
  const changedChunks = comparison.chunkChanges.filter(c => c.status === 'changed' && c.sizeChange !== 0);
  
  if (addedChunks.length > 0) {
    report.push('### Added Chunks');
    report.push(...addedChunks.map(c => `- ${c.name}: ${filesize(c.sizeChange)}`));
    report.push('');
  }
  
  if (removedChunks.length > 0) {
    report.push('### Removed Chunks');
    report.push(...removedChunks.map(c => `- ${c.name}: ${filesize(Math.abs(c.sizeChange))}`));
    report.push('');
  }
  
  if (changedChunks.length > 0) {
    report.push('### Changed Chunks');
    report.push(...changedChunks
      .sort((a, b) => Math.abs(b.sizeChange) - Math.abs(a.sizeChange))
      .map(c => `- ${c.name}: ${formatSizeChange(c.sizeChange)}`));
  }
  
  return report.join('\n');
};