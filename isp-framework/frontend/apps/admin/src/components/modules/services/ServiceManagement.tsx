'use client';

import { Card, CardContent, CardHeader, CardTitle } from '../../ui/Card';
import { Button } from '../../ui/Button';
import { Router, Wifi, Globe, Phone, Tv, Plus } from 'lucide-react';

export function ServiceManagement() {
  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Service Management</h1>
          <p className='text-gray-600'>Manage service catalog and customer service instances</p>
        </div>
        <Button className='flex items-center'>
          <Plus className='w-4 h-4 mr-2' />
          Add Service
        </Button>
      </div>

      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6 text-center'>
            <Wifi className='w-12 h-12 text-blue-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Internet Services</h3>
            <p className='text-3xl font-bold text-blue-600'>847</p>
            <p className='text-sm text-gray-500'>Active connections</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Phone className='w-12 h-12 text-green-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Phone Services</h3>
            <p className='text-3xl font-bold text-green-600'>234</p>
            <p className='text-sm text-gray-500'>Active lines</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Tv className='w-12 h-12 text-purple-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>TV Services</h3>
            <p className='text-3xl font-bold text-purple-600'>156</p>
            <p className='text-sm text-gray-500'>Active subscriptions</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Globe className='w-12 h-12 text-orange-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Business Services</h3>
            <p className='text-3xl font-bold text-orange-600'>89</p>
            <p className='text-sm text-gray-500'>Enterprise accounts</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Service Catalog</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='text-center py-8 text-gray-500'>
            Service catalog management interface - connects to ISP Framework services module
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
