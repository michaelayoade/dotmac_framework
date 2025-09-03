/**
 * Service Integration Dashboard
 * Centralized dashboard for managing service integrations and monitoring workflows
 * Leverages existing dotmac_shared patterns for consistent architecture
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  Card,
  Button,
  Input,
  Select,
  Badge,
  Table,
  Modal,
  Alert,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Progress,
} from '@dotmac/primitives';
import { PermissionGuard } from '@dotmac/rbac';
import { withComponentRegistration } from '@dotmac/registry';
import { useRenderProfiler } from '@dotmac/primitives/utils/performance';
import { standard_exception_handler } from '@dotmac/shared';
import { UniversalChart } from '@dotmac/primitives/charts';
import {
  Settings,
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  Link,
  Database,
  Cloud,
  Server,
  Globe,
  Shield,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Pause,
  Play,
  Edit3,
} from 'lucide-react';

// Service integration types
interface ServiceIntegration {
  id: string;
  name: string;
  type: 'api' | 'webhook' | 'database' | 'queue' | 'external';
  status: 'active' | 'inactive' | 'error' | 'pending';
  endpoint?: string;
  lastSync?: string;
  syncCount: number;
  errorCount: number;
  responseTime: number;
  uptime: number;
  settings: Record<string, any>;
  workflows: string[];
  metadata: {
    description?: string;
    version?: string;
    maintainer?: string;
    documentation?: string;
  };
}

interface IntegrationMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  uptime: number;
  throughput: number;
}

interface ServiceIntegrationDashboardProps {
  tenantId: string;
  onIntegrationChange?: (integration: ServiceIntegration) => void;
  className?: string;
}

const SERVICE_TYPES = {
  api: { label: 'API Service', icon: Cloud, color: 'bg-blue-100 text-blue-800' },
  webhook: { label: 'Webhook', icon: Zap, color: 'bg-green-100 text-green-800' },
  database: { label: 'Database', icon: Database, color: 'bg-purple-100 text-purple-800' },
  queue: { label: 'Message Queue', icon: Server, color: 'bg-orange-100 text-orange-800' },
  external: { label: 'External Service', icon: Globe, color: 'bg-gray-100 text-gray-800' },
};

function ServiceIntegrationDashboardImpl({
  tenantId,
  onIntegrationChange,
  className = '',
}: ServiceIntegrationDashboardProps) {
  useRenderProfiler('ServiceIntegrationDashboard', { tenantId });

  // State
  const [integrations, setIntegrations] = useState<ServiceIntegration[]>([]);
  const [selectedIntegration, setSelectedIntegration] = useState<ServiceIntegration | null>(null);
  const [editingIntegration, setEditingIntegration] = useState<ServiceIntegration | null>(null);
  const [metrics, setMetrics] = useState<Record<string, IntegrationMetrics>>({});
  const [activeTab, setActiveTab] = useState<
    'overview' | 'integrations' | 'monitoring' | 'analytics'
  >('overview');
  const [filters, setFilters] = useState({
    status: 'all',
    type: 'all',
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load integrations and metrics
  useEffect(() => {
    loadIntegrations();
    loadMetrics();

    // Set up auto-refresh
    const interval = setInterval(() => {
      loadMetrics();
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [tenantId]);

  const loadIntegrations = useCallback(async () => {
    try {
      // Mock data - in real implementation, fetch from API
      const mockIntegrations: ServiceIntegration[] = [
        {
          id: '1',
          name: 'Customer Portal API',
          type: 'api',
          status: 'active',
          endpoint: '/api/v1/customers',
          lastSync: new Date().toISOString(),
          syncCount: 1250,
          errorCount: 3,
          responseTime: 145,
          uptime: 99.8,
          workflows: ['customer_onboarding', 'service_activation'],
          settings: {
            timeout: 30000,
            retries: 3,
            authentication: 'bearer',
          },
          metadata: {
            description: 'Customer management API integration',
            version: '2.1.0',
            maintainer: 'Platform Team',
          },
        },
        {
          id: '2',
          name: 'Payment Gateway',
          type: 'external',
          status: 'active',
          endpoint: 'https://api.stripe.com',
          lastSync: new Date(Date.now() - 5000).toISOString(),
          syncCount: 890,
          errorCount: 12,
          responseTime: 234,
          uptime: 99.2,
          workflows: ['payment_processing', 'subscription_billing'],
          settings: {
            apiKey: '***hidden***',
            webhook_endpoint: '/webhooks/stripe',
          },
          metadata: {
            description: 'Stripe payment processing integration',
            version: '1.5.2',
            maintainer: 'Finance Team',
          },
        },
        {
          id: '3',
          name: 'SMS Notifications',
          type: 'webhook',
          status: 'error',
          endpoint: '/webhooks/sms',
          lastSync: new Date(Date.now() - 3600000).toISOString(),
          syncCount: 456,
          errorCount: 45,
          responseTime: 892,
          uptime: 87.3,
          workflows: ['notification_service'],
          settings: {
            provider: 'twilio',
            retry_count: 3,
          },
          metadata: {
            description: 'SMS notification service integration',
            version: '1.0.0',
            maintainer: 'DevOps Team',
          },
        },
      ];

      setIntegrations(mockIntegrations);
    } catch (error) {
      console.error('Failed to load integrations:', error);
    }
  }, [tenantId]);

  const loadMetrics = useCallback(async () => {
    setIsRefreshing(true);

    try {
      // Mock metrics data
      const mockMetrics: Record<string, IntegrationMetrics> = {
        '1': {
          totalRequests: 1250,
          successfulRequests: 1247,
          failedRequests: 3,
          averageResponseTime: 145,
          uptime: 99.8,
          throughput: 42,
        },
        '2': {
          totalRequests: 890,
          successfulRequests: 878,
          failedRequests: 12,
          averageResponseTime: 234,
          uptime: 99.2,
          throughput: 31,
        },
        '3': {
          totalRequests: 456,
          successfulRequests: 411,
          failedRequests: 45,
          averageResponseTime: 892,
          uptime: 87.3,
          throughput: 18,
        },
      };

      setMetrics(mockMetrics);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Filtered integrations
  const filteredIntegrations = useMemo(() => {
    return integrations.filter((integration) => {
      if (filters.status !== 'all' && integration.status !== filters.status) return false;
      if (filters.type !== 'all' && integration.type !== filters.type) return false;
      return true;
    });
  }, [integrations, filters]);

  // Overall metrics
  const overallMetrics = useMemo(() => {
    const totalIntegrations = integrations.length;
    const activeIntegrations = integrations.filter((i) => i.status === 'active').length;
    const errorIntegrations = integrations.filter((i) => i.status === 'error').length;
    const totalRequests = Object.values(metrics).reduce((sum, m) => sum + m.totalRequests, 0);
    const totalErrors = Object.values(metrics).reduce((sum, m) => sum + m.failedRequests, 0);
    const avgResponseTime =
      Object.values(metrics).reduce((sum, m) => sum + m.averageResponseTime, 0) /
      Object.values(metrics).length;
    const avgUptime =
      Object.values(metrics).reduce((sum, m) => sum + m.uptime, 0) / Object.values(metrics).length;

    return {
      totalIntegrations,
      activeIntegrations,
      errorIntegrations,
      totalRequests,
      totalErrors,
      successRate: totalRequests > 0 ? ((totalRequests - totalErrors) / totalRequests) * 100 : 0,
      avgResponseTime: isNaN(avgResponseTime) ? 0 : avgResponseTime,
      avgUptime: isNaN(avgUptime) ? 0 : avgUptime,
    };
  }, [integrations, metrics]);

  // Integration operations
  const toggleIntegration = useCallback(async (integrationId: string) => {
    try {
      setIntegrations((prev) =>
        prev.map((integration) =>
          integration.id === integrationId
            ? {
                ...integration,
                status: integration.status === 'active' ? 'inactive' : 'active',
              }
            : integration
        )
      );
    } catch (error) {
      console.error('Failed to toggle integration:', error);
    }
  }, []);

  const testIntegration = useCallback(async (integrationId: string) => {
    try {
      // Mock test - would make actual API call in real implementation
      console.log('Testing integration:', integrationId);
      alert('Integration test completed successfully!');
    } catch (error) {
      console.error('Integration test failed:', error);
    }
  }, []);

  return (
    <div className={clsx('h-full flex flex-col bg-gray-50', className)}>
      {/* Header */}
      <div className='bg-white border-b px-6 py-4'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Service Integration Dashboard</h1>
            <p className='text-gray-600'>Monitor and manage service integrations and workflows</p>
          </div>

          <div className='flex items-center space-x-3'>
            <Button
              variant='outline'
              onClick={() => loadMetrics()}
              disabled={isRefreshing}
              className='flex items-center space-x-2'
            >
              <RefreshCw className={clsx('h-4 w-4', isRefreshing && 'animate-spin')} />
              <span>Refresh</span>
            </Button>

            <PermissionGuard permissions={['integrations:create']}>
              <Button
                onClick={() =>
                  setEditingIntegration({
                    id: `new_${Date.now()}`,
                    name: 'New Integration',
                    type: 'api',
                    status: 'pending',
                    syncCount: 0,
                    errorCount: 0,
                    responseTime: 0,
                    uptime: 0,
                    workflows: [],
                    settings: {},
                    metadata: {},
                  })
                }
                className='flex items-center space-x-2'
              >
                <Link className='h-4 w-4' />
                <span>Add Integration</span>
              </Button>
            </PermissionGuard>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className='flex-1 p-6'>
        <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)}>
          <TabsList>
            <TabsTrigger value='overview'>
              <Activity className='h-4 w-4 mr-2' />
              Overview
            </TabsTrigger>
            <TabsTrigger value='integrations'>
              <Link className='h-4 w-4 mr-2' />
              Integrations ({filteredIntegrations.length})
            </TabsTrigger>
            <TabsTrigger value='monitoring'>
              <Shield className='h-4 w-4 mr-2' />
              Monitoring
            </TabsTrigger>
            <TabsTrigger value='analytics'>
              <TrendingUp className='h-4 w-4 mr-2' />
              Analytics
            </TabsTrigger>
          </TabsList>

          <TabsContent value='overview' className='mt-6'>
            <OverviewTab metrics={overallMetrics} integrations={integrations} />
          </TabsContent>

          <TabsContent value='integrations' className='mt-6'>
            <IntegrationsTab
              integrations={filteredIntegrations}
              filters={filters}
              onFiltersChange={setFilters}
              onToggle={toggleIntegration}
              onTest={testIntegration}
              onEdit={setEditingIntegration}
            />
          </TabsContent>

          <TabsContent value='monitoring' className='mt-6'>
            <MonitoringTab integrations={integrations} metrics={metrics} />
          </TabsContent>

          <TabsContent value='analytics' className='mt-6'>
            <AnalyticsTab integrations={integrations} metrics={metrics} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Integration Editor Modal */}
      {editingIntegration && (
        <IntegrationEditorModal
          integration={editingIntegration}
          onSave={(integration) => {
            if (integrations.find((i) => i.id === integration.id)) {
              setIntegrations((prev) =>
                prev.map((i) => (i.id === integration.id ? integration : i))
              );
            } else {
              setIntegrations((prev) => [...prev, integration]);
            }
            setEditingIntegration(null);
            onIntegrationChange?.(integration);
          }}
          onCancel={() => setEditingIntegration(null)}
        />
      )}
    </div>
  );
}

