'use client';

import { Card, CardContent, CardHeader, CardTitle } from '../../ui/Card';
import { Package, Truck, AlertTriangle, CheckCircle } from 'lucide-react';

export function InventoryManagement() {
  return (
    <div className='space-y-6'>
      <div>
        <h1 className='text-2xl font-bold text-gray-900'>Inventory Management</h1>
        <p className='text-gray-600'>
          Equipment tracking, warehouse management, and asset lifecycle
        </p>
      </div>

      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6 text-center'>
            <Package className='w-12 h-12 text-blue-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Total Items</h3>
            <p className='text-3xl font-bold text-blue-600'>1,247</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <CheckCircle className='w-12 h-12 text-green-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>In Stock</h3>
            <p className='text-3xl font-bold text-green-600'>876</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <Truck className='w-12 h-12 text-yellow-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>In Transit</h3>
            <p className='text-3xl font-bold text-yellow-600'>45</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6 text-center'>
            <AlertTriangle className='w-12 h-12 text-red-600 mx-auto mb-4' />
            <h3 className='text-lg font-semibold text-gray-900 mb-2'>Low Stock</h3>
            <p className='text-3xl font-bold text-red-600'>12</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Equipment Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='text-center py-8 text-gray-500'>
            Equipment and asset management interface - connects to ISP Framework inventory module
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
