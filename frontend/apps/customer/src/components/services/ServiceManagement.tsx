'use client';

import { useCachedData } from '@dotmac/headless';
import { Card } from '@dotmac/ui/customer';
import {
  AlertCircle,
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
  MapPin,
  Pause,
  Phone,
  Settings,
  TrendingUp,
  Tv,
  Upgrade,
  Wifi,
} from 'lucide-react';
import { useState } from 'react';

// Mock service data
const mockServiceData = {
  services: [
    {
      id: 'SVC-001',
      name: 'Fiber Internet 100/100',
      type: 'internet',
      status: 'active',
      plan: 'Fiber 100/100',
      speed: { download: 100, upload: 100 },
      usage: {
        current: 450,
        limit: 1000,
        unit: 'GB',
        billingPeriod: '2024-01-15 to 2024-02-14',
      },
      monthlyPrice: 79.99,
      installDate: '2024-01-15',
      nextBillDate: '2024-02-15',
      features: ['Unlimited Data', 'No Contracts', 'Free Installation', '24/7 Support'],
      equipment: [
        { name: 'Fiber Modem', model: 'FM-2000', serialNumber: 'FM123456789' },
        { name: 'WiFi Router', model: 'WR-5000', serialNumber: 'WR987654321' },
      ],
      technicalDetails: {
        ipAddress: '192.168.1.100',
        dnsServers: ['8.8.8.8', '8.8.4.4'],
        gateway: '192.168.1.1',
        subnet: '255.255.255.0',
      },
    },
    {
      id: 'SVC-002',
      name: 'Basic Phone Service',
      type: 'phone',
      status: 'active',
      plan: 'Basic Phone',
      monthlyPrice: 29.99,
      installDate: '2024-01-15',
      nextBillDate: '2024-02-15',
      features: ['Unlimited Local Calls', 'Voicemail', 'Caller ID', 'Call Waiting'],
      phoneNumber: '+1 (555) 123-4567',
      equipment: [{ name: 'Phone Adapter', model: 'PA-100', serialNumber: 'PA555666777' }],
    },
  ],
  serviceAddress: {
    street: '123 Main Street',
    city: 'Anytown',
    state: 'ST',
    zipCode: '12345',
    instructions: 'Apartment 2B, use side entrance',
  },
  availableUpgrades: [
    {
      id: 'UPGRADE-001',
      name: 'Fiber 500/500',
      currentPlan: 'Fiber 100/100',
      newPlan: 'Fiber 500/500',
      priceIncrease: 40.0,
      benefits: ['5x faster speeds', 'Priority support', 'Advanced WiFi 6 router'],
      estimatedInstall: '1-2 business days',
    },
    {
      id: 'UPGRADE-002',
      name: 'Premium Phone Package',
      currentPlan: 'Basic Phone',
      newPlan: 'Premium Phone',
      priceIncrease: 15.0,
      benefits: ['Unlimited long distance', 'International calling credits', 'Advanced voicemail'],
      estimatedInstall: 'Instant activation',
    },
  ],
  recentActivity: [
    {
      id: 'ACT-001',
      type: 'usage_alert',
      message: 'You have used 75% of your data allowance',
      timestamp: '2024-01-28T10:30:00Z',
      severity: 'warning',
    },
    {
      id: 'ACT-002',
      type: 'service_update',
      message: 'Network maintenance completed successfully',
      timestamp: '2024-01-25T08:00:00Z',
      severity: 'info',
    },
    {
      id: 'ACT-003',
      type: 'payment_processed',
      message: 'Monthly payment of $109.98 processed',
      timestamp: '2024-01-15T12:00:00Z',
      severity: 'success',
    },
  ],
};

export function ServiceManagement() {
  const [activeTab, setActiveTab] = useState<'overview' | 'usage' | 'equipment' | 'upgrades'>(
    'overview'
  );
  const [_selectedService, setSelectedService] = useState<string | null>(null);

  const { data: serviceData, isLoading } = useCachedData(
    'customer-services',
    async () => mockServiceData,
    { ttl: 5 * 60 * 1000 }
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'suspended':
        return <Pause className="h-5 w-5 text-yellow-600" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-blue-600" />;
      case 'cancelled':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return <AlertTriangle className="h-5 w-5 text-gray-600" />;
    }
  };

  const getServiceIcon = (type: string) => {
    switch (type) {
      case 'internet':
        return <Wifi className="h-6 w-6 text-blue-600" />;
      case 'phone':
        return <Phone className="h-6 w-6 text-green-600" />;
      case 'tv':
        return <Tv className="h-6 w-6 text-purple-600" />;
      default:
        return <Settings className="h-6 w-6 text-gray-600" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'success':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  if (isLoading || !serviceData) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Service Overview Cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {serviceData.services.map(service => (
          <Card key={service.id} className="p-6">
            <div className="mb-4 flex items-start justify-between">
              <div className="flex items-center">
                {getServiceIcon(service.type)}
                <div className="ml-3">
                  <h3 className="font-semibold text-gray-900 text-lg">{service.name}</h3>
                  <p className="text-gray-500 text-sm">{service.plan}</p>
                </div>
              </div>
              <div className="flex items-center">
                {getStatusIcon(service.status)}
                <span className="ml-2 font-medium text-gray-900 text-sm capitalize">
                  {service.status}
                </span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600 text-sm">Monthly Rate</span>
                <span className="font-medium text-sm">{formatCurrency(service.monthlyPrice)}</span>
              </div>

              {service.speed ? (
                <div className="flex justify-between">
                  <span className="text-gray-600 text-sm">Speed</span>
                  <span className="font-medium text-sm">
                    {service.speed.download}/{service.speed.upload} Mbps
                  </span>
                </div>
              ) : null}

              {service.phoneNumber ? (
                <div className="flex justify-between">
                  <span className="text-gray-600 text-sm">Phone Number</span>
                  <span className="font-medium text-sm">{service.phoneNumber}</span>
                </div>
              ) : null}

              <div className="flex justify-between">
                <span className="text-gray-600 text-sm">Next Bill</span>
                <span className="font-medium text-sm">{formatDate(service.nextBillDate)}</span>
              </div>

              {service.usage ? (
                <div className="mt-4">
                  <div className="mb-1 flex justify-between text-gray-600 text-sm">
                    <span>Data Usage</span>
                    <span>
                      {service.usage.current} / {service.usage.limit} {service.usage.unit}
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-gray-200">
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        service.usage.current / service.usage.limit > 0.8
                          ? 'bg-yellow-500'
                          : 'bg-blue-600'
                      }`}
                      style={{
                        width: `${Math.min((service.usage.current / service.usage.limit) * 100, 100)}%`,
                      }}
                    />
                  </div>
                  <p className="mt-1 text-gray-500 text-xs">
                    Billing period: {service.usage.billingPeriod}
                  </p>
                </div>
              ) : null}
            </div>

            <div className="mt-6 flex space-x-2">
              <button
                type="button"
                onClick={() => setSelectedService(service.id)}
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
              >
                Manage Service
              </button>
              <button
                type="button"
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
              >
                View Details
              </button>
            </div>
          </Card>
        ))}
      </div>

      {/* Service Address */}
      <Card className="p-6">
        <div className="mb-4 flex items-center">
          <MapPin className="mr-2 h-5 w-5 text-gray-400" />
          <h3 className="font-semibold text-gray-900 text-lg">Service Address</h3>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <p className="text-gray-900">
              {serviceData.serviceAddress.street}
              <br />
              {serviceData.serviceAddress.city}, {serviceData.serviceAddress.state}{' '}
              {serviceData.serviceAddress.zipCode}
            </p>
            {serviceData.serviceAddress.instructions ? (
              <p className="mt-2 text-gray-600 text-sm">
                <strong>Special Instructions:</strong> {serviceData.serviceAddress.instructions}
              </p>
            ) : null}
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
            >
              Update Address
            </button>
          </div>
        </div>
      </Card>

      {/* Tab Navigation */}
      <div className="border-gray-200 border-b">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: 'Service Overview' },
            { id: 'usage', label: 'Usage Details' },
            { id: 'equipment', label: 'Equipment' },
            { id: 'upgrades', label: 'Available Upgrades' },
          ].map(tab => (
            <button
              type="button"
              key={tab.id}
              onClick={() => setActiveTab(tab.id as unknown)}
              className={`border-b-2 px-1 py-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Service Features */}
          <Card className="p-6">
            <h3 className="mb-4 font-semibold text-gray-900 text-lg">Service Features</h3>
            {serviceData.services.map(service => (
              <div key={service.id} className="mb-6">
                <h4 className="mb-2 font-medium text-gray-900">{service.name}</h4>
                <ul className="space-y-1">
                  {service.features.map((feature, index) => (
                    <li
                      key={`${service.id}-feature-${index}`}
                      className="flex items-center text-gray-600 text-sm"
                    >
                      <CheckCircle className="mr-2 h-4 w-4 text-green-600" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </Card>

          {/* Recent Activity */}
          <Card className="p-6">
            <h3 className="mb-4 font-semibold text-gray-900 text-lg">Recent Activity</h3>
            <div className="space-y-3">
              {serviceData.recentActivity.map(activity => (
                <div
                  key={activity.id}
                  className={`rounded-lg border p-3 ${getSeverityColor(activity.severity)}`}
                >
                  <p className="font-medium text-sm">{activity.message}</p>
                  <p className="mt-1 text-xs">{formatTimestamp(activity.timestamp)}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'usage' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {serviceData.services
            .filter(service => service.usage)
            .map(service => (
              <Card key={service.id} className="p-6">
                <div className="mb-4 flex items-center">
                  <TrendingUp className="mr-2 h-5 w-5 text-blue-600" />
                  <h3 className="font-semibold text-gray-900 text-lg">{service.name} Usage</h3>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="mb-2 flex justify-between font-medium text-sm">
                      <span>Current Usage</span>
                      <span>
                        {service.usage?.current} / {service.usage?.limit} {service.usage?.unit}
                      </span>
                    </div>
                    <div className="h-3 w-full rounded-full bg-gray-200">
                      <div
                        className={`h-3 rounded-full transition-all duration-300 ${
                          service.usage?.current / service.usage?.limit > 0.8
                            ? 'bg-yellow-500'
                            : 'bg-blue-600'
                        }`}
                        style={{
                          width: `${Math.min((service.usage?.current / service.usage?.limit) * 100, 100)}%`,
                        }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Billing Period</span>
                      <p className="font-medium">{service.usage?.billingPeriod}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Days Remaining</span>
                      <p className="font-medium">17 days</p>
                    </div>
                  </div>

                  {service.speed ? (
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Download Speed</span>
                        <p className="font-medium">{service.speed.download} Mbps</p>
                      </div>
                      <div>
                        <span className="text-gray-600">Upload Speed</span>
                        <p className="font-medium">{service.speed.upload} Mbps</p>
                      </div>
                    </div>
                  ) : null}
                </div>

                <button
                  type="button"
                  className="mt-4 w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50"
                >
                  View Detailed Usage
                </button>
              </Card>
            ))}
        </div>
      )}

      {activeTab === 'equipment' && (
        <div className="space-y-6">
          {serviceData.services.map(service => (
            <Card key={service.id} className="p-6">
              <h3 className="mb-4 font-semibold text-gray-900 text-lg">{service.name} Equipment</h3>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {service.equipment.map((equipment, index) => (
                  <div key={`${service.id}-equipment-${index}`} className="rounded-lg border p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <h4 className="font-medium text-gray-900">{equipment.name}</h4>
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    </div>
                    <div className="space-y-1 text-gray-600 text-sm">
                      <p>
                        <strong>Model:</strong> {equipment.model}
                      </p>
                      <p>
                        <strong>Serial:</strong> {equipment.serialNumber}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {service.technicalDetails ? (
                <div className="mt-6 rounded-lg bg-gray-50 p-4">
                  <h4 className="mb-2 font-medium text-gray-900">Technical Details</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">IP Address:</span>
                      <span className="ml-2 font-mono">{service.technicalDetails.ipAddress}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Gateway:</span>
                      <span className="ml-2 font-mono">{service.technicalDetails.gateway}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">DNS:</span>
                      <span className="ml-2 font-mono">
                        {service.technicalDetails.dnsServers.join(', ')}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Subnet:</span>
                      <span className="ml-2 font-mono">{service.technicalDetails.subnet}</span>
                    </div>
                  </div>
                </div>
              ) : null}
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'upgrades' && (
        <div className="space-y-6">
          <Card className="p-6">
            <div className="mb-4 flex items-center">
              <Upgrade className="mr-2 h-5 w-5 text-green-600" />
              <h3 className="font-semibold text-gray-900 text-lg">Available Service Upgrades</h3>
            </div>

            <div className="space-y-4">
              {serviceData.availableUpgrades.map(upgrade => (
                <div key={upgrade.id} className="rounded-lg border p-6">
                  <div className="mb-4 flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-gray-900 text-lg">{upgrade.name}</h4>
                      <p className="text-gray-600 text-sm">
                        Upgrade from {upgrade.currentPlan} to {upgrade.newPlan}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-green-600 text-lg">
                        +{formatCurrency(upgrade.priceIncrease)}/month
                      </p>
                    </div>
                  </div>

                  <div className="mb-4">
                    <h5 className="mb-2 font-medium text-gray-900">Benefits Include:</h5>
                    <ul className="space-y-1">
                      {upgrade.benefits.map((benefit, index) => (
                        <li
                          key={`${upgrade.id}-benefit-${index}`}
                          className="flex items-center text-gray-600 text-sm"
                        >
                          <CheckCircle className="mr-2 h-4 w-4 text-green-600" />
                          {benefit}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center text-gray-600 text-sm">
                      <Calendar className="mr-1 h-4 w-4" />
                      Installation: {upgrade.estimatedInstall}
                    </div>
                    <button
                      type="button"
                      className="rounded-lg bg-green-600 px-6 py-2 text-white transition-colors hover:bg-green-700"
                    >
                      Upgrade Now
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
