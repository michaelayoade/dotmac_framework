/**
 * Advanced Bundle Analysis and Monitoring
 * Comprehensive bundle analysis, size tracking, and performance monitoring
 */

import { BundleAnalyzerPlugin } from 'webpack-bundle-analyzer';
import { gzipSize } from 'gzip-size';
import { brotliSize } from 'brotli-size';
import filesize from 'filesize';
import chalk from 'chalk';
import fs from 'fs';
import path from 'path';

export interface BundleAnalysisOptions {
  enabled: boolean;
  mode: 'server' | 'static' | 'json' | 'disabled';
  openAnalyzer: boolean;
  reportPath: string;
  generateStats: boolean;
  sizeLimits?: BundleSizeLimits;
  compressionAnalysis?: boolean;
  historicalTracking?: boolean;
}

export interface BundleSizeLimits {
  maxBundleSize: number;
  maxChunkSize: number;
  maxAssetSize: number;
  budgets: BudgetConfig[];
}

export interface BudgetConfig {
  type: 'bundle' | 'initial' | 'allScript' | 'all' | 'anyComponentStyle' | 'anyScript' | 'any';
  name?: string;
  baseline?: number;
  maximumWarning: number;
  maximumError: number;
}

export interface BundleStats {
  totalSize: number;
  compressedSize: {
    gzip: number;
    brotli: number;
  };
  chunks: ChunkInfo[];
  assets: AssetInfo[];
  modules: ModuleInfo[];
  timestamp: string;
  buildTime: number;
}

export interface ChunkInfo {
  name: string;
  size: number;
  files: string[];
  modules: string[];
  parents: string[];
  children: string[];
}

export interface AssetInfo {
  name: string;
  size: number;
  chunks: string[];
  emitted: boolean;
  type: 'js' | 'css' | 'html' | 'other';
}

export interface ModuleInfo {
  name: string;
  size: number;
  chunks: string[];
  reasons: string[];
  depth: number;
}

/**
 * Create bundle analyzer plugin with advanced configuration
 */
export const createBundleAnalyzer = (options: BundleAnalysisOptions) => {
  if (!options.enabled) return null;
  
  return new BundleAnalyzerPlugin({
    analyzerMode: options.mode === 'disabled' ? 'disabled' : options.mode,
    analyzerPort: 'auto',
    reportFilename: path.join(options.reportPath, 'bundle-report.html'),
    openAnalyzer: options.openAnalyzer && options.mode === 'server',
    generateStatsFile: options.generateStats,
    statsFilename: path.join(options.reportPath, 'bundle-stats.json'),
    logLevel: 'info',
    statsOptions: {
      source: false,
      modules: true,
      chunks: true,
      chunkModules: true,
      chunkOrigins: true,
      assets: true,
      assetsSort: 'size',
      chunksSort: 'size',
      modulesSort: 'size',
      reasons: true,
      usedExports: true,
      providedExports: true,
    },
  });
};

/**
 * Advanced bundle analysis class
 */
export class BundleAnalyzer {
  private options: BundleAnalysisOptions;
  private history: BundleStats[] = [];
  
  constructor(options: BundleAnalysisOptions) {
    this.options = options;
    
    if (options.historicalTracking) {
      this.loadHistory();
    }
  }
  
  /**
   * Analyze webpack compilation stats
   */
  async analyzeStats(stats: any): Promise<BundleStats> {
    const compilation = stats.compilation;
    const chunks = this.extractChunkInfo(compilation.chunks);
    const assets = this.extractAssetInfo(compilation.assets);
    const modules = this.extractModuleInfo(compilation.modules);
    
    const totalSize = this.calculateTotalSize(assets);
    const compressedSize = await this.calculateCompressedSizes(assets);
    
    const bundleStats: BundleStats = {
      totalSize,
      compressedSize,
      chunks,
      assets,
      modules,
      timestamp: new Date().toISOString(),
      buildTime: stats.endTime - stats.startTime,
    };
    
    if (this.options.historicalTracking) {
      this.addToHistory(bundleStats);
    }
    
    await this.generateReports(bundleStats);
    this.checkSizeLimits(bundleStats);
    
    return bundleStats;
  }
  
