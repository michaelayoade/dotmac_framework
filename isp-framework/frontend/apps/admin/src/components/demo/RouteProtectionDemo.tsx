'use client';

import {
  AdminOnlyGuard,
  BillingManagerGuard,
  NetworkEngineerGuard,
  PermissionGuard,
  RouteGuard,
  usePermissions,
} from '@dotmac/headless';
import { Card } from '@dotmac/styled-components/admin';
import { AlertTriangle, CheckCircle, Shield, XCircle } from 'lucide-react';

export function RouteProtectionDemo() {
  const { userRoles, expandedPermissions, isAdmin, isSuperAdmin } = usePermissions();

  return (
    <div className='space-y-6'>
      <div className='rounded-lg border border-blue-200 bg-blue-50 p-6'>
        <div className='mb-4 flex items-center'>
          <Shield className='mr-2 h-6 w-6 text-blue-600' />
          <h2 className='font-semibold text-blue-900 text-xl'>Route Protection Demo</h2>
        </div>
        <p className='text-blue-800'>
          This page demonstrates role-based access control and route protection features. Different
          sections below will show or hide based on your current permissions and roles.
        </p>

        <div className='mt-4 rounded border bg-white p-4'>
          <h3 className='mb-2 font-medium text-gray-900'>Your Current Access Level:</h3>
          <div className='grid grid-cols-2 gap-4 text-sm'>
            <div>
              <strong>Roles:</strong> {userRoles.join(', ') || 'None'}
            </div>
            <div>
              <strong>Admin:</strong> {isAdmin() ? '✅ Yes' : '❌ No'}
            </div>
            <div>
              <strong>Super Admin:</strong> {isSuperAdmin() ? '✅ Yes' : '❌ No'}
            </div>
            <div>
              <strong>Permissions:</strong> {expandedPermissions.length} total
            </div>
          </div>
        </div>
      </div>

      <div className='grid grid-cols-1 gap-6 lg:grid-cols-2'>
        {/* Admin Only Section */}
        <Card className='p-6'>
          <h3 className='mb-4 flex items-center font-semibold text-gray-900 text-lg'>
            <Shield className='mr-2 h-5 w-5 text-blue-600' />
            Admin Only Section
          </h3>

          <AdminOnlyGuard
            fallback={
              <div className='flex items-center rounded-lg border border-red-200 bg-red-50 p-4'>
                <XCircle className='mr-2 h-5 w-5 text-red-600' />
                <div>
                  <p className='font-medium text-red-800 text-sm'>Access Denied</p>
                  <p className='text-red-600 text-xs'>Requires admin privileges</p>
                </div>
              </div>
            }
          >
            <div className='flex items-center rounded-lg border border-green-200 bg-green-50 p-4'>
              <CheckCircle className='mr-2 h-5 w-5 text-green-600' />
              <div>
                <p className='font-medium text-green-800 text-sm'>Access Granted</p>
                <p className='text-green-600 text-xs'>Welcome, admin user</p>
              </div>
            </div>
          </AdminOnlyGuard>
        </Card>

        {/* Network Engineer Section */}
        <Card className='p-6'>
          <h3 className='mb-4 flex items-center font-semibold text-gray-900 text-lg'>
            <Shield className='mr-2 h-5 w-5 text-purple-600' />
            Network Engineer Only
          </h3>

          <NetworkEngineerGuard
            fallback={
              <div className='flex items-center rounded-lg border border-red-200 bg-red-50 p-4'>
                <XCircle className='mr-2 h-5 w-5 text-red-600' />
                <div>
                  <p className='font-medium text-red-800 text-sm'>Access Denied</p>
                  <p className='text-red-600 text-xs'>Requires network engineer role</p>
                </div>
              </div>
            }
          >
            <div className='flex items-center rounded-lg border border-green-200 bg-green-50 p-4'>
              <CheckCircle className='mr-2 h-5 w-5 text-green-600' />
              <div>
                <p className='font-medium text-green-800 text-sm'>Network Access Granted</p>
                <p className='text-green-600 text-xs'>Network management available</p>
              </div>
            </div>
          </NetworkEngineerGuard>
        </Card>

        {/* Billing Manager Section */}
        <Card className='p-6'>
          <h3 className='mb-4 flex items-center font-semibold text-gray-900 text-lg'>
            <Shield className='mr-2 h-5 w-5 text-orange-600' />
            Billing Manager Only
          </h3>

          <BillingManagerGuard
            fallback={
              <div className='flex items-center rounded-lg border border-red-200 bg-red-50 p-4'>
                <XCircle className='mr-2 h-5 w-5 text-red-600' />
                <div>
                  <p className='font-medium text-red-800 text-sm'>Access Denied</p>
                  <p className='text-red-600 text-xs'>Requires billing manager role</p>
                </div>
              </div>
            }
          >
            <div className='flex items-center rounded-lg border border-green-200 bg-green-50 p-4'>
              <CheckCircle className='mr-2 h-5 w-5 text-green-600' />
              <div>
                <p className='font-medium text-green-800 text-sm'>Billing Access Granted</p>
                <p className='text-green-600 text-xs'>Financial operations available</p>
              </div>
            </div>
          </BillingManagerGuard>
        </Card>

        {/* Permission-Based Section */}
        <Card className='p-6'>
          <h3 className='mb-4 flex items-center font-semibold text-gray-900 text-lg'>
            <Shield className='mr-2 h-5 w-5 text-green-600' />
            Permission-Based Access
          </h3>

          <div className='space-y-3'>
            <PermissionGuard
              permissions={['customers:read']}
              fallback={
                <div className='flex items-center rounded border border-yellow-200 bg-yellow-50 p-3'>
                  <AlertTriangle className='mr-2 h-4 w-4 text-yellow-600' />
                  <span className='text-sm text-yellow-800'>Customer read access required</span>
                </div>
              }
            >
              <div className='flex items-center rounded border border-green-200 bg-green-50 p-3'>
                <CheckCircle className='mr-2 h-4 w-4 text-green-600' />
                <span className='text-green-800 text-sm'>✓ Can read customer data</span>
              </div>
            </PermissionGuard>

            <PermissionGuard
              permissions={['customers:write']}
              fallback={
                <div className='flex items-center rounded border border-yellow-200 bg-yellow-50 p-3'>
                  <AlertTriangle className='mr-2 h-4 w-4 text-yellow-600' />
                  <span className='text-sm text-yellow-800'>Customer write access required</span>
                </div>
              }
            >
              <div className='flex items-center rounded border border-green-200 bg-green-50 p-3'>
                <CheckCircle className='mr-2 h-4 w-4 text-green-600' />
                <span className='text-green-800 text-sm'>✓ Can modify customer data</span>
              </div>
            </PermissionGuard>

            <PermissionGuard
              permissions={['billing:write']}
              fallback={
                <div className='flex items-center rounded border border-yellow-200 bg-yellow-50 p-3'>
                  <AlertTriangle className='mr-2 h-4 w-4 text-yellow-600' />
                  <span className='text-sm text-yellow-800'>Billing write access required</span>
                </div>
              }
            >
              <div className='flex items-center rounded border border-green-200 bg-green-50 p-3'>
                <CheckCircle className='mr-2 h-4 w-4 text-green-600' />
                <span className='text-green-800 text-sm'>✓ Can modify billing data</span>
              </div>
            </PermissionGuard>
          </div>
        </Card>
      </div>

      {/* Multi-Level Protection Example */}
      <Card className='p-6'>
        <h3 className='mb-4 flex items-center font-semibold text-gray-900 text-lg'>
          <Shield className='mr-2 h-5 w-5 text-red-600' />
          Super Admin Only - High Security Section
        </h3>

        <RouteGuard
          requiredRoles={['super-admin']}
          requiredPermissions={['security:read', 'audit:read']}
          fallback={
            <div className='rounded-lg border-2 border-red-200 bg-red-50 p-6 text-center'>
              <XCircle className='mx-auto mb-2 h-8 w-8 text-red-600' />
              <h4 className='mb-2 font-medium text-lg text-red-900'>Restricted Area</h4>
              <p className='text-red-800'>
                This section requires Super Admin role AND security permissions.
              </p>
              <p className='mt-2 text-red-600 text-sm'>
                Multi-factor authentication and elevated privileges required.
              </p>
            </div>
          }
        >
          <div className='rounded-lg border-2 border-green-200 bg-green-50 p-6 text-center'>
            <CheckCircle className='mx-auto mb-2 h-8 w-8 text-green-600' />
            <h4 className='mb-2 font-medium text-green-900 text-lg'>
              High Security Access Granted
            </h4>
            <p className='text-green-800'>Welcome to the high-security administrative area.</p>
            <p className='mt-2 text-green-600 text-sm'>
              All security requirements have been verified.
            </p>
          </div>
        </RouteGuard>
      </Card>
    </div>
  );
}
