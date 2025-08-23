'use client';

import { Card, CardContent, CardHeader, CardTitle } from '../../ui/Card';
import { Headphones, AlertCircle, CheckCircle, Clock } from 'lucide-react';

export function SupportManagement() {
  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Support Management</h1>
        <p className='text-gray-600'>Customer support tickets, SLA tracking, and knowledge base</p>
      </div>

      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6 text-center'>
            <Headphones className='w-12 h-12 text-blue-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Open Tickets</h3>
            <p className='text-3xl font-bold text-blue-600'>23</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <AlertCircle className='w-12 h-12 text-red-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>High Priority</h3>
            <p className='text-3xl font-bold text-red-600'>5</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <CheckCircle className='w-12 h-12 text-green-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Resolved Today</h3>
            <p className='text-3xl font-bold text-green-600'>18</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Clock className='w-12 h-12 text-yellow-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Avg Response</h3>
            <p className='text-3xl font-bold text-yellow-600'>2.5h</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Support Tickets</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='text-center py-8 text-gray-500'>
            Support ticket management interface - connects to ISP Framework support module
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
