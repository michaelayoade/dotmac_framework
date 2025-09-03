import React, { useEffect, useState } from 'react';
import { Card } from '@dotmac/ui/Card';
import { Button } from '@dotmac/ui/Button';
import { Badge } from '@dotmac/ui/Badge';
import {
  Package,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Warehouse,
  ShoppingCart,
  Activity,
} from 'lucide-react';
import { useInventory, useStock, usePurchaseOrders, useAssetTracking } from '../hooks';
import { LowStockAlerts } from './LowStockAlerts';
import { RecentMovements } from './MovementHistory';
import clsx from 'clsx';

interface InventoryDashboardProps {
  className?: string;
  showLowStockAlerts?: boolean;
  showRecentMovements?: boolean;
  showProvisioningRequests?: boolean;
}

export function InventoryDashboard({
  className,
  showLowStockAlerts = true,
  showRecentMovements = true,
  showProvisioningRequests = true,
}: InventoryDashboardProps) {
  const { getLowStockItems } = useInventory();
  const { stockLevels, getLowStockAlerts } = useStock();
  const { purchaseOrders } = usePurchaseOrders();
  const { getMaintenanceDue } = useAssetTracking();

  const [dashboardStats, setDashboardStats] = useState({
    totalItems: 0,
    lowStockItems: 0,
    pendingPOs: 0,
    maintenanceDue: 0,
    totalValue: 0,
    movementsToday: 0,
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);

        const [lowStock, lowStockAlerts, maintenanceDue] = await Promise.all([
          getLowStockItems(),
          getLowStockAlerts(),
          getMaintenanceDue(30),
        ]);

        const pendingPOs = purchaseOrders.filter((po) =>
          ['draft', 'pending_approval', 'approved', 'sent_to_vendor'].includes(po.po_status)
        ).length;

        const totalValue = stockLevels.reduce(
          (sum, stock) => sum + (stock.quantity * (stock as any).unit_cost || 0),
          0
        );

        setDashboardStats({
          totalItems: stockLevels.length,
          lowStockItems: lowStock.length,
          pendingPOs,
          maintenanceDue: maintenanceDue.length,
          totalValue,
          movementsToday: 0, // Would need to calculate from recent movements
        });
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDashboardData();
  }, [stockLevels, purchaseOrders]);

  const statCards = [
    {
      title: 'Total Items',
      value: dashboardStats.totalItems.toLocaleString(),
      icon: Package,
      trend: { value: '+12%', positive: true },
      color: 'blue',
    },
    {
      title: 'Low Stock Alerts',
      value: dashboardStats.lowStockItems.toString(),
      icon: AlertTriangle,
      trend: { value: '-5%', positive: true },
      color: dashboardStats.lowStockItems > 0 ? 'red' : 'green',
    },
    {
      title: 'Pending POs',
      value: dashboardStats.pendingPOs.toString(),
      icon: ShoppingCart,
      trend: { value: '+3', positive: false },
      color: 'orange',
    },
    {
      title: 'Maintenance Due',
      value: dashboardStats.maintenanceDue.toString(),
      icon: Activity,
      trend: { value: '+2', positive: false },
      color: dashboardStats.maintenanceDue > 10 ? 'red' : 'yellow',
    },
  ];

  if (loading) {
    return (
      <div className={clsx('space-y-6', className)}>
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className='p-6'>
              <div className='animate-pulse space-y-4'>
                <div className='h-4 bg-gray-200 rounded w-24'></div>
                <div className='h-8 bg-gray-200 rounded w-16'></div>
                <div className='h-3 bg-gray-200 rounded w-20'></div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Stats Overview */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
        {statCards.map(({ title, value, icon: Icon, trend, color }) => (
          <Card key={title} className='p-6'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-600'>{title}</p>
                <p className='text-2xl font-bold text-gray-900 mt-1'>{value}</p>
                <div className='flex items-center mt-2'>
                  {trend.positive ? (
                    <TrendingUp className='h-3 w-3 text-green-500 mr-1' />
                  ) : (
                    <TrendingDown className='h-3 w-3 text-red-500 mr-1' />
                  )}
                  <span
                    className={clsx(
                      'text-xs font-medium',
                      trend.positive ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    {trend.value}
                  </span>
                </div>
              </div>
              <div
                className={clsx('h-12 w-12 rounded-lg flex items-center justify-center', {
                  'bg-blue-100': color === 'blue',
                  'bg-red-100': color === 'red',
                  'bg-green-100': color === 'green',
                  'bg-orange-100': color === 'orange',
                  'bg-yellow-100': color === 'yellow',
                })}
              >
                <Icon
                  className={clsx('h-6 w-6', {
                    'text-blue-600': color === 'blue',
                    'text-red-600': color === 'red',
                    'text-green-600': color === 'green',
                    'text-orange-600': color === 'orange',
                    'text-yellow-600': color === 'yellow',
                  })}
                />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <Card className='p-6'>
        <h3 className='text-lg font-semibold text-gray-900 mb-4'>Quick Actions</h3>
        <div className='flex flex-wrap gap-3'>
          <Button variant='outline' size='sm'>
            <Package className='h-4 w-4 mr-2' />
            Add New Item
          </Button>
          <Button variant='outline' size='sm'>
            <Warehouse className='h-4 w-4 mr-2' />
            Stock Adjustment
          </Button>
          <Button variant='outline' size='sm'>
            <ShoppingCart className='h-4 w-4 mr-2' />
            Create PO
          </Button>
          <Button variant='outline' size='sm'>
            <Activity className='h-4 w-4 mr-2' />
            Asset Tracking
          </Button>
        </div>
      </Card>

      {/* Alerts and Recent Activity */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {showLowStockAlerts && (
          <Card className='p-6'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-lg font-semibold text-gray-900'>Low Stock Alerts</h3>
              <Badge variant='destructive'>{dashboardStats.lowStockItems}</Badge>
            </div>
            <LowStockAlerts limit={5} />
          </Card>
        )}

        {showRecentMovements && (
          <Card className='p-6'>
            <div className='flex items-center justify-between mb-4'>
              <h3 className='text-lg font-semibold text-gray-900'>Recent Movements</h3>
              <Button variant='ghost' size='sm'>
                View All
              </Button>
            </div>
            <RecentMovements limit={5} />
          </Card>
        )}
      </div>

      {/* Value Summary */}
      <Card className='p-6'>
        <h3 className='text-lg font-semibold text-gray-900 mb-4'>Inventory Value Summary</h3>
        <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Total Inventory Value</p>
            <p className='text-2xl font-bold text-gray-900 mt-1'>
              ${dashboardStats.totalValue.toLocaleString()}
            </p>
          </div>
          <div>
            <p className='text-sm font-medium text-gray-600'>Available Value</p>
            <p className='text-2xl font-bold text-green-600 mt-1'>
              ${(dashboardStats.totalValue * 0.85).toLocaleString()}
            </p>
          </div>
          <div>
            <p className='text-sm font-medium text-gray-600'>Reserved Value</p>
            <p className='text-2xl font-bold text-orange-600 mt-1'>
              ${(dashboardStats.totalValue * 0.15).toLocaleString()}
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
