import { EventEmitter } from 'events';

export interface PerformanceMetrics {
  renderTime: number;
  interactionTime: number;
  memoryUsage: number;
  bundleSize: number;
  networkLatency: number;
  errorRate: number;
  fps: number;
  componentMountTime: number;
}

export interface PerformanceBudget {
  renderTime: number;
  interactionTime: number;
  memoryUsage: number;
  bundleSize: number;
  networkLatency: number;
  errorRate: number;
  fps: number;
}

export interface PerformanceAlert {
  metric: keyof PerformanceMetrics;
  value: number;
  threshold: number;
  severity: 'warning' | 'critical';
  timestamp: Date;
  component?: string;
}

export class PerformanceMonitor extends EventEmitter {
  private metrics: Map<string, PerformanceMetrics> = new Map();
  private budget: PerformanceBudget;
  private observer: PerformanceObserver | null = null;
  private rafId: number | null = null;
  private frameCount = 0;
  private lastFrameTime = performance.now();

  constructor(budget: PerformanceBudget) {
    super();
    this.budget = budget;
    this.initializeObserver();
    this.startFPSMonitoring();
  }

  private initializeObserver() {
    if (typeof PerformanceObserver !== 'undefined') {
      this.observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          this.processPerformanceEntry(entry);
        });
      });

      this.observer.observe({
        entryTypes: ['measure', 'navigation', 'resource', 'longtask', 'layout-shift', 'paint'],
      });
    }
  }

  private processPerformanceEntry(entry: PerformanceEntry) {
    switch (entry.entryType) {
      case 'measure':
        this.processMeasureEntry(entry as PerformanceMeasure);
        break;
      case 'navigation':
        this.processNavigationEntry(entry as PerformanceNavigationTiming);
        break;
      case 'resource':
        this.processResourceEntry(entry as PerformanceResourceTiming);
        break;
      case 'longtask':
        this.processLongTaskEntry(entry);
        break;
      case 'layout-shift':
        this.processLayoutShiftEntry(entry as any);
        break;
      case 'paint':
        this.processPaintEntry(entry);
        break;
    }
  }

  private processMeasureEntry(entry: PerformanceMeasure) {
    if (entry.name.includes('render')) {
      this.updateMetric('renderTime', entry.duration);
    } else if (entry.name.includes('interaction')) {
      this.updateMetric('interactionTime', entry.duration);
    } else if (entry.name.includes('mount')) {
      this.updateMetric('componentMountTime', entry.duration);
    }
  }

  private processNavigationEntry(entry: PerformanceNavigationTiming) {
    const networkLatency = entry.responseEnd - entry.requestStart;
    this.updateMetric('networkLatency', networkLatency);
  }

  private processResourceEntry(entry: PerformanceResourceTiming) {
    if (entry.name.includes('.js') || entry.name.includes('.css')) {
      const size = entry.transferSize || entry.decodedBodySize || 0;
      this.updateMetric('bundleSize', size);
    }
  }

  private processLongTaskEntry(entry: PerformanceEntry) {
    if (entry.duration > 50) {
      this.emit('longTask', {
        duration: entry.duration,
        startTime: entry.startTime,
        name: entry.name,
      });
    }
  }

  private processLayoutShiftEntry(entry: any) {
    if (entry.value > 0.1) {
      this.emit('layoutShift', {
        value: entry.value,
        startTime: entry.startTime,
      });
    }
  }

  private processPaintEntry(entry: PerformanceEntry) {
    this.emit('paintTiming', {
      name: entry.name,
      startTime: entry.startTime,
    });
  }

  private startFPSMonitoring() {
    const measureFPS = () => {
      const now = performance.now();
      this.frameCount++;

      if (now - this.lastFrameTime >= 1000) {
        const fps = Math.round((this.frameCount * 1000) / (now - this.lastFrameTime));
        this.updateMetric('fps', fps);
        this.frameCount = 0;
        this.lastFrameTime = now;
      }

      this.rafId = requestAnimationFrame(measureFPS);
    };

    measureFPS();
  }

  private updateMetric(key: keyof PerformanceMetrics, value: number, component?: string) {
    const metricKey = component ? `${component}:${key}` : key;
    const currentMetrics = this.metrics.get(metricKey) || ({} as PerformanceMetrics);

    currentMetrics[key] = value;
    this.metrics.set(metricKey, currentMetrics);

    // Check against budget
    this.checkBudget(key, value, component);

    // Update memory usage
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      currentMetrics.memoryUsage = memory.usedJSHeapSize;
    }

    this.emit('metricUpdate', { metric: key, value, component });
  }

  private checkBudget(metric: keyof PerformanceMetrics, value: number, component?: string) {
    const threshold = this.budget[metric];
    if (!threshold) return;

    let severity: 'warning' | 'critical' = 'warning';

    if (value > threshold * 1.5) {
      severity = 'critical';
    } else if (value <= threshold) {
      return; // Within budget
    }

    const alert: PerformanceAlert = {
      metric,
      value,
      threshold,
      severity,
      timestamp: new Date(),
      component,
    };

    this.emit('budgetExceeded', alert);
  }

  public measureRender<T>(componentName: string, renderFn: () => T): T {
    const startTime = performance.now();
    performance.mark(`${componentName}-render-start`);

    const result = renderFn();

    performance.mark(`${componentName}-render-end`);
    performance.measure(
      `${componentName}-render`,
      `${componentName}-render-start`,
      `${componentName}-render-end`
    );

    const endTime = performance.now();
    this.updateMetric('renderTime', endTime - startTime, componentName);

    return result;
  }

  public measureInteraction<T>(interactionName: string, interactionFn: () => T): T {
    const startTime = performance.now();
    performance.mark(`${interactionName}-start`);

    const result = interactionFn();

    performance.mark(`${interactionName}-end`);
    performance.measure(
      `${interactionName}-interaction`,
      `${interactionName}-start`,
      `${interactionName}-end`
    );

    const endTime = performance.now();
    this.updateMetric('interactionTime', endTime - startTime);

    return result;
  }

  public async measureAsync<T>(name: string, asyncFn: () => Promise<T>): Promise<T> {
    const startTime = performance.now();
    performance.mark(`${name}-start`);

    try {
      const result = await asyncFn();

      performance.mark(`${name}-end`);
      performance.measure(name, `${name}-start`, `${name}-end`);

      const endTime = performance.now();
      this.updateMetric('networkLatency', endTime - startTime);

      return result;
    } catch (error) {
      this.recordError(name, error as Error);
      throw error;
    }
  }

  public recordError(operation: string, error: Error) {
    const currentErrorRate = this.getMetric('errorRate') || 0;
    this.updateMetric('errorRate', currentErrorRate + 1);

    this.emit('error', {
      operation,
      error: error.message,
      stack: error.stack,
      timestamp: new Date(),
    });
  }

  public getMetric(key: keyof PerformanceMetrics, component?: string): number | undefined {
    const metricKey = component ? `${component}:${key}` : key;
    return this.metrics.get(metricKey)?.[key];
  }

  public getMetrics(component?: string): PerformanceMetrics | undefined {
    const metricKey = component || 'global';
    return this.metrics.get(metricKey);
  }

  public getAllMetrics(): Map<string, PerformanceMetrics> {
    return new Map(this.metrics);
  }

  public getBudget(): PerformanceBudget {
    return { ...this.budget };
  }

  public updateBudget(newBudget: Partial<PerformanceBudget>) {
    this.budget = { ...this.budget, ...newBudget };
    this.emit('budgetUpdate', this.budget);
  }

  public generateReport(): {
    summary: Record<
      keyof PerformanceMetrics,
      { value: number; status: 'good' | 'warning' | 'critical' }
    >;
    components: Record<string, PerformanceMetrics>;
    violations: PerformanceAlert[];
  } {
    const globalMetrics = this.getMetrics() || ({} as PerformanceMetrics);
    const summary: Record<string, { value: number; status: 'good' | 'warning' | 'critical' }> = {};
    const violations: PerformanceAlert[] = [];

    Object.keys(this.budget).forEach((key) => {
      const metric = key as keyof PerformanceMetrics;
      const value = globalMetrics[metric] || 0;
      const threshold = this.budget[metric];

      let status: 'good' | 'warning' | 'critical' = 'good';
      if (value > threshold * 1.5) {
        status = 'critical';
        violations.push({
          metric,
          value,
          threshold,
          severity: 'critical',
          timestamp: new Date(),
        });
      } else if (value > threshold) {
        status = 'warning';
        violations.push({
          metric,
          value,
          threshold,
          severity: 'warning',
          timestamp: new Date(),
        });
      }

      summary[metric] = { value, status };
    });

    const components: Record<string, PerformanceMetrics> = {};
    this.metrics.forEach((metrics, key) => {
      if (key.includes(':')) {
        const [componentName] = key.split(':');
        components[componentName] = metrics;
      }
    });

    return { summary, components, violations };
  }

  public clearMetrics() {
    this.metrics.clear();
    this.emit('metricsCleared');
  }

  public destroy() {
    if (this.observer) {
      this.observer.disconnect();
    }

    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }

    this.removeAllListeners();
    this.clearMetrics();
  }
}
