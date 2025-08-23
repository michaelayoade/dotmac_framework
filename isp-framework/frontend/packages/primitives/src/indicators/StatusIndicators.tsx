/**
 * Enhanced Status Indicators for ISP Management Platform
 * Improved visual hierarchy and ISP-specific status types
 */

'use client';

import { cva, type VariantProps } from 'class-variance-authority';
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Local cn utility
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Enhanced status badge variants
const statusBadgeVariants = cva(
  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
  {
    variants: {
      variant: {
        // Network Status
        online:
          'bg-gradient-to-r from-green-50 to-emerald-50 text-green-800 border border-green-200 shadow-sm',
        offline:
          'bg-gradient-to-r from-red-50 to-rose-50 text-red-800 border border-red-200 shadow-sm',
        maintenance:
          'bg-gradient-to-r from-amber-50 to-yellow-50 text-amber-800 border border-amber-200 shadow-sm',
        degraded:
          'bg-gradient-to-r from-orange-50 to-red-50 text-orange-800 border border-orange-200 shadow-sm',

        // Service Status
        active:
          'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-800 border border-blue-200 shadow-sm',
        suspended:
          'bg-gradient-to-r from-gray-50 to-slate-50 text-gray-800 border border-gray-200 shadow-sm',
        pending:
          'bg-gradient-to-r from-purple-50 to-indigo-50 text-purple-800 border border-purple-200 shadow-sm',

        // Payment Status
        paid: 'bg-gradient-to-r from-green-50 to-emerald-50 text-green-800 border border-green-200 shadow-sm',
        overdue:
          'bg-gradient-to-r from-red-50 to-rose-50 text-red-800 border border-red-200 shadow-sm',
        processing:
          'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-800 border border-blue-200 shadow-sm',

        // Priority Levels
        critical:
          'bg-gradient-to-r from-red-500 to-rose-600 text-white shadow-lg shadow-red-500/25',
        high: 'bg-gradient-to-r from-orange-500 to-red-500 text-white shadow-lg shadow-orange-500/25',
        medium:
          'bg-gradient-to-r from-yellow-500 to-orange-500 text-white shadow-lg shadow-yellow-500/25',
        low: 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg shadow-blue-500/25',
      },
      size: {
        sm: 'px-2 py-1 text-xs',
        md: 'px-3 py-1.5 text-sm',
        lg: 'px-4 py-2 text-base',
      },
      animated: {
        true: 'animate-pulse',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'active',
      size: 'md',
      animated: false,
    },
  }
);

// Status indicator dot
const statusDotVariants = cva('rounded-full flex-shrink-0 transition-all duration-200', {
  variants: {
    status: {
      online: 'bg-gradient-to-r from-green-400 to-emerald-500 shadow-lg shadow-green-400/50',
      offline: 'bg-gradient-to-r from-red-400 to-rose-500 shadow-lg shadow-red-400/50',
      maintenance: 'bg-gradient-to-r from-amber-400 to-yellow-500 shadow-lg shadow-amber-400/50',
      degraded: 'bg-gradient-to-r from-orange-400 to-red-500 shadow-lg shadow-orange-400/50',
      active: 'bg-gradient-to-r from-blue-400 to-indigo-500 shadow-lg shadow-blue-400/50',
      suspended: 'bg-gradient-to-r from-gray-400 to-slate-500 shadow-lg shadow-gray-400/50',
      pending: 'bg-gradient-to-r from-purple-400 to-indigo-500 shadow-lg shadow-purple-400/50',
    },
    size: {
      sm: 'w-2 h-2',
      md: 'w-3 h-3',
      lg: 'w-4 h-4',
    },
    pulse: {
      true: 'animate-ping',
      false: '',
    },
  },
  defaultVariants: {
    status: 'active',
    size: 'md',
    pulse: false,
  },
});

// Main status badge component
interface StatusBadgeProps extends VariantProps<typeof statusBadgeVariants> {
  children: React.ReactNode;
  className?: string;
  showDot?: boolean;
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  variant,
  size,
  animated,
  children,
  className,
  showDot = true,
  pulse = false,
}) => {
  return (
    <span className={cn(statusBadgeVariants({ variant, size, animated }), className)}>
      {showDot && (
        <span
          className={cn(
            statusDotVariants({
              status: variant as any,
              size: size === 'sm' ? 'sm' : size === 'lg' ? 'lg' : 'md',
              pulse,
            })
          )}
        />
      )}
      {children}
    </span>
  );
};

// Service uptime indicator
interface UptimeIndicatorProps {
  uptime: number;
  className?: string;
}

export const UptimeIndicator: React.FC<UptimeIndicatorProps> = ({ uptime, className }) => {
  const getUptimeStatus = (percentage: number) => {
    if (percentage >= 99.9)
      return { status: 'excellent', color: 'text-green-600', bg: 'bg-green-500' };
    if (percentage >= 99.5) return { status: 'good', color: 'text-blue-600', bg: 'bg-blue-500' };
    if (percentage >= 98) return { status: 'fair', color: 'text-yellow-600', bg: 'bg-yellow-500' };
    return { status: 'poor', color: 'text-red-600', bg: 'bg-red-500' };
  };

  const status = getUptimeStatus(uptime);

  return (
    <div className={cn('flex items-center space-x-3', className)}>
      <div className='flex-1'>
        <div className='flex items-center justify-between mb-1'>
          <span className='text-sm font-medium text-gray-700'>Uptime</span>
          <span className={cn('text-sm font-bold', status.color)}>{uptime.toFixed(2)}%</span>
        </div>
        <div className='w-full bg-gray-200 rounded-full h-2'>
          <div
            className={cn('h-2 rounded-full transition-all duration-300', status.bg)}
            style={{ width: `${uptime}%` }}
          />
        </div>
      </div>
    </div>
  );
};

