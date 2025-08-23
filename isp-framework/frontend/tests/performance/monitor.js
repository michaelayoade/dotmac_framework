
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
