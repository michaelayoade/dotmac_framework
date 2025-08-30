import type { NavigationItem, NavigationVariant } from './types';

// Re-export cn utility from canonical source
export { cn } from '@dotmac/primitives/utils';

export function isNavigationItemActive(item: NavigationItem, currentPath: string): boolean {
  if (item.href === currentPath) return true;

  // Check if current path starts with item href (for parent routes)
  if (item.children && item.children.length > 0) {
    return item.children.some(child => isNavigationItemActive(child, currentPath));
  }

  return false;
}

export function findActiveNavigationItem(items: NavigationItem[], currentPath: string): NavigationItem | null {
  for (const item of items) {
    if (isNavigationItemActive(item, currentPath)) {
      // Check children first for more specific matches
      if (item.children) {
        const activeChild = findActiveNavigationItem(item.children, currentPath);
        if (activeChild) return activeChild;
      }

      // Return parent if no child matches
      if (item.href === currentPath) return item;
    }
  }

  return null;
}

export function getVariantStyles(variant: NavigationVariant): Record<string, string> {
  const variants = {
    admin: {
      primary: 'bg-blue-600 hover:bg-blue-700 text-white',
      secondary: 'bg-blue-50 text-blue-600 hover:bg-blue-100',
      accent: 'border-blue-200',
      text: 'text-blue-900',
    },
    customer: {
      primary: 'bg-green-600 hover:bg-green-700 text-white',
      secondary: 'bg-green-50 text-green-600 hover:bg-green-100',
      accent: 'border-green-200',
      text: 'text-green-900',
    },
    reseller: {
      primary: 'bg-purple-600 hover:bg-purple-700 text-white',
      secondary: 'bg-purple-50 text-purple-600 hover:bg-purple-100',
      accent: 'border-purple-200',
      text: 'text-purple-900',
    },
    technician: {
      primary: 'bg-orange-600 hover:bg-orange-700 text-white',
      secondary: 'bg-orange-50 text-orange-600 hover:bg-orange-100',
      accent: 'border-orange-200',
      text: 'text-orange-900',
    },
    management: {
      primary: 'bg-gray-800 hover:bg-gray-900 text-white',
      secondary: 'bg-gray-50 text-gray-700 hover:bg-gray-100',
      accent: 'border-gray-200',
      text: 'text-gray-900',
    },
  };

  return variants[variant] || variants.admin;
}

export function generateNavigationId(label: string, parentId?: string): string {
  const cleanLabel = label.toLowerCase().replace(/[^a-z0-9]/g, '-');
  return parentId ? `${parentId}-${cleanLabel}` : cleanLabel;
}

export function flattenNavigationItems(items: NavigationItem[]): NavigationItem[] {
  const flattened: NavigationItem[] = [];

  function traverse(items: NavigationItem[]) {
    for (const item of items) {
      flattened.push(item);
      if (item.children) {
        traverse(item.children);
      }
    }
  }

  traverse(items);
  return flattened;
}

export function buildNavigationTree(items: NavigationItem[], parentId?: string): NavigationItem[] {
  return items
    .filter(item => {
      const pathParts = item.id.split('-');
      const itemParentId = pathParts.length > 1 ? pathParts.slice(0, -1).join('-') : undefined;
      return itemParentId === parentId;
    })
    .map(item => ({
      ...item,
      children: buildNavigationTree(items, item.id),
    }));
}

export function getNavigationDepth(items: NavigationItem[]): number {
  let maxDepth = 0;

  function traverse(items: NavigationItem[], depth = 1) {
    maxDepth = Math.max(maxDepth, depth);
    for (const item of items) {
      if (item.children) {
        traverse(item.children, depth + 1);
      }
    }
  }

  traverse(items);
  return maxDepth;
}