// Network performance indicator
interface NetworkPerformanceProps {
  latency: number;
  packetLoss: number;
  bandwidth: number;
  className?: string;
}

export const NetworkPerformanceIndicator: React.FC<NetworkPerformanceProps> = ({
  latency,
  packetLoss,
  bandwidth,
  className,
}) => {
  const getLatencyStatus = (ms: number) => {
    if (ms < 20) return 'excellent';
    if (ms < 50) return 'good';
    if (ms < 100) return 'fair';
    return 'poor';
  };

  const getPacketLossStatus = (loss: number) => {
    if (loss < 0.01) return 'excellent';
    if (loss < 0.1) return 'good';
    if (loss < 1) return 'fair';
    return 'poor';
  };

  const getBandwidthStatus = (bw: number) => {
    if (bw > 80) return 'high';
    if (bw > 50) return 'medium';
    return 'low';
  };

  return (
    <div className={cn('grid grid-cols-3 gap-4', className)}>
      <div className='text-center'>
        <div className='flex items-center justify-center mb-2'>
          <StatusBadge
            variant={
              getLatencyStatus(latency) === 'excellent'
                ? 'online'
                : getLatencyStatus(latency) === 'good'
                  ? 'active'
                  : getLatencyStatus(latency) === 'fair'
                    ? 'maintenance'
                    : 'offline'
            }
            size='sm'
            showDot={true}
            pulse={latency > 100}
          >
            {latency}ms
          </StatusBadge>
        </div>
        <p className='text-xs text-gray-600'>Latency</p>
      </div>

      <div className='text-center'>
        <div className='flex items-center justify-center mb-2'>
          <StatusBadge
            variant={
              getPacketLossStatus(packetLoss) === 'excellent'
                ? 'online'
                : getPacketLossStatus(packetLoss) === 'good'
                  ? 'active'
                  : getPacketLossStatus(packetLoss) === 'fair'
                    ? 'maintenance'
                    : 'offline'
            }
            size='sm'
            showDot={true}
            pulse={packetLoss > 1}
          >
            {packetLoss}%
          </StatusBadge>
        </div>
        <p className='text-xs text-gray-600'>Packet Loss</p>
      </div>

      <div className='text-center'>
        <div className='flex items-center justify-center mb-2'>
          <StatusBadge
            variant={
              getBandwidthStatus(bandwidth) === 'high'
                ? 'online'
                : getBandwidthStatus(bandwidth) === 'medium'
                  ? 'maintenance'
                  : 'offline'
            }
            size='sm'
            showDot={true}
          >
            {bandwidth}%
          </StatusBadge>
        </div>
        <p className='text-xs text-gray-600'>Bandwidth</p>
      </div>
    </div>
  );
};

// Service tier indicator
interface ServiceTierProps {
  tier: 'basic' | 'standard' | 'premium' | 'enterprise';
  className?: string;
}

export const ServiceTierIndicator: React.FC<ServiceTierProps> = ({ tier, className }) => {
  const tierConfig = {
    basic: {
      label: 'Basic',
      variant: 'low' as const,
      icon: '🥉',
    },
    standard: {
      label: 'Standard',
      variant: 'medium' as const,
      icon: '🥈',
    },
    premium: {
      label: 'Premium',
      variant: 'high' as const,
      icon: '🥇',
    },
    enterprise: {
      label: 'Enterprise',
      variant: 'critical' as const,
      icon: '👑',
    },
  };

  const config = tierConfig[tier];

  return (
    <div className={cn('flex items-center space-x-2', className)}>
      <span className='text-lg'>{config.icon}</span>
      <StatusBadge variant={config.variant} size='md'>
        {config.label}
      </StatusBadge>
    </div>
  );
};

// Alert severity indicator
interface AlertSeverityProps {
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp?: Date;
  className?: string;
}

export const AlertSeverityIndicator: React.FC<AlertSeverityProps> = ({
  severity,
  message,
  timestamp,
  className,
}) => {
  const severityConfig = {
    info: {
      variant: 'active' as const,
      icon: 'ℹ️',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
    },
    warning: {
      variant: 'maintenance' as const,
      icon: '⚠️',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
    },
    error: {
      variant: 'offline' as const,
      icon: '❌',
      bg: 'bg-red-50',
      border: 'border-red-200',
    },
    critical: {
      variant: 'critical' as const,
      icon: '🚨',
      bg: 'bg-red-50',
      border: 'border-red-200',
    },
  };

  const config = severityConfig[severity];

  return (
    <div
      className={cn(
        'flex items-start space-x-3 p-4 rounded-lg border',
        config.bg,
        config.border,
        className
      )}
    >
      <div className='flex-shrink-0'>
        <StatusBadge
          variant={config.variant}
          size='sm'
          pulse={severity === 'critical'}
          showDot={true}
        >
          <span className='mr-1'>{config.icon}</span>
          {severity.toUpperCase()}
        </StatusBadge>
      </div>
      <div className='flex-1 min-w-0'>
        <p className='text-sm font-medium text-gray-900'>{message}</p>
        {timestamp && <p className='text-xs text-gray-500 mt-1'>{timestamp.toLocaleString()}</p>}
      </div>
    </div>
  );
};
