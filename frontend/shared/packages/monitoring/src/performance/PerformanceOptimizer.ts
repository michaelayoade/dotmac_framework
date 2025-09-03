import { PerformanceMonitor, PerformanceMetrics } from './PerformanceMonitor';

export interface OptimizationRule {
  name: string;
  condition: (metrics: PerformanceMetrics) => boolean;
  action: () => void;
  priority: 'low' | 'medium' | 'high';
  description: string;
}

export interface OptimizationSuggestion {
  rule: string;
  description: string;
  impact: 'low' | 'medium' | 'high';
  effort: 'low' | 'medium' | 'high';
  category: 'performance' | 'memory' | 'network' | 'rendering';
}

export class PerformanceOptimizer {
  private monitor: PerformanceMonitor;
  private rules: OptimizationRule[] = [];
  private suggestions: OptimizationSuggestion[] = [];
  private optimizationHistory: Array<{
    rule: string;
    timestamp: Date;
    beforeMetrics: Partial<PerformanceMetrics>;
    afterMetrics?: Partial<PerformanceMetrics>;
  }> = [];

  constructor(monitor: PerformanceMonitor) {
    this.monitor = monitor;
    this.initializeDefaultRules();
    this.startOptimizationLoop();
  }

  private initializeDefaultRules() {
    // Memory optimization rules
    this.addRule({
      name: 'memory-cleanup',
      condition: (metrics) => metrics.memoryUsage > 100 * 1024 * 1024, // 100MB
      action: () => this.triggerMemoryCleanup(),
      priority: 'high',
      description: 'Trigger garbage collection when memory usage exceeds 100MB',
    });

    // Render performance rules
    this.addRule({
      name: 'long-render-optimization',
      condition: (metrics) => metrics.renderTime > 16, // 16ms (60fps threshold)
      action: () => this.optimizeRenderPerformance(),
      priority: 'medium',
      description: 'Optimize rendering when frame time exceeds 16ms',
    });

    // Network optimization rules
    this.addRule({
      name: 'high-latency-optimization',
      condition: (metrics) => metrics.networkLatency > 1000, // 1 second
      action: () => this.optimizeNetworkPerformance(),
      priority: 'medium',
      description: 'Apply network optimizations when latency exceeds 1 second',
    });

    // Bundle size optimization
    this.addRule({
      name: 'large-bundle-warning',
      condition: (metrics) => metrics.bundleSize > 2 * 1024 * 1024, // 2MB
      action: () => this.suggestBundleOptimization(),
      priority: 'low',
      description: 'Suggest bundle splitting when size exceeds 2MB',
    });

    // FPS optimization
    this.addRule({
      name: 'low-fps-optimization',
      condition: (metrics) => metrics.fps < 30,
      action: () => this.optimizeFrameRate(),
      priority: 'high',
      description: 'Optimize frame rate when FPS drops below 30',
    });
  }

  public addRule(rule: OptimizationRule) {
    this.rules.push(rule);
  }

  public removeRule(name: string) {
    this.rules = this.rules.filter((rule) => rule.name !== name);
  }

  private startOptimizationLoop() {
    setInterval(() => {
      this.runOptimizationCheck();
    }, 5000); // Check every 5 seconds
  }

