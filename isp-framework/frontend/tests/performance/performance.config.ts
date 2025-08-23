
/**
 * Performance Testing Configuration
 * Auto-generated performance benchmarks
 */

export const PERFORMANCE_THRESHOLDS = {
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

export const PERFORMANCE_SCENARIOS = [
  {
    "name": "Simple Button Component",
    "component": "Button",
    "expectedRenderTime": "fast",
    "expectedDomNodes": "small",
    "props": {
      "children": "Click me"
    }
  },
  {
    "name": "Complex Form Component",
    "component": "Form",
    "expectedRenderTime": "acceptable",
    "expectedDomNodes": "medium",
    "props": {
      "fields": [
        "email",
        "password",
        "name",
        "phone"
      ],
      "validation": true
    }
  },
  {
    "name": "Large Data Table",
    "component": "Table",
    "expectedRenderTime": "acceptable",
    "expectedDomNodes": "large",
    "props": {
      "rows": 100,
      "columns": 8,
      "sortable": true,
      "filterable": true
    }
  },
  {
    "name": "Dashboard with Multiple Charts",
    "component": "Dashboard",
    "expectedRenderTime": "slow",
    "expectedDomNodes": "large",
    "props": {
      "charts": 6,
      "realTimeData": true,
      "animations": true
    }
  }
];

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
        `${window.innerWidth}x${window.innerHeight}` : 'N/A'
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
