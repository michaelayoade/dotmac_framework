import { useState, useCallback, useEffect } from 'react';
import type { NavigationItem } from '../types';
import { findActiveNavigationItem } from '../utils';

export interface UseNavigationStateOptions {
  items: NavigationItem[];
  initialActiveItem?: string;
  onNavigate?: (item: NavigationItem) => void;
  syncWithUrl?: boolean;
}

export interface NavigationState {
  activeItem: string | undefined;
  expandedItems: Set<string>;
  collapsed: boolean;
}

export function useNavigationState({
  items,
  initialActiveItem,
  onNavigate,
  syncWithUrl = true,
}: UseNavigationStateOptions) {
  const [state, setState] = useState<NavigationState>(() => {
    const currentPath = syncWithUrl ? window?.location?.pathname : undefined;
    const activeItem = initialActiveItem ||
      (currentPath ? findActiveNavigationItem(items, currentPath)?.id : undefined);

    return {
      activeItem,
      expandedItems: new Set(),
      collapsed: false,
    };
  });

  // Handle navigation
  const handleNavigate = useCallback((item: NavigationItem) => {
    setState(prev => ({
      ...prev,
      activeItem: item.id,
    }));

    onNavigate?.(item);

    // Basic client-side navigation
    if (!onNavigate && item.href) {
      window.location.href = item.href;
    }
  }, [onNavigate]);

  // Toggle expanded state for items with children
  const toggleExpanded = useCallback((itemId: string) => {
    setState(prev => {
      const newExpanded = new Set(prev.expandedItems);
      if (newExpanded.has(itemId)) {
        newExpanded.delete(itemId);
      } else {
        newExpanded.add(itemId);
      }
      return {
        ...prev,
        expandedItems: newExpanded,
      };
    });
  }, []);

  // Toggle collapsed state
  const toggleCollapsed = useCallback(() => {
    setState(prev => ({
      ...prev,
      collapsed: !prev.collapsed,
    }));
  }, []);

  // Set active item
  const setActiveItem = useCallback((itemId: string) => {
    setState(prev => ({
      ...prev,
      activeItem: itemId,
    }));
  }, []);

  // Expand all parent items for the active item
  useEffect(() => {
    if (!state.activeItem) return;

    const findParents = (items: NavigationItem[], targetId: string, parents: string[] = []): string[] => {
      for (const item of items) {
        const currentParents = [...parents, item.id];

        if (item.id === targetId) {
          return parents; // Return parents, not including the target itself
        }

        if (item.children) {
          const found = findParents(item.children, targetId, currentParents);
          if (found.length > 0) {
            return found;
          }
        }
      }
      return [];
    };

    const parentIds = findParents(items, state.activeItem);

    if (parentIds.length > 0) {
      setState(prev => ({
        ...prev,
        expandedItems: new Set([...prev.expandedItems, ...parentIds]),
      }));
    }
  }, [state.activeItem, items]);

  // Sync with URL changes
  useEffect(() => {
    if (!syncWithUrl) return;

    const handleUrlChange = () => {
      const currentPath = window.location.pathname;
      const activeItem = findActiveNavigationItem(items, currentPath);

      if (activeItem && activeItem.id !== state.activeItem) {
        setState(prev => ({
          ...prev,
          activeItem: activeItem.id,
        }));
      }
    };

    // Listen for browser navigation
    window.addEventListener('popstate', handleUrlChange);

    return () => {
      window.removeEventListener('popstate', handleUrlChange);
    };
  }, [syncWithUrl, items, state.activeItem]);

  return {
    ...state,
    handleNavigate,
    toggleExpanded,
    toggleCollapsed,
    setActiveItem,
    isExpanded: (itemId: string) => state.expandedItems.has(itemId),
    isActive: (itemId: string) => state.activeItem === itemId,
  };
}
