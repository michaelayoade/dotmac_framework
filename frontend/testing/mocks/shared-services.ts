/**
 * Shared service mocks for new DRY architecture packages
 * Prevents test failures from missing service implementations
 */

export const sharedServiceMocks = {
  // Mock @dotmac/portal-components
  '@dotmac/portal-components': () => ({
    PortalProviderFactory: ({ children, config }: any) => (
      <div data-testid="portal-provider-factory" data-config={JSON.stringify(config)}>
        {children}
      </div>
    ),
    PackageIntegrations: {
      enabledForPortal: jest.fn(() => ['network', 'assets', 'journey-orchestration']),
      getNetworkFeatures: jest.fn(() => ({ topology: true, monitoring: true, snmp: true })),
      getAssetsFeatures: jest.fn(() => ({ lifecycle: true, depreciation: true, tracking: true })),
      getJourneyFeatures: jest.fn(() => ({ orchestration: true, analytics: true, conversion: true })),
      isFeatureEnabled: jest.fn(() => true)
    },
    CustomerWidgets: {
      ServiceStatusWidget: ({ children }: any) => <div data-testid="service-status-widget">{children}</div>,
      BillingWidget: ({ children }: any) => <div data-testid="billing-widget">{children}</div>,
      UsageWidget: ({ children }: any) => <div data-testid="usage-widget">{children}</div>,
      SupportWidget: ({ children }: any) => <div data-testid="support-widget">{children}</div>,
      CustomerJourneyWidget: ({ children }: any) => <div data-testid="journey-widget">{children}</div>
    }
  }),

  // Mock @dotmac/network package
  '@dotmac/network': () => ({
    NetworkTopology: ({ children }: any) => <div data-testid="network-topology">{children}</div>,
    DeviceMonitoring: ({ children }: any) => <div data-testid="device-monitoring">{children}</div>,
    SNMPMonitor: ({ children }: any) => <div data-testid="snmp-monitor">{children}</div>,
    
    // Hooks
    useNetworkStatus: () => ({ 
      status: 'connected', 
      devices: [
        { id: 'router-1', name: 'Main Router', status: 'online', ip: '192.168.1.1' },
        { id: 'switch-1', name: 'Core Switch', status: 'online', ip: '192.168.1.2' }
      ],
      loading: false 
    }),
    useNetworkTopology: () => ({
      topology: {
        nodes: [
          { id: 'router-1', label: 'Main Router', type: 'router' },
          { id: 'switch-1', label: 'Core Switch', type: 'switch' }
        ],
        links: [
          { source: 'router-1', target: 'switch-1', bandwidth: '1Gbps' }
        ]
      },
      loading: false
    }),

    // Services
    NetworkManager: {
      scanNetwork: jest.fn().mockResolvedValue([]),
      getTopology: jest.fn().mockResolvedValue({ nodes: [], links: [] }),
      getDeviceStatus: jest.fn().mockResolvedValue('online'),
      getDeviceMetrics: jest.fn().mockResolvedValue({ cpu: 45, memory: 60, uptime: '99.9%' }),
      updateDeviceConfig: jest.fn().mockResolvedValue({ success: true })
    }
  }),

  // Mock @dotmac/assets package
  '@dotmac/assets': () => ({
    AssetLifecycle: ({ children }: any) => <div data-testid="asset-lifecycle">{children}</div>,
    AssetTracking: ({ children }: any) => <div data-testid="asset-tracking">{children}</div>,
    DepreciationCalculator: ({ children }: any) => <div data-testid="depreciation-calculator">{children}</div>,
    
    // Hooks
    useAssetTracking: () => ({ 
      assets: [
        { 
          id: 'asset-1', 
          name: 'Core Router', 
          purchasePrice: 10000,
          currentValue: 7500,
          depreciation: 2500,
          purchaseDate: '2023-01-01',
          status: 'active'
        }
      ], 
      loading: false 
    }),
    useDepreciation: () => ({
      calculate: jest.fn().mockReturnValue({ currentValue: 7500, annualDepreciation: 1000 }),
      methods: ['straight-line', 'declining-balance', 'sum-of-years']
    }),

    // Services
    AssetManager: {
      calculateDepreciation: jest.fn().mockReturnValue({ 
        currentValue: 7500, 
        annualDepreciation: 1000,
        accumulatedDepreciation: 2500,
        remainingValue: 7500
      }),
      getROI: jest.fn().mockReturnValue(15.5),
      trackAsset: jest.fn().mockResolvedValue({ id: 'asset-123', tracked: true }),
      getAssetHistory: jest.fn().mockResolvedValue([]),
      updateAssetStatus: jest.fn().mockResolvedValue({ success: true }),
      generateAssetReport: jest.fn().mockResolvedValue({ reportUrl: '/reports/assets-123.pdf' })
    }
  }),

  // Mock @dotmac/journey-orchestration package
  '@dotmac/journey-orchestration': () => ({
    CustomerJourneyWidget: ({ children }: any) => <div data-testid="journey-widget">{children}</div>,
    JourneyVisualization: ({ children }: any) => <div data-testid="journey-visualization">{children}</div>,
    ConversionAnalytics: ({ children }: any) => <div data-testid="conversion-analytics">{children}</div>,
    
    // Hooks
    useCustomerJourney: () => ({ 
      journey: {
        id: 'journey-1',
        customerId: 'customer-1',
        currentStep: 'onboarding',
        progress: 65,
        status: 'active',
        estimatedCompletion: '2024-01-15'
      }, 
      loading: false 
    }),
    useJourneyAnalytics: () => ({
      analytics: {
        totalJourneys: 150,
        activeJourneys: 85,
        completedJourneys: 45,
        conversionRate: 78.5,
        averageCompletionTime: '14 days'
      },
      loading: false
    }),

    // Services
    JourneyOrchestrator: {
      startJourney: jest.fn().mockResolvedValue({ 
        id: 'journey-123', 
        status: 'started',
        currentStep: 'lead-capture',
        nextAction: 'qualify-lead'
      }),
      advanceStep: jest.fn().mockResolvedValue({ 
        success: true, 
        newStep: 'qualified-lead',
        nextAction: 'schedule-demo' 
      }),
      completeJourney: jest.fn().mockResolvedValue({ 
        success: true, 
        completedAt: new Date().toISOString(),
        outcome: 'converted'
      }),
      getJourneyStatus: jest.fn().mockResolvedValue({
        id: 'journey-123',
        status: 'active',
        progress: 65,
        currentStep: 'onboarding'
      }),
      pauseJourney: jest.fn().mockResolvedValue({ success: true, status: 'paused' }),
      resumeJourney: jest.fn().mockResolvedValue({ success: true, status: 'active' }),
      getJourneyMetrics: jest.fn().mockResolvedValue({
        completionRate: 78.5,
        averageDuration: '14 days',
        dropOffPoints: ['qualification', 'pricing']
      })
    }
  }),

  // Mock @dotmac/navigation-system
  '@dotmac/navigation-system': () => ({
    UniversalNavigation: ({ children }: any) => <div data-testid="universal-navigation">{children}</div>,
    NavigationPresets: {
      customer: () => [
        { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
        { label: 'Services', path: '/services', icon: 'services' },
        { label: 'Billing', path: '/billing', icon: 'billing' },
        { label: 'Support', path: '/support', icon: 'support' }
      ],
      admin: () => [
        { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
        { label: 'Users', path: '/users', icon: 'users' },
        { label: 'Network', path: '/network', icon: 'network' },
        { label: 'Assets', path: '/assets', icon: 'assets' }
      ],
      management: () => [
        { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
        { label: 'Tenants', path: '/tenants', icon: 'tenants' },
        { label: 'Analytics', path: '/analytics', icon: 'analytics' }
      ]
    },
    UserHelper: {
      format: jest.fn((user) => user || { name: 'Test User', email: 'test@example.com' })
    },
    BrandingHelper: {
      fromTenant: jest.fn(() => ({ name: 'Test Tenant', theme: 'default' }))
    },
    NavigationHookHelpers: {
      createNavigationHandler: jest.fn(() => jest.fn()),
      createLogoutHandler: jest.fn(() => jest.fn())
    }
  })
};

// Helper to apply all mocks at once
export const applySharedServiceMocks = () => {
  Object.entries(sharedServiceMocks).forEach(([moduleName, mockFactory]) => {
    jest.doMock(moduleName, mockFactory, { virtual: true });
  });
};

// Individual mock helpers for specific testing scenarios
export const mockNetworkDown = () => {
  jest.doMock('@dotmac/network', () => ({
    ...sharedServiceMocks['@dotmac/network'](),
    useNetworkStatus: () => ({ 
      status: 'disconnected', 
      devices: [], 
      loading: false,
      error: 'Network connection failed'
    }),
    NetworkManager: {
      ...sharedServiceMocks['@dotmac/network']().NetworkManager,
      scanNetwork: jest.fn().mockRejectedValue(new Error('Network unreachable'))
    }
  }));
};

export const mockAssetError = () => {
  jest.doMock('@dotmac/assets', () => ({
    ...sharedServiceMocks['@dotmac/assets'](),
    useAssetTracking: () => ({ 
      assets: [], 
      loading: false,
      error: 'Failed to load assets'
    }),
    AssetManager: {
      ...sharedServiceMocks['@dotmac/assets']().AssetManager,
      trackAsset: jest.fn().mockRejectedValue(new Error('Asset tracking service unavailable'))
    }
  }));
};

export const mockJourneyFailure = () => {
  jest.doMock('@dotmac/journey-orchestration', () => ({
    ...sharedServiceMocks['@dotmac/journey-orchestration'](),
    JourneyOrchestrator: {
      ...sharedServiceMocks['@dotmac/journey-orchestration']().JourneyOrchestrator,
      startJourney: jest.fn().mockRejectedValue(new Error('Journey orchestration service unavailable'))
    }
  }));
};