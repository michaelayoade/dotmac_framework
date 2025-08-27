/**
 * Skeleton Loading Components
 * Provides smooth loading states while data is fetching
 */

import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  animate?: boolean;
}

export function Skeleton({ 
  className, 
  variant = 'rectangular',
  width,
  height,
  animate = true,
  ...props 
}: SkeletonProps) {
  const variantStyles = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-none',
    rounded: 'rounded-lg',
  };

  const style = {
    ...(width && { width: typeof width === 'number' ? `${width}px` : width }),
    ...(height && { height: typeof height === 'number' ? `${height}px` : height }),
  };

  return (
    <div
      className={cn(
        'bg-gray-200',
        animate && 'animate-pulse',
        variantStyles[variant],
        className
      )}
      style={style}
      {...props}
    />
  );
}

// Specialized skeleton components
export function SkeletonText({ 
  lines = 1, 
  className, 
  animate = true 
}: { 
  lines?: number; 
  className?: string; 
  animate?: boolean; 
}) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          animate={animate}
          className={index === lines - 1 ? 'w-3/4' : 'w-full'} // Last line shorter
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ 
  className,
  hasAvatar = false,
  hasActions = false,
  animate = true 
}: { 
  className?: string;
  hasAvatar?: boolean;
  hasActions?: boolean;
  animate?: boolean;
}) {
  return (
    <div className={cn('p-6 bg-white rounded-lg border border-gray-200', className)}>
      <div className="flex items-start space-x-4">
        {hasAvatar && (
          <Skeleton variant="circular" width={40} height={40} animate={animate} />
        )}
        <div className="flex-1 space-y-3">
          <Skeleton variant="text" className="w-1/3" animate={animate} />
          <SkeletonText lines={2} animate={animate} />
          {hasActions && (
            <div className="flex space-x-2 pt-2">
              <Skeleton variant="rounded" width={80} height={32} animate={animate} />
              <Skeleton variant="rounded" width={60} height={32} animate={animate} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function SkeletonTable({ 
  rows = 5, 
  columns = 4, 
  className,
  animate = true 
}: { 
  rows?: number; 
  columns?: number; 
  className?: string;
  animate?: boolean;
}) {
  return (
    <div className={cn('space-y-4', className)}>
      {/* Table header */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={`header-${index}`} variant="text" animate={animate} />
        ))}
      </div>
      
      {/* Table rows */}
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div 
            key={`row-${rowIndex}`}
            className="grid gap-4" 
            style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
          >
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton 
                key={`cell-${rowIndex}-${colIndex}`} 
                variant="text" 
                animate={animate}
                className={colIndex === 0 ? 'w-3/4' : 'w-full'} // First column often shorter
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonDashboard({ 
  className,
  animate = true 
}: { 
  className?: string;
  animate?: boolean;
}) {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="space-y-2">
        <Skeleton variant="text" width="200px" height="32px" animate={animate} />
        <Skeleton variant="text" width="300px" animate={animate} />
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={`stat-${index}`} className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="flex items-center">
              <Skeleton variant="circular" width={32} height={32} animate={animate} />
              <div className="ml-4 flex-1 space-y-2">
                <Skeleton variant="text" width="80px" animate={animate} />
                <Skeleton variant="text" width="60px" height="24px" animate={animate} />
              </div>
            </div>
            <div className="mt-2">
              <Skeleton variant="text" width="100px" animate={animate} />
            </div>
          </div>
        ))}
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {Array.from({ length: 2 }).map((_, index) => (
          <div key={`section-${index}`} className="bg-white p-6 rounded-lg border border-gray-200">
            <div className="mb-4">
              <Skeleton variant="text" width="150px" height="24px" animate={animate} />
            </div>
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, itemIndex) => (
                <div key={`item-${itemIndex}`} className="flex items-center space-x-3">
                  <Skeleton variant="circular" width={24} height={24} animate={animate} />
                  <div className="flex-1 space-y-1">
                    <Skeleton variant="text" width="200px" animate={animate} />
                    <Skeleton variant="text" width="100px" className="text-sm" animate={animate} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonForm({ 
  fields = 3, 
  hasButtons = true,
  className,
  animate = true 
}: { 
  fields?: number; 
  hasButtons?: boolean;
  className?: string;
  animate?: boolean;
}) {
  return (
    <div className={cn('space-y-6', className)}>
      {Array.from({ length: fields }).map((_, index) => (
        <div key={`field-${index}`} className="space-y-2">
          <Skeleton variant="text" width="100px" animate={animate} />
          <Skeleton variant="rounded" height="40px" animate={animate} />
        </div>
      ))}
      
      {hasButtons && (
        <div className="flex space-x-3 pt-4">
          <Skeleton variant="rounded" width="100px" height="40px" animate={animate} />
          <Skeleton variant="rounded" width="80px" height="40px" animate={animate} />
        </div>
      )}
    </div>
  );
}