  /**
   * Extract chunk information
   */
  private extractChunkInfo(chunks: any[]): ChunkInfo[] {
    return Array.from(chunks).map((chunk: any) => ({
      name: chunk.name || chunk.id,
      size: chunk.size(),
      files: Array.from(chunk.files),
      modules: Array.from(chunk.modulesIterable).map((m: any) => m.identifier()),
      parents: Array.from(chunk.parents).map((p: any) => p.name || p.id),
      children: Array.from(chunk.children).map((c: any) => c.name || c.id),
    }));
  }
  
  /**
   * Extract asset information
   */
  private extractAssetInfo(assets: Map<string, any>): AssetInfo[] {
    return Array.from(assets.entries()).map(([name, asset]) => ({
      name,
      size: asset.size(),
      chunks: asset.chunks || [],
      emitted: asset.emitted,
      type: this.getAssetType(name),
    }));
  }
  
  /**
   * Extract module information
   */
  private extractModuleInfo(modules: any[]): ModuleInfo[] {
    return Array.from(modules)
      .filter((module: any) => module.size !== undefined)
      .map((module: any) => ({
        name: module.identifier(),
        size: module.size(),
        chunks: Array.from(module.chunksIterable).map((c: any) => c.name || c.id),
        reasons: module.reasons.map((r: any) => r.module?.identifier() || 'unknown'),
        depth: module.depth || 0,
      }));
  }
  
  /**
   * Calculate total bundle size
   */
  private calculateTotalSize(assets: AssetInfo[]): number {
    return assets
      .filter(asset => asset.type === 'js' || asset.type === 'css')
      .reduce((total, asset) => total + asset.size, 0);
  }
  
  /**
   * Calculate compressed sizes
   */
  private async calculateCompressedSizes(assets: AssetInfo[]): Promise<{ gzip: number; brotli: number }> {
    if (!this.options.compressionAnalysis) {
      return { gzip: 0, brotli: 0 };
    }
    
    const jsAssets = assets.filter(asset => asset.type === 'js');
    const cssAssets = assets.filter(asset => asset.type === 'css');
    
    let totalGzipSize = 0;
    let totalBrotliSize = 0;
    
    for (const asset of [...jsAssets, ...cssAssets]) {
      try {
        const assetPath = path.join(process.cwd(), '.next', asset.name);
        if (fs.existsSync(assetPath)) {
          const content = fs.readFileSync(assetPath);
          totalGzipSize += await gzipSize(content);
          totalBrotliSize += await brotliSize(content);
        }
      } catch (error) {
        console.warn(`Could not analyze compression for ${asset.name}:`, error);
      }
    }
    
    return {
      gzip: totalGzipSize,
      brotli: totalBrotliSize,
    };
  }
  
  /**
   * Determine asset type from filename
   */
  private getAssetType(filename: string): AssetInfo['type'] {
    const extension = path.extname(filename);
    switch (extension) {
      case '.js':
      case '.mjs':
        return 'js';
      case '.css':
        return 'css';
      case '.html':
        return 'html';
      default:
        return 'other';
    }
  }
  
