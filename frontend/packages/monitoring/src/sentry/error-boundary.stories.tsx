import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import React from 'react';
import { SentryErrorBoundary, withErrorBoundary } from './error-boundary';
import { Card, Button } from '@dotmac/primitives';

// Mock types if they don't exist
type PortalType = 'admin' | 'customer' | 'reseller' | 'technician' | 'management';
type ErrorSeverity = 'error' | 'warning' | 'info' | 'debug';

const meta: Meta<typeof SentryErrorBoundary> = {
  title: 'Monitoring/SentryErrorBoundary',
  component: SentryErrorBoundary,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: `
Production-ready Sentry Error Boundary for comprehensive error handling and user feedback.

## Features
- Automatic error reporting to Sentry
- User feedback dialog integration
- Portal-specific error handling
- Custom fallback UI support
- Error recovery mechanisms
- Development vs production error display
- HOC wrapper for easy integration

## Usage
\`\`\`tsx
import { SentryErrorBoundary, withErrorBoundary } from '@dotmac/monitoring';

// Wrap components
<SentryErrorBoundary
  portalType="admin"
  showDialog={true}
  onError={handleError}
>
  <MyComponent />
</SentryErrorBoundary>

// Or use HOC
const SafeComponent = withErrorBoundary(MyComponent, {
  portalType: 'admin',
  showDialog: true
});
\`\`\`
      `,
    },
  },
  tags: ['autodocs', 'monitoring', 'error-handling'],
  argTypes: {
    portalType: {
      control: { type: 'select' },
      options: ['admin', 'customer', 'reseller', 'technician', 'management'],
      description: 'Portal type for error context',
    },
    showDialog: {
      control: 'boolean',
      description: 'Show Sentry user feedback dialog on errors',
    },
    enableReporting: {
      control: 'boolean',
      description: 'Enable error reporting to Sentry',
    },
    level: {
      control: { type: 'select' },
      options: ['error', 'warning', 'info', 'debug'],
      description: 'Error severity level',
    },
  },
  args: {
    onError: fn(),
    beforeCapture: fn(),
  },
} satisfies Meta<typeof SentryErrorBoundary>;

export default meta;
type Story = StoryObj<typeof meta>;

// Component that can trigger errors for testing
const ErrorProneComponent: React.FC<{
  errorType?: 'render' | 'async' | 'network' | 'none';
  errorMessage?: string;
  children?: React.ReactNode;
}> = ({
  errorType = 'none',
  errorMessage = 'Test error occurred',
  children
}) => {
  const [shouldThrow, setShouldThrow] = React.useState(false);
  const [asyncError, setAsyncError] = React.useState<string | null>(null);

  // Trigger render error
  if (shouldThrow && errorType === 'render') {
    throw new Error(errorMessage);
  }

  // Handle async error
  const triggerAsyncError = async () => {
    try {
      if (errorType === 'async') {
        throw new Error(errorMessage);
      }
      if (errorType === 'network') {
        // Simulate network error
        const response = await fetch('https://nonexistent-api.example.com/data');
        if (!response.ok) throw new Error('Network request failed');
      }
    } catch (error) {
      setAsyncError((error as Error).message);
      throw error; // Re-throw to be caught by error boundary
    }
  };

  return (
    <Card className="p-6 max-w-md mx-auto">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Error Testing Component</h3>
        <p className="text-sm text-gray-600">
          Current error type: <span className="font-medium">{errorType}</span>
        </p>

        {children}

        <div className="space-y-2">
          {errorType === 'render' && (
            <Button
              onClick={() => setShouldThrow(true)}
              variant="destructive"
              className="w-full"
            >
              Trigger Render Error
            </Button>
          )}

          {(errorType === 'async' || errorType === 'network') && (
            <Button
              onClick={triggerAsyncError}
              variant="destructive"
              className="w-full"
            >
              Trigger {errorType === 'async' ? 'Async' : 'Network'} Error
            </Button>
          )}

          {errorType === 'none' && (
            <div className="text-center text-green-600 font-medium">
              ✅ No errors - component is working normally
            </div>
          )}
        </div>

        {asyncError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            Async Error: {asyncError}
          </div>
        )}
      </div>
    </Card>
  );
};

