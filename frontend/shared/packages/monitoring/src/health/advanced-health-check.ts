/**
 * Advanced health check implementation for frontend monitoring
 * Provides comprehensive health monitoring with configurable probes
 */

export interface HealthProbe {
  name: string;
  description?: string;
  timeout?: number;
  critical?: boolean;
  execute: () => Promise<ProbeResult>;
}

export interface ProbeResult {
  success: boolean;
  duration: number;
  error?: string;
  metadata?: Record<string, any>;
}

export interface AdvancedHealthCheck {
  name: string;
  status: 'pass' | 'fail' | 'warn';
  duration: number;
  error?: string;
  timestamp: string;
  probes?: Array<{
    name: string;
    status: 'pass' | 'fail' | 'warn';
    duration: number;
    error?: string;
    metadata?: Record<string, any>;
  }>;
}

export interface HealthCheckConfig {
  timeout?: number;
  criticalOnly?: boolean;
  enableDetailedProbes?: boolean;
}

class AdvancedHealthChecker {
  private probes: Map<string, HealthProbe> = new Map();
  private config: HealthCheckConfig;

  constructor(config: HealthCheckConfig = {}) {
    this.config = {
      timeout: 5000,
      criticalOnly: false,
      enableDetailedProbes: true,
      ...config,
    };

    // Register default probes
    this.registerDefaultProbes();
  }

  registerProbe(probe: HealthProbe): void {
    this.probes.set(probe.name, probe);
  }

  async check(): Promise<AdvancedHealthCheck> {
    const startTime = Date.now();
    const timestamp = new Date().toISOString();
    
    const probesToRun = Array.from(this.probes.values()).filter(
      probe => !this.config.criticalOnly || probe.critical
    );

    const probeResults: AdvancedHealthCheck['probes'] = [];
    let overallStatus: 'pass' | 'fail' | 'warn' = 'pass';
    let overallError: string | undefined;

    // Execute probes in parallel with timeout
    const probePromises = probesToRun.map(async (probe) => {
      try {
        const probeStart = Date.now();
        const timeoutPromise = new Promise<ProbeResult>((_, reject) =>
          setTimeout(() => reject(new Error('Probe timeout')), probe.timeout || this.config.timeout!)
        );

        const result = await Promise.race([probe.execute(), timeoutPromise]);
        const duration = Date.now() - probeStart;

        const probeStatus = result.success ? 'pass' : (probe.critical ? 'fail' : 'warn');
        
        if (probeStatus === 'fail') {
          overallStatus = 'fail';
          overallError = result.error || 'Critical probe failed';
        } else if (probeStatus === 'warn' && overallStatus === 'pass') {
          overallStatus = 'warn';
        }

        if (this.config.enableDetailedProbes) {
          probeResults.push({
            name: probe.name,
            status: probeStatus,
            duration,
            error: result.error,
            metadata: result.metadata,
          });
        }

      } catch (error) {
        const duration = Date.now() - startTime;
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        
        if (probe.critical) {
          overallStatus = 'fail';
          overallError = errorMessage;
        } else if (overallStatus === 'pass') {
          overallStatus = 'warn';
        }

        if (this.config.enableDetailedProbes) {
          probeResults.push({
            name: probe.name,
            status: probe.critical ? 'fail' : 'warn',
            duration,
            error: errorMessage,
          });
        }
      }
    });

    await Promise.allSettled(probePromises);

    const totalDuration = Date.now() - startTime;

    return {
      name: 'advanced-health-check',
      status: overallStatus,
      duration: totalDuration,
      error: overallError,
      timestamp,
      probes: this.config.enableDetailedProbes ? probeResults : undefined,
    };
  }

