import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import React from 'react';
import {
  PerformanceMonitor,
  usePerformanceMetrics,
  withPerformanceMonitoring,
  performanceAggregator,
  type PerformanceReport,
  type PerformanceMetrics
} from './PerformanceMonitor';
import { Card } from '@dotmac/primitives';

const meta: Meta<typeof PerformanceMonitor> = {
  title: 'Monitoring/PerformanceMonitor',
  component: PerformanceMonitor,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
Universal PerformanceMonitor component for tracking and optimizing application performance.

## Features
- Web Vitals monitoring (CLS, FCP, FID, LCP, TTFB)
- Component render time tracking
- Memory usage monitoring
- Automatic performance reporting
- Threshold-based warnings and recommendations
- HOC wrapper for easy integration
- Performance aggregation and analytics

## Usage
\`\`\`tsx
import { PerformanceMonitor, withPerformanceMonitoring } from '@dotmac/monitoring';

// Wrap components
<PerformanceMonitor
  componentName="MyComponent"
  onReport={handlePerformanceReport}
>
  <MyComponent />
</PerformanceMonitor>

// Or use HOC
const MonitoredComponent = withPerformanceMonitoring(MyComponent, {
  componentName: 'MyComponent',
  onReport: handlePerformanceReport
});
\`\`\`
      `,
    },
    performance: {
      allowedGroups: ['paint', 'interaction', 'measure', 'navigation'],
    },
  },
  tags: ['autodocs', 'monitoring', 'performance'],
  argTypes: {
    componentName: {
      control: 'text',
      description: 'Name of the component being monitored',
    },
    enableWebVitals: {
      control: 'boolean',
      description: 'Enable Web Vitals monitoring',
    },
    enableComponentMetrics: {
      control: 'boolean',
      description: 'Enable component-specific performance metrics',
    },
    reportInterval: {
      control: 'number',
      description: 'Interval for performance reports in milliseconds',
    },
    disabled: {
      control: 'boolean',
      description: 'Disable performance monitoring',
    },
  },
  args: {
    onReport: fn(),
  },
} satisfies Meta<typeof PerformanceMonitor>;

export default meta;
type Story = StoryObj<typeof meta>;

// Sample component to monitor
const SampleComponent: React.FC<{ complexity?: 'low' | 'medium' | 'high' }> = ({
  complexity = 'low'
}) => {
  const [count, setCount] = React.useState(0);
  const [items, setItems] = React.useState<number[]>([]);

  // Simulate different levels of computational complexity
  React.useEffect(() => {
    let itemCount = 10;
    if (complexity === 'medium') itemCount = 100;
    if (complexity === 'high') itemCount = 1000;

    // Intentionally expensive operation for demonstration
    const newItems = Array.from({ length: itemCount }, (_, i) => {
      // Some computation to simulate real work
      let result = i;
      for (let j = 0; j < (complexity === 'high' ? 1000 : 100); j++) {
        result = Math.sqrt(result + j) * Math.random();
      }
      return Math.floor(result);
    });

    setItems(newItems);
  }, [complexity]);

  return (
    <Card className="p-6 max-w-md">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Sample Component</h3>
        <p className="text-sm text-gray-600">
          Complexity: <span className="font-medium">{complexity}</span>
        </p>
        <p className="text-sm text-gray-600">
          Items processed: <span className="font-medium">{items.length}</span>
        </p>

        <div className="space-y-2">
          <button
            onClick={() => setCount(count + 1)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Count: {count}
          </button>

          {complexity === 'high' && (
            <div className="text-xs text-orange-600">
              High complexity mode - expect performance warnings
            </div>
          )}
        </div>

        <div className="bg-gray-50 p-3 rounded text-xs">
          <strong>Items:</strong> {items.slice(0, 10).join(', ')}
          {items.length > 10 && '...'}
        </div>
      </div>
    </Card>
  );
};

// Basic usage
export const Default: Story = {
  args: {
    componentName: 'SampleComponent',
    enableWebVitals: true,
    enableComponentMetrics: true,
    reportInterval: 5000, // 5 seconds for demo
  },
  render: (args) => (
    <PerformanceMonitor {...args}>
      <SampleComponent />
    </PerformanceMonitor>
  ),
};

// Monitoring disabled
export const Disabled: Story = {
  args: {
    componentName: 'SampleComponent',
    disabled: true,
  },
  render: (args) => (
    <PerformanceMonitor {...args}>
      <SampleComponent />
    </PerformanceMonitor>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Performance monitoring disabled - no metrics will be collected.',
      },
    },
  },
};

