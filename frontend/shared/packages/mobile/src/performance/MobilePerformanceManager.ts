/**
 * Mobile Performance Optimization Manager
 * Battery-aware and mobile-specific performance optimizations
 */

export interface PerformanceConfig {
  batteryOptimization: boolean;
  adaptiveQuality: boolean;
  preloadImages: boolean;
  lazyLoadThreshold: number;
  maxConcurrentRequests: number;
  frameRateCap: number;
}

export interface BatteryStatus {
  charging: boolean;
  level: number;
  chargingTime: number;
  dischargingTime: number;
}

export interface PerformanceMetrics {
  fps: number;
  memoryUsage: number;
  networkType: string;
  batteryLevel: number;
  isLowPowerMode: boolean;
}

export class MobilePerformanceManager {
  private config: PerformanceConfig;
  private batteryStatus: BatteryStatus | null = null;
  private performanceObserver: PerformanceObserver | null = null;
  private frameRateMonitor: number | null = null;
  private isLowPowerMode = false;
  private metrics: PerformanceMetrics = {
    fps: 60,
    memoryUsage: 0,
    networkType: 'unknown',
    batteryLevel: 100,
    isLowPowerMode: false,
  };

  constructor(config: Partial<PerformanceConfig> = {}) {
    this.config = {
      batteryOptimization: true,
      adaptiveQuality: true,
      preloadImages: true,
      lazyLoadThreshold: 100,
      maxConcurrentRequests: 6,
      frameRateCap: 60,
      ...config,
    };

    this.initialize();
  }

  private async initialize(): Promise<void> {
    await this.setupBatteryMonitoring();
    this.setupPerformanceMonitoring();
    this.setupNetworkMonitoring();
    this.startFrameRateMonitoring();
  }

  private async setupBatteryMonitoring(): Promise<void> {
    if (!this.config.batteryOptimization) return;

    try {
      if ('getBattery' in navigator) {
        const battery = await (navigator as any).getBattery();

        const updateBatteryStatus = () => {
          this.batteryStatus = {
            charging: battery.charging,
            level: Math.round(battery.level * 100),
            chargingTime: battery.chargingTime,
            dischargingTime: battery.dischargingTime,
          };

          this.metrics.batteryLevel = this.batteryStatus.level;
          this.updateLowPowerMode();
        };

        updateBatteryStatus();

        battery.addEventListener('chargingchange', updateBatteryStatus);
        battery.addEventListener('levelchange', updateBatteryStatus);
      }
    } catch (error) {
      console.warn('Battery API not available:', error);
    }
  }

  private updateLowPowerMode(): void {
    if (!this.batteryStatus) return;

    const wasLowPowerMode = this.isLowPowerMode;

    // Enter low power mode if battery < 20% and not charging
    this.isLowPowerMode = this.batteryStatus.level < 20 && !this.batteryStatus.charging;

    this.metrics.isLowPowerMode = this.isLowPowerMode;

    // Apply optimizations when entering low power mode
    if (this.isLowPowerMode && !wasLowPowerMode) {
      this.applyLowPowerOptimizations();
    } else if (!this.isLowPowerMode && wasLowPowerMode) {
      this.removeLowPowerOptimizations();
    }
  }

  private applyLowPowerOptimizations(): void {
    // Reduce animation frame rate
    this.config.frameRateCap = 30;

    // Disable non-essential animations
    document.body.classList.add('low-power-mode');

    // Reduce image quality
    this.setImageQuality('low');

    // Limit concurrent requests
    this.config.maxConcurrentRequests = 3;

    console.log('Low power mode enabled - performance optimizations applied');
  }

  private removeLowPowerOptimizations(): void {
    // Restore normal frame rate
    this.config.frameRateCap = 60;

    // Re-enable animations
    document.body.classList.remove('low-power-mode');

    // Restore image quality
    this.setImageQuality('auto');

    // Restore concurrent requests
    this.config.maxConcurrentRequests = 6;

    console.log('Low power mode disabled - normal performance restored');
  }

  private setupPerformanceMonitoring(): void {
    if ('PerformanceObserver' in window) {
      this.performanceObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();

        entries.forEach((entry) => {
          if (entry.entryType === 'navigation') {
            // Track page load performance
            console.log('Navigation timing:', entry);
          } else if (entry.entryType === 'paint') {
            // Track rendering performance
            console.log('Paint timing:', entry);
          }
        });
      });