  /**
   * Check bundle size limits and budgets
   */
  private checkSizeLimits(stats: BundleStats): void {
    if (!this.options.sizeLimits) return;
    
    const { maxBundleSize, maxChunkSize, maxAssetSize, budgets } = this.options.sizeLimits;
    const warnings: string[] = [];
    const errors: string[] = [];
    
    // Check total bundle size
    if (stats.totalSize > maxBundleSize) {
      errors.push(`Total bundle size (${filesize(stats.totalSize)}) exceeds limit (${filesize(maxBundleSize)})`);
    }
    
    // Check individual chunk sizes
    stats.chunks.forEach(chunk => {
      if (chunk.size > maxChunkSize) {
        warnings.push(`Chunk "${chunk.name}" (${filesize(chunk.size)}) exceeds limit (${filesize(maxChunkSize)})`);
      }
    });
    
    // Check individual asset sizes
    stats.assets.forEach(asset => {
      if (asset.size > maxAssetSize) {
        warnings.push(`Asset "${asset.name}" (${filesize(asset.size)}) exceeds limit (${filesize(maxAssetSize)})`);
      }
    });
    
    // Check budget configurations
    budgets.forEach(budget => {
      const budgetSize = this.calculateBudgetSize(stats, budget);
      
      if (budgetSize > budget.maximumError) {
        errors.push(`Budget "${budget.type}" (${filesize(budgetSize)}) exceeds error threshold (${filesize(budget.maximumError)})`);
      } else if (budgetSize > budget.maximumWarning) {
        warnings.push(`Budget "${budget.type}" (${filesize(budgetSize)}) exceeds warning threshold (${filesize(budget.maximumWarning)})`);
      }
    });
    
    // Log warnings and errors
    if (warnings.length > 0) {
      console.warn(chalk.yellow('Bundle size warnings:'));
      warnings.forEach(warning => console.warn(chalk.yellow(`  • ${warning}`)));
    }
    
    if (errors.length > 0) {
      console.error(chalk.red('Bundle size errors:'));
      errors.forEach(error => console.error(chalk.red(`  • ${error}`)));
      
      if (process.env.CI) {
        process.exit(1);
      }
    }
  }
  
  /**
   * Calculate size for specific budget
   */
  private calculateBudgetSize(stats: BundleStats, budget: BudgetConfig): number {
    switch (budget.type) {
      case 'bundle':
        return stats.totalSize;
      case 'initial':
        return stats.chunks
          .filter(chunk => chunk.parents.length === 0)
          .reduce((total, chunk) => total + chunk.size, 0);
      case 'allScript':
        return stats.assets
          .filter(asset => asset.type === 'js')
          .reduce((total, asset) => total + asset.size, 0);
      case 'all':
        return stats.assets.reduce((total, asset) => total + asset.size, 0);
      case 'anyScript':
        return Math.max(...stats.assets
          .filter(asset => asset.type === 'js')
          .map(asset => asset.size));
      case 'any':
        return Math.max(...stats.assets.map(asset => asset.size));
      default:
        return stats.totalSize;
    }
  }
  
  /**
   * Generate analysis reports
   */
  private async generateReports(stats: BundleStats): Promise<void> {
    const reportsDir = this.options.reportPath;
    
    // Ensure reports directory exists
    if (!fs.existsSync(reportsDir)) {
      fs.mkdirSync(reportsDir, { recursive: true });
    }
    
    // Generate JSON report
    await this.generateJSONReport(stats, path.join(reportsDir, 'bundle-analysis.json'));
    
    // Generate human-readable report
    await this.generateTextReport(stats, path.join(reportsDir, 'bundle-analysis.txt'));
    
    // Generate CSV report for trend analysis
    if (this.options.historicalTracking) {
      await this.generateTrendReport(path.join(reportsDir, 'bundle-trend.csv'));
    }
    
    // Generate size comparison report
    if (this.history.length > 1) {
      await this.generateComparisonReport(stats, path.join(reportsDir, 'bundle-comparison.json'));
    }
  }
  
  /**
   * Generate JSON report
   */
  private async generateJSONReport(stats: BundleStats, filepath: string): Promise<void> {
    fs.writeFileSync(filepath, JSON.stringify(stats, null, 2));
  }
  
