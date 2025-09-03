'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Settings,
  Key,
  Shield,
  Globe,
  Mail,
  CreditCard,
  Network,
  Users,
  Bell,
  Database,
  Zap,
  Clock,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';

// Configuration categories
interface ConfigCategory {
  id: string;
  title: string;
  description: string;
  icon: any;
  status: 'configured' | 'needs_attention' | 'not_configured';
  lastUpdated?: string;
  route?: string;
  items: ConfigItem[];
}

interface ConfigItem {
  id: string;
  name: string;
  description: string;
  status: 'configured' | 'needs_attention' | 'not_configured';
  route?: string;
}

export default function SystemConfigurationPage() {
  const router = useRouter();

  const [categories] = useState<ConfigCategory[]>([
    {
      id: 'authentication',
      title: 'Authentication & Access',
      description: 'Portal IDs, user authentication, and access control settings',
      icon: Key,
      status: 'configured',
      lastUpdated: '2024-01-25T10:30:00Z',
      items: [
        {
          id: 'portal-id',
          name: 'Portal ID Generation',
          description: 'Configure how Portal IDs are generated for customers',
          status: 'configured',
          route: '/configuration/portal-id',
        },
        {
          id: 'password-policy',
          name: 'Password Policy',
          description: 'Set password requirements and security rules',
          status: 'needs_attention',
        },
        {
          id: 'mfa',
          name: 'Multi-Factor Authentication',
          description: 'Configure MFA settings for different user types',
          status: 'not_configured',
        },
        {
          id: 'sso',
          name: 'Single Sign-On',
          description: 'External authentication providers and SAML/OIDC',
          status: 'not_configured',
        },
      ],
    },
    {
      id: 'security',
      title: 'Security & Compliance',
      description: 'Security policies, encryption, and compliance settings',
      icon: Shield,
      status: 'needs_attention',
      lastUpdated: '2024-01-20T14:15:00Z',
      items: [
        {
          id: 'encryption',
          name: 'Data Encryption',
          description: 'Configure encryption for data at rest and in transit',
          status: 'configured',
        },
        {
          id: 'audit-logs',
          name: 'Audit Logging',
          description: 'System activity logging and retention policies',
          status: 'configured',
        },
        {
          id: 'firewall',
          name: 'Firewall Rules',
          description: 'Network access control and IP restrictions',
          status: 'needs_attention',
        },
        {
          id: 'backup',
          name: 'Backup & Recovery',
          description: 'Automated backups and disaster recovery settings',
          status: 'needs_attention',
        },
      ],
    },
    {
      id: 'network',
      title: 'Network & Infrastructure',
      description: 'Network configuration, DNS, and infrastructure settings',
      icon: Network,
      status: 'configured',
      lastUpdated: '2024-01-24T09:45:00Z',
      items: [
        {
          id: 'dns',
          name: 'DNS Configuration',
          description: 'Domain name system settings and custom domains',
          status: 'configured',
        },
        {
          id: 'load-balancer',
          name: 'Load Balancing',
          description: 'Traffic distribution and failover configuration',
          status: 'configured',
        },
        {
          id: 'cdn',
          name: 'Content Delivery Network',
          description: 'CDN settings and cache configuration',
          status: 'needs_attention',
        },
        {
          id: 'monitoring',
          name: 'Network Monitoring',
          description: 'Network performance and health monitoring',
          status: 'configured',
        },
      ],
    },
    {
      id: 'billing',
      title: 'Billing & Payments',
      description: 'Payment processing, billing cycles, and pricing configuration',
      icon: CreditCard,
      status: 'configured',
      lastUpdated: '2024-01-23T16:20:00Z',
      items: [
        {
          id: 'payment-gateways',
          name: 'Payment Gateways',
          description: 'Configure payment processors and methods',
          status: 'configured',
        },
        {
          id: 'billing-cycles',
          name: 'Billing Cycles',
          description: 'Set billing frequencies and invoice generation',
          status: 'configured',
        },
        {
          id: 'pricing-tiers',
          name: 'Pricing Tiers',
          description: 'Service packages and pricing configuration',
          status: 'needs_attention',
        },
        {
          id: 'tax-settings',
          name: 'Tax Configuration',
          description: 'Tax rates and compliance settings by region',
          status: 'not_configured',
        },
      ],
    },
    {
      id: 'communication',
      title: 'Communication & Notifications',
      description: 'Email, SMS, and notification system configuration',
      icon: Mail,
      status: 'needs_attention',
      lastUpdated: '2024-01-22T11:30:00Z',
      items: [
        {
          id: 'email-server',
          name: 'Email Server',
          description: 'SMTP configuration and email delivery settings',
          status: 'configured',
        },
        {
          id: 'sms-gateway',
          name: 'SMS Gateway',
          description: 'SMS provider and messaging configuration',
          status: 'needs_attention',
        },
        {
          id: 'notification-templates',
          name: 'Notification Templates',
          description: 'Email and SMS templates for system notifications',
          status: 'needs_attention',
        },
        {
          id: 'push-notifications',
          name: 'Push Notifications',
          description: 'Mobile and web push notification settings',
          status: 'not_configured',
        },
      ],
    },
    {
      id: 'integration',
      title: 'Integrations & APIs',
      description: 'Third-party integrations and API configurations',
      icon: Zap,
      status: 'not_configured',
      lastUpdated: '2024-01-18T08:00:00Z',
      items: [
        {
          id: 'api-keys',
          name: 'API Keys & Webhooks',
          description: 'Manage API keys and webhook endpoints',
          status: 'not_configured',
        },
        {
          id: 'crm-integration',
          name: 'CRM Integration',
          description: 'Connect with customer relationship management systems',
          status: 'not_configured',
        },
        {
          id: 'accounting-sync',
          name: 'Accounting Sync',
          description: 'Integration with accounting and bookkeeping systems',
          status: 'not_configured',
        },
        {
          id: 'helpdesk',
          name: 'Helpdesk Integration',
          description: 'Support ticket system integration',
          status: 'not_configured',
        },
      ],
    },
  ]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'configured':
        return <CheckCircle2 className='h-4 w-4 text-green-600' />;
      case 'needs_attention':
        return <AlertTriangle className='h-4 w-4 text-yellow-600' />;
      case 'not_configured':
        return <AlertTriangle className='h-4 w-4 text-red-600' />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'configured':
        return (
          <Badge variant='secondary' className='text-green-700 bg-green-100'>
            Configured
          </Badge>
        );
      case 'needs_attention':
        return (
          <Badge variant='secondary' className='text-yellow-700 bg-yellow-100'>
            Needs Attention
          </Badge>
        );
      case 'not_configured':
        return (
          <Badge variant='secondary' className='text-red-700 bg-red-100'>
            Not Configured
          </Badge>
        );
      default:
        return null;
    }
  };

  const handleCategoryClick = (category: ConfigCategory) => {
    if (category.route) {
      router.push(category.route);
    }
  };

  const handleItemClick = (item: ConfigItem) => {
    if (item.route) {
      router.push(item.route);
    }
  };

  const configuredCount = categories.reduce(
    (count, cat) => count + cat.items.filter((item) => item.status === 'configured').length,
    0
  );
  const totalItems = categories.reduce((count, cat) => count + cat.items.length, 0);
  const completionPercentage = Math.round((configuredCount / totalItems) * 100);

  return (
    <div className='min-h-screen bg-gray-50'>
      {/* Header */}
      <div className='bg-white border-b border-gray-200 shadow-sm'>
        <div className='max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center'>
              <Settings className='h-8 w-8 text-gray-600 mr-3' />
              <div>
                <h1 className='text-2xl font-semibold text-gray-900'>System Configuration</h1>
                <p className='mt-1 text-sm text-gray-600'>
                  Configure and manage all aspects of your ISP platform
                </p>
              </div>
            </div>
            <div className='text-right'>
              <div className='text-2xl font-bold text-gray-900'>{completionPercentage}%</div>
              <div className='text-sm text-gray-600'>
                {configuredCount} of {totalItems} configured
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className='max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8'>
        {/* Overview Stats */}
        <div className='grid grid-cols-1 md:grid-cols-4 gap-4 mb-8'>
          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <div className='text-2xl font-bold text-green-600'>{configuredCount}</div>
                  <div className='text-sm text-gray-600'>Configured</div>
                </div>
                <CheckCircle2 className='h-8 w-8 text-green-600' />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <div className='text-2xl font-bold text-yellow-600'>
                    {categories.reduce(
                      (count, cat) =>
                        count +
                        cat.items.filter((item) => item.status === 'needs_attention').length,
                      0
                    )}
                  </div>
                  <div className='text-sm text-gray-600'>Need Attention</div>
                </div>
                <AlertTriangle className='h-8 w-8 text-yellow-600' />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <div className='text-2xl font-bold text-red-600'>
                    {categories.reduce(
                      (count, cat) =>
                        count + cat.items.filter((item) => item.status === 'not_configured').length,
                      0
                    )}
                  </div>
                  <div className='text-sm text-gray-600'>Not Configured</div>
                </div>
                <AlertTriangle className='h-8 w-8 text-red-600' />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className='p-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <div className='text-2xl font-bold text-gray-900'>{categories.length}</div>
                  <div className='text-sm text-gray-600'>Categories</div>
                </div>
                <Settings className='h-8 w-8 text-gray-600' />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Configuration Categories */}
        <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <Card key={category.id} className='hover:shadow-lg transition-shadow'>
                <CardHeader className='pb-3'>
                  <div className='flex items-center justify-between'>
                    <div className='flex items-center space-x-3'>
                      <div className='p-2 bg-gray-100 rounded-lg'>
                        <Icon className='h-6 w-6 text-gray-600' />
                      </div>
                      <div>
                        <CardTitle className='text-lg'>{category.title}</CardTitle>
                        <CardDescription className='text-sm'>
                          {category.description}
                        </CardDescription>
                      </div>
                    </div>
                    {getStatusBadge(category.status)}
                  </div>
                  {category.lastUpdated && (
                    <div className='text-xs text-gray-500 mt-2'>
                      Last updated: {new Date(category.lastUpdated).toLocaleString()}
                    </div>
                  )}
                </CardHeader>
                <CardContent className='pt-0'>
                  <div className='space-y-2'>
                    {category.items.map((item) => (
                      <div
                        key={item.id}
                        className={`flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 transition-colors ${
                          item.route ? 'cursor-pointer' : ''
                        }`}
                        onClick={() => handleItemClick(item)}
                      >
                        <div className='flex items-center space-x-3'>
                          {getStatusIcon(item.status)}
                          <div>
                            <div className='text-sm font-medium text-gray-900'>{item.name}</div>
                            <div className='text-xs text-gray-600'>{item.description}</div>
                          </div>
                        </div>
                        {item.route && <ChevronRight className='h-4 w-4 text-gray-400' />}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Quick Actions */}
        <Card className='mt-8'>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common configuration tasks and system management</CardDescription>
          </CardHeader>
          <CardContent>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              <Button variant='outline' className='h-auto p-4 justify-start'>
                <Database className='mr-3 h-5 w-5' />
                <div className='text-left'>
                  <div className='font-medium'>Database Maintenance</div>
                  <div className='text-sm text-gray-600'>Optimize and backup database</div>
                </div>
              </Button>

              <Button variant='outline' className='h-auto p-4 justify-start'>
                <Clock className='mr-3 h-5 w-5' />
                <div className='text-left'>
                  <div className='font-medium'>Scheduled Tasks</div>
                  <div className='text-sm text-gray-600'>Manage automated processes</div>
                </div>
              </Button>

              <Button variant='outline' className='h-auto p-4 justify-start'>
                <Bell className='mr-3 h-5 w-5' />
                <div className='text-left'>
                  <div className='font-medium'>System Health</div>
                  <div className='text-sm text-gray-600'>Monitor system status</div>
                </div>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
