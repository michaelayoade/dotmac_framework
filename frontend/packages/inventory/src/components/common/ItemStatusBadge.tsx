import React from 'react';
import { Badge } from '@dotmac/ui/Badge';
import {
  CheckCircle,
  Package,
  Clock,
  AlertCircle,
  XCircle,
  AlertTriangle
} from 'lucide-react';
import { ItemStatus } from '../../types';
import clsx from 'clsx';

interface ItemStatusBadgeProps {
  status: ItemStatus;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  variant?: 'default' | 'outline';
}

const statusConfig = {
  [ItemStatus.AVAILABLE]: {
    label: 'Available',
    color: 'success' as const,
    icon: CheckCircle,
    bgColor: 'bg-green-100',
    textColor: 'text-green-800',
    borderColor: 'border-green-200'
  },
  [ItemStatus.IN_USE]: {
    label: 'In Use',
    color: 'info' as const,
    icon: Package,
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-800',
    borderColor: 'border-blue-200'
  },
  [ItemStatus.ALLOCATED]: {
    label: 'Allocated',
    color: 'warning' as const,
    icon: Clock,
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-800',
    borderColor: 'border-orange-200'
  },
  [ItemStatus.RESERVED]: {
    label: 'Reserved',
    color: 'warning' as const,
    icon: Clock,
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
    borderColor: 'border-yellow-200'
  },
  [ItemStatus.IN_REPAIR]: {
    label: 'In Repair',
    color: 'destructive' as const,
    icon: AlertCircle,
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
    borderColor: 'border-red-200'
  },
  [ItemStatus.RETIRED]: {
    label: 'Retired',
    color: 'secondary' as const,
    icon: XCircle,
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-800',
    borderColor: 'border-gray-200'
  },
  [ItemStatus.LOST]: {
    label: 'Lost',
    color: 'destructive' as const,
    icon: AlertTriangle,
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
    borderColor: 'border-red-200'
  },
  [ItemStatus.QUARANTINED]: {
    label: 'Quarantined',
    color: 'destructive' as const,
    icon: AlertTriangle,
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
    borderColor: 'border-red-200'
  }
};

export function ItemStatusBadge({
  status,
  size = 'md',
  showIcon = true,
  variant = 'default'
}: ItemStatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5'
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  };

  if (variant === 'outline') {
    return (
      <span className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        sizeClasses[size],
        config.textColor,
        config.borderColor,
        'bg-white'
      )}>
        {showIcon && <Icon className={iconSizes[size]} />}
        {config.label}
      </span>
    );
  }

  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-full font-medium',
      sizeClasses[size],
      config.bgColor,
      config.textColor
    )}>
      {showIcon && <Icon className={iconSizes[size]} />}
      {config.label}
    </span>
  );
}