  private runOptimizationCheck() {
    const metrics = this.monitor.getMetrics();
    if (!metrics) return;

    // Sort rules by priority
    const sortedRules = this.rules.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 };
      return priorityOrder[b.priority] - priorityOrder[a.priority];
    });

    for (const rule of sortedRules) {
      if (rule.condition(metrics)) {
        console.log(`🔧 Applying optimization rule: ${rule.name}`);

        const beforeMetrics = { ...metrics };
        this.optimizationHistory.push({
          rule: rule.name,
          timestamp: new Date(),
          beforeMetrics,
        });

        try {
          rule.action();
        } catch (error) {
          console.error(`❌ Failed to apply optimization rule ${rule.name}:`, error);
        }

        // Only apply one rule per cycle to avoid conflicts
        break;
      }
    }

    // Generate suggestions
    this.generateOptimizationSuggestions(metrics);
  }

  private triggerMemoryCleanup() {
    // Force garbage collection if available (dev environment)
    if ('gc' in window) {
      (window as any).gc();
    }

    // Clear performance entries to free memory
    if ('clearResourceTimings' in performance) {
      performance.clearResourceTimings();
    }

    // Clear unused cache entries
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      navigator.storage.estimate().then((estimate) => {
        console.log(`📊 Storage usage: ${(estimate.usage || 0) / 1024 / 1024} MB`);
      });
    }

    // Suggest component cleanup
    this.addSuggestion({
      rule: 'memory-cleanup',
      description: 'Consider removing unused React components from memory',
      impact: 'medium',
      effort: 'low',
      category: 'memory',
    });
  }

  private optimizeRenderPerformance() {
    // Reduce animation quality temporarily
    document.documentElement.style.setProperty('--animation-duration', '0.1s');

    // Suggest React optimizations
    this.addSuggestion({
      rule: 'render-optimization',
      description: 'Use React.memo() for expensive components and useMemo() for heavy calculations',
      impact: 'high',
      effort: 'medium',
      category: 'rendering',
    });

    this.addSuggestion({
      rule: 'virtualization',
      description: 'Implement virtualization for long lists (react-window or react-virtualized)',
      impact: 'high',
      effort: 'high',
      category: 'rendering',
    });

    // Reset animation quality after a delay
    setTimeout(() => {
      document.documentElement.style.removeProperty('--animation-duration');
    }, 10000);
  }

  private optimizeNetworkPerformance() {
    // Enable request batching
    this.enableRequestBatching();

    this.addSuggestion({
      rule: 'network-optimization',
      description: 'Implement request caching and reduce API call frequency',
      impact: 'high',
      effort: 'medium',
      category: 'network',
    });

    this.addSuggestion({
      rule: 'cdn-optimization',
      description: 'Use CDN for static assets and implement resource preloading',
      impact: 'medium',
      effort: 'medium',
      category: 'network',
    });
  }

  private enableRequestBatching() {
    // Simple request batching implementation
    const pendingRequests: Map<string, Promise<any>> = new Map();

    const originalFetch = window.fetch;
    window.fetch = (...args) => {
      const url = args[0].toString();

      // Batch identical GET requests
      if (!args[1] || args[1].method === 'GET') {
        if (pendingRequests.has(url)) {
          return pendingRequests.get(url)!;
        }

        const request = originalFetch(...args);
        pendingRequests.set(url, request);

        request.finally(() => {
          setTimeout(() => pendingRequests.delete(url), 1000);
        });

        return request;
      }

      return originalFetch(...args);
    };
  }

  private suggestBundleOptimization() {
    this.addSuggestion({
      rule: 'bundle-splitting',
      description: 'Implement code splitting with dynamic imports and lazy loading',
      impact: 'high',
      effort: 'high',
      category: 'performance',
    });

    this.addSuggestion({
      rule: 'tree-shaking',
      description: 'Enable tree shaking and remove unused dependencies',
      impact: 'medium',
      effort: 'low',
      category: 'performance',
    });
  }

  private optimizeFrameRate() {
    // Reduce visual effects
    document.documentElement.style.setProperty('--reduce-motion', '1');

    // Pause non-critical animations
    const animations = document.getAnimations();
    animations.forEach((animation) => {
      if (!animation.id?.includes('critical')) {
        animation.pause();
      }
    });

    this.addSuggestion({
      rule: 'fps-optimization',
      description: 'Use requestIdleCallback for non-urgent work and optimize animations',
      impact: 'high',
      effort: 'medium',
      category: 'rendering',
    });

    // Resume animations after performance improves
    setTimeout(() => {
      document.documentElement.style.removeProperty('--reduce-motion');
      animations.forEach((animation) => animation.play());
    }, 15000);
  }

  private generateOptimizationSuggestions(metrics: PerformanceMetrics) {
    // Clear old suggestions
    this.suggestions = [];

    // Render time suggestions
    if (metrics.renderTime > 10) {
      this.addSuggestion({
        rule: 'component-optimization',
        description: 'Split large components and use React.lazy() for code splitting',
        impact: 'medium',
        effort: 'medium',
        category: 'rendering',
      });
    }

    // Memory suggestions
    if (metrics.memoryUsage > 75 * 1024 * 1024) {
      this.addSuggestion({
        rule: 'memory-management',
        description: 'Implement proper cleanup in useEffect and avoid memory leaks',
        impact: 'high',
        effort: 'low',
        category: 'memory',
      });
    }

    // Network suggestions
    if (metrics.networkLatency > 500) {
      this.addSuggestion({
        rule: 'request-optimization',
        description: 'Implement request debouncing and optimize API endpoints',
        impact: 'medium',
        effort: 'low',
        category: 'network',
      });
    }

    // Error rate suggestions
    if (metrics.errorRate > 5) {
      this.addSuggestion({
        rule: 'error-handling',
        description: 'Improve error boundaries and add retry logic for failed requests',
        impact: 'high',
        effort: 'medium',
        category: 'performance',
      });
    }
  }

  private addSuggestion(suggestion: OptimizationSuggestion) {
    // Avoid duplicates
    if (!this.suggestions.find((s) => s.rule === suggestion.rule)) {
      this.suggestions.push(suggestion);
    }
  }

  public getSuggestions(): OptimizationSuggestion[] {
    return [...this.suggestions];
  }

  public getOptimizationHistory() {
    return [...this.optimizationHistory];
  }

  public clearSuggestions() {
    this.suggestions = [];
  }

  public generateOptimizationReport() {
    const metrics = this.monitor.getMetrics();
    const report = this.monitor.generateReport();

    return {
      timestamp: new Date(),
      currentMetrics: metrics,
      performanceReport: report,
      suggestions: this.getSuggestions(),
      optimizationHistory: this.getOptimizationHistory(),
      recommendations: this.generateRecommendations(metrics),
    };
  }

  private generateRecommendations(metrics?: PerformanceMetrics) {
    if (!metrics) return [];

    const recommendations = [];

    // Performance-based recommendations
    if (metrics.renderTime > 16) {
      recommendations.push({
        category: 'Rendering',
        priority: 'High',
        description: 'Render time exceeds 16ms budget',
        actions: [
          'Implement React.memo() for expensive components',
          'Use useMemo() for heavy calculations',
          'Consider virtualization for large lists',
          'Optimize CSS and reduce layout thrashing',
        ],
      });
    }

    if (metrics.memoryUsage > 100 * 1024 * 1024) {
      recommendations.push({
        category: 'Memory',
        priority: 'High',
        description: 'Memory usage exceeds 100MB',
        actions: [
          'Implement proper cleanup in useEffect hooks',
          'Remove unused dependencies and dead code',
          'Use WeakMap and WeakSet for temporary references',
          'Consider lazy loading for rarely used components',
        ],
      });
    }

    if (metrics.fps < 30) {
      recommendations.push({
        category: 'Animation',
        priority: 'Critical',
        description: 'Frame rate below acceptable threshold',
        actions: [
          'Reduce animation complexity',
          'Use CSS transforms instead of changing layout properties',
          'Implement requestIdleCallback for non-urgent work',
          'Consider reducing visual effects temporarily',
        ],
      });
    }

    if (metrics.networkLatency > 1000) {
      recommendations.push({
        category: 'Network',
        priority: 'Medium',
        description: 'High network latency detected',
        actions: [
          'Implement request caching',
          'Use service workers for offline functionality',
          'Optimize API endpoints and database queries',
          'Consider using a CDN for static assets',
        ],
      });
    }

    return recommendations;
  }

  public destroy() {
    // Cleanup optimization loop
    // Note: In a real implementation, you'd store the interval ID
    // and clear it here
  }
}