      this.performanceObserver.observe({
        entryTypes: ['navigation', 'paint', 'largest-contentful-paint'],
      });
    }

    // Memory monitoring
    if ('memory' in performance) {
      setInterval(() => {
        const memory = (performance as any).memory;
        this.metrics.memoryUsage = memory.usedJSHeapSize / memory.jsHeapSizeLimit;

        // Trigger garbage collection hint if memory usage is high
        if (this.metrics.memoryUsage > 0.8) {
          this.optimizeMemoryUsage();
        }
      }, 5000);
    }
  }

  private setupNetworkMonitoring(): void {
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;

      const updateNetworkInfo = () => {
        this.metrics.networkType = connection.effectiveType || 'unknown';

        // Apply network-based optimizations
        if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
          this.applySlowNetworkOptimizations();
        } else {
          this.removeSlowNetworkOptimizations();
        }
      };

      updateNetworkInfo();
      connection.addEventListener('change', updateNetworkInfo);
    }
  }

  private startFrameRateMonitoring(): void {
    let lastTime = performance.now();
    let frameCount = 0;

    const measureFPS = (currentTime: number) => {
      frameCount++;

      if (currentTime - lastTime >= 1000) {
        this.metrics.fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        frameCount = 0;
        lastTime = currentTime;

        // Reduce quality if FPS drops below threshold
        if (this.metrics.fps < 30 && this.config.adaptiveQuality) {
          this.applyPerformanceOptimizations();
        }
      }

      this.frameRateMonitor = requestAnimationFrame(measureFPS);
    };

    this.frameRateMonitor = requestAnimationFrame(measureFPS);
  }

  private applySlowNetworkOptimizations(): void {
    // Disable image preloading
    this.config.preloadImages = false;

    // Reduce concurrent requests
    this.config.maxConcurrentRequests = 2;

    // Set low image quality
    this.setImageQuality('low');

    document.body.classList.add('slow-network');
  }

  private removeSlowNetworkOptimizations(): void {
    this.config.preloadImages = true;
    this.config.maxConcurrentRequests = 6;
    this.setImageQuality('auto');

    document.body.classList.remove('slow-network');
  }

  private applyPerformanceOptimizations(): void {
    // Disable complex animations
    document.body.classList.add('reduced-animations');

    // Reduce rendering quality
    this.setImageQuality('medium');

    // Limit frame rate
    this.config.frameRateCap = Math.max(30, this.config.frameRateCap - 10);
  }

  private setImageQuality(quality: 'low' | 'medium' | 'high' | 'auto'): void {
    const qualityMap = {
      low: '0.6',
      medium: '0.8',
      high: '0.95',
      auto: '1.0',
    };

    document.documentElement.style.setProperty('--image-quality', qualityMap[quality]);

    // Apply to existing images
    const images = document.querySelectorAll('img[data-quality]');
    images.forEach((img) => {
      (img as HTMLImageElement).style.filter =
        quality === 'auto' ? 'none' : `contrast(${qualityMap[quality]})`;
    });
  }

  private optimizeMemoryUsage(): void {
    // Clean up unused image caches
    if ('caches' in window) {
      caches.keys().then((cacheNames) => {
        cacheNames.forEach((cacheName) => {
          if (cacheName.includes('images') || cacheName.includes('temp')) {
            caches.delete(cacheName);
          }
        });
      });
    }

    // Trigger garbage collection hint
    if ('gc' in window && typeof (window as any).gc === 'function') {
      (window as any).gc();
    }

    console.log('Memory optimization performed');
  }

  // Public API
  public getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  public getBatteryStatus(): BatteryStatus | null {
    return this.batteryStatus;
  }

  public isLowPowerModeActive(): boolean {
    return this.isLowPowerMode;
  }

  public optimizeForBattery(enable: boolean): void {
    this.config.batteryOptimization = enable;

    if (enable && this.batteryStatus?.level && this.batteryStatus.level < 30) {
      this.applyLowPowerOptimizations();
    } else if (!enable) {
      this.removeLowPowerOptimizations();
    }
  }

  public setAdaptiveQuality(enable: boolean): void {
    this.config.adaptiveQuality = enable;
  }

  public preloadImage(src: string): Promise<void> {
    if (!this.config.preloadImages || this.isLowPowerMode) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve();
      img.onerror = reject;
      img.src = src;
    });
  }

  public async preloadImages(sources: string[]): Promise<void> {
    if (!this.config.preloadImages) return;

    const chunks = [];
    for (let i = 0; i < sources.length; i += this.config.maxConcurrentRequests) {
      chunks.push(sources.slice(i, i + this.config.maxConcurrentRequests));
    }

    for (const chunk of chunks) {
      await Promise.allSettled(chunk.map((src) => this.preloadImage(src)));
    }
  }

  public createLazyLoader(threshold = this.config.lazyLoadThreshold): IntersectionObserver {
    return new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const target = entry.target as HTMLElement;
            const src = target.dataset.src;

            if (src) {
              if (target.tagName === 'IMG') {
                (target as HTMLImageElement).src = src;
              } else {
                target.style.backgroundImage = `url(${src})`;
              }

              target.removeAttribute('data-src');
              target.classList.add('loaded');
            }
          }
        });
      },
      {
        rootMargin: `${threshold}px`,
      }
    );
  }

  public destroy(): void {
    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }

    if (this.frameRateMonitor) {
      cancelAnimationFrame(this.frameRateMonitor);
    }

    document.body.classList.remove('low-power-mode', 'slow-network', 'reduced-animations');
  }
}
