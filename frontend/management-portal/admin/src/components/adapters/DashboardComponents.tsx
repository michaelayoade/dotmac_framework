'use client'

import { ReactNode, ComponentType } from 'react'
import { createAdaptiveComponent } from './ComponentLoader'

// Fallback implementations for dashboard components
function FallbackDashboardGrid({ stats, loading }: any) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat: any, index: number) => (
        <div key={index} className="card p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <stat.icon className="h-8 w-8 text-primary-600" aria-hidden="true" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">{stat.name}</dt>
                <dd>
                  {loading ? (
                    <div className="animate-pulse h-6 bg-gray-200 rounded mt-1"></div>
                  ) : (
                    <>
                      <div className="text-lg font-medium text-gray-900">{stat.value}</div>
                      <div className={`text-sm ${
                        stat.changeType === 'positive' ? 'text-success-600' :
                        stat.changeType === 'negative' ? 'text-danger-600' :
                        'text-gray-500'
                      }`}>
                        {stat.change}
                      </div>
                    </>
                  )}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function FallbackPackageDashboardWidgets({ layout }: any) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div className="card p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Network Status</h3>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Active Connections</span>
            <span className="text-sm font-medium text-gray-900">1,247</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Bandwidth Usage</span>
            <span className="text-sm font-medium text-success-600">Normal</span>
          </div>
        </div>
      </div>
      
      <div className="card p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Asset Management</h3>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Total Assets</span>
            <span className="text-sm font-medium text-gray-900">89</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Asset Health</span>
            <span className="text-sm font-medium text-success-600">Good</span>
          </div>
        </div>
      </div>
      
      <div className="card p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Customer Journey</h3>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Active Journeys</span>
            <span className="text-sm font-medium text-gray-900">23</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-gray-600">Completion Rate</span>
            <span className="text-sm font-medium text-success-600">94%</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Create adaptive components
export const DashboardGrid = createAdaptiveComponent(
  '@dotmac/portal-components',
  'DashboardGrid',
  FallbackDashboardGrid
)

export const PackageDashboardWidgets = createAdaptiveComponent(
  '@dotmac/portal-components',
  'PackageDashboardWidgets',
  FallbackPackageDashboardWidgets
)