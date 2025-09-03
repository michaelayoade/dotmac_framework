import { forwardRef } from 'react';
import { useNavigationContext } from '../context';
import type { UniversalTabNavigationProps } from '../types';
import { cn, getVariantStyles } from '../utils';

export const UniversalTabNavigation = forwardRef<HTMLDivElement, UniversalTabNavigationProps>(
  (
    {
      items,
      activeItem,
      variant = 'default',
      size = 'md',
      orientation = 'horizontal',
      onNavigate,
      className,
      ...props
    },
    ref
  ) => {
    const { onNavigate: contextOnNavigate } = useNavigationContext();
    const handleNavigate = onNavigate || contextOnNavigate;

    const sizeClasses = {
      sm: 'text-xs px-2 py-1',
      md: 'text-sm px-3 py-2',
      lg: 'text-base px-4 py-3',
    };

    const variantClasses = {
      default: {
        container: 'border-b border-gray-200',
        tab: 'border-b-2 border-transparent',
        active: 'border-blue-500 text-blue-600',
        inactive: 'text-gray-500 hover:text-gray-700 hover:border-gray-300',
      },
      pills: {
        container: 'bg-gray-100 rounded-lg p-1',
        tab: 'rounded-md',
        active: 'bg-white text-gray-900 shadow-sm',
        inactive: 'text-gray-600 hover:text-gray-900 hover:bg-gray-50',
      },
      underline: {
        container: '',
        tab: 'border-b-2 border-transparent',
        active: 'border-blue-500 text-blue-600',
        inactive: 'text-gray-500 hover:text-gray-700 hover:border-gray-300',
      },
      cards: {
        container: 'border-b border-gray-200',
        tab: 'border border-transparent border-b-0 rounded-t-lg',
        active: 'border-gray-200 border-b-white text-gray-900 bg-white',
        inactive: 'text-gray-500 hover:text-gray-700 hover:bg-gray-50',
      },
    };

    const orientationClasses = {
      horizontal: {
        container: 'flex',
        tab: 'whitespace-nowrap',
      },
      vertical: {
        container: 'flex flex-col space-y-1',
        tab: 'text-left',
      },
    };

    const styles = variantClasses[variant];
    const orientationStyle = orientationClasses[orientation];

    return (
      <div
        ref={ref}
        className={cn(
          'tab-navigation',
          styles.container,
          orientationStyle.container,
          {
            'space-x-8': orientation === 'horizontal' && variant !== 'pills',
            'space-x-1': orientation === 'horizontal' && variant === 'pills',
          },
          className
        )}
        role='tablist'
        aria-orientation={orientation}
        {...props}
      >
        {items.map((item) => {
          const isActive = activeItem === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              type='button'
              role='tab'
              aria-selected={isActive}
              aria-controls={`panel-${item.id}`}
              onClick={() => handleNavigate?.(item)}
              disabled={item.disabled}
              className={cn(
                'flex items-center font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                sizeClasses[size],
                styles.tab,
                orientationStyle.tab,
                {
                  [styles.active]: isActive,
                  [styles.inactive]: !isActive && !item.disabled,
                  'opacity-50 cursor-not-allowed': item.disabled,
                }
              )}
            >
              {Icon && (
                <Icon
                  className={cn('flex-shrink-0', {
                    'mr-2 h-4 w-4': size === 'sm',
                    'mr-2 h-5 w-5': size === 'md',
                    'mr-3 h-5 w-5': size === 'lg',
                  })}
                />
              )}

              <span>{item.label}</span>

              {item.badge && (
                <span
                  className={cn(
                    'inline-flex items-center justify-center rounded-full font-bold text-xs',
                    {
                      'ml-2 px-2 py-1': size === 'sm',
                      'ml-2 px-2 py-1': size === 'md',
                      'ml-3 px-2.5 py-1': size === 'lg',
                      'bg-blue-100 text-blue-600': isActive,
                      'bg-gray-100 text-gray-600': !isActive,
                    }
                  )}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }
);

UniversalTabNavigation.displayName = 'UniversalTabNavigation';
