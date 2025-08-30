import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';
import { Button, Card, Input } from '@dotmac/primitives';

const meta: Meta = {
  title: 'Design System/Overview',
  component: () => null,
  parameters: {
    docs: {
      description: {
        component: `
# DotMac Framework Design System

A comprehensive design system built for multi-portal ISP management applications.

## 🎯 Portal-First Design

Our design system is built around **portal-specific variants** that adapt automatically to different user contexts:

- **Admin Portal**: Professional, data-dense interfaces for system administration
- **Customer Portal**: Friendly, accessible self-service experiences
- **Reseller Portal**: Business-focused interfaces for partner management
- **Technician Portal**: Mobile-optimized, task-oriented field interfaces
- **Management Portal**: Executive dashboards with enterprise-grade analytics

## 🏗️ Architecture

### Universal Components (\`@dotmac/ui\`)
Core UI primitives that adapt to portal contexts through variant props and theming.

### Portal-Specific Implementations
Each portal can override default styling while maintaining consistent behavior.

### Headless Logic (\`@dotmac/headless\`)
Business logic and state management separated from presentation for maximum flexibility.

### Unified Providers (\`@dotmac/providers\`)
Standardized provider architecture that configures components for specific portals automatically.

## 🎨 Design Principles

1. **Portal Context Awareness**: Every component understands its portal environment
2. **Accessibility First**: WCAG 2.1 AA compliance across all portals
3. **Mobile Responsive**: Adaptive layouts from mobile-first to desktop
4. **Performance Optimized**: Minimal bundle impact with tree shaking
5. **Type Safety**: Full TypeScript support with comprehensive type definitions

## 📦 Package Structure

\`\`\`
packages/
├── ui/                 # Core UI components
├── headless/          # Business logic hooks
├── providers/         # Universal provider system
├── auth/             # Authentication components
├── monitoring/       # Performance & error monitoring
├── primitives/       # Low-level building blocks
└── governance/       # Development standards & tools
\`\`\`

## 🚀 Quick Start

\`\`\`tsx
import { UniversalProviders } from '@dotmac/providers';
import { Button } from '@dotmac/primitives';

function App() {
  return (
    <UniversalProviders portal="admin">
      <Button variant="admin">Admin Action</Button>
    </UniversalProviders>
  );
}
\`\`\`

Components automatically adapt to portal context without additional configuration.
        `
      }
    }
  },
  tags: ['autodocs']
};

export default meta;
type Story = StoryObj;

