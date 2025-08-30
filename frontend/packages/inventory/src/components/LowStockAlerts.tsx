import React, { useEffect, useState } from 'react';
import { Card } from '@dotmac/ui/Card';
import { Button } from '@dotmac/ui/Button';
import { Badge } from '@dotmac/ui/Badge';
import {
  AlertTriangle,
  Package,
  TrendingDown,
  ShoppingCart,
  RefreshCw
} from 'lucide-react';
import { useInventory, useStock } from '../hooks';
import type { Item } from '../types';
import clsx from 'clsx';

interface LowStockAlert {
  item: Item;
  current_stock: number;
  reorder_point: number;
  reorder_quantity: number;
  shortage: number;
  criticality: 'low' | 'medium' | 'high' | 'critical';
}

interface LowStockAlertsProps {
  className?: string;
  limit?: number;
  showActions?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number; // in seconds
}

export function LowStockAlerts({
  className,
  limit,
  showActions = true,
  autoRefresh = false,
  refreshInterval = 300 // 5 minutes
}: LowStockAlertsProps) {
  const { getLowStockItems, loading: inventoryLoading } = useInventory();
  const { getLowStockAlerts, loading: stockLoading } = useStock();

  const [alerts, setAlerts] = useState<LowStockAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);

      const lowStockItems = await getLowStockItems();

      // Transform and categorize alerts
      const transformedAlerts: LowStockAlert[] = lowStockItems.map(item => {
        const shortagePercent = (item.shortage / item.reorder_point) * 100;
        let criticality: LowStockAlert['criticality'] = 'low';

        if (item.current_stock === 0) {
          criticality = 'critical';
        } else if (shortagePercent >= 75) {
          criticality = 'high';
        } else if (shortagePercent >= 50) {
          criticality = 'medium';
        }

        return {
          ...item,
          criticality
        };
      }).sort((a, b) => {
        // Sort by criticality first, then by shortage amount
        const criticalityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
        const aCriticality = criticalityOrder[a.criticality];
        const bCriticality = criticalityOrder[b.criticality];

        if (aCriticality !== bCriticality) {
          return bCriticality - aCriticality;
        }

        return b.shortage - a.shortage;
      });

      const limitedAlerts = limit ? transformedAlerts.slice(0, limit) : transformedAlerts;
      setAlerts(limitedAlerts);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load low stock alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();

    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(loadAlerts, refreshInterval * 1000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [autoRefresh, refreshInterval, limit]);

  const getCriticalityColor = (criticality: LowStockAlert['criticality']): string => {
    const colors = {
      critical: 'bg-red-100 text-red-800 border-red-200',
      high: 'bg-orange-100 text-orange-800 border-orange-200',
      medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      low: 'bg-blue-100 text-blue-800 border-blue-200'
    };
    return colors[criticality];
  };

  const getCriticalityIcon = (criticality: LowStockAlert['criticality']) => {
    if (criticality === 'critical') {
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
    }
    return <TrendingDown className="h-4 w-4 text-orange-500" />;
  };

  const handleCreatePO = (item: Item) => {
    // Would typically open a modal or navigate to PO creation
    console.log('Creating PO for item:', item.id);
  };

  const handleAdjustStock = (item: Item) => {
    // Would typically open stock adjustment modal
    console.log('Adjusting stock for item:', item.id);
  };

  if (loading) {
    return (
      <div className={clsx('space-y-3', className)}>
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse">
            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <div className="w-10 h-10 bg-gray-200 rounded"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
              <div className="h-6 w-16 bg-gray-200 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className={clsx('p-6 text-center', className)}>
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-2" />
        <p className="text-red-600 font-medium">Failed to load low stock alerts</p>
        <p className="text-sm text-gray-500 mt-1">{error}</p>
        <Button
          variant="outline"
          size="sm"
          onClick={loadAlerts}
          className="mt-3"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </Card>
    );
  }

  if (alerts.length === 0) {
    return (
      <Card className={clsx('p-6 text-center', className)}>
        <Package className="h-12 w-12 text-green-500 mx-auto mb-2" />
        <p className="text-gray-600 font-medium">No low stock alerts</p>
        <p className="text-sm text-gray-500 mt-1">All items are adequately stocked</p>
      </Card>
    );
  }

  return (
    <div className={clsx('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-500" />
          <h3 className="font-medium text-gray-900">
            Low Stock Alerts ({alerts.length})
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {autoRefresh && (
            <span className="text-xs text-gray-500">
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={loadAlerts}
            disabled={loading}
          >
            <RefreshCw className={clsx('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Alert List */}
      <div className="space-y-2">
        {alerts.map((alert) => (
          <div
            key={alert.item.id}
            className={clsx(
              'flex items-center space-x-3 p-3 border rounded-lg',
              getCriticalityColor(alert.criticality),
              'hover:shadow-sm transition-shadow'
            )}
          >
            <div className="flex-shrink-0">
              {getCriticalityIcon(alert.criticality)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900 truncate">
                    {alert.item.name}
                  </p>
                  <p className="text-sm text-gray-600">
                    {alert.item.item_code}
                  </p>
                </div>

                <div className="flex items-center gap-3 ml-4">
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {alert.current_stock} / {alert.reorder_point}
                    </p>
                    <p className="text-xs text-gray-500">
                      Need: {alert.reorder_quantity}
                    </p>
                  </div>

                  <Badge variant="outline" size="sm">
                    -{alert.shortage}
                  </Badge>
                </div>
              </div>

              {alert.criticality === 'critical' && (
                <p className="text-xs text-red-600 mt-1 font-medium">
                  Out of stock - Immediate action required
                </p>
              )}
            </div>

            {showActions && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleCreatePO(alert.item)}
                  className="text-xs"
                >
                  <ShoppingCart className="h-3 w-3 mr-1" />
                  PO
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleAdjustStock(alert.item)}
                  className="text-xs"
                >
                  <Package className="h-3 w-3 mr-1" />
                  Adjust
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>

      {showActions && alerts.some(alert => alert.criticality === 'critical') && (
        <Card className="p-4 bg-red-50 border-red-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <p className="text-sm font-medium text-red-800">
                Critical items require immediate attention
              </p>
            </div>
            <Button variant="destructive" size="sm">
              Create Emergency POs
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
