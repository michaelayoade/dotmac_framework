import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { forwardRef, useState } from 'react';
import { useNavigationContext } from '../context';
import type { UniversalSidebarProps } from '../types';
import { cn, getVariantStyles, isNavigationItemActive } from '../utils';

export const UniversalSidebar = forwardRef<HTMLElement, UniversalSidebarProps>(
  ({
    items,
    activeItem,
    variant = 'admin',
    collapsed = false,
    collapsible = false,
    onCollapsedChange,
    behavior = 'push',
    width = 'md',
    header,
    footer,
    onNavigate,
    className,
    ...props
  }, ref) => {
    const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
    const variantStyles = getVariantStyles(variant);
    const { onNavigate: contextOnNavigate } = useNavigationContext();

    const handleNavigate = onNavigate || contextOnNavigate;

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

    const widthClasses = {
      sm: 'w-16',
      md: 'w-64',
      lg: 'w-72',
      xl: 'w-80',
    };

    const collapsedWidthClasses = {
      sm: 'w-16',
      md: 'w-16',
      lg: 'w-16',
      xl: 'w-16',
    };

    const renderNavigationItem = (item: typeof items[0], depth = 0) => {
      const hasChildren = item.children && item.children.length > 0;
      const isExpanded = expandedItems.has(item.id);
      const isActive = activeItem === item.id || isNavigationItemActive(item, activeItem || '');
      const Icon = item.icon;

      const handleClick = () => {
        if (hasChildren) {
          toggleExpanded(item.id);
        } else {
          handleNavigate?.(item);
        }
      };

      return (
        <li key={item.id}>
          <button
            type="button"
            onClick={handleClick}
            disabled={item.disabled}
            className={cn(
              'flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition-all duration-200',
              'hover:bg-gray-100 focus:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2',
              {
                [variantStyles.secondary]: isActive,
                'text-gray-400 cursor-not-allowed': item.disabled,
                'text-gray-700': !isActive && !item.disabled,
                'pl-8': depth === 1,
                'pl-12': depth === 2,
                'pl-16': depth >= 3,
              }
            )}
            aria-expanded={hasChildren ? isExpanded : undefined}
            aria-current={isActive ? 'page' : undefined}
          >
            <div className="flex items-center min-w-0 flex-1">
              {Icon && (
                <Icon className={cn(
                  'mr-3 h-5 w-5 flex-shrink-0',
                  { 'mr-0': collapsed }
                )} />
              )}
              {!collapsed && (
                <>
                  <span className="truncate font-medium">{item.label}</span>
                  {item.badge && (
                    <span className="ml-2 inline-flex items-center justify-center rounded-full bg-red-100 px-2 py-1 text-xs font-bold text-red-600">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </div>
            {hasChildren && !collapsed && (
              <ChevronDown className={cn(
                'ml-2 h-4 w-4 flex-shrink-0 transition-transform',
                { 'rotate-180': isExpanded }
              )} />
            )}
          </button>

          {hasChildren && isExpanded && !collapsed && (
            <ul className="mt-1 space-y-1">
              {item.children?.map(child => renderNavigationItem(child, depth + 1))}
            </ul>
          )}
        </li>
      );
    };

    return (
      <aside
        ref={ref}
        className={cn(
          'flex h-full flex-col bg-white border-r border-gray-200 transition-all duration-300',
          collapsed ? collapsedWidthClasses[width] : widthClasses[width],
          {
            'shadow-lg': behavior === 'overlay',
            'border-r-2': behavior === 'push',
          },
          className
        )}
        {...props}
      >
        {/* Header */}
        {header && (
          <div className="flex items-center justify-between border-b border-gray-200 p-4">
            {!collapsed && header}
            {collapsible && (
              <button
                type="button"
                onClick={() => onCollapsedChange?.(!collapsed)}
                className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-500"
                aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {collapsed ? (
                  <ChevronRight className="h-5 w-5" />
                ) : (
                  <ChevronLeft className="h-5 w-5" />
                )}
              </button>
            )}
          </div>
        )}

        {/* Navigation Items */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1">
            {items.map(item => renderNavigationItem(item))}
          </ul>
        </nav>

        {/* Footer */}
        {footer && !collapsed && (
          <div className="border-t border-gray-200 p-4">
            {footer}
          </div>
        )}
      </aside>
    );
  }
);

UniversalSidebar.displayName = 'UniversalSidebar';