// Portal Comparison Demo
export const PortalComparison: Story = {
  name: 'Portal Variant Comparison',
  render: () => {
    const portals = [
      { name: 'admin', label: 'Admin Portal', color: 'blue', description: 'Professional system administration' },
      { name: 'customer', label: 'Customer Portal', color: 'green', description: 'Friendly self-service experience' },
      { name: 'reseller', label: 'Reseller Portal', color: 'purple', description: 'Business partner management' },
      { name: 'technician', label: 'Technician Portal', color: 'orange', description: 'Mobile field operations' },
      { name: 'management-admin', label: 'Management Admin Portal', color: 'red', description: 'Executive analytics dashboard' },
      { name: 'management-reseller', label: 'Management Reseller Portal', color: 'indigo', description: 'Corporate partner oversight' },
      { name: 'tenant-portal', label: 'Tenant Portal', color: 'teal', description: 'Minimal tenant interface' }
    ];

    return (
      <div className="p-6 space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Portal Variant System</h2>
          <p className="text-gray-600">Same components, different contexts - automatically adapted styling</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {portals.map((portal) => (
            <Card key={portal.name} className={`border-l-4 border-${portal.color}-500`}>
              <div className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-lg">{portal.label}</h3>
                  <div className={`w-3 h-3 rounded-full bg-${portal.color}-500`} />
                </div>

                <p className="text-sm text-gray-600">{portal.description}</p>

                <div className="space-y-2">
                  <Button variant={portal.name as any} size="sm" className="w-full">
                    {portal.label} Button
                  </Button>

                  <Input
                    placeholder={`${portal.label} input`}
                    variant={portal.name as any}
                    size="sm"
                  />

                  <div className={`p-2 rounded bg-${portal.color}-50 border border-${portal.color}-200`}>
                    <div className="text-xs font-medium text-gray-600">Theme Colors</div>
                    <div className={`text-sm text-${portal.color}-800`}>
                      Primary: {portal.color}-600
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>

        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium mb-2">Implementation</h4>
          <pre className="text-sm bg-gray-900 text-green-400 p-3 rounded overflow-x-auto">
{`// Components automatically adapt to portal context
<UniversalProviders portal="admin">
  <Button variant="admin">Admin Button</Button>
</UniversalProviders>

<UniversalProviders portal="customer">
  <Button variant="customer">Customer Button</Button>
</UniversalProviders>`}
          </pre>
        </div>
      </div>
    );
  }
};

// Component Ecosystem Demo
export const ComponentEcosystem: Story = {
  name: 'Component Ecosystem',
  render: () => {
    const packages = [
      {
        name: '@dotmac/ui',
        description: 'Core UI components with portal variants',
        components: ['Button', 'Card', 'Input', 'Modal', 'Alert', 'Badge'],
        color: 'blue'
      },
      {
        name: '@dotmac/headless',
        description: 'Business logic and state management hooks',
        components: ['useApiData', 'useAppState', 'useAuth', 'useWebSocket'],
        color: 'green'
      },
      {
        name: '@dotmac/providers',
        description: 'Universal provider system for standardized architecture',
        components: ['UniversalProviders', 'AuthProvider', 'ThemeProvider'],
        color: 'purple'
      },
      {
        name: '@dotmac/monitoring',
        description: 'Performance monitoring and error tracking',
        components: ['PerformanceMonitor', 'ErrorBoundary', 'SentryProvider'],
        color: 'red'
      },
      {
        name: '@dotmac/auth',
        description: 'Authentication components and utilities',
        components: ['LoginForm', 'AuthGuard', 'SessionManager'],
        color: 'orange'
      },
      {
        name: '@dotmac/primitives',
        description: 'Low-level building blocks and utilities',
        components: ['Layout', 'Charts', 'Maps', 'DataTable'],
        color: 'teal'
      }
    ];

    return (
      <div className="p-6 space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Component Ecosystem</h2>
          <p className="text-gray-600">Modular packages working together seamlessly</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {packages.map((pkg) => (
            <Card key={pkg.name} className={`border-l-4 border-${pkg.color}-500`}>
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold font-mono text-sm">{pkg.name}</h3>
                  <div className={`px-2 py-1 rounded-full text-xs bg-${pkg.color}-100 text-${pkg.color}-800`}>
                    {pkg.components.length} items
                  </div>
                </div>

                <p className="text-sm text-gray-600 mb-3">{pkg.description}</p>

                <div className="space-y-1">
                  {pkg.components.map((component) => (
                    <div key={component} className={`inline-block mr-2 mb-1 px-2 py-1 rounded text-xs bg-${pkg.color}-50 text-${pkg.color}-700 font-mono`}>
                      {component}
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>

        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h4 className="font-medium text-blue-800 mb-2">Package Dependencies</h4>
          <div className="text-sm text-blue-700">
            <div className="space-y-1">
              <div>• <code>@dotmac/ui</code> → Core components used by all portals</div>
              <div>• <code>@dotmac/headless</code> → Business logic consumed by UI components</div>
              <div>• <code>@dotmac/providers</code> → Orchestrates all other packages</div>
              <div>• <code>@dotmac/monitoring</code> → Wraps components with observability</div>
              <div>• <code>@dotmac/auth</code> → Provides authentication context to all components</div>
              <div>• <code>@dotmac/primitives</code> → Foundation for complex UI patterns</div>
            </div>
          </div>
        </div>
      </div>
    );
  }
};

// Design Tokens Demo
export const DesignTokens: Story = {
  name: 'Design Tokens',
  render: () => {
    const colorTokens = [
      { name: 'Primary', admin: 'blue-600', customer: 'green-600', reseller: 'purple-600', technician: 'orange-600', 'management-admin': 'red-600', 'management-reseller': 'indigo-600', 'tenant-portal': 'teal-600' },
      { name: 'Secondary', admin: 'gray-600', customer: 'emerald-600', reseller: 'violet-600', technician: 'amber-600', 'management-admin': 'rose-600', 'management-reseller': 'indigo-500', 'tenant-portal': 'teal-500' },
      { name: 'Accent', admin: 'indigo-500', customer: 'teal-500', reseller: 'fuchsia-500', technician: 'yellow-500', 'management-admin': 'pink-500', 'management-reseller': 'violet-500', 'tenant-portal': 'cyan-500' }
    ];

    const spacingTokens = ['xs: 4px', 'sm: 8px', 'md: 16px', 'lg: 24px', 'xl: 32px', '2xl: 48px'];
    const typographyTokens = ['xs: 12px', 'sm: 14px', 'base: 16px', 'lg: 18px', 'xl: 20px', '2xl: 24px', '3xl: 30px'];

    return (
      <div className="p-6 space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Design Tokens</h2>
          <p className="text-gray-600">Consistent design language across all portals</p>
        </div>

        <div className="space-y-6">
          {/* Color Tokens */}
          <div>
            <h3 className="font-semibold mb-3">Color System</h3>
            <div className="space-y-3">
              {colorTokens.map((token) => (
                <div key={token.name} className="space-y-2">
                  <h4 className="font-medium text-sm">{token.name} Colors</h4>
                  <div className="grid grid-cols-7 gap-2">
                    <div className="space-y-1">
                      <div className={`h-12 w-full rounded bg-blue-600`}></div>
                      <div className="text-xs text-center">Admin<br/>{token.admin}</div>
                    </div>
                    <div className="space-y-1">
                      <div className={`h-12 w-full rounded bg-green-600`}></div>
                      <div className="text-xs text-center">Customer<br/>{token.customer}</div>
                    </div>
                    <div className="space-y-1">
                      <div className={`h-12 w-full rounded bg-purple-600`}></div>
                      <div className="text-xs text-center">Reseller<br/>{token.reseller}</div>
                    </div>
                    <div className="space-y-1">
                      <div className={`h-12 w-full rounded bg-orange-600`}></div>
                      <div className="text-xs text-center">Technician<br/>{token.technician}</div>
                    </div>
                    <div className="space-y-1">
                      <div className={`h-12 w-full rounded bg-red-600`}></div>
                      <div className="text-xs text-center">Mgmt Admin<br/>{token['management-admin']}</div>
                    </div>
                    <div className="space-y-1">
                      <div className={`h-12 w-full rounded bg-indigo-600`}></div>
                      <div className="text-xs text-center">Mgmt Reseller<br/>{token['management-reseller']}</div>
                    </div>
                    <div className="space-y-1">
                      <div className={`h-12 w-full rounded bg-teal-600`}></div>
                      <div className="text-xs text-center">Tenant<br/>{token['tenant-portal']}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Spacing Tokens */}
          <div>
            <h3 className="font-semibold mb-3">Spacing Scale</h3>
            <div className="space-y-2">
              {spacingTokens.map((token) => {
                const [name, value] = token.split(': ');
                const px = parseInt(value);
                return (
                  <div key={token} className="flex items-center space-x-4">
                    <div className="w-16 text-xs font-mono">{token}</div>
                    <div className={`bg-blue-500 rounded`} style={{ width: `${px}px`, height: '16px' }}></div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Typography Tokens */}
          <div>
            <h3 className="font-semibold mb-3">Typography Scale</h3>
            <div className="space-y-2">
              {typographyTokens.map((token) => {
                const [name, value] = token.split(': ');
                return (
                  <div key={token} className="flex items-center space-x-4">
                    <div className="w-20 text-xs font-mono">{token}</div>
                    <div className={`text-${name}`}>
                      Sample text in {name} size
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium mb-2">Token Usage</h4>
          <pre className="text-sm bg-gray-900 text-green-400 p-3 rounded overflow-x-auto">
{`// CSS Variables (automatically generated)
:root {
  --color-primary: var(--portal-primary, theme('colors.blue.600'));
  --spacing-md: theme('spacing.4');
  --text-base: theme('fontSize.base');
}

// Tailwind Classes (portal-aware)
<div className="bg-primary text-base p-md">
  Portal-adaptive styling
</div>`}
          </pre>
        </div>
      </div>
    );
  }
};

// Accessibility Demo
export const AccessibilityFeatures: Story = {
  name: 'Accessibility Features',
  render: () => {
    const [highContrast, setHighContrast] = useState(false);
    const [reducedMotion, setReducedMotion] = useState(false);
    const [fontSize, setFontSize] = useState('base');

    const accessibilityFeatures = [
      '✅ WCAG 2.1 AA compliant color contrasts',
      '✅ Keyboard navigation support',
      '✅ Screen reader optimized markup',
      '✅ Focus management and visible indicators',
      '✅ Reduced motion preferences respect',
      '✅ High contrast mode support',
      '✅ Scalable typography system',
      '✅ Alternative text for all images',
      '✅ Form validation with clear error messages',
      '✅ Skip links and landmark navigation'
    ];

    return (
      <div className={`p-6 space-y-6 ${highContrast ? 'contrast-125 bg-white' : ''} ${reducedMotion ? '' : 'transition-all duration-200'}`}>
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Accessibility Features</h2>
          <p className="text-gray-600">WCAG 2.1 AA compliant design system</p>
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="font-semibold mb-3">Accessibility Controls</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={highContrast}
                  onChange={(e) => setHighContrast(e.target.checked)}
                  className="rounded"
                />
                <span>High Contrast Mode</span>
              </label>

              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={reducedMotion}
                  onChange={(e) => setReducedMotion(e.target.checked)}
                  className="rounded"
                />
                <span>Reduced Motion</span>
              </label>

              <select
                value={fontSize}
                onChange={(e) => setFontSize(e.target.value)}
                className="px-3 py-2 border rounded-md"
                aria-label="Font size selector"
              >
                <option value="sm">Small Text</option>
                <option value="base">Normal Text</option>
                <option value="lg">Large Text</option>
                <option value="xl">Extra Large Text</option>
              </select>
            </div>
          </div>

          <div className={`text-${fontSize}`}>
            <h3 className="font-semibold mb-3">Sample Content</h3>
            <Card className={`p-4 ${highContrast ? 'border-2 border-black' : ''}`}>
              <div className="space-y-3">
                <h4 className="font-medium">Accessible Form Example</h4>

                <div className="space-y-2">
                  <label htmlFor="sample-input" className="block font-medium">
                    Email Address <span className="text-red-500" aria-label="required">*</span>
                  </label>
                  <Input
                    id="sample-input"
                    type="email"
                    placeholder="Enter your email"
                    aria-required="true"
                    aria-describedby="email-help"
                    className={`${fontSize === 'lg' || fontSize === 'xl' ? 'text-lg p-3' : ''}`}
                  />
                  <div id="email-help" className="text-sm text-gray-600">
                    We'll never share your email address
                  </div>
                </div>

                <div className="flex space-x-2">
                  <Button
                    className={`${reducedMotion ? '' : 'hover:scale-105 transition-transform'} focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
                    aria-describedby="submit-help"
                  >
                    Submit Form
                  </Button>
                  <Button variant="secondary">
                    Cancel
                  </Button>
                </div>
                <div id="submit-help" className="text-xs text-gray-500">
                  Press Tab to navigate, Enter to submit
                </div>
              </div>
            </Card>
          </div>

          <div>
            <h3 className="font-semibold mb-3">Accessibility Checklist</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {accessibilityFeatures.map((feature, index) => (
                <div key={index} className={`p-2 rounded text-sm ${highContrast ? 'bg-white border border-black' : 'bg-green-50 text-green-800'}`}>
                  {feature}
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Accessibility Testing</h4>
            <div className="text-sm text-blue-700 space-y-1">
              <div>• Automated testing with <code>@axe-core/react</code></div>
              <div>• Manual keyboard navigation testing</div>
              <div>• Screen reader compatibility (NVDA, JAWS, VoiceOver)</div>
              <div>• Color contrast validation (4.5:1 ratio minimum)</div>
              <div>• Focus management verification</div>
            </div>
          </div>
        </div>
      </div>
    );
  }
};

// Development Workflow Demo
export const DevelopmentWorkflow: Story = {
  name: 'Development Workflow',
  render: () => {
    const workflowSteps = [
      {
        step: '1',
        title: 'Component Development',
        description: 'Build components in isolation with Storybook',
        tools: ['Storybook', 'TypeScript', 'Tailwind CSS'],
        color: 'blue'
      },
      {
        step: '2',
        title: 'Portal Integration',
        description: 'Test components across all portal variants',
        tools: ['Portal Variants', 'Theme System', 'Provider Testing'],
        color: 'green'
      },
      {
        step: '3',
        title: 'Quality Assurance',
        description: 'Automated testing and accessibility validation',
        tools: ['Jest', 'Testing Library', 'Axe-core', 'Lighthouse'],
        color: 'purple'
      },
      {
        step: '4',
        title: 'Performance Optimization',
        description: 'Bundle analysis and performance monitoring',
        tools: ['Webpack Bundle Analyzer', 'Web Vitals', 'Sentry'],
        color: 'orange'
      },
      {
        step: '5',
        title: 'Documentation',
        description: 'Auto-generated docs and usage examples',
        tools: ['Storybook Docs', 'TypeDoc', 'MDX'],
        color: 'red'
      }
    ];

    return (
      <div className="p-6 space-y-6">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-2">Development Workflow</h2>
          <p className="text-gray-600">Streamlined development process for design system components</p>
        </div>

        <div className="space-y-4">
          {workflowSteps.map((step, index) => (
            <div key={step.step} className="flex items-start space-x-4">
              <div className={`flex-shrink-0 w-8 h-8 rounded-full bg-${step.color}-500 text-white flex items-center justify-center font-bold text-sm`}>
                {step.step}
              </div>
              <div className="flex-1">
                <Card className={`border-l-4 border-${step.color}-500`}>
                  <div className="p-4">
                    <h3 className="font-semibold mb-2">{step.title}</h3>
                    <p className="text-gray-600 text-sm mb-3">{step.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {step.tools.map((tool) => (
                        <span key={tool} className={`px-2 py-1 rounded text-xs bg-${step.color}-100 text-${step.color}-800`}>
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <h3 className="font-semibold">Development Commands</h3>
          <div className="space-y-2">
            <div className="p-3 bg-gray-900 text-green-400 rounded font-mono text-sm">
              <div># Start Storybook development server</div>
              <div>pnpm storybook</div>
            </div>
            <div className="p-3 bg-gray-900 text-green-400 rounded font-mono text-sm">
              <div># Run component tests</div>
              <div>pnpm test:components</div>
            </div>
            <div className="p-3 bg-gray-900 text-green-400 rounded font-mono text-sm">
              <div># Build and analyze bundle</div>
              <div>pnpm build:analyze</div>
            </div>
            <div className="p-3 bg-gray-900 text-green-400 rounded font-mono text-sm">
              <div># Generate component documentation</div>
              <div>pnpm docs:generate</div>
            </div>
          </div>
        </div>

        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <h4 className="font-medium text-green-800 mb-2">Best Practices</h4>
          <ul className="text-sm text-green-700 space-y-1">
            <li>• Develop components in isolation before integration</li>
            <li>• Test all portal variants during development</li>
            <li>• Write accessibility tests alongside functional tests</li>
            <li>• Document component APIs and usage patterns</li>
            <li>• Monitor performance impact of new components</li>
            <li>• Follow semantic versioning for package updates</li>
          </ul>
        </div>
      </div>
    );
  }
};
