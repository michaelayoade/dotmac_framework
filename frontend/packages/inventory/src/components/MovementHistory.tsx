import React, { useEffect, useState } from 'react';
import { Card } from '@dotmac/ui/Card';
import { Button } from '@dotmac/ui/Button';
import { Badge } from '@dotmac/ui/Badge';
import {
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  Package,
  AlertCircle,
  Calendar,
  User,
  FileText
} from 'lucide-react';
import { useMovements } from '../hooks';
import { ItemStatusBadge } from './common';
import type { StockMovement, MovementType } from '../types';
import clsx from 'clsx';
import { formatDistanceToNow } from 'date-fns';

interface MovementHistoryProps {
  className?: string;
  itemId?: string;
  warehouseId?: string;
  limit?: number;
  showFilters?: boolean;
}

interface RecentMovementsProps {
  className?: string;
  limit?: number;
}

const movementConfig = {
  receipt: {
    label: 'Receipt',
    color: 'success' as const,
    icon: ArrowRight,
    description: 'Items received into inventory'
  },
  issue: {
    label: 'Issue',
    color: 'info' as const,
    icon: ArrowLeft,
    description: 'Items issued from inventory'
  },
  transfer: {
    label: 'Transfer',
    color: 'warning' as const,
    icon: RotateCcw,
    description: 'Items transferred between locations'
  },
  adjustment: {
    label: 'Adjustment',
    color: 'secondary' as const,
    icon: AlertCircle,
    description: 'Stock quantity adjusted'
  },
  return: {
    label: 'Return',
    color: 'success' as const,
    icon: ArrowRight,
    description: 'Items returned to inventory'
  },
  write_off: {
    label: 'Write Off',
    color: 'destructive' as const,
    icon: AlertCircle,
    description: 'Items written off from inventory'
  },
  found: {
    label: 'Found',
    color: 'success' as const,
    icon: Package,
    description: 'Found items added to inventory'
  },
  installation: {
    label: 'Installation',
    color: 'info' as const,
    icon: ArrowLeft,
    description: 'Items issued for installation'
  },
  replacement: {
    label: 'Replacement',
    color: 'warning' as const,
    icon: RotateCcw,
    description: 'Items replaced'
  }
};

