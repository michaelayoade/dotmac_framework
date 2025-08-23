'use client';

import { Card, CardContent } from '../../ui/Card';
import { Bell } from 'lucide-react';

export function NotificationManagement() {
  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Notification Management</h1>
        <p className='text-gray-600'>Customer communications, email templates, SMS integration</p>
      </div>
      <Card>
        <CardContent className='p-6 text-center'>
          <Bell className='w-12 h-12 text-blue-600 mx-auto mb-4' />
          <div className='text-center py-8 text-gray-500'>
            Notification and communication management interface - connects to ISP Framework
            notifications module
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
