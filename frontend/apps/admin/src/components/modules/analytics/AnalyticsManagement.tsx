'use client';

import { Card, CardContent, CardHeader, CardTitle } from '../../ui/Card';
import { BarChart3, TrendingUp, PieChart, Activity } from 'lucide-react';

export function AnalyticsManagement() {
  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Analytics & Reporting</h1>
        <p className='text-gray-600'>Business intelligence, dashboards, and performance reports</p>
      </div>

      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6 text-center'>
            <BarChart3 className='w-12 h-12 text-blue-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Revenue Analytics</h3>
            <p className='text-sm text-gray-500'>Financial performance tracking</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <TrendingUp className='w-12 h-12 text-green-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Customer Growth</h3>
            <p className='text-sm text-gray-500'>Subscriber acquisition trends</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <PieChart className='w-12 h-12 text-purple-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Service Usage</h3>
            <p className='text-sm text-gray-500'>Bandwidth and service metrics</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Activity className='w-12 h-12 text-orange-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Network Performance</h3>
            <p className='text-sm text-gray-500'>Infrastructure health metrics</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Interactive Dashboards</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='text-center py-8 text-gray-500'>
            Analytics dashboards and reporting interface - connects to ISP Framework analytics
            module
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
