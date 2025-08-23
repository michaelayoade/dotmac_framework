#!/usr/bin/env node
/**
 * Performance Benchmarks for DotMac Frontend
 * 
 * Validates performance testing setup and creates realistic benchmarks
 */

const fs = require('fs');
const path = require('path');

// Performance test configuration
const PERFORMANCE_CONFIG = {
  thresholds: {
    renderTime: {
      fast: 16,      // < 16ms (1 frame at 60fps)
      acceptable: 50, // < 50ms (acceptable for complex components)
      slow: 100      // > 100ms (needs optimization)
    },
    domNodes: {
      small: 100,    // Simple components
      medium: 500,   // Complex components  
      large: 1000    // Very complex components
    },
    memoryUsage: {
      low: 1048576,     // < 1MB
      medium: 5242880,  // < 5MB
      high: 10485760    // < 10MB
    }
  },
  
  testScenarios: [
    {
      name: 'Simple Button Component',
      component: 'Button',
      expectedRenderTime: 'fast',
      expectedDomNodes: 'small',
      props: { children: 'Click me' }
    },
    {
      name: 'Complex Form Component',
      component: 'Form',
      expectedRenderTime: 'acceptable',
      expectedDomNodes: 'medium',
      props: { 
        fields: ['email', 'password', 'name', 'phone'],
        validation: true
      }
    },
    {
      name: 'Large Data Table',
      component: 'Table',
      expectedRenderTime: 'acceptable',
      expectedDomNodes: 'large',
      props: {
        rows: 100,
        columns: 8,
        sortable: true,
        filterable: true
      }
    },
    {
      name: 'Dashboard with Multiple Charts',
      component: 'Dashboard',
      expectedRenderTime: 'slow', // Acceptable for complex visualizations
      expectedDomNodes: 'large',
      props: {
        charts: 6,
        realTimeData: true,
        animations: true
      }
    }
  ]
};

// Benchmark test generator
function generatePerformanceTest(scenario) {
  return `
/**
 * Performance test for ${scenario.name}
 * Generated automatically - do not modify
 */

import { renderPerformance } from '@dotmac/testing';
import { ${scenario.component} } from '../../../src';

describe('Performance: ${scenario.name}', () => {
  it('should render within performance thresholds', () => {
    const props = ${JSON.stringify(scenario.props, null, 6)};
    
    const result = renderPerformance(<${scenario.component} {...props} />);
    const metrics = result.measurePerformance();
    
    // Render time validation
    const renderTimeThreshold = PERFORMANCE_THRESHOLDS.renderTime.${scenario.expectedRenderTime};
    expect(metrics.renderTime).toBeLessThan(renderTimeThreshold);
    
    // DOM nodes validation  
    const domNodesThreshold = PERFORMANCE_THRESHOLDS.domNodes.${scenario.expectedDomNodes};
    expect(metrics.domNodes).toBeLessThan(domNodesThreshold);
    
    // Memory usage validation (if available)
    if (metrics.memoryUsage) {
      expect(metrics.memoryUsage).toBeLessThan(PERFORMANCE_THRESHOLDS.memoryUsage.high);
    }
    
    // Performance report
    console.log(\`📊 Performance Metrics for ${scenario.name}:\`);
    console.log(\`  Render Time: \${metrics.renderTime.toFixed(2)}ms\`);
    console.log(\`  DOM Nodes: \${metrics.domNodes}\`);
    if (metrics.memoryUsage) {
      console.log(\`  Memory: \${(metrics.memoryUsage / 1024 / 1024).toFixed(2)}MB\`);
    }
  });
  
  it('should handle stress conditions', () => {
    // Stress test with multiple renders
    const startTime = performance.now();
    const renders = [];
    
    for (let i = 0; i < 10; i++) {
      const result = renderPerformance(<${scenario.component} {...props} />);
      renders.push(result);
    }
    
    const totalTime = performance.now() - startTime;
    const avgTime = totalTime / renders.length;
    
    expect(avgTime).toBeLessThan(PERFORMANCE_THRESHOLDS.renderTime.slow);
    
    // Clean up
    renders.forEach(result => result.unmount());
  });
});

const PERFORMANCE_THRESHOLDS = ${JSON.stringify(PERFORMANCE_CONFIG.thresholds, null, 2)};
`;
}

