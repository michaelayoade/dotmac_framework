import { ChevronDown, ChevronRight, Menu, X } from 'lucide-react';
import { forwardRef, useEffect, useState } from 'react';
import { useNavigationContext } from '../context';
import type { UniversalMobileNavigationProps } from '../types';
import { cn, getVariantStyles, isNavigationItemActive } from '../utils';

export const UniversalMobileNavigation = forwardRef<HTMLDivElement, UniversalMobileNavigationProps>(
  ({
    items,
    activeItem,
    variant = 'drawer',
    onNavigate,
    className,
    ...props
  }, ref) => {
    const [isOpen, setIsOpen] = useState(false);
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
    const { onNavigate: contextOnNavigate } = useNavigationContext();

    const handleNavigate = onNavigate || contextOnNavigate;

    // Close drawer on escape key
    useEffect(() => {
      const handleEscape = (e: KeyboardEvent) => {
        if (e.key === 'Escape' && isOpen) {
          setIsOpen(false);
        }
      };

      if (isOpen) {
        document.addEventListener('keydown', handleEscape);
        // Prevent body scroll when drawer is open
        if (variant === 'drawer' || variant === 'bottom-sheet') {
          document.body.style.overflow = 'hidden';
        }
      }

      return () => {
        document.removeEventListener('keydown', handleEscape);
        document.body.style.overflow = '';
      };
    }, [isOpen, variant]);

    const toggleExpanded = (itemId: string) => {
      setExpandedItems(prev => {
        const newSet = new Set(prev);
        if (newSet.has(itemId)) {
          newSet.delete(itemId);
        } else {
          newSet.add(itemId);
        }
        return newSet;
      });
    };

    const handleItemClick = (item: typeof items[0]) => {
      if (item.children && item.children.length > 0) {
        toggleExpanded(item.id);
      } else {
        handleNavigate?.(item);
        if (variant !== 'tabs') {
          setIsOpen(false);
        }
      }
    };

    const renderNavigationItem = (item: typeof items[0], depth = 0) => {
      const hasChildren = item.children && item.children.length > 0;
      const isExpanded = expandedItems.has(item.id);
      const isActive = activeItem === item.id || isNavigationItemActive(item, activeItem || '');
      const Icon = item.icon;

      return (
        <li key={item.id}>
          <button
            type="button"
            onClick={() => handleItemClick(item)}
            disabled={item.disabled}
            className={cn(
              'flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium transition-colors',
              'hover:bg-gray-100 focus:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500',
              {
                'bg-blue-50 text-blue-700 border-r-2 border-blue-700': isActive,
                'text-gray-700': !isActive && !item.disabled,
                'text-gray-400 cursor-not-allowed': item.disabled,
                'pl-8': depth === 1,
                'pl-12': depth === 2,
                'pl-16': depth >= 3,
              }
            )}
            aria-current={isActive ? 'page' : undefined}
            aria-expanded={hasChildren ? isExpanded : undefined}
          >
            <div className="flex items-center min-w-0 flex-1">
              {Icon && (
                <Icon className="mr-3 h-5 w-5 flex-shrink-0 text-gray-400" />
              )}
              <span className="truncate">{item.label}</span>
              {item.badge && (
                <span className="ml-2 inline-flex items-center justify-center rounded-full bg-red-100 px-2 py-1 text-xs font-bold text-red-600">
                  {item.badge}
                </span>
              )}
            </div>
            {hasChildren && (
              <ChevronRight className={cn(
                'ml-2 h-4 w-4 flex-shrink-0 transition-transform',
                { 'rotate-90': isExpanded }
              )} />
            )}
          </button>

          {hasChildren && isExpanded && (
            <ul className="bg-gray-50">
              {item.children?.map(child => renderNavigationItem(child, depth + 1))}
            </ul>
          )}
        </li>
      );
    };

    if (variant === 'tabs') {
      return (
        <nav
          ref={ref}
          className={cn('mobile-tab-navigation', className)}
          aria-label="Main navigation"
          {...props}
        >
          <div className="flex overflow-x-auto scrollbar-hide">
            {items.map((item) => {
              const isActive = activeItem === item.id;
              const Icon = item.icon;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleItemClick(item)}
                  disabled={item.disabled}
                  className={cn(
                    'flex min-w-max items-center whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors',
                    'hover:border-gray-300 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                    {
                      'border-blue-500 text-blue-600': isActive,
                      'border-transparent text-gray-500': !isActive && !item.disabled,
                      'border-transparent text-gray-300 cursor-not-allowed': item.disabled,
                    }
                  )}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {Icon && (
                    <Icon className={cn(
                      'mr-2 h-4 w-4 flex-shrink-0',
                      {
                        'text-blue-500': isActive,
                        'text-gray-400': !isActive,
                      }
                    )} />
                  )}
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className={cn(
                      'ml-2 inline-flex items-center justify-center rounded-full px-2 py-1 text-xs font-bold',
                      {
                        'bg-blue-100 text-blue-600': isActive,
                        'bg-red-100 text-red-600': !isActive,
                      }
                    )}>
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </nav>
      );
    }

    const drawerClasses = variant === 'bottom-sheet'
      ? 'fixed inset-x-0 bottom-0 max-h-96 rounded-t-lg'
      : 'fixed inset-y-0 left-0 w-80 max-w-full';

    return (
      <>
        {/* Mobile menu trigger */}
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className={cn(
            'inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 md:hidden',
            className
          )}
          aria-label="Open navigation menu"
          aria-expanded={isOpen}
        >
          <Menu className="h-6 w-6" />
        </button>

        {/* Overlay */}
        {isOpen && (
          <div
            className="fixed inset-0 z-40 bg-black bg-opacity-50 md:hidden"
            onClick={() => setIsOpen(false)}
            onKeyDown={(e) => e.key === 'Enter' && setIsOpen(false)}
            role="button"
            tabIndex={0}
            aria-hidden="true"
          />
        )}

        {/* Mobile navigation drawer */}
        <div
          ref={ref}
          className={cn(
            drawerClasses,
            'z-50 transform bg-white shadow-xl transition-transform duration-300 ease-in-out md:hidden',
            {
              'translate-x-0': isOpen && variant === 'drawer',
              '-translate-x-full': !isOpen && variant === 'drawer',
              'translate-y-0': isOpen && variant === 'bottom-sheet',
              'translate-y-full': !isOpen && variant === 'bottom-sheet',
            }
          )}
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
          {...props}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 p-4">
            <h2 className="text-lg font-semibold text-gray-900">Navigation</h2>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close navigation menu"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Navigation items */}
          <nav className="flex-1 overflow-y-auto">
            <ul className="py-2">
              {items.map(item => renderNavigationItem(item))}
            </ul>
          </nav>

          {/* Footer */}
          <div className="border-t border-gray-200 p-4">
            <p className="text-center text-xs text-gray-500">
              Tap outside to close
            </p>
          </div>
        </div>
      </>
    );
  }
);

UniversalMobileNavigation.displayName = 'UniversalMobileNavigation';
