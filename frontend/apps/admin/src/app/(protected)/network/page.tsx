import { Suspense } from 'react';
import AdminLayout from '../../../components/layout/AdminLayout';
import { NetworkTopologyViewer } from '../../../components/network/NetworkTopologyViewer';
import { ServiceProvisioningDashboard } from '../../../components/network/ServiceProvisioningDashboard';

export default function NetworkPage() {
  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Network Management</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Monitor network infrastructure and manage service provisioning
            </p>
          </div>
          <div className='flex gap-3'>
            <button className='px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium'>
              Network Health Report
            </button>
            <button className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium'>
              Export Topology
            </button>
          </div>
        </div>

        <Suspense
          fallback={
            <div className='grid grid-cols-1 gap-6'>
              {/* Network Topology Skeleton */}
              <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                <div className='animate-pulse'>
                  <div className='h-6 bg-gray-200 rounded w-1/4 mb-4'></div>
                  <div className='h-96 bg-gray-200 rounded'></div>
                </div>
              </div>

              {/* Service Provisioning Skeleton */}
              <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
                <div className='animate-pulse'>
                  <div className='h-6 bg-gray-200 rounded w-1/4 mb-4'></div>
                  <div className='grid grid-cols-6 gap-4 mb-6'>
                    {[...Array(6)].map((_, i) => (
                      <div key={i} className='h-16 bg-gray-200 rounded'></div>
                    ))}
                  </div>
                  <div className='h-64 bg-gray-200 rounded'></div>
                </div>
              </div>
            </div>
          }
        >
          <NetworkContent />
        </Suspense>
      </div>
    </AdminLayout>
  );
}

async function NetworkContent() {
  // Simulate loading delay
  await new Promise((resolve) => setTimeout(resolve, 200));

  return (
    <div className='space-y-6'>
      {/* Network Topology Viewer */}
      <NetworkTopologyViewer />

      {/* Service Provisioning Dashboard */}
      <ServiceProvisioningDashboard />
    </div>
  );
}