export function MovementHistory({
  className,
  itemId,
  warehouseId,
  limit = 50,
  showFilters = true
}: MovementHistoryProps) {
  const {
    movements,
    loading,
    error,
    listMovements,
    getMovementsByItem,
    getMovementsByWarehouse
  } = useMovements();

  const [filteredMovements, setFilteredMovements] = useState<StockMovement[]>([]);
  const [filters, setFilters] = useState({
    movementType: 'all' as MovementType | 'all',
    dateRange: '7' // days
  });

  useEffect(() => {
    const loadMovements = async () => {
      if (itemId) {
        const itemMovements = await getMovementsByItem(itemId, limit);
        setFilteredMovements(itemMovements);
      } else if (warehouseId) {
        const warehouseMovements = await getMovementsByWarehouse(warehouseId, limit);
        setFilteredMovements(warehouseMovements);
      } else {
        await listMovements({}, 1, limit);
        setFilteredMovements(movements);
      }
    };

    loadMovements();
  }, [itemId, warehouseId, limit]);

  const getMovementIcon = (type: MovementType) => {
    const config = movementConfig[type];
    const Icon = config?.icon || Package;
    return <Icon className="h-4 w-4" />;
  };

  const getMovementColor = (type: MovementType, quantity: number) => {
    if (quantity > 0) {
      return 'text-green-600'; // Inbound
    } else {
      return 'text-red-600'; // Outbound
    }
  };

  const formatQuantity = (quantity: number) => {
    return quantity > 0 ? `+${quantity}` : quantity.toString();
  };

  if (loading) {
    return (
      <div className={clsx('space-y-3', className)}>
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse">
            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <div className="w-8 h-8 bg-gray-200 rounded"></div>
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
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-2" />
        <p className="text-red-600 font-medium">Failed to load movement history</p>
        <p className="text-sm text-gray-500 mt-1">{error}</p>
      </Card>
    );
  }

  if (filteredMovements.length === 0) {
    return (
      <Card className={clsx('p-6 text-center', className)}>
        <Package className="h-12 w-12 text-gray-400 mx-auto mb-2" />
        <p className="text-gray-600 font-medium">No movements found</p>
        <p className="text-sm text-gray-500 mt-1">No stock movements recorded</p>
      </Card>
    );
  }

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Filters */}
      {showFilters && (
        <div className="flex items-center gap-4">
          <select
            value={filters.movementType}
            onChange={(e) => setFilters(prev => ({
              ...prev,
              movementType: e.target.value as MovementType | 'all'
            }))}
            className="text-sm border rounded px-3 py-1"
          >
            <option value="all">All Types</option>
            {Object.entries(movementConfig).map(([key, config]) => (
              <option key={key} value={key}>
                {config.label}
              </option>
            ))}
          </select>

          <select
            value={filters.dateRange}
            onChange={(e) => setFilters(prev => ({ ...prev, dateRange: e.target.value }))}
            className="text-sm border rounded px-3 py-1"
          >
            <option value="1">Last 24 hours</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 3 months</option>
          </select>
        </div>
      )}

      {/* Movement Timeline */}
      <div className="space-y-2">
        {filteredMovements.map((movement) => (
          <div
            key={movement.id}
            className="flex items-start space-x-4 p-4 border rounded-lg hover:shadow-sm transition-shadow"
          >
            <div className={clsx(
              'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
              movement.quantity > 0 ? 'bg-green-100' : 'bg-red-100'
            )}>
              {getMovementIcon(movement.movement_type)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-gray-900">
                    {movementConfig[movement.movement_type]?.label || movement.movement_type}
                  </h4>
                  <Badge
                    variant="outline"
                    size="sm"
                    className={getMovementColor(movement.movement_type, movement.quantity)}
                  >
                    {formatQuantity(movement.quantity)}
                  </Badge>
                </div>

                <span className="text-sm text-gray-500">
                  {formatDistanceToNow(new Date(movement.movement_date), { addSuffix: true })}
                </span>
              </div>

              <p className="text-sm text-gray-600 mt-1">
                {movement.reason_description || movementConfig[movement.movement_type]?.description}
              </p>

              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                {movement.reference_number && (
                  <div className="flex items-center gap-1">
                    <FileText className="h-3 w-3" />
                    <span>Ref: {movement.reference_number}</span>
                  </div>
                )}

                {movement.processed_by && (
                  <div className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    <span>By: {movement.processed_by}</span>
                  </div>
                )}

                <div className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  <span>{new Date(movement.movement_date).toLocaleString()}</span>
                </div>
              </div>

              {movement.from_warehouse_id && movement.movement_type === 'transfer' && (
                <div className="mt-2 text-sm text-gray-600">
                  <span>Transfer from another warehouse</span>
                </div>
              )}

              {movement.serial_numbers && Object.keys(movement.serial_numbers).length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500 mb-1">Serial Numbers:</p>
                  <div className="flex flex-wrap gap-1">
                    {Object.values(movement.serial_numbers).slice(0, 3).map((sn, index) => (
                      <Badge key={index} variant="secondary" size="sm">
                        {sn as string}
                      </Badge>
                    ))}
                    {Object.keys(movement.serial_numbers).length > 3 && (
                      <Badge variant="secondary" size="sm">
                        +{Object.keys(movement.serial_numbers).length - 3} more
                      </Badge>
                    )}
                  </div>
                </div>
              )}

              {movement.notes && (
                <div className="mt-2 p-2 bg-gray-50 rounded text-sm text-gray-600">
                  {movement.notes}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function RecentMovements({ className, limit = 5 }: RecentMovementsProps) {
  const { getRecentMovements } = useMovements();
  const [recentMovements, setRecentMovements] = useState<StockMovement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadRecentMovements = async () => {
      try {
        const movements = await getRecentMovements(limit);
        setRecentMovements(movements);
      } catch (error) {
        console.error('Failed to load recent movements:', error);
      } finally {
        setLoading(false);
      }
    };

    loadRecentMovements();
  }, [limit]);

  if (loading) {
    return (
      <div className={clsx('space-y-3', className)}>
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse flex items-center space-x-3">
            <div className="w-8 h-8 bg-gray-200 rounded-full"></div>
            <div className="flex-1 space-y-1">
              <div className="h-3 bg-gray-200 rounded w-3/4"></div>
              <div className="h-2 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (recentMovements.length === 0) {
    return (
      <div className={clsx('text-center py-4', className)}>
        <Package className="h-8 w-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm text-gray-500">No recent movements</p>
      </div>
    );
  }

  return (
    <div className={clsx('space-y-3', className)}>
      {recentMovements.map((movement) => (
        <div key={movement.id} className="flex items-center space-x-3">
          <div className={clsx(
            'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
            movement.quantity > 0 ? 'bg-green-100' : 'bg-red-100'
          )}>
            {getMovementIcon(movement.movement_type)}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900 truncate">
                {movementConfig[movement.movement_type]?.label || movement.movement_type}
              </span>
              <Badge
                variant="outline"
                size="sm"
                className={getMovementColor(movement.movement_type, movement.quantity)}
              >
                {formatQuantity(movement.quantity)}
              </Badge>
            </div>
            <p className="text-xs text-gray-500 truncate">
              {movement.reason_description || movementConfig[movement.movement_type]?.description}
            </p>
          </div>

          <span className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(movement.movement_date), { addSuffix: true })}
          </span>
        </div>
      ))}
    </div>
  );
}

function getMovementIcon(type: MovementType) {
  const config = movementConfig[type];
  const Icon = config?.icon || Package;
  return <Icon className="h-4 w-4" />;
}

function getMovementColor(type: MovementType, quantity: number) {
  if (quantity > 0) {
    return 'text-green-600'; // Inbound
  } else {
    return 'text-red-600'; // Outbound
  }
}