// Web Vitals only
export const WebVitalsOnly: Story = {
  args: {
    componentName: 'SampleComponent',
    enableWebVitals: true,
    enableComponentMetrics: false,
  },
  render: (args) => (
    <PerformanceMonitor {...args}>
      <SampleComponent />
    </PerformanceMonitor>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Monitor only Web Vitals (CLS, FCP, FID, LCP, TTFB).',
      },
    },
  },
};

// Component metrics only
export const ComponentMetricsOnly: Story = {
  args: {
    componentName: 'SampleComponent',
    enableWebVitals: false,
    enableComponentMetrics: true,
  },
  render: (args) => (
    <PerformanceMonitor {...args}>
      <SampleComponent />
    </PerformanceMonitor>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Monitor only component-specific metrics (render time, memory usage).',
      },
    },
  },
};

// High complexity component (performance warnings expected)
export const HighComplexityComponent: Story = {
  args: {
    componentName: 'HighComplexityComponent',
    thresholds: {
      renderTime: 10, // Lower threshold to trigger warnings
    },
    reportInterval: 3000,
  },
  render: (args) => (
    <PerformanceMonitor {...args}>
      <SampleComponent complexity="high" />
    </PerformanceMonitor>
  ),
  parameters: {
    docs: {
      description: {
        story: 'High complexity component that should trigger performance warnings.',
      },
    },
  },
};

// Custom thresholds
export const CustomThresholds: Story = {
  args: {
    componentName: 'CustomThresholdComponent',
    thresholds: {
      renderTime: 5, // Very strict render time threshold
      memoryUsage: 10 * 1024 * 1024, // 10MB memory threshold
    },
    reportInterval: 5000,
  },
  render: (args) => (
    <PerformanceMonitor {...args}>
      <SampleComponent complexity="medium" />
    </PerformanceMonitor>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Component with custom performance thresholds.',
      },
    },
  },
};

// Using the usePerformanceMetrics hook
export const UsingPerformanceHook: Story = {
  render: () => {
    const PerformanceHookDemo: React.FC = () => {
      const { metrics, isTracking, startTracking, stopTracking, addCustomMetric } =
        usePerformanceMetrics('HookDemo');
      const [operationCount, setOperationCount] = React.useState(0);

      const runExpensiveOperation = () => {
        startTracking();

        // Simulate expensive operation
        setTimeout(() => {
          const result = Array.from({ length: 10000 }, (_, i) => Math.sqrt(i));
          setOperationCount(prev => prev + 1);
          addCustomMetric('operationCount', operationCount + 1);
          addCustomMetric('resultLength', result.length);
          stopTracking();
        }, Math.random() * 100 + 50); // Random delay 50-150ms
      };

      return (
        <Card className="p-6 max-w-md">
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Performance Hook Demo</h3>

            <div className="space-y-2">
              <button
                onClick={runExpensiveOperation}
                disabled={isTracking}
                className={`px-4 py-2 text-white rounded ${
                  isTracking
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700'
                }`}
              >
                {isTracking ? 'Running...' : 'Run Operation'}
              </button>

              <p className="text-sm text-gray-600">
                Operations completed: {operationCount}
              </p>
            </div>

            <div className="bg-gray-50 p-3 rounded text-sm">
              <h4 className="font-medium mb-2">Current Metrics:</h4>
              <pre className="text-xs">
                {JSON.stringify(metrics, null, 2)}
              </pre>
            </div>
          </div>
        </Card>
      );
    };

    return <PerformanceHookDemo />;
  },
  parameters: {
    docs: {
      description: {
        story: 'Demonstrates using the usePerformanceMetrics hook for manual tracking.',
      },
    },
  },
};

// HOC wrapper example
export const HOCWrapper: Story = {
  render: () => {
    // Create a monitored version of the component
    const MonitoredComponent = withPerformanceMonitoring(SampleComponent, {
      componentName: 'HOC-WrappedComponent',
      onReport: (report) => {
        console.log('Performance Report:', report);
      },
      reportInterval: 5000,
    });

    return (
      <div className="space-y-4">
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">HOC Wrapped Component</h3>
          <p className="text-sm text-gray-600 mb-4">
            This component is automatically monitored using withPerformanceMonitoring HOC
          </p>
        </div>
        <MonitoredComponent complexity="medium" />
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Component wrapped with the withPerformanceMonitoring HOC.',
      },
    },
  },
};

