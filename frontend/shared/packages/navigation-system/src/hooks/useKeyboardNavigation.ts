import { useEffect, useRef, useCallback } from 'react';
import type { NavigationItem } from '../types';
import { flattenNavigationItems } from '../utils';

export interface UseKeyboardNavigationOptions {
  items: NavigationItem[];
  activeItem?: string;
  onNavigate?: (item: NavigationItem) => void;
  enabled?: boolean;
}

export function useKeyboardNavigation({
  items,
  activeItem,
  onNavigate,
  enabled = true,
}: UseKeyboardNavigationOptions) {
  const containerRef = useRef<HTMLElement>(null);

  const flatItems = flattenNavigationItems(items).filter((item) => !item.disabled);

  const currentIndex = activeItem ? flatItems.findIndex((item) => item.id === activeItem) : -1;

  const focusItem = useCallback(
    (index: number) => {
      if (!containerRef.current) return;

      const item = flatItems[index];
      if (!item) return;

      // Find the corresponding DOM element
      const element = containerRef.current.querySelector(
        `[data-nav-item="${item.id}"]`
      ) as HTMLElement;
      element?.focus();
    },
    [flatItems]
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled || flatItems.length === 0) return;

      switch (event.key) {
        case 'ArrowDown':
        case 'j': {
          // Vim-style navigation
          event.preventDefault();
          const nextIndex = currentIndex < flatItems.length - 1 ? currentIndex + 1 : 0;
          focusItem(nextIndex);
          break;
        }

        case 'ArrowUp':
        case 'k': {
          // Vim-style navigation
          event.preventDefault();
          const prevIndex = currentIndex > 0 ? currentIndex - 1 : flatItems.length - 1;
          focusItem(prevIndex);
          break;
        }

        case 'Home':
        case 'g': {
          // Vim-style navigation
          event.preventDefault();
          focusItem(0);
          break;
        }

        case 'End':
        case 'G': {
          // Vim-style navigation
          event.preventDefault();
          focusItem(flatItems.length - 1);
          break;
        }

        case 'Enter':
        case ' ': {
          // Space for selection
          event.preventDefault();
          if (currentIndex >= 0) {
            const item = flatItems[currentIndex];
            onNavigate?.(item);
          }
          break;
        }

        case 'Escape': {
          // Blur the current focused element
          const activeElement = document.activeElement as HTMLElement;
          activeElement?.blur();
          break;
        }
      }
    },
    [enabled, flatItems, currentIndex, focusItem, onNavigate]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled) return;

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown, enabled]);

  // Auto-focus the active item when it changes
  useEffect(() => {
    if (enabled && currentIndex >= 0) {
      focusItem(currentIndex);
    }
  }, [activeItem, enabled, currentIndex, focusItem]);

  return {
    containerRef,
    currentIndex,
    flatItems,
    focusItem,
  };
}