// Overview Tab Component
function OverviewTab({
  metrics,
  integrations,
}: {
  metrics: any;
  integrations: ServiceIntegration[];
}) {
  return (
    <div className='space-y-6'>
      {/* Key Metrics */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <div className='text-2xl font-bold text-blue-600'>{metrics.activeIntegrations}</div>
              <div className='text-sm text-gray-600'>Active Integrations</div>
            </div>
            <CheckCircle className='h-8 w-8 text-green-500' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <div className='text-2xl font-bold text-green-600'>
                {metrics.successRate.toFixed(1)}%
              </div>
              <div className='text-sm text-gray-600'>Success Rate</div>
            </div>
            <TrendingUp className='h-8 w-8 text-green-500' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <div className='text-2xl font-bold text-orange-600'>
                {Math.round(metrics.avgResponseTime)}ms
              </div>
              <div className='text-sm text-gray-600'>Avg Response Time</div>
            </div>
            <Clock className='h-8 w-8 text-orange-500' />
          </div>
        </Card>

        <Card className='p-6'>
          <div className='flex items-center justify-between'>
            <div>
              <div className='text-2xl font-bold text-purple-600'>
                {metrics.avgUptime.toFixed(1)}%
              </div>
              <div className='text-sm text-gray-600'>Average Uptime</div>
            </div>
            <Activity className='h-8 w-8 text-purple-500' />
          </div>
        </Card>
      </div>

      {/* Integration Status */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        <Card className='p-6'>
          <h3 className='font-semibold mb-4'>Integration Status</h3>
          <div className='space-y-3'>
            {integrations.map((integration) => (
              <div key={integration.id} className='flex items-center justify-between'>
                <div className='flex items-center space-x-3'>
                  <div
                    className={clsx(
                      'w-3 h-3 rounded-full',
                      integration.status === 'active'
                        ? 'bg-green-500'
                        : integration.status === 'error'
                          ? 'bg-red-500'
                          : integration.status === 'inactive'
                            ? 'bg-gray-400'
                            : 'bg-yellow-500'
                    )}
                  />
                  <span className='font-medium'>{integration.name}</span>
                </div>
                <Badge
                  variant={
                    integration.status === 'active'
                      ? 'default'
                      : integration.status === 'error'
                        ? 'destructive'
                        : 'secondary'
                  }
                >
                  {integration.status}
                </Badge>
              </div>
            ))}
          </div>
        </Card>

        <Card className='p-6'>
          <h3 className='font-semibold mb-4'>Recent Activity</h3>
          <div className='space-y-3'>
            {integrations
              .filter((i) => i.lastSync)
              .sort((a, b) => new Date(b.lastSync!).getTime() - new Date(a.lastSync!).getTime())
              .slice(0, 5)
              .map((integration) => (
                <div key={integration.id} className='flex items-center justify-between'>
                  <span className='font-medium'>{integration.name}</span>
                  <span className='text-sm text-gray-500'>
                    {new Date(integration.lastSync!).toLocaleTimeString()}
                  </span>
                </div>
              ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// Integrations Tab Component
interface IntegrationsTabProps {
  integrations: ServiceIntegration[];
  filters: any;
  onFiltersChange: (filters: any) => void;
  onToggle: (id: string) => void;
  onTest: (id: string) => void;
  onEdit: (integration: ServiceIntegration) => void;
}

function IntegrationsTab({
  integrations,
  filters,
  onFiltersChange,
  onToggle,
  onTest,
  onEdit,
}: IntegrationsTabProps) {
  return (
    <div className='space-y-6'>
      {/* Filters */}
      <Card className='p-4'>
        <div className='flex items-center space-x-4'>
          <Select
            value={filters.status}
            onValueChange={(value) => onFiltersChange({ ...filters, status: value })}
          >
            <option value='all'>All Status</option>
            <option value='active'>Active</option>
            <option value='inactive'>Inactive</option>
            <option value='error'>Error</option>
          </Select>

          <Select
            value={filters.type}
            onValueChange={(value) => onFiltersChange({ ...filters, type: value })}
          >
            <option value='all'>All Types</option>
            <option value='api'>API Service</option>
            <option value='webhook'>Webhook</option>
            <option value='database'>Database</option>
            <option value='external'>External Service</option>
          </Select>
        </div>
      </Card>

      {/* Integrations Table */}
      <Card>
        <Table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Response Time</th>
              <th>Uptime</th>
              <th>Last Sync</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {integrations.map((integration) => {
              const serviceConfig = SERVICE_TYPES[integration.type];
              const Icon = serviceConfig.icon;

              return (
                <tr key={integration.id} className='hover:bg-gray-50'>
                  <td>
                    <div className='flex items-center space-x-3'>
                      <div className={clsx('p-2 rounded', serviceConfig.color)}>
                        <Icon className='h-4 w-4' />
                      </div>
                      <div>
                        <div className='font-medium'>{integration.name}</div>
                        <div className='text-sm text-gray-500'>
                          {integration.metadata.description}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Badge variant='outline'>{serviceConfig.label}</Badge>
                  </td>
                  <td>
                    <Badge
                      variant={
                        integration.status === 'active'
                          ? 'default'
                          : integration.status === 'error'
                            ? 'destructive'
                            : 'secondary'
                      }
                    >
                      {integration.status}
                    </Badge>
                  </td>
                  <td>{integration.responseTime}ms</td>
                  <td>{integration.uptime.toFixed(1)}%</td>
                  <td>{integration.lastSync && new Date(integration.lastSync).toLocaleString()}</td>
                  <td>
                    <div className='flex items-center space-x-1'>
                      <Button size='sm' variant='ghost' onClick={() => onToggle(integration.id)}>
                        {integration.status === 'active' ? (
                          <Pause className='h-4 w-4' />
                        ) : (
                          <Play className='h-4 w-4' />
                        )}
                      </Button>

                      <Button size='sm' variant='ghost' onClick={() => onTest(integration.id)}>
                        <Zap className='h-4 w-4' />
                      </Button>

                      <Button size='sm' variant='ghost' onClick={() => onEdit(integration)}>
                        <Edit3 className='h-4 w-4' />
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}

// Monitoring Tab (simplified)
function MonitoringTab({
  integrations,
  metrics,
}: {
  integrations: ServiceIntegration[];
  metrics: Record<string, IntegrationMetrics>;
}) {
  return (
    <div className='space-y-6'>
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {integrations.map((integration) => {
          const integrationMetrics = metrics[integration.id];
          if (!integrationMetrics) return null;

          return (
            <Card key={integration.id} className='p-6'>
              <div className='flex items-center justify-between mb-4'>
                <h3 className='font-semibold'>{integration.name}</h3>
                <Badge
                  variant={
                    integration.status === 'active'
                      ? 'default'
                      : integration.status === 'error'
                        ? 'destructive'
                        : 'secondary'
                  }
                >
                  {integration.status}
                </Badge>
              </div>

              <div className='space-y-3'>
                <div>
                  <div className='flex justify-between text-sm'>
                    <span>Uptime</span>
                    <span>{integrationMetrics.uptime.toFixed(1)}%</span>
                  </div>
                  <Progress value={integrationMetrics.uptime} className='mt-1' />
                </div>

                <div className='grid grid-cols-2 gap-4 text-sm'>
                  <div>
                    <span className='text-gray-600'>Requests</span>
                    <div className='font-medium'>
                      {integrationMetrics.totalRequests.toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <span className='text-gray-600'>Errors</span>
                    <div className='font-medium text-red-600'>
                      {integrationMetrics.failedRequests}
                    </div>
                  </div>
                </div>

                <div>
                  <span className='text-gray-600 text-sm'>Avg Response Time</span>
                  <div className='font-medium'>{integrationMetrics.averageResponseTime}ms</div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// Analytics Tab (simplified)
function AnalyticsTab({
  integrations,
  metrics,
}: {
  integrations: ServiceIntegration[];
  metrics: Record<string, IntegrationMetrics>;
}) {
  return (
    <div className='space-y-6'>
      <Card className='p-6'>
        <h3 className='font-semibold mb-4'>Integration Performance</h3>
        <div className='h-64'>
          <UniversalChart
            type='bar'
            data={{
              labels: integrations.map((i) => i.name),
              datasets: [
                {
                  label: 'Response Time (ms)',
                  data: integrations.map((i) => metrics[i.id]?.averageResponseTime || 0),
                  backgroundColor: 'rgba(59, 130, 246, 0.5)',
                },
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
            }}
          />
        </div>
      </Card>
    </div>
  );
}

// Integration Editor Modal (simplified)
function IntegrationEditorModal({
  integration,
  onSave,
  onCancel,
}: {
  integration: ServiceIntegration;
  onSave: (integration: ServiceIntegration) => void;
  onCancel: () => void;
}) {
  const [editedIntegration, setEditedIntegration] = useState(integration);

  return (
    <Modal isOpen onClose={onCancel} size='large'>
      <div className='p-6'>
        <h2 className='text-xl font-bold mb-4'>Edit Integration</h2>

        <div className='space-y-4'>
          <div>
            <label className='block text-sm font-medium mb-2'>Integration Name</label>
            <Input
              value={editedIntegration.name}
              onChange={(e) => setEditedIntegration((prev) => ({ ...prev, name: e.target.value }))}
            />
          </div>

          <div>
            <label className='block text-sm font-medium mb-2'>Type</label>
            <Select
              value={editedIntegration.type}
              onValueChange={(value: any) =>
                setEditedIntegration((prev) => ({ ...prev, type: value }))
              }
            >
              {Object.entries(SERVICE_TYPES).map(([key, type]) => (
                <option key={key} value={key}>
                  {type.label}
                </option>
              ))}
            </Select>
          </div>

          <div className='flex justify-end space-x-3'>
            <Button variant='outline' onClick={onCancel}>
              Cancel
            </Button>
            <Button onClick={() => onSave(editedIntegration)}>Save Integration</Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}

export const ServiceIntegrationDashboard = standard_exception_handler(
  withComponentRegistration(ServiceIntegrationDashboardImpl, {
    name: 'ServiceIntegrationDashboard',
    category: 'workflow',
    portal: 'shared',
    version: '1.0.0',
    description: 'Service integration monitoring and management dashboard',
  })
);

export default ServiceIntegrationDashboard;