// Performance comparison
export const PerformanceComparison: Story = {
  render: () => {
    const [showReports, setShowReports] = React.useState(false);
    const [reports, setReports] = React.useState<PerformanceReport[]>([]);

    React.useEffect(() => {
      const unsubscribe = performanceAggregator.onReport((report) => {
        setReports(prev => [...prev.slice(-9), report]); // Keep last 10 reports
      });

      return unsubscribe;
    }, []);

    const handleReport = (report: PerformanceReport) => {
      performanceAggregator.addReport(report);
    };

    return (
      <div className="space-y-6">
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">Performance Comparison</h3>
          <button
            onClick={() => setShowReports(!showReports)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {showReports ? 'Hide' : 'Show'} Performance Reports
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <h4 className="font-medium mb-2 text-center">Low Complexity</h4>
            <PerformanceMonitor
              componentName="LowComplexity"
              onReport={handleReport}
              reportInterval={3000}
            >
              <SampleComponent complexity="low" />
            </PerformanceMonitor>
          </div>

          <div>
            <h4 className="font-medium mb-2 text-center">Medium Complexity</h4>
            <PerformanceMonitor
              componentName="MediumComplexity"
              onReport={handleReport}
              reportInterval={3000}
            >
              <SampleComponent complexity="medium" />
            </PerformanceMonitor>
          </div>

          <div>
            <h4 className="font-medium mb-2 text-center">High Complexity</h4>
            <PerformanceMonitor
              componentName="HighComplexity"
              onReport={handleReport}
              reportInterval={3000}
              thresholds={{ renderTime: 10 }}
            >
              <SampleComponent complexity="high" />
            </PerformanceMonitor>
          </div>
        </div>

        {showReports && (
          <div className="mt-6">
            <h4 className="font-medium mb-3">Recent Performance Reports</h4>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {reports.length === 0 ? (
                <p className="text-sm text-gray-500">No reports yet. Wait for components to report...</p>
              ) : (
                reports.map((report, index) => (
                  <Card key={index} className="p-3">
                    <div className="text-sm">
                      <div className="flex justify-between items-start mb-2">
                        <strong>{report.componentName}</strong>
                        <span className="text-xs text-gray-500">
                          {report.timestamp.toLocaleTimeString()}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 mb-2">
                        {Object.entries(report.metrics).map(([key, value]) => (
                          <div key={key} className="text-xs">
                            <span className="font-medium">{key}:</span>{' '}
                            {typeof value === 'number' ? value.toFixed(2) : value}
                          </div>
                        ))}
                      </div>

                      {report.warnings.length > 0 && (
                        <div className="mt-2">
                          <strong className="text-red-600">Warnings:</strong>
                          {report.warnings.map((warning, i) => (
                            <div key={i} className="text-xs text-red-600 ml-2">
                              • {warning.message}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    );
  },
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        story: 'Compare performance across different component complexities with real-time reporting.',
      },
    },
  },
};

// Real-time metrics dashboard
export const RealTimeMetrics: Story = {
  render: () => {
    const [currentMetrics, setCurrentMetrics] = React.useState<PerformanceMetrics>({});
    const [isMonitoring, setIsMonitoring] = React.useState(true);

    const handleReport = React.useCallback((report: PerformanceReport) => {
      setCurrentMetrics(report.metrics);
    }, []);

    const MetricsDisplay: React.FC<{ metrics: PerformanceMetrics }> = ({ metrics }) => (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Object.entries(metrics).map(([key, value]) => {
          if (typeof value !== 'number') return null;

          let displayValue = value.toFixed(2);
          let unit = '';
          let color = 'text-blue-600';

          // Format different metric types
          switch (key) {
            case 'cls':
              displayValue = value.toFixed(3);
              color = value > 0.1 ? 'text-red-600' : value > 0.05 ? 'text-yellow-600' : 'text-green-600';
              break;
            case 'fcp':
            case 'lcp':
            case 'ttfb':
            case 'renderTime':
              unit = 'ms';
              color = value > 1000 ? 'text-red-600' : value > 500 ? 'text-yellow-600' : 'text-green-600';
              break;
            case 'fid':
              unit = 'ms';
              color = value > 100 ? 'text-red-600' : value > 50 ? 'text-yellow-600' : 'text-green-600';
              break;
            case 'memoryUsage':
              displayValue = (value / 1024 / 1024).toFixed(1);
              unit = 'MB';
              color = value > 50 * 1024 * 1024 ? 'text-red-600' : 'text-blue-600';
              break;
          }

          return (
            <Card key={key} className="p-4 text-center">
              <div className="text-xs text-gray-600 uppercase tracking-wide mb-1">
                {key.replace(/([A-Z])/g, ' $1').trim()}
              </div>
              <div className={`text-2xl font-bold ${color}`}>
                {displayValue}
                <span className="text-sm ml-1">{unit}</span>
              </div>
            </Card>
          );
        })}
      </div>
    );

    return (
      <div className="space-y-6">
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">Real-time Performance Metrics</h3>
          <button
            onClick={() => setIsMonitoring(!isMonitoring)}
            className={`px-4 py-2 text-white rounded ${
              isMonitoring
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isMonitoring ? 'Stop' : 'Start'} Monitoring
          </button>
        </div>

        <MetricsDisplay metrics={currentMetrics} />

        <div className="border-t pt-4">
          <PerformanceMonitor
            componentName="RealTimeDemo"
            onReport={handleReport}
            reportInterval={2000} // Update every 2 seconds
            disabled={!isMonitoring}
          >
            <SampleComponent complexity="medium" />
          </PerformanceMonitor>
        </div>
      </div>
    );
  },
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        story: 'Real-time performance metrics dashboard with live updates.',
      },
    },
  },
};

// Performance optimization guide
export const OptimizationGuide: Story = {
  render: () => {
    const [selectedTip, setSelectedTip] = React.useState<string | null>(null);

    const optimizationTips = [
      {
        metric: 'Render Time',
        threshold: '> 16ms',
        tips: [
          'Use React.memo() to prevent unnecessary re-renders',
          'Implement useCallback() and useMemo() for expensive calculations',
          'Consider virtualization for large lists',
          'Break large components into smaller ones',
          'Use lazy loading for heavy components'
        ]
      },
      {
        metric: 'Memory Usage',
        threshold: '> 50MB',
        tips: [
          'Remove unused dependencies and imports',
          'Clean up event listeners and subscriptions',
          'Avoid creating objects in render methods',
          'Use object pooling for frequently created objects',
          'Profile memory usage in DevTools'
        ]
      },
      {
        metric: 'First Contentful Paint',
        threshold: '> 1.8s',
        tips: [
          'Optimize fonts and use font-display: swap',
          'Minimize critical CSS',
          'Preload important resources',
          'Reduce server response time',
          'Use efficient image formats (WebP, AVIF)'
        ]
      },
      {
        metric: 'Largest Contentful Paint',
        threshold: '> 2.5s',
        tips: [
          'Optimize images and use proper sizing',
          'Preload LCP element resources',
          'Remove unused CSS and JavaScript',
          'Use a CDN for static assets',
          'Implement effective caching strategies'
        ]
      },
      {
        metric: 'Cumulative Layout Shift',
        threshold: '> 0.1',
        tips: [
          'Always include size attributes for images and videos',
          'Reserve space for ads and embeds',
          'Avoid inserting content above existing content',
          'Use CSS transforms instead of changing layout properties',
          'Preload fonts to prevent layout shifts'
        ]
      }
    ];

    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center">
          <h3 className="text-2xl font-bold mb-4">Performance Optimization Guide</h3>
          <p className="text-gray-600">
            Click on a performance metric below to see optimization recommendations
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {optimizationTips.map((tip) => (
            <Card
              key={tip.metric}
              className={`p-4 cursor-pointer transition-all hover:shadow-lg ${
                selectedTip === tip.metric ? 'ring-2 ring-blue-500' : ''
              }`}
              onClick={() => setSelectedTip(selectedTip === tip.metric ? null : tip.metric)}
            >
              <h4 className="font-semibold text-lg">{tip.metric}</h4>
              <p className="text-sm text-gray-600 mt-1">
                Threshold: <span className="font-mono">{tip.threshold}</span>
              </p>
              <p className="text-xs text-blue-600 mt-2">
                Click to view optimization tips →
              </p>
            </Card>
          ))}
        </div>

        {selectedTip && (
          <Card className="p-6">
            <h4 className="text-xl font-bold mb-4">
              Optimizing {selectedTip}
            </h4>
            <div className="space-y-3">
              {optimizationTips
                .find(tip => tip.metric === selectedTip)
                ?.tips.map((tipText, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                    <p className="text-gray-700">{tipText}</p>
                  </div>
                ))
              }
            </div>
          </Card>
        )}

        <div className="text-center text-sm text-gray-500">
          <p>
            Performance thresholds based on{' '}
            <a
              href="https://web.dev/vitals/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              Web Vitals
            </a>{' '}
            and React best practices
          </p>
        </div>
      </div>
    );
  },
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        story: 'Interactive guide for performance optimization with actionable tips.',
      },
    },
  },
};
