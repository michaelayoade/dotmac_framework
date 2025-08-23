'use client';

import { useState } from 'react';
import { WorkOrdersList } from '../../components/work-orders/WorkOrdersList';
import { WorkOrderRoutingMap, TechnicianLocationTracker } from '@dotmac/mapping';
import { MobileLayout } from '../../components/layout/MobileLayout';

// Mock data for demonstration
const mockTechnicians = [
  {
    id: 'TECH-001',
    name: 'John Smith',
    coordinates: { latitude: 47.6062, longitude: -122.3321 },
    status: 'available' as const,
    skills: ['installation', 'repair', 'maintenance'],
    territory: 'Seattle Central',
  },
  {
    id: 'TECH-002',
    name: 'Sarah Johnson',
    coordinates: { latitude: 47.6205, longitude: -122.3212 },
    status: 'on-job' as const,
    currentWorkOrder: 'WO-003',
    skills: ['installation', 'survey'],
    territory: 'Capitol Hill',
  },
  {
    id: 'TECH-003',
    name: 'Mike Chen',
    coordinates: { latitude: 47.6512, longitude: -122.3501 },
    status: 'available' as const,
    skills: ['repair', 'maintenance'],
    territory: 'Fremont',
  },
];

const mockWorkOrders = [
  {
    id: 'WO-001',
    type: 'installation' as const,
    priority: 'high' as const,
    coordinates: { latitude: 47.6101, longitude: -122.2015 },
    address: '123 Bellevue Ave, Seattle, WA',
    status: 'pending' as const,
    estimatedDuration: 120,
    description: 'Fiber internet installation for residential customer',
  },
  {
    id: 'WO-002',
    type: 'repair' as const,
    priority: 'critical' as const,
    coordinates: { latitude: 47.637, longitude: -122.3572 },
    address: '456 Queen Anne Rd, Seattle, WA',
    status: 'pending' as const,
    estimatedDuration: 90,
    description: 'Service outage - fiber cut repair',
  },
  {
    id: 'WO-003',
    type: 'maintenance' as const,
    priority: 'medium' as const,
    coordinates: { latitude: 47.6205, longitude: -122.3212 },
    address: '789 Capitol Hill St, Seattle, WA',
    status: 'in-progress' as const,
    technicianId: 'TECH-002',
    estimatedDuration: 60,
    description: 'Scheduled maintenance on fiber node',
  },
  {
    id: 'WO-004',
    type: 'survey' as const,
    priority: 'low' as const,
    coordinates: { latitude: 47.674, longitude: -122.1215 },
    address: '321 Redmond Way, Redmond, WA',
    status: 'pending' as const,
    estimatedDuration: 45,
    scheduledTime: new Date(Date.now() + 2 * 60 * 60 * 1000), // 2 hours from now
    description: 'Site survey for new business installation',
  },
];

export default function WorkOrdersPage() {
  const [activeView, setActiveView] = useState<'list' | 'map' | 'tracking'>('list');

  return (
    <MobileLayout headerTitle='Work Orders'>
      <div className='flex flex-col h-full'>
        {/* View Toggle */}
        <div className='flex bg-gray-100 rounded-lg p-1 m-4 mb-2'>
          <button
            onClick={() => setActiveView('list')}
            className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
              activeView === 'list'
                ? 'bg-white text-blue-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📋 List
          </button>
          <button
            onClick={() => setActiveView('map')}
            className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
              activeView === 'map'
                ? 'bg-white text-blue-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            🗺️ Route Map
          </button>
          <button
            onClick={() => setActiveView('tracking')}
            className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
              activeView === 'tracking'
                ? 'bg-white text-blue-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📍 Live Tracking
          </button>
        </div>

        {/* Content Area */}
        <div className='flex-1 overflow-hidden'>
          {activeView === 'list' && (
            <div className='h-full px-4'>
              <WorkOrdersList />
            </div>
          )}

          {activeView === 'map' && (
            <div className='h-full bg-gray-50'>
              <WorkOrderRoutingMap
                technicians={mockTechnicians}
                workOrders={mockWorkOrders}
                showOptimizedRoutes={true}
                routingAlgorithm='balanced'
                className='h-full'
              />
            </div>
          )}

          {activeView === 'tracking' && (
            <div className='h-full bg-gray-50'>
              <TechnicianLocationTracker
                technicians={mockTechnicians}
                workOrders={mockWorkOrders}
                showRoutes={true}
                showWorkOrders={true}
                autoRefresh={true}
                refreshInterval={30000}
                className='h-full'
              />
            </div>
          )}
        </div>

        {/* Quick Stats */}
        <div className='bg-white border-t border-gray-200 p-4'>
          <div className='grid grid-cols-4 gap-4 text-center text-sm'>
            <div>
              <div className='text-lg font-bold text-blue-600'>
                {mockWorkOrders.filter((wo) => wo.status === 'pending').length}
              </div>
              <div className='text-gray-600'>Pending</div>
            </div>
            <div>
              <div className='text-lg font-bold text-yellow-600'>
                {mockWorkOrders.filter((wo) => wo.status === 'assigned').length}
              </div>
              <div className='text-gray-600'>Assigned</div>
            </div>
            <div>
              <div className='text-lg font-bold text-green-600'>
                {mockWorkOrders.filter((wo) => wo.status === 'in-progress').length}
              </div>
              <div className='text-gray-600'>Active</div>
            </div>
            <div>
              <div className='text-lg font-bold text-purple-600'>
                {mockWorkOrders.filter((wo) => wo.priority === 'critical').length}
              </div>
              <div className='text-gray-600'>Critical</div>
            </div>
          </div>
        </div>
      </div>
    </MobileLayout>
  );
}