// Basic error boundary
export const Default: Story = {
  args: {
    portalType: 'admin' as PortalType,
    showDialog: false,
    enableReporting: true,
  },
  render: (args) => (
    <SentryErrorBoundary {...args}>
      <ErrorProneComponent />
    </SentryErrorBoundary>
  ),
};

// Error boundary with render error
export const WithRenderError: Story = {
  args: {
    portalType: 'admin' as PortalType,
    showDialog: false,
    enableReporting: true,
  },
  render: (args) => (
    <SentryErrorBoundary {...args}>
      <ErrorProneComponent
        errorType="render"
        errorMessage="This is a simulated render error for testing purposes"
      />
    </SentryErrorBoundary>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Error boundary catching a render error. Click the button to trigger the error.',
      },
    },
  },
};

// Portal-specific error boundaries
export const AdminPortalError: Story = {
  args: {
    portalType: 'admin' as PortalType,
    showDialog: true,
    enableReporting: true,
    tags: { feature: 'admin-dashboard' },
  },
  render: (args) => (
    <SentryErrorBoundary {...args}>
      <ErrorProneComponent
        errorType="render"
        errorMessage="Admin portal component failed to render"
      >
        <div className="text-blue-600 text-sm mb-2">
          🔧 Admin Portal Context
        </div>
      </ErrorProneComponent>
    </SentryErrorBoundary>
  ),
  parameters: {
    portal: 'admin',
  },
};

export const CustomerPortalError: Story = {
  args: {
    portalType: 'customer' as PortalType,
    showDialog: true,
    enableReporting: true,
    tags: { feature: 'customer-dashboard' },
  },
  render: (args) => (
    <SentryErrorBoundary {...args}>
      <ErrorProneComponent
        errorType="render"
        errorMessage="Customer portal component failed to render"
      >
        <div className="text-green-600 text-sm mb-2">
          👤 Customer Portal Context
        </div>
      </ErrorProneComponent>
    </SentryErrorBoundary>
  ),
  parameters: {
    portal: 'customer',
  },
};

export const ResellerPortalError: Story = {
  args: {
    portalType: 'reseller' as PortalType,
    showDialog: true,
    enableReporting: true,
    tags: { feature: 'reseller-dashboard' },
  },
  render: (args) => (
    <SentryErrorBoundary {...args}>
      <ErrorProneComponent
        errorType="render"
        errorMessage="Reseller portal component failed to render"
      >
        <div className="text-purple-600 text-sm mb-2">
          🏢 Reseller Portal Context
        </div>
      </ErrorProneComponent>
    </SentryErrorBoundary>
  ),
  parameters: {
    portal: 'reseller',
  },
};

// Custom fallback UI
export const WithCustomFallback: Story = {
  args: {
    portalType: 'admin' as PortalType,
    showDialog: false,
    enableReporting: true,
    fallback: (error: Error, eventId: string) => (
      <div className="min-h-64 flex items-center justify-center bg-gradient-to-br from-red-50 to-pink-50">
        <Card className="p-8 max-w-lg mx-4">
          <div className="text-center space-y-4">
            <div className="text-6xl">🚨</div>
            <h2 className="text-2xl font-bold text-red-700">
              Custom Error Handler
            </h2>
            <p className="text-red-600">
              {error.message}
            </p>
            {eventId && (
              <div className="bg-red-100 p-3 rounded font-mono text-sm">
                Event ID: {eventId}
              </div>
            )}
            <Button
              onClick={() => window.location.reload()}
              variant="destructive"
            >
              Reload Application
            </Button>
          </div>
        </Card>
      </div>
    ),
  },
  render: (args) => (
    <SentryErrorBoundary {...args}>
      <ErrorProneComponent
        errorType="render"
        errorMessage="Error handled by custom fallback UI"
      />
    </SentryErrorBoundary>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Error boundary with custom fallback UI instead of the default error page.',
      },
    },
  },
};

