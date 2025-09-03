'use client';

import { Card, CardContent } from '../../ui/Card';
import { Truck, MapPin, Wrench, Clock } from 'lucide-react';

export function FieldOpsManagement() {
  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Field Operations</h1>
        <p className='text-gray-600'>
          Work orders, technician management, and field service coordination
        </p>
      </div>
      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6 text-center'>
            <Wrench className='w-12 h-12 text-blue-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Work Orders</h3>
            <p className='text-3xl font-bold text-blue-600'>34</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