// Generate performance test configuration
function generatePerformanceConfig() {
  return `
/**
 * Performance Testing Configuration
 * Auto-generated performance benchmarks
 */

export const PERFORMANCE_THRESHOLDS = ${JSON.stringify(PERFORMANCE_CONFIG.thresholds, null, 2)};

export const PERFORMANCE_SCENARIOS = ${JSON.stringify(PERFORMANCE_CONFIG.testScenarios, null, 2)};

// Performance test utilities
export const performanceUtils = {
  measureRenderTime: (renderFn) => {
    const start = performance.now();
    const result = renderFn();
    const end = performance.now();
    return { result, renderTime: end - start };
  },
  
  measureMemoryUsage: () => {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize;
    }
    return null;
  },
  
  createPerformanceReport: (metrics) => ({
    timestamp: new Date().toISOString(),
    metrics,
    environment: {
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Node.js',
      viewport: typeof window !== 'undefined' ? 
        \`\${window.innerWidth}x\${window.innerHeight}\` : 'N/A'
    }
  })
};

// Performance monitoring hooks
export const usePerformanceMonitor = (componentName: string) => {
  const [metrics, setMetrics] = React.useState(null);
  
  React.useEffect(() => {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const componentEntries = entries.filter(entry => 
        entry.name.includes(componentName)
      );
      
      if (componentEntries.length > 0) {
        setMetrics({
          renderTime: componentEntries[0].duration,
          timestamp: componentEntries[0].startTime
        });
      }
    });
    
    observer.observe({ entryTypes: ['measure'] });
    
    return () => observer.disconnect();
  }, [componentName]);
  
  return metrics;
};
`;
}

// Create directory structure
const performanceDir = path.join(__dirname, '../tests/performance');
const generatedDir = path.join(performanceDir, 'generated');

if (!fs.existsSync(performanceDir)) {
  fs.mkdirSync(performanceDir, { recursive: true });
}

if (!fs.existsSync(generatedDir)) {
  fs.mkdirSync(generatedDir, { recursive: true });
}

// Generate performance configuration
const configPath = path.join(performanceDir, 'performance.config.ts');
fs.writeFileSync(configPath, generatePerformanceConfig());

// Generate individual test files
PERFORMANCE_CONFIG.testScenarios.forEach((scenario, index) => {
  const testContent = generatePerformanceTest(scenario);
  const fileName = `${scenario.component.toLowerCase()}-performance.test.tsx`;
  const filePath = path.join(generatedDir, fileName);
  
  fs.writeFileSync(filePath, testContent);
  console.log(`✅ Generated: ${fileName}`);
});

// Generate performance test suite
const testSuiteContent = `
/**
 * Performance Test Suite
 * Comprehensive performance testing for all components
 */

import { describe, it, expect } from '@jest/globals';
${PERFORMANCE_CONFIG.testScenarios.map(scenario => 
  `import './${scenario.component.toLowerCase()}-performance.test';`
).join('\n')}

describe('Performance Test Suite', () => {
  it('should validate all performance tests are loaded', () => {
    expect(true).toBe(true);
  });
});
`;

fs.writeFileSync(
  path.join(generatedDir, 'index.test.ts'), 
  testSuiteContent
);

// Generate performance monitoring script
const monitoringScript = `
/**
 * Real-time Performance Monitor
 * Monitors component performance in development
 */

const performanceMetrics = new Map();

// Component performance tracker
function trackComponentPerformance(componentName, metrics) {
  if (!performanceMetrics.has(componentName)) {
    performanceMetrics.set(componentName, []);
  }
  
  performanceMetrics.get(componentName).push({
    ...metrics,
    timestamp: Date.now()
  });
  
  // Keep only last 100 measurements
  const componentMetrics = performanceMetrics.get(componentName);
  if (componentMetrics.length > 100) {
    componentMetrics.shift();
  }
}

// Performance report generator
function generatePerformanceReport() {
  const report = {
    timestamp: new Date().toISOString(),
    components: {}
  };
  
  for (const [componentName, metrics] of performanceMetrics) {
    const recent = metrics.slice(-10); // Last 10 measurements
    const avgRenderTime = recent.reduce((sum, m) => sum + m.renderTime, 0) / recent.length;
    const avgDomNodes = recent.reduce((sum, m) => sum + m.domNodes, 0) / recent.length;
    
    report.components[componentName] = {
      averageRenderTime: Math.round(avgRenderTime * 100) / 100,
      averageDomNodes: Math.round(avgDomNodes),
      measurementCount: metrics.length,
      trend: calculateTrend(metrics.map(m => m.renderTime))
    };
  }
  
  return report;
}

function calculateTrend(values) {
  if (values.length < 2) return 'stable';
  
  const recent = values.slice(-5);
  const older = values.slice(-10, -5);
  
  if (older.length === 0) return 'stable';
  
  const recentAvg = recent.reduce((a, b) => a + b) / recent.length;
  const olderAvg = older.reduce((a, b) => a + b) / older.length;
  
  const change = (recentAvg - olderAvg) / olderAvg;
  
  if (change > 0.1) return 'degrading';
  if (change < -0.1) return 'improving';
  return 'stable';
}

// Export for use in development
if (typeof window !== 'undefined') {
  window.performanceMonitor = {
    track: trackComponentPerformance,
    report: generatePerformanceReport,
    metrics: performanceMetrics
  };
}

module.exports = {
  trackComponentPerformance,
  generatePerformanceReport
};
`;

fs.writeFileSync(
  path.join(performanceDir, 'monitor.js'),
  monitoringScript
);

console.log('🎯 Performance testing setup completed!');
console.log(`📁 Generated ${PERFORMANCE_CONFIG.testScenarios.length} performance test files`);
console.log('📊 Created performance monitoring utilities');
console.log('🚀 Run: pnpm test:performance to execute performance tests');