  private registerDefaultProbes(): void {
    // API Connectivity Probe
    this.registerProbe({
      name: 'api-connectivity',
      description: 'Check API server connectivity',
      timeout: 3000,
      critical: true,
      execute: async (): Promise<ProbeResult> => {
        const start = Date.now();
        try {
          const response = await fetch('/api/health', { method: 'GET' });
          const duration = Date.now() - start;
          
          if (response.ok) {
            return {
              success: true,
              duration,
              metadata: { status: response.status, statusText: response.statusText },
            };
          } else {
            return {
              success: false,
              duration,
              error: `HTTP ${response.status}: ${response.statusText}`,
            };
          }
        } catch (error) {
          return {
            success: false,
            duration: Date.now() - start,
            error: error instanceof Error ? error.message : 'Network error',
          };
        }
      },
    });

    // Local Storage Probe
    this.registerProbe({
      name: 'local-storage',
      description: 'Check local storage functionality',
      timeout: 1000,
      critical: false,
      execute: async (): Promise<ProbeResult> => {
        const start = Date.now();
        try {
          const testKey = '__health_check_test__';
          const testValue = Date.now().toString();
          
          localStorage.setItem(testKey, testValue);
          const retrieved = localStorage.getItem(testKey);
          localStorage.removeItem(testKey);
          
          const duration = Date.now() - start;
          
          if (retrieved === testValue) {
            return { success: true, duration };
          } else {
            return {
              success: false,
              duration,
              error: 'Local storage read/write mismatch',
            };
          }
        } catch (error) {
          return {
            success: false,
            duration: Date.now() - start,
            error: error instanceof Error ? error.message : 'Local storage error',
          };
        }
      },
    });

    // WebSocket Connectivity Probe (if available)
    this.registerProbe({
      name: 'websocket-connectivity',
      description: 'Check WebSocket connectivity',
      timeout: 5000,
      critical: false,
      execute: async (): Promise<ProbeResult> => {
        const start = Date.now();
        try {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const wsUrl = `${protocol}//${window.location.host}/ws/health`;
          
          return new Promise<ProbeResult>((resolve) => {
            const ws = new WebSocket(wsUrl);
            let resolved = false;
            
            const cleanup = () => {
              if (!resolved) {
                resolved = true;
                ws.close();
              }
            };
            
            ws.onopen = () => {
              cleanup();
              resolve({
                success: true,
                duration: Date.now() - start,
              });
            };
            
            ws.onerror = (error) => {
              cleanup();
              resolve({
                success: false,
                duration: Date.now() - start,
                error: 'WebSocket connection failed',
              });
            };
            
            setTimeout(() => {
              cleanup();
              resolve({
                success: false,
                duration: Date.now() - start,
                error: 'WebSocket connection timeout',
              });
            }, 5000);
          });
        } catch (error) {
          return {
            success: false,
            duration: Date.now() - start,
            error: error instanceof Error ? error.message : 'WebSocket error',
          };
        }
      },
    });

    // Performance Probe
    this.registerProbe({
      name: 'performance',
      description: 'Check basic performance metrics',
      timeout: 1000,
      critical: false,
      execute: async (): Promise<ProbeResult> => {
        const start = Date.now();
        try {
          const performanceData = {
            memory: (performance as any).memory ? {
              used: (performance as any).memory.usedJSHeapSize,
              total: (performance as any).memory.totalJSHeapSize,
              limit: (performance as any).memory.jsHeapSizeLimit,
            } : null,
            timing: performance.timing ? {
              loadTime: performance.timing.loadEventEnd - performance.timing.navigationStart,
              domReady: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
            } : null,
          };
          
          const duration = Date.now() - start;
          
          return {
            success: true,
            duration,
            metadata: performanceData,
          };
        } catch (error) {
          return {
            success: false,
            duration: Date.now() - start,
            error: error instanceof Error ? error.message : 'Performance check error',
          };
        }
      },
    });
  }
}

export const createAdvancedHealthCheck = (config?: HealthCheckConfig) => {
  return new AdvancedHealthChecker(config);
};

export { AdvancedHealthChecker };
export default createAdvancedHealthCheck;
