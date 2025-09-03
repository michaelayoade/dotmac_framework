export type HealthStatus = 'healthy' | 'unhealthy' | 'degraded';

export interface HealthCheck {
  name: string;
  status: 'pass' | 'fail' | 'warn';
  duration: number;
  error?: string;
  details?: any;
  critical?: boolean;
}

export interface HealthMetrics {
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  requests: {
    total: number;
    errors: number;
    errorRate: number;
  };
  performance: {
    avgResponseTime: number;
    p95ResponseTime: number;
  };
}

export interface HealthCheckResult {
  status: HealthStatus;
  timestamp: string;
  version: string;
  environment: string;
  uptime: number;
  portal: string;
  checks: Record<string, HealthCheck>;
  metrics: HealthMetrics;
}

export interface PortalHealthConfig {
  name: string;
  critical: string[];
  optional: string[];
  cacheTtl: number;
  timeout: number;
}

export interface HealthCheckFunction {
  (): Promise<HealthCheck>;
}

export interface HealthCheckRegistry {
  register(name: string, check: HealthCheckFunction, critical?: boolean): void;
  unregister(name: string): void;
  getCheck(name: string): HealthCheckFunction | undefined;
  getAllChecks(): Map<string, { check: HealthCheckFunction; critical: boolean }>;
}
