/**
 * Admin Dashboard - Component Integration Tests
 * Tests the integration between dashboard components, real-time data, and multi-service coordination
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WebSocketProvider } from '@dotmac/headless/providers/WebSocketProvider';
import { AdminDashboard } from '../../../isp-framework/admin/src/components/dashboard/DashboardOverview';
import { AnalyticsApiClient } from '../../headless/src/api/clients/AnalyticsApiClient';
import { NetworkingApiClient } from '../../headless/src/api/clients/NetworkingApiClient';
import { IdentityApiClient } from '../../headless/src/api/clients/IdentityApiClient';
import { BillingApiClient } from '../../headless/src/api/clients/BillingApiClient';
import { SupportApiClient } from '../../headless/src/api/clients/SupportApiClient';
import { NotificationsApiClient } from '../../headless/src/api/clients/NotificationsApiClient';
import { useISPTenant } from '../../headless/src/hooks/useISPTenant';
import type {
  DashboardMetrics,
  NetworkStatus,
  SystemAlert,
} from '../../headless/src/types/dashboard';

// Mock API clients and hooks
jest.mock('../../headless/src/api/clients/AnalyticsApiClient');
jest.mock('../../headless/src/api/clients/NetworkingApiClient');
jest.mock('../../headless/src/api/clients/IdentityApiClient');
jest.mock('../../headless/src/api/clients/BillingApiClient');
jest.mock('../../headless/src/api/clients/SupportApiClient');
jest.mock('../../headless/src/api/clients/NotificationsApiClient');
jest.mock('../../headless/src/hooks/useISPTenant');

const MockedAnalyticsApiClient = AnalyticsApiClient as jest.MockedClass<typeof AnalyticsApiClient>;
const MockedNetworkingApiClient = NetworkingApiClient as jest.MockedClass<
  typeof NetworkingApiClient
>;
const MockedIdentityApiClient = IdentityApiClient as jest.MockedClass<typeof IdentityApiClient>;
const MockedBillingApiClient = BillingApiClient as jest.MockedClass<typeof BillingApiClient>;
const MockedSupportApiClient = SupportApiClient as jest.MockedClass<typeof SupportApiClient>;
const MockedNotificationsApiClient = NotificationsApiClient as jest.MockedClass<
  typeof NotificationsApiClient
>;
const mockUseISPTenant = useISPTenant as jest.MockedFunction<typeof useISPTenant>;

// Mock WebSocket for real-time updates
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN,
};

// Mock data
const mockDashboardMetrics: DashboardMetrics = {
  overview: {
    totalCustomers: 2547,
    activeServices: 3204,
    monthlyRevenue: 485630.0,
    networkUptime: 99.97,
    openTickets: 23,
    criticalAlerts: 2,
    bandwidthUtilization: 67.3,
    newCustomersThisMonth: 127,
  },
  revenue: {
    current: 485630.0,
    lastMonth: 461250.0,
    growth: 5.29,
    recurring: 425600.0,
    oneTime: 60030.0,
    projectedMonthly: 502400.0,
  },
  network: {
    totalDevices: 145,
    onlineDevices: 143,
    offlineDevices: 2,
    avgLatency: 12.3,
    avgThroughput: 8.9,
    errorRate: 0.02,
    maintenanceWindows: 3,
  },
  customers: {
    total: 2547,
    active: 2398,
    suspended: 89,
    churned: 60,
    newSignups: 127,
    churnRate: 2.4,
    satisfactionScore: 4.2,
    avgLifetimeValue: 2847.5,
  },
  support: {
    openTickets: 23,
    resolvedToday: 47,
    avgResolutionTime: 4.2,
    firstCallResolution: 78.5,
    criticalTickets: 2,
    escalatedTickets: 5,
    satisfactionRating: 4.1,
  },
  alerts: {
    critical: 2,
    warning: 8,
    info: 12,
    total: 22,
    acknowledged: 18,
    resolved: 156,
  },
};

const mockNetworkStatus: NetworkStatus = {
  coreRouters: [
    { id: 'router_core_01', name: 'Core Router 1', status: 'online', uptime: 99.98, load: 34.2 },
    { id: 'router_core_02', name: 'Core Router 2', status: 'online', uptime: 99.95, load: 41.7 },
  ],
  accessPoints: {
    total: 89,
    online: 87,
    offline: 2,
    maintenance: 0,
  },
  bandwidth: {
    total: '10 Gbps',
    utilized: '6.73 Gbps',
    utilization: 67.3,
    peak: '8.9 Gbps',
  },
  latency: {
    average: 12.3,
    peak: 28.7,
    regions: [
      { region: 'Downtown', avgLatency: 8.2 },
      { region: 'Suburbs', avgLatency: 15.1 },
      { region: 'Industrial', avgLatency: 13.8 },
    ],
  },
};

const mockSystemAlerts: SystemAlert[] = [
  {
    id: 'alert_001',
    type: 'critical',
    category: 'network',
    title: 'Core Router High CPU Usage',
    description: 'Router Core-01 CPU usage at 89% for 15 minutes',
    timestamp: '2024-01-22T14:30:00Z',
    acknowledged: false,
    source: 'monitoring_system',
    affectedServices: ['internet', 'voip'],
    estimatedImpact: 'high',
    recommendedAction: 'Investigate traffic patterns and consider load balancing',
  },
  {
    id: 'alert_002',
    type: 'warning',
    category: 'billing',
    title: 'Payment Processing Delays',
    description: 'Credit card processing experiencing 15-20 second delays',
    timestamp: '2024-01-22T13:45:00Z',
    acknowledged: true,
    source: 'payment_gateway',
    affectedServices: ['billing'],
    estimatedImpact: 'medium',
    recommendedAction: 'Monitor payment gateway status and consider failover',
  },
  {
    id: 'alert_003',
    type: 'info',
    category: 'maintenance',
    title: 'Scheduled Maintenance Window',
    description: 'Planned network maintenance on Sunday 2 AM - 4 AM',
    timestamp: '2024-01-22T12:00:00Z',
    acknowledged: true,
    source: 'maintenance_scheduler',
    affectedServices: ['network'],
    estimatedImpact: 'low',
    recommendedAction: 'Notify customers of planned maintenance',
  },
];

// Test wrapper with providers
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <WebSocketProvider url='ws://localhost:8080/ws'>{children}</WebSocketProvider>
    </QueryClientProvider>
  );
};

describe('AdminDashboard Integration Tests', () => {
  let analyticsClient: jest.Mocked<AnalyticsApiClient>;
  let networkingClient: jest.Mocked<NetworkingApiClient>;
  let identityClient: jest.Mocked<IdentityApiClient>;
  let billingClient: jest.Mocked<BillingApiClient>;
  let supportClient: jest.Mocked<SupportApiClient>;
  let notificationsClient: jest.Mocked<NotificationsApiClient>;

  beforeEach(() => {
    // Setup API client mocks
    analyticsClient = {
      getDashboardMetrics: jest.fn(),
      getRealtimeMetrics: jest.fn(),
      createReport: jest.fn(),
      getCustomReport: jest.fn(),
      trackEvent: jest.fn(),
      getAnalytics: jest.fn(),
    } as any;

    networkingClient = {
      getNetworkStatus: jest.fn(),
      getDevices: jest.fn(),
      getNetworkTopology: jest.fn(),
      monitorBandwidth: jest.fn(),
      getAlerts: jest.fn(),
      acknowledgeAlert: jest.fn(),
    } as any;

    identityClient = {
      getCustomers: jest.fn(),
      getCustomerStats: jest.fn(),
      getRecentSignups: jest.fn(),
    } as any;

    billingClient = {
      getBillingAnalytics: jest.fn(),
      getRevenueMetrics: jest.fn(),
      getPaymentStatus: jest.fn(),
    } as any;

    supportClient = {
      getTickets: jest.fn(),
      getTicketStats: jest.fn(),
      getSatisfactionMetrics: jest.fn(),
      getRecentTickets: jest.fn(),
    } as any;

    notificationsClient = {
      getSystemAlerts: jest.fn(),
      acknowledgeAlert: jest.fn(),
      dismissAlert: jest.fn(),
      createAlert: jest.fn(),
    } as any;

    mockUseISPTenant.mockReturnValue({
      currentTenant: {
        id: 'tenant_test',
        name: 'Test ISP',
        domain: 'test-isp.com',
        settings: {
          timezone: 'America/Los_Angeles',
          currency: 'USD',
          language: 'en',
        },
      },
      isLoading: false,
      error: null,
      switchTenant: jest.fn(),
      refreshTenant: jest.fn(),
    });

    // Mock implementations
    MockedAnalyticsApiClient.mockImplementation(() => analyticsClient);
    MockedNetworkingApiClient.mockImplementation(() => networkingClient);
    MockedIdentityApiClient.mockImplementation(() => identityClient);
    MockedBillingApiClient.mockImplementation(() => billingClient);
    MockedSupportApiClient.mockImplementation(() => supportClient);
    MockedNotificationsApiClient.mockImplementation(() => notificationsClient);

    // Setup default mock responses
    analyticsClient.getDashboardMetrics.mockResolvedValue(mockDashboardMetrics);
    networkingClient.getNetworkStatus.mockResolvedValue(mockNetworkStatus);
    notificationsClient.getSystemAlerts.mockResolvedValue(mockSystemAlerts);

    // Mock WebSocket
    global.WebSocket = jest.fn().mockImplementation(() => mockWebSocket) as any;
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Multi-Service Dashboard Integration', () => {
    it('should load and display data from all integrated services', async () => {
      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      // Wait for dashboard to load
      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
      });

      // Verify all API clients called
      expect(analyticsClient.getDashboardMetrics).toHaveBeenCalledWith({
        tenantId: 'tenant_test',
        period: '24h',
      });
      expect(networkingClient.getNetworkStatus).toHaveBeenCalledWith('tenant_test');
      expect(notificationsClient.getSystemAlerts).toHaveBeenCalledWith({
        tenantId: 'tenant_test',
        status: 'active',
        limit: 50,
      });

      // Check key metrics displayed
      await waitFor(() => {
        expect(screen.getByText('2,547')).toBeInTheDocument(); // Total customers
        expect(screen.getByText('$485,630.00')).toBeInTheDocument(); // Monthly revenue
        expect(screen.getByText('99.97%')).toBeInTheDocument(); // Network uptime
        expect(screen.getByText('23')).toBeInTheDocument(); // Open tickets
      });

      // Check network status
      expect(screen.getByText('Core Router 1')).toBeInTheDocument();
      expect(screen.getByText('Core Router 2')).toBeInTheDocument();
      expect(screen.getByText('67.3%')).toBeInTheDocument(); // Bandwidth utilization

      // Check alerts
      expect(screen.getByText('Core Router High CPU Usage')).toBeInTheDocument();
      expect(screen.getByText('Payment Processing Delays')).toBeInTheDocument();
    });

    it('should handle real-time updates via WebSocket integration', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
      });

      // Simulate real-time network update
      const networkUpdate = {
        type: 'network_status_update',
        data: {
          ...mockNetworkStatus,
          bandwidth: {
            ...mockNetworkStatus.bandwidth,
            utilized: '7.2 Gbps',
            utilization: 72.0,
          },
        },
      };

      // Simulate WebSocket message
      act(() => {
        const messageHandler = mockWebSocket.addEventListener.mock.calls.find(
          (call) => call[0] === 'message'
        )?.[1];
        if (messageHandler) {
          messageHandler({ data: JSON.stringify(networkUpdate) } as MessageEvent);
        }
      });

      // Verify updated bandwidth utilization
      await waitFor(() => {
        expect(screen.getByText('72.0%')).toBeInTheDocument();
      });

      // Simulate new alert via WebSocket
      const newAlert: SystemAlert = {
        id: 'alert_004',
        type: 'critical',
        category: 'security',
        title: 'Unusual Login Activity Detected',
        description: 'Multiple failed login attempts from IP 192.168.1.100',
        timestamp: new Date().toISOString(),
        acknowledged: false,
        source: 'security_system',
        affectedServices: ['admin_portal'],
        estimatedImpact: 'high',
        recommendedAction: 'Review login logs and consider IP blocking',
      };

      act(() => {
        const messageHandler = mockWebSocket.addEventListener.mock.calls.find(
          (call) => call[0] === 'message'
        )?.[1];
        if (messageHandler) {
          messageHandler({
            data: JSON.stringify({ type: 'new_alert', data: newAlert }),
          } as MessageEvent);
        }
      });

      // Verify new alert appears
      await waitFor(() => {
        expect(screen.getByText('Unusual Login Activity Detected')).toBeInTheDocument();
      });
    });

    it('should coordinate alert acknowledgment across multiple services', async () => {
      const user = userEvent.setup();
      networkingClient.acknowledgeAlert.mockResolvedValue({ success: true });
      notificationsClient.acknowledgeAlert.mockResolvedValue({ success: true });

      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Core Router High CPU Usage')).toBeInTheDocument();
      });

      // Acknowledge critical alert
      const acknowledgeButton = screen.getByTestId('acknowledge-alert-alert_001');
      await user.click(acknowledgeButton);

      await waitFor(() => {
        // Verify acknowledgment in networking service
        expect(networkingClient.acknowledgeAlert).toHaveBeenCalledWith('alert_001', {
          acknowledgedBy: 'admin_user',
          acknowledgedAt: expect.any(String),
          notes: '',
        });

        // Verify acknowledgment in notifications service
        expect(notificationsClient.acknowledgeAlert).toHaveBeenCalledWith('alert_001');

        // Verify UI updated
        expect(screen.getByText('Acknowledged')).toBeInTheDocument();
      });
    });
  });

  describe('Cross-Service Data Correlation', () => {
    it('should correlate customer, billing, and support data in unified view', async () => {
      const user = userEvent.setup();

      // Setup correlated data
      identityClient.getRecentSignups.mockResolvedValue([
        {
          id: 'cust_new_001',
          name: 'New Customer Corp',
          signupDate: '2024-01-22T10:00:00Z',
          plan: 'Enterprise',
        },
      ]);

      billingClient.getRevenueMetrics.mockResolvedValue({
        newCustomerRevenue: 15680.0,
        upsellRevenue: 8420.0,
        churnImpact: -2340.0,
      });

      supportClient.getRecentTickets.mockResolvedValue([
        {
          id: 'ticket_001',
          customerId: 'cust_new_001',
          subject: 'Setup assistance needed',
          priority: 'medium',
          status: 'open',
          createdAt: '2024-01-22T11:30:00Z',
        },
      ]);

      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
      });

      // Switch to customer insights view
      const customerInsightsTab = screen.getByText('Customer Insights');
      await user.click(customerInsightsTab);

      await waitFor(() => {
        // Verify correlated data displayed
        expect(screen.getByText('New Customer Corp')).toBeInTheDocument();
        expect(screen.getByText('$15,680.00')).toBeInTheDocument(); // New customer revenue
        expect(screen.getByText('Setup assistance needed')).toBeInTheDocument();
      });

      // Click on customer for detailed view
      const customerCard = screen.getByTestId('customer-card-cust_new_001');
      await user.click(customerCard);

      await waitFor(() => {
        // Verify detailed correlation
        expect(screen.getByText('Customer Journey Timeline')).toBeInTheDocument();
        expect(screen.getByText('Signed up: Jan 22, 2024')).toBeInTheDocument();
        expect(screen.getByText('Support ticket opened: Jan 22, 2024')).toBeInTheDocument();
      });
    });

    it('should provide predictive insights based on multi-service data', async () => {
      analyticsClient.getAnalytics.mockResolvedValue({
        churnRisk: {
          highRiskCustomers: 23,
          predictedChurnRevenue: 12400.0,
          topRiskFactors: ['payment_delays', 'support_escalations', 'usage_decline'],
        },
        growthOpportunities: {
          upsellCandidates: 156,
          potentialRevenue: 87500.0,
          topUpgradeReasons: ['bandwidth_usage_high', 'plan_feature_requests'],
        },
        networkOptimization: {
          congestionPrediction: [
            { region: 'Downtown', riskLevel: 'high', timeframe: '2-3 weeks' },
            { region: 'Suburbs', riskLevel: 'medium', timeframe: '1-2 months' },
          ],
          recommendedUpgrades: ['core_router_capacity', 'fiber_expansion'],
        },
      });

      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
      });

      // Switch to insights view
      const insightsTab = screen.getByText('Predictive Insights');
      const user = userEvent.setup();
      await user.click(insightsTab);

      await waitFor(() => {
        // Verify predictive insights displayed
        expect(screen.getByText('Churn Risk Analysis')).toBeInTheDocument();
        expect(screen.getByText('23 high-risk customers')).toBeInTheDocument();
        expect(screen.getByText('$12,400.00 at risk')).toBeInTheDocument();

        expect(screen.getByText('Growth Opportunities')).toBeInTheDocument();
        expect(screen.getByText('156 upsell candidates')).toBeInTheDocument();
        expect(screen.getByText('$87,500.00 potential revenue')).toBeInTheDocument();

        expect(screen.getByText('Network Optimization')).toBeInTheDocument();
        expect(screen.getByText('Downtown: High risk')).toBeInTheDocument();
      });
    });
  });

  describe('Performance and Scalability Integration', () => {
    it('should handle high-frequency real-time updates efficiently', async () => {
      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
      });

      // Simulate high-frequency updates (every second for 10 seconds)
      const updates = Array(10)
        .fill(null)
        .map((_, index) => ({
          type: 'metrics_update',
          data: {
            ...mockDashboardMetrics,
            overview: {
              ...mockDashboardMetrics.overview,
              bandwidthUtilization: 65 + index * 0.5, // Gradually increasing
            },
          },
        }));

      // Send updates rapidly
      for (const update of updates) {
        act(() => {
          const messageHandler = mockWebSocket.addEventListener.mock.calls.find(
            (call) => call[0] === 'message'
          )?.[1];
          if (messageHandler) {
            messageHandler({ data: JSON.stringify(update) } as MessageEvent);
          }
        });

        // Small delay to simulate real-time updates
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      // Verify final update rendered (should be throttled/debounced)
      await waitFor(() => {
        expect(screen.getByText(/69\.5%/)).toBeInTheDocument();
      });

      // Verify performance - should not have excessive re-renders
      expect(analyticsClient.getDashboardMetrics).toHaveBeenCalledTimes(1); // Initial call only
    });

    it('should implement efficient data caching and invalidation', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
      });

      // Switch between tabs multiple times
      const networkTab = screen.getByText('Network Status');
      const overviewTab = screen.getByText('System Overview');

      await user.click(networkTab);
      await user.click(overviewTab);
      await user.click(networkTab);
      await user.click(overviewTab);

      // Verify API calls are cached (not called multiple times)
      expect(analyticsClient.getDashboardMetrics).toHaveBeenCalledTimes(1);
      expect(networkingClient.getNetworkStatus).toHaveBeenCalledTimes(1);

      // Force refresh to test cache invalidation
      const refreshButton = screen.getByTestId('dashboard-refresh');
      await user.click(refreshButton);

      await waitFor(() => {
        // Should trigger new API calls
        expect(analyticsClient.getDashboardMetrics).toHaveBeenCalledTimes(2);
        expect(networkingClient.getNetworkStatus).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Error Handling and Resilience', () => {
    it('should gracefully handle partial service failures', async () => {
      // Simulate partial service failures
      analyticsClient.getDashboardMetrics.mockResolvedValue(mockDashboardMetrics);
      networkingClient.getNetworkStatus.mockRejectedValue(new Error('Network service unavailable'));
      notificationsClient.getSystemAlerts.mockRejectedValue(new Error('Alert service down'));

      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      // Core dashboard should still load
      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
        expect(screen.getByText('2,547')).toBeInTheDocument(); // Customer count from analytics
      });

      // Failed services should show error states
      expect(screen.getByText(/network status unavailable/i)).toBeInTheDocument();
      expect(screen.getByText(/alerts temporarily unavailable/i)).toBeInTheDocument();

      // Retry buttons should be available
      expect(screen.getByText('Retry Network Status')).toBeInTheDocument();
      expect(screen.getByText('Retry Alerts')).toBeInTheDocument();
    });

    it('should handle WebSocket disconnection and reconnection', async () => {
      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('System Overview')).toBeInTheDocument();
      });

      // Simulate WebSocket disconnection
      act(() => {
        const closeHandler = mockWebSocket.addEventListener.mock.calls.find(
          (call) => call[0] === 'close'
        )?.[1];
        if (closeHandler) {
          closeHandler({ code: 1006, reason: 'Connection lost' } as CloseEvent);
        }
      });

      // Should show disconnection indicator
      await waitFor(() => {
        expect(screen.getByText(/connection lost/i)).toBeInTheDocument();
      });

      // Simulate reconnection
      act(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls.find(
          (call) => call[0] === 'open'
        )?.[1];
        if (openHandler) {
          openHandler({} as Event);
        }
      });

      // Should restore real-time updates
      await waitFor(() => {
        expect(screen.getByText(/real-time updates active/i)).toBeInTheDocument();
      });
    });

    it('should implement automatic retry with exponential backoff for failed requests', async () => {
      const user = userEvent.setup();

      // Setup initial failure then success
      analyticsClient.getDashboardMetrics
        .mockRejectedValueOnce(new Error('Service temporarily unavailable'))
        .mockRejectedValueOnce(new Error('Service temporarily unavailable'))
        .mockResolvedValueOnce(mockDashboardMetrics);

      render(
        <TestWrapper>
          <AdminDashboard />
        </TestWrapper>
      );

      // Should show error state initially
      await waitFor(() => {
        expect(screen.getByText(/dashboard temporarily unavailable/i)).toBeInTheDocument();
      });

      // Manual retry
      const retryButton = screen.getByText('Retry');
      await user.click(retryButton);

      // Should eventually succeed
      await waitFor(
        () => {
          expect(screen.getByText('2,547')).toBeInTheDocument();
        },
        { timeout: 5000 }
      );

      // Verify retry attempts with backoff
      expect(analyticsClient.getDashboardMetrics).toHaveBeenCalledTimes(3);
    });
  });
});
