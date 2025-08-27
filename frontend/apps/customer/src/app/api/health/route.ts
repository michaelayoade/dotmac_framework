/**
 * Optimized Health Check API Route
 * Provides fast, cached health status for load balancers and monitoring systems
 */
import { NextRequest, NextResponse } from 'next/server';

interface HealthCheckResult {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  version: string;
  environment: string;
  uptime: number;
  checks: {
    [key: string]: {
      status: 'pass' | 'fail' | 'warn';
      duration: number;
      error?: string;
      details?: any;
    };
  };
  metrics: {
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
  };
}

// Track application metrics
let applicationMetrics = {
  startTime: Date.now(),
  requestCount: 0,
  errorCount: 0,
  lastError: null as string | null,
};

// Cache for health check results (avoid expensive operations on every request)
let healthCheckCache: {
  result: HealthCheckResult | null;
  timestamp: number;
  ttl: number;
} = {
  result: null,
  timestamp: 0,
  ttl: 30000, // 30 seconds cache
};

export async function GET(request: NextRequest): Promise<NextResponse> {
  const startTime = Date.now();
  applicationMetrics.requestCount++;

  try {
    // Check if we have a fresh cached result
    const now = Date.now();
    const cacheValid = healthCheckCache.result && 
                      (now - healthCheckCache.timestamp) < healthCheckCache.ttl;

    let healthResult: HealthCheckResult;

    if (cacheValid) {
      // Use cached result and update timestamp
      healthResult = {
        ...healthCheckCache.result!,
        timestamp: new Date().toISOString(),
        uptime: now - applicationMetrics.startTime,
      };
    } else {
      // Perform fresh health checks
      healthResult = await performOptimizedHealthChecks();
      
      // Cache the result
      healthCheckCache = {
        result: healthResult,
        timestamp: now,
        ttl: 30000, // 30 seconds
      };
    }
    
    // Add current request response time
    healthResult.checks.healthCheck = {
      status: 'pass',
      duration: Date.now() - startTime,
    };

    const statusCode = healthResult.status === 'healthy' ? 200 : 
                      healthResult.status === 'degraded' ? 200 : 503;

    return NextResponse.json(healthResult, { 
      status: statusCode,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Content-Type': 'application/json',
        'X-Health-Check': 'true',
        'X-Response-Time': (Date.now() - startTime).toString(),
      }
    });

  } catch (error) {
    applicationMetrics.errorCount++;
    applicationMetrics.lastError = error instanceof Error ? error.message : 'Unknown error';

    const errorResult: HealthCheckResult = {
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
      environment: process.env.NODE_ENV || 'development',
      uptime: Date.now() - applicationMetrics.startTime,
      checks: {
        healthCheck: {
          status: 'fail',
          duration: Date.now() - startTime,
          error: error instanceof Error ? error.message : 'Health check failed',
        },
      },
      metrics: getBasicMetrics(),
    };

    return NextResponse.json(errorResult, { 
      status: 503,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Content-Type': 'application/json',
        'X-Health-Check': 'true',
        'X-Response-Time': (Date.now() - startTime).toString(),
      }
    });
  }
}

/**
 * Perform optimized health checks (cached)
 */
async function performOptimizedHealthChecks(): Promise<HealthCheckResult> {
  const checks: HealthCheckResult['checks'] = {};
  const startTime = Date.now();
  
  // Run non-blocking checks in parallel with timeouts
  const checkPromises = [
    checkApplicationHealth(),
    checkMemoryUsage(),
    checkEnvironmentVariables(),
    checkCriticalDependencies(),
  ];

  // Wait for all checks with a global timeout
  try {
    const results = await Promise.allSettled(checkPromises);
    
    checks.application = results[0].status === 'fulfilled' ? results[0].value : {
      status: 'fail',
      duration: Date.now() - startTime,
      error: 'Application health check timeout'
    };
    
    checks.memory = results[1].status === 'fulfilled' ? results[1].value : {
      status: 'warn',
      duration: Date.now() - startTime,
      error: 'Memory check timeout'
    };
    
    checks.environment = results[2].status === 'fulfilled' ? results[2].value : {
      status: 'warn',
      duration: Date.now() - startTime,
      error: 'Environment check timeout'
    };
    
    checks.dependencies = results[3].status === 'fulfilled' ? results[3].value : {
      status: 'warn',
      duration: Date.now() - startTime,
      error: 'Dependencies check timeout'
    };

  } catch (error) {
    checks.global = {
      status: 'fail',
      duration: Date.now() - startTime,
      error: error instanceof Error ? error.message : 'Global health check failed'
    };
  }

  const overallStatus = determineOverallStatus(checks);

  return {
    status: overallStatus,
    timestamp: new Date().toISOString(),
    version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
    environment: process.env.NODE_ENV || 'development',
    uptime: Date.now() - applicationMetrics.startTime,
    checks,
    metrics: getBasicMetrics(),
  };
}

/**
 * Fast application health check (no external dependencies)
 */
