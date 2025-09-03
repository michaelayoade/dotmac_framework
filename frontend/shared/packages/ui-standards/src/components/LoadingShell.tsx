import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

const loadingShellVariants = cva(
  'animate-pulse rounded-md bg-muted',
  {
    variants: {
      variant: {
        default: 'bg-gray-200 dark:bg-gray-700',
        shimmer: 'bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:400%_100%] animate-shimmer dark:from-gray-700 dark:via-gray-600 dark:to-gray-700',
        skeleton: 'bg-gray-200 dark:bg-gray-700',
      },
      size: {
        sm: 'h-4',
        md: 'h-6',
        lg: 'h-8',
        xl: 'h-12',
        custom: '',
      },
      width: {
        full: 'w-full',
        '3/4': 'w-3/4',
        '1/2': 'w-1/2',
        '1/4': 'w-1/4',
        custom: '',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
      width: 'full',
    },
  }
);

interface LoadingShellProps extends VariantProps<typeof loadingShellVariants> {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

export const LoadingShell: React.FC<LoadingShellProps> = ({
  variant,
  size,
  width,
  className,
  style,
  children,
}) => {
  return (
    <div
      className={clsx(loadingShellVariants({ variant, size, width }), className)}
      style={style}
      role="status"
      aria-label="Loading"
    >
      {children}
    </div>
  );
};

// Specific loading components
export const TextLoadingSkeleton: React.FC<{
  lines?: number;
  className?: string;
}> = ({ lines = 3, className }) => {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }, (_, i) => (
        <LoadingShell
          key={i}
          variant="shimmer"
          size="md"
          width={i === lines - 1 ? '3/4' : 'full'}
        />
      ))}
    </div>
  );
};

export const CardLoadingSkeleton: React.FC<{
  className?: string;
}> = ({ className }) => {
  return (
    <div className={clsx('p-4 border rounded-lg space-y-4', className)}>
      {/* Header */}
      <div className="space-y-2">
        <LoadingShell variant="shimmer" size="lg" width="1/2" />
        <LoadingShell variant="shimmer" size="sm" width="3/4" />
      </div>
      
      {/* Content */}
      <div className="space-y-2">
        <LoadingShell variant="shimmer" size="md" width="full" />
        <LoadingShell variant="shimmer" size="md" width="full" />
        <LoadingShell variant="shimmer" size="md" width="1/2" />
      </div>
      
      {/* Actions */}
      <div className="flex gap-2">
        <LoadingShell variant="shimmer" size="lg" className="w-20" />
        <LoadingShell variant="shimmer" size="lg" className="w-16" />
      </div>
    </div>
  );
};

export const TableLoadingSkeleton: React.FC<{
  rows?: number;
  columns?: number;
  className?: string;
}> = ({ rows = 5, columns = 4, className }) => {
  return (
    <div className={clsx('space-y-3', className)}>
      {/* Header */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }, (_, i) => (
          <LoadingShell key={`header-${i}`} variant="shimmer" size="md" width="3/4" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div
          key={`row-${rowIndex}`}
          className="grid gap-4"
          style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
        >
          {Array.from({ length: columns }, (_, colIndex) => (
            <LoadingShell
              key={`cell-${rowIndex}-${colIndex}`}
              variant="shimmer"
              size="md"
              width={colIndex === 0 ? 'full' : Math.random() > 0.5 ? 'full' : '3/4'}
            />
          ))}
        </div>
      ))}
    </div>
  );
};

export const ListLoadingSkeleton: React.FC<{
  items?: number;
  showAvatar?: boolean;
  className?: string;
}> = ({ items = 5, showAvatar = true, className }) => {
  return (
    <div className={clsx('space-y-3', className)}>
      {Array.from({ length: items }, (_, i) => (
        <div key={i} className="flex items-center space-x-3">
          {showAvatar && (
            <LoadingShell
              variant="shimmer"
              size="custom"
              className="w-10 h-10 rounded-full"
            />
          )}
          <div className="flex-1 space-y-2">
            <LoadingShell variant="shimmer" size="md" width="1/2" />
            <LoadingShell variant="shimmer" size="sm" width="3/4" />
          </div>
        </div>
      ))}
    </div>
  );
};