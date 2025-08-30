import { ChevronRight, Home } from 'lucide-react';
import { forwardRef, Fragment } from 'react';
import type { UniversalBreadcrumbProps } from '../types';
import { cn } from '../utils';

export const UniversalBreadcrumb = forwardRef<HTMLElement, UniversalBreadcrumbProps>(
  ({
    items,
    separator = <ChevronRight className="h-4 w-4" />,
    maxItems,
    showHome = true,
    onNavigate,
    className,
    ...props
  }, ref) => {
    // Handle item collapsing if maxItems is specified
    let displayItems = [...items];
    let hasEllipsis = false;

    if (maxItems && items.length > maxItems) {
      hasEllipsis = true;
      const keepStart = Math.floor(maxItems / 2);
      const keepEnd = maxItems - keepStart - 1; // -1 for ellipsis

      displayItems = [
        ...items.slice(0, keepStart),
        { id: 'ellipsis', label: '...', current: false },
        ...items.slice(-keepEnd),
      ];
    }

    const handleItemClick = (item: typeof items[0]) => {
      if (item.href && !item.current) {
        onNavigate?.(item);
      }
    };

    return (
      <nav
        ref={ref}
        className={cn('breadcrumb', className)}
        aria-label="Breadcrumb"
        {...props}
      >
        <ol className="flex items-center space-x-1 text-sm text-gray-500">
          {showHome && (
            <>
              <li>
                <button
                  type="button"
                  onClick={() => onNavigate?.({ id: 'home', label: 'Home', href: '/' })}
                  className="flex items-center text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
                  aria-label="Go to home page"
                >
                  <Home className="h-4 w-4" />
                </button>
              </li>
              {displayItems.length > 0 && (
                <li className="flex items-center text-gray-300" aria-hidden="true">
                  {separator}
                </li>
              )}
            </>
          )}

          {displayItems.map((item, index) => (
            <Fragment key={item.id}>
              <li className="flex items-center">
                {item.id === 'ellipsis' ? (
                  <span
                    className="px-2 py-1 text-gray-500"
                    aria-label="More items"
                  >
                    ...
                  </span>
                ) : item.current || !item.href ? (
                  <span
                    className="font-medium text-gray-900"
                    aria-current="page"
                  >
                    {item.label}
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleItemClick(item)}
                    className="font-medium text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded px-1 py-0.5"
                  >
                    {item.label}
                  </button>
                )}
              </li>

              {/* Separator */}
              {index < displayItems.length - 1 && (
                <li className="flex items-center text-gray-300" aria-hidden="true">
                  {separator}
                </li>
              )}
            </Fragment>
          ))}
        </ol>
      </nav>
    );
  }
);

UniversalBreadcrumb.displayName = 'UniversalBreadcrumb';