  /**
   * Generate human-readable text report
   */
  private async generateTextReport(stats: BundleStats, filepath: string): Promise<void> {
    const report = [
      '# Bundle Analysis Report',
      `Generated: ${stats.timestamp}`,
      `Build Time: ${stats.buildTime}ms`,
      '',
      '## Bundle Size',
      `Total Size: ${filesize(stats.totalSize)}`,
      `Gzipped: ${filesize(stats.compressedSize.gzip)}`,
      `Brotli: ${filesize(stats.compressedSize.brotli)}`,
      '',
      '## Chunks',
      ...stats.chunks
        .sort((a, b) => b.size - a.size)
        .slice(0, 10)
        .map(chunk => `${chunk.name}: ${filesize(chunk.size)}`),
      '',
      '## Assets',
      ...stats.assets
        .sort((a, b) => b.size - a.size)
        .slice(0, 20)
        .map(asset => `${asset.name}: ${filesize(asset.size)}`),
      '',
      '## Top Modules',
      ...stats.modules
        .sort((a, b) => b.size - a.size)
        .slice(0, 20)
        .map(module => `${path.basename(module.name)}: ${filesize(module.size)}`),
    ].join('\n');
    
    fs.writeFileSync(filepath, report);
  }
  
  /**
   * Generate trend report
   */
  private async generateTrendReport(filepath: string): Promise<void> {
    if (this.history.length === 0) return;
    
    const headers = 'Timestamp,Total Size,Gzip Size,Brotli Size,Build Time,Chunks,Assets,Modules';
    const rows = this.history.map(stats => [
      stats.timestamp,
      stats.totalSize,
      stats.compressedSize.gzip,
      stats.compressedSize.brotli,
      stats.buildTime,
      stats.chunks.length,
      stats.assets.length,
      stats.modules.length,
    ].join(','));
    
    const csv = [headers, ...rows].join('\n');
    fs.writeFileSync(filepath, csv);
  }
  
  /**
   * Generate comparison report
   */
  private async generateComparisonReport(currentStats: BundleStats, filepath: string): Promise<void> {
    const previousStats = this.history[this.history.length - 2];
    if (!previousStats) return;
    
    const comparison = {
      current: currentStats,
      previous: previousStats,
      changes: {
        totalSize: currentStats.totalSize - previousStats.totalSize,
        gzipSize: currentStats.compressedSize.gzip - previousStats.compressedSize.gzip,
        brotliSize: currentStats.compressedSize.brotli - previousStats.compressedSize.brotli,
        chunkCount: currentStats.chunks.length - previousStats.chunks.length,
        assetCount: currentStats.assets.length - previousStats.assets.length,
        moduleCount: currentStats.modules.length - previousStats.modules.length,
      },
    };
    
    fs.writeFileSync(filepath, JSON.stringify(comparison, null, 2));
  }
  
  /**
   * Load historical data
   */
  private loadHistory(): void {
    const historyPath = path.join(this.options.reportPath, 'bundle-history.json');
    
    if (fs.existsSync(historyPath)) {
      try {
        const historyData = fs.readFileSync(historyPath, 'utf8');
        this.history = JSON.parse(historyData);
      } catch (error) {
        console.warn('Could not load bundle history:', error);
        this.history = [];
      }
    }
  }
  
  /**
   * Add stats to history
   */
  private addToHistory(stats: BundleStats): void {
    this.history.push(stats);
    
    // Keep only last 50 builds
    if (this.history.length > 50) {
      this.history = this.history.slice(-50);
    }
    
    // Save history
    const historyPath = path.join(this.options.reportPath, 'bundle-history.json');
    fs.writeFileSync(historyPath, JSON.stringify(this.history, null, 2));
  }
}

/**
 * Create bundle size monitor
 */
export const createBundleSizeMonitor = (options: BundleAnalysisOptions) => {
  const analyzer = new BundleAnalyzer(options);
  
  return {
    // Webpack plugin
    plugin: {
      apply: (compiler: any) => {
        compiler.hooks.done.tapAsync('BundleSizeMonitor', async (stats: any, callback: Function) => {
          try {
            await analyzer.analyzeStats(stats);
            callback();
          } catch (error) {
            console.error('Bundle analysis failed:', error);
            callback();
          }
        });
      },
    },
    
    // Standalone analyzer
    analyzer,
  };
};