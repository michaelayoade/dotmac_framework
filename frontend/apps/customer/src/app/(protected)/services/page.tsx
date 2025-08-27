'use client';

import { ServiceCoverageMap } from '@dotmac/mapping';
// import { SkeletonCard } from '@dotmac/primitives';

// Temporary skeleton component
const SkeletonCardPlaceholder = ({ className = "h-32" }: { className?: string }) => (
  <div className={`bg-gray-200 rounded animate-pulse ${className}`} />
);
import { Suspense, useState } from 'react';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';
import { ServiceManagement } from '../../../components/services/ServiceManagement';
import { ServicePlans } from '../../../components/services/ServicePlans';
import { ServiceTroubleshooting } from '../../../components/services/ServiceTroubleshooting';

// Mock service coverage data for demonstration
const mockServiceAreas = [
  {
    id: 'SA-001',
    name: 'Downtown Seattle Fiber',
    type: 'fiber' as const,
    polygon: [
      { latitude: 47.6, longitude: -122.34 },
      { latitude: 47.6, longitude: -122.32 },
      { latitude: 47.615, longitude: -122.32 },
      { latitude: 47.615, longitude: -122.34 },
    ],
    serviceLevel: 'full' as const,
    maxSpeed: 1000,
    population: 25000,
    households: 12000,
    coverage: 95,
  },
  {
    id: 'SA-002',
    name: 'Capitol Hill Mixed Service',
    type: 'cable' as const,
    polygon: [
      { latitude: 47.615, longitude: -122.33 },
      { latitude: 47.615, longitude: -122.31 },
      { latitude: 47.63, longitude: -122.31 },
      { latitude: 47.63, longitude: -122.33 },
    ],
    serviceLevel: 'partial' as const,
    maxSpeed: 500,
    population: 18000,
    households: 9500,
    coverage: 72,
  },
  {
    id: 'SA-003',
    name: 'Bellevue Expansion',
    type: 'fiber' as const,
    polygon: [
      { latitude: 47.605, longitude: -122.21 },
      { latitude: 47.605, longitude: -122.19 },
      { latitude: 47.62, longitude: -122.19 },
      { latitude: 47.62, longitude: -122.21 },
    ],
    serviceLevel: 'planned' as const,
    maxSpeed: 1000,
    population: 22000,
    households: 11000,
    coverage: 0,
  },
];

const mockCustomers = [
  {
    id: 'CUST-001',
    name: 'Current Customer Location',
    coordinates: { latitude: 47.6062, longitude: -122.3321 },
    serviceType: 'residential' as const,
    plan: 'Fiber 500 Mbps',
    speed: 500,
    monthlyRevenue: 79.99,
    installDate: new Date('2023-06-15'),
    status: 'active' as const,
    satisfaction: 8.5,
  },
];

export default function ServicesPage() {
  const [showCoverageMap, setShowCoverageMap] = useState(false);

  return (
    <CustomerLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Services</h1>
            <p className="mt-1 text-sm text-gray-500">
              Manage your services, monitor usage, and explore upgrades
            </p>
          </div>
          <button
            onClick={() => setShowCoverageMap(!showCoverageMap)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {showCoverageMap ? '📋 Service Details' : '🗺️ Coverage Map'}
          </button>
        </div>

        {showCoverageMap ? (
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Service Coverage in Your Area</h2>
              <p className="text-sm text-gray-600 mt-1">
                Explore available services and coverage areas near your location
              </p>
            </div>
            <div className="h-[500px] bg-gray-50">
              <ServiceCoverageMap
                serviceAreas={mockServiceAreas}
                customers={mockCustomers}
                showCustomers={true}
                filterServiceType="all"
                className="h-full"
                config={{
                  defaultCenter: { latitude: 47.6062, longitude: -122.3321 },
                  defaultZoom: 12,
                }}
              />
            </div>
            <div className="p-4 bg-gray-50 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="font-semibold text-green-600">
                    {mockServiceAreas.filter(sa => sa.serviceLevel === 'full').length} Areas
                  </div>
                  <div className="text-gray-600">Full Service Available</div>
                </div>
                <div className="text-center">
                  <div className="font-semibold text-yellow-600">
                    {mockServiceAreas.filter(sa => sa.serviceLevel === 'partial').length} Areas
                  </div>
                  <div className="text-gray-600">Partial Coverage</div>
                </div>
                <div className="text-center">
                  <div className="font-semibold text-blue-600">
                    {mockServiceAreas.filter(sa => sa.serviceLevel === 'planned').length} Areas
                  </div>
                  <div className="text-gray-600">Coming Soon</div>
                </div>
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <span className="text-blue-600 text-lg">💡</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-blue-800">
                      <strong>Your Location:</strong> You're currently in our full fiber coverage
                      area with speeds up to 1 Gbps available.
                    </p>
                    <p className="text-sm text-blue-700 mt-1">
                      Interested in upgrading or adding services? Contact us to explore your
                      options.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <Suspense fallback={<ServicesSkeleton />}>
            <ServicesContent />
          </Suspense>
        )}
      </div>
    </CustomerLayout>
  );
}

function ServicesContent() {
  return (
    <div className="space-y-8">
      <ServiceManagement />
      <ServicePlans />
      <ServiceTroubleshooting />
    </div>
  );
}

function ServicesSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <SkeletonCardPlaceholder />
        <SkeletonCardPlaceholder />
        <SkeletonCardPlaceholder />
      </div>
      <SkeletonCardPlaceholder className="h-64" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonCardPlaceholder />
        <SkeletonCardPlaceholder />
      </div>
    </div>
  );
}