async function checkApplicationHealth(): Promise<HealthCheckResult['checks'][string]> {
  const start = Date.now();
  
  try {
    // Basic application health indicators
    const isHealthy = process.uptime() > 0 && 
                     applicationMetrics.errorCount < 100 && 
                     (applicationMetrics.errorCount / Math.max(applicationMetrics.requestCount, 1)) < 0.5;

    return {
      status: isHealthy ? 'pass' : 'warn',
      duration: Date.now() - start,
      details: {
        processUptime: Math.floor(process.uptime()),
        errorRate: applicationMetrics.requestCount > 0 ? 
          (applicationMetrics.errorCount / applicationMetrics.requestCount) : 0,
        requestCount: applicationMetrics.requestCount,
        errorCount: applicationMetrics.errorCount,
      },
    };
  } catch (error) {
    return {
      status: 'fail',
      duration: Date.now() - start,
      error: error instanceof Error ? error.message : 'Application check failed',
    };
  }
}

/**
 * Fast memory usage check
 */
async function checkMemoryUsage(): Promise<HealthCheckResult['checks'][string]> {
  const start = Date.now();
  
  try {
    const memoryUsage = process.memoryUsage();
    const totalMemory = memoryUsage.heapTotal;
    const usedMemory = memoryUsage.heapUsed;
    const memoryPercentage = (usedMemory / totalMemory) * 100;
    
    const status = memoryPercentage > 90 ? 'fail' : 
                   memoryPercentage > 75 ? 'warn' : 'pass';
    
    return {
      status,
      duration: Date.now() - start,
      details: {
        heapUsed: Math.round(usedMemory / 1024 / 1024),
        heapTotal: Math.round(totalMemory / 1024 / 1024),
        heapPercentage: Math.round(memoryPercentage),
        rss: Math.round(memoryUsage.rss / 1024 / 1024),
      },
      error: status !== 'pass' ? `Memory usage: ${Math.round(memoryPercentage)}%` : undefined,
    };
  } catch (error) {
    return {
      status: 'fail',
      duration: Date.now() - start,
      error: error instanceof Error ? error.message : 'Memory check failed',
    };
  }
}

/**
 * Fast environment variables check
 */
async function checkEnvironmentVariables(): Promise<HealthCheckResult['checks'][string]> {
  const start = Date.now();
  
  const requiredVars = [
    'NODE_ENV',
    'NEXT_PUBLIC_API_URL',
  ];
  
  const missing: string[] = [];
  
  for (const varName of requiredVars) {
    if (!process.env[varName]) {
      missing.push(varName);
    }
  }
  
  const status = missing.length > 0 ? 'fail' : 'pass';
  
  return {
    status,
    duration: Date.now() - start,
    details: {
      required: requiredVars.length - missing.length,
      missing: missing.length,
      environment: process.env.NODE_ENV,
    },
    error: missing.length > 0 ? `Missing: ${missing.join(', ')}` : undefined,
  };
}

/**
 * Fast dependencies check (no imports)
 */
async function checkCriticalDependencies(): Promise<HealthCheckResult['checks'][string]> {
  const start = Date.now();
  
  try {
    // Check if critical modules are available without importing them
    const criticalModules = ['react', 'next'];
    const moduleStatus: Record<string, boolean> = {};
    
    for (const module of criticalModules) {
      try {
        require.resolve(module);
        moduleStatus[module] = true;
      } catch {
        moduleStatus[module] = false;
      }
    }
    
    const failedModules = Object.entries(moduleStatus)
      .filter(([_, available]) => !available)
      .map(([module]) => module);
    
    return {
      status: failedModules.length === 0 ? 'pass' : 'fail',
      duration: Date.now() - start,
      details: {
        modules: moduleStatus,
        nodeVersion: process.version,
      },
      error: failedModules.length > 0 ? `Missing modules: ${failedModules.join(', ')}` : undefined,
    };
  } catch (error) {
    return {
      status: 'warn',
      duration: Date.now() - start,
      error: error instanceof Error ? error.message : 'Dependencies check failed',
    };
  }
}

/**
 * Get basic metrics (fast)
 */
function getBasicMetrics(): HealthCheckResult['metrics'] {
  const memoryUsage = process.memoryUsage();
  
  return {
    memory: {
      used: Math.round(memoryUsage.heapUsed / 1024 / 1024),
      total: Math.round(memoryUsage.heapTotal / 1024 / 1024),
      percentage: Math.round((memoryUsage.heapUsed / memoryUsage.heapTotal) * 100),
    },
    requests: {
      total: applicationMetrics.requestCount,
      errors: applicationMetrics.errorCount,
      errorRate: applicationMetrics.requestCount > 0 ? 
        Math.round((applicationMetrics.errorCount / applicationMetrics.requestCount) * 100) / 100 : 0,
    },
  };
}

/**
 * Determine overall status from individual checks
 */
function determineOverallStatus(checks: HealthCheckResult['checks']): 'healthy' | 'unhealthy' | 'degraded' {
  let hasFailures = false;
  let hasWarnings = false;
  
  for (const check of Object.values(checks)) {
    if (check.status === 'fail') {
      hasFailures = true;
    } else if (check.status === 'warn') {
      hasWarnings = true;
    }
  }
  
  if (hasFailures) return 'unhealthy';
  if (hasWarnings) return 'degraded';
  return 'healthy';
}

// Export for testing removed - Next.js API routes only support GET, POST, etc. exports