import { HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'success' | 'warning' | 'destructive'
}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        className={cn(
          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
          {
            'bg-primary-100 text-primary-800': variant === 'default',
            'bg-gray-100 text-gray-800': variant === 'secondary',
            'bg-success-100 text-success-800': variant === 'success',
            'bg-warning-100 text-warning-800': variant === 'warning',
            'bg-red-100 text-red-800': variant === 'destructive',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Badge.displayName = 'Badge'

export { Badge }