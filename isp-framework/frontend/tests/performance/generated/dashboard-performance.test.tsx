
/**
 * Performance test for Dashboard with Multiple Charts
 * Generated automatically - do not modify
 */

import { renderPerformance } from '@dotmac/testing';
import { Dashboard } from '../../../src';

describe('Performance: Dashboard with Multiple Charts', () => {
  it('should render within performance thresholds', () => {
    const props = {
      "charts": 6,
      "realTimeData": true,
      "animations": true
};
    
    const result = renderPerformance(<Dashboard {...props} />);
    const metrics = result.measurePerformance();
    
    // Render time validation
    const renderTimeThreshold = PERFORMANCE_THRESHOLDS.renderTime.slow;
    expect(metrics.renderTime).toBeLessThan(renderTimeThreshold);
    
    // DOM nodes validation  
    const domNodesThreshold = PERFORMANCE_THRESHOLDS.domNodes.large;
    expect(metrics.domNodes).toBeLessThan(domNodesThreshold);
    
    // Memory usage validation (if available)
    if (metrics.memoryUsage) {
      expect(metrics.memoryUsage).toBeLessThan(PERFORMANCE_THRESHOLDS.memoryUsage.high);
    }
    
    // Performance report
    console.log(`📊 Performance Metrics for Dashboard with Multiple Charts:`);
    console.log(`  Render Time: ${metrics.renderTime.toFixed(2)}ms`);
    console.log(`  DOM Nodes: ${metrics.domNodes}`);
    if (metrics.memoryUsage) {
      console.log(`  Memory: ${(metrics.memoryUsage / 1024 / 1024).toFixed(2)}MB`);
    }
  });
  
  it('should handle stress conditions', () => {
    // Stress test with multiple renders
    const startTime = performance.now();
    const renders = [];
    
    for (let i = 0; i < 10; i++) {
      const result = renderPerformance(<Dashboard {...props} />);
      renders.push(result);
    }
    
    const totalTime = performance.now() - startTime;
    const avgTime = totalTime / renders.length;
    
    expect(avgTime).toBeLessThan(PERFORMANCE_THRESHOLDS.renderTime.slow);
    
    // Clean up
    renders.forEach(result => result.unmount());
  });
});

const PERFORMANCE_THRESHOLDS = {
  "renderTime": {
    "fast": 16,
    "acceptable": 50,
    "slow": 100
  },
  "domNodes": {
    "small": 100,
    "medium": 500,
    "large": 1000
  },
  "memoryUsage": {
    "low": 1048576,
    "medium": 5242880,
    "high": 10485760
  }
};