// Error boundary with user feedback dialog
export const WithUserFeedback: Story = {
  args: {
    portalType: 'admin' as PortalType,
    showDialog: true,
    enableReporting: true,
  },
  render: (args) => (
    <SentryErrorBoundary {...args}>
      <ErrorProneComponent
        errorType="render"
        errorMessage="Error that will show user feedback dialog"
      >
        <div className="bg-blue-50 p-3 rounded text-sm text-blue-700 mb-2">
          💬 This error will show a user feedback dialog when triggered
        </div>
      </ErrorProneComponent>
    </SentryErrorBoundary>
  ),
  parameters: {
    docs: {
      description: {
        story: 'Error boundary that shows Sentry user feedback dialog for error reporting.',
      },
    },
  },
};

// Error severity levels
export const ErrorSeverityLevels: Story = {
  render: () => (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-center">Error Severity Levels</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(['error', 'warning', 'info', 'debug'] as const).map((level) => (
          <SentryErrorBoundary
            key={level}
            portalType="admin"
            level={level}
            enableReporting={true}
            tags={{ severity: level }}
          >
            <ErrorProneComponent
              errorType="render"
              errorMessage={`${level.toUpperCase()} level error`}
            >
              <div className="text-center mb-2">
                <span className={`inline-block px-3 py-1 rounded text-sm font-medium ${
                  level === 'error' ? 'bg-red-100 text-red-700' :
                  level === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                  level === 'info' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {level.toUpperCase()} Level
                </span>
              </div>
            </ErrorProneComponent>
          </SentryErrorBoundary>
        ))}
      </div>
    </div>
  ),
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        story: 'Different error severity levels for categorizing errors in Sentry.',
      },
    },
  },
};

// HOC wrapper example
export const HOCWrapper: Story = {
  render: () => {
    // Create a component wrapped with error boundary
    const SafeErrorProneComponent = withErrorBoundary(ErrorProneComponent, {
      portalType: 'admin',
      showDialog: false,
      enableReporting: true,
      tags: { wrapped: 'true' },
    });

    return (
      <div className="space-y-4">
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">HOC Wrapped Component</h3>
          <p className="text-sm text-gray-600 mb-4">
            This component is automatically wrapped with an error boundary using the HOC
          </p>
        </div>
        <SafeErrorProneComponent
          errorType="render"
          errorMessage="Error from HOC-wrapped component"
        />
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Component wrapped with error boundary using the withErrorBoundary HOC.',
      },
    },
  },
};

// Error recovery demonstration
export const ErrorRecovery: Story = {
  render: () => {
    const [errorKey, setErrorKey] = React.useState(0);
    const [hasTriggeredError, setHasTriggeredError] = React.useState(false);

    return (
      <div className="space-y-4">
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">Error Recovery</h3>
          <p className="text-sm text-gray-600 mb-4">
            Demonstrates error boundary recovery mechanisms
          </p>
          <Button
            onClick={() => {
              setErrorKey(prev => prev + 1);
              setHasTriggeredError(false);
            }}
            className="mb-4"
          >
            Reset Component
          </Button>
        </div>

        <SentryErrorBoundary
          key={errorKey} // Force remount on reset
          portalType="admin"
          showDialog={false}
          enableReporting={true}
          onError={() => setHasTriggeredError(true)}
        >
          <ErrorProneComponent
            errorType={hasTriggeredError ? 'none' : 'render'}
            errorMessage="Recoverable component error"
          >
            <div className="text-sm text-gray-600 mb-2">
              Component state: {hasTriggeredError ? '❌ Error occurred' : '✅ Working normally'}
            </div>
          </ErrorProneComponent>
        </SentryErrorBoundary>
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Demonstrates error recovery by resetting the error boundary state.',
      },
    },
  },
};

// Multiple nested error boundaries
export const NestedErrorBoundaries: Story = {
  render: () => {
    const InnerComponent = () => (
      <ErrorProneComponent
        errorType="render"
        errorMessage="Inner component error"
      >
        <div className="bg-red-50 p-2 rounded text-sm">
          Inner Component (will throw error)
        </div>
      </ErrorProneComponent>
    );

    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-center">Nested Error Boundaries</h3>

        {/* Outer error boundary */}
        <SentryErrorBoundary
          portalType="admin"
          showDialog={false}
          enableReporting={true}
          tags={{ boundary: 'outer' }}
        >
          <Card className="p-4">
            <h4 className="font-medium mb-2">Outer Boundary</h4>

            {/* Inner error boundary */}
            <SentryErrorBoundary
              portalType="admin"
              showDialog={false}
              enableReporting={true}
              tags={{ boundary: 'inner' }}
            >
              <Card className="p-3 bg-gray-50">
                <h5 className="font-medium mb-2">Inner Boundary</h5>
                <InnerComponent />
              </Card>
            </SentryErrorBoundary>
          </Card>
        </SentryErrorBoundary>
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Nested error boundaries showing how errors are caught at the appropriate level.',
      },
    },
  },
};

// Development vs Production error display
export const DevelopmentVsProduction: Story = {
  render: () => {
    const [isDevelopment, setIsDevelopment] = React.useState(false);

    // Temporarily override NODE_ENV for demonstration
    const originalEnv = process.env.NODE_ENV;
    if (isDevelopment && originalEnv !== 'development') {
      process.env.NODE_ENV = 'development';
    } else if (!isDevelopment && originalEnv === 'development') {
      process.env.NODE_ENV = 'production';
    }

    return (
      <div className="space-y-4">
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-2">Development vs Production</h3>
          <div className="flex justify-center gap-2 mb-4">
            <Button
              onClick={() => setIsDevelopment(false)}
              variant={!isDevelopment ? 'default' : 'outline'}
              size="sm"
            >
              Production Mode
            </Button>
            <Button
              onClick={() => setIsDevelopment(true)}
              variant={isDevelopment ? 'default' : 'outline'}
              size="sm"
            >
              Development Mode
            </Button>
          </div>
          <p className="text-sm text-gray-600">
            Current mode: <strong>{isDevelopment ? 'Development' : 'Production'}</strong>
          </p>
        </div>

        <SentryErrorBoundary
          portalType="admin"
          showDialog={false}
          enableReporting={true}
        >
          <ErrorProneComponent
            errorType="render"
            errorMessage="Detailed error message that shows differently in dev vs prod"
          />
        </SentryErrorBoundary>
      </div>
    );
  },
  parameters: {
    docs: {
      description: {
        story: 'Shows how error messages are displayed differently in development vs production.',
      },
    },
  },
};

// Performance impact demonstration
export const PerformanceImpact: Story = {
  render: () => {
    const [componentsCount, setComponentsCount] = React.useState(100);
    const [withErrorBoundary, setWithErrorBoundary] = React.useState(true);

    const components = Array.from({ length: componentsCount }, (_, i) => i);

    const SimpleComponent = ({ id }: { id: number }) => (
      <div className="p-2 bg-blue-50 rounded text-xs">
        Component {id}
      </div>
    );

    const renderComponents = () => {
      if (withErrorBoundary) {
        return components.map(id => (
          <SentryErrorBoundary
            key={id}
            portalType="admin"
            enableReporting={false} // Disable for performance test
          >
            <SimpleComponent id={id} />
          </SentryErrorBoundary>
        ));
      } else {
        return components.map(id => (
          <SimpleComponent key={id} id={id} />
        ));
      }
    };

    return (
      <div className="space-y-4">
        <div className="text-center">
          <h3 className="text-lg font-semibold mb-4">Performance Impact</h3>
          <div className="flex justify-center gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Components:</label>
              <input
                type="range"
                min="10"
                max="500"
                value={componentsCount}
                onChange={(e) => setComponentsCount(Number(e.target.value))}
                className="w-32"
              />
              <div className="text-sm text-gray-600">{componentsCount}</div>
            </div>
            <div className="flex items-center">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={withErrorBoundary}
                  onChange={(e) => setWithErrorBoundary(e.target.checked)}
                />
                <span className="text-sm">With Error Boundaries</span>
              </label>
            </div>
          </div>
        </div>

        <div className="border rounded p-4 max-h-96 overflow-y-auto">
          <div className="grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-1">
            {renderComponents()}
          </div>
        </div>

        <div className="text-xs text-gray-500 text-center">
          Rendering {componentsCount} components {withErrorBoundary ? 'with' : 'without'} error boundaries
        </div>
      </div>
    );
  },
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        story: 'Demonstrates the performance impact of wrapping many components with error boundaries.',
      },
    },
  },
};
