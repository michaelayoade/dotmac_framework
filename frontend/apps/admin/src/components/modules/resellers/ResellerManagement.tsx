'use client';

import { Card, CardContent } from '../../ui/Card';
import { Building } from 'lucide-react';

export function ResellerManagement() {
  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Reseller Management</h1>
        <p className='text-gray-600'>
          Partner management, commission tracking, and reseller portal access
        </p>
      </div>
      <Card>
        <CardContent className='p-6 text-center'>
          <Building className='w-12 h-12 text-purple-600 mx-auto mb-4' />
          <div className='text-center py-8 text-gray-500'>
            Reseller and partner management interface - connects to ISP Framework resellers module
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
