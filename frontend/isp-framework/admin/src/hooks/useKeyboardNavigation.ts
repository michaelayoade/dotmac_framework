/**
 * Keyboard Navigation Hooks
 * Provides keyboard navigation support for improved accessibility
 */

import { useEffect, useRef, useCallback } from 'react';

// Types
export interface KeyboardNavigationOptions {
  enabled?: boolean;
  loop?: boolean;
  orientation?: 'horizontal' | 'vertical' | 'both';
  preventDefault?: boolean;
  stopPropagation?: boolean;
}

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  callback: (event: KeyboardEvent) => void;
  description?: string;
}

// Hook for focus management within a container
export function useFocusManagement<T extends HTMLElement = HTMLElement>(
  options: KeyboardNavigationOptions = {}
) {
  const containerRef = useRef<T>(null);
  const {
    enabled = true,
    loop = true,
    orientation = 'both',
    preventDefault = true,
    stopPropagation = false,
  } = options;

  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!containerRef.current) return [];

    const selector = [
      'button:not([disabled])',
      '[href]',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
      'details summary',
    ].join(', ');

    const elements = Array.from(
      containerRef.current.querySelectorAll<HTMLElement>(selector)
    ).filter((element) => {
      // Check if element is visible and not hidden
      const style = getComputedStyle(element);
      return (
        element.offsetWidth > 0 &&
        element.offsetHeight > 0 &&
        style.visibility !== 'hidden' &&
        style.display !== 'none'
      );
    });

    return elements;
  }, []);

  const getCurrentIndex = useCallback((): number => {
    const elements = getFocusableElements();
    const activeElement = document.activeElement as HTMLElement;
    return elements.indexOf(activeElement);
  }, [getFocusableElements]);

  const focusElement = useCallback(
    (index: number) => {
      const elements = getFocusableElements();
      if (elements.length === 0) return;

      let targetIndex = index;

      if (loop) {
        if (targetIndex < 0) targetIndex = elements.length - 1;
        if (targetIndex >= elements.length) targetIndex = 0;
      } else {
        targetIndex = Math.max(0, Math.min(elements.length - 1, targetIndex));
      }

      const targetElement = elements[targetIndex];
      if (targetElement) {
        targetElement.focus();
      }
    },
    [getFocusableElements, loop]
  );

  const focusFirst = useCallback(() => {
    focusElement(0);
  }, [focusElement]);

  const focusLast = useCallback(() => {
    const elements = getFocusableElements();
    focusElement(elements.length - 1);
  }, [focusElement, getFocusableElements]);

  const focusNext = useCallback(() => {
    const currentIndex = getCurrentIndex();
    focusElement(currentIndex + 1);
  }, [getCurrentIndex, focusElement]);

  const focusPrevious = useCallback(() => {
    const currentIndex = getCurrentIndex();
    focusElement(currentIndex - 1);
  }, [getCurrentIndex, focusElement]);

  useEffect(() => {
    if (!enabled) return;

    const container = containerRef.current;
    if (!container) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      const { key, shiftKey } = event;

      // Arrow key navigation
      if (orientation === 'vertical' || orientation === 'both') {
        if (key === 'ArrowDown') {
          if (preventDefault) event.preventDefault();
          if (stopPropagation) event.stopPropagation();
          focusNext();
          return;
        }
        if (key === 'ArrowUp') {
          if (preventDefault) event.preventDefault();
          if (stopPropagation) event.stopPropagation();
          focusPrevious();
          return;
        }
      }

      if (orientation === 'horizontal' || orientation === 'both') {
        if (key === 'ArrowRight') {
          if (preventDefault) event.preventDefault();
          if (stopPropagation) event.stopPropagation();
          focusNext();
          return;
        }
        if (key === 'ArrowLeft') {
          if (preventDefault) event.preventDefault();
          if (stopPropagation) event.stopPropagation();
          focusPrevious();
          return;
        }
      }

      // Tab navigation (respect shift for reverse)
      if (key === 'Tab') {
        if (preventDefault) {
          event.preventDefault();
          if (stopPropagation) event.stopPropagation();

          if (shiftKey) {
            focusPrevious();
          } else {
            focusNext();
          }
        }
      }

      // Home/End navigation
      if (key === 'Home') {
        if (preventDefault) event.preventDefault();
        if (stopPropagation) event.stopPropagation();
        focusFirst();
      }
      if (key === 'End') {
        if (preventDefault) event.preventDefault();
        if (stopPropagation) event.stopPropagation();
        focusLast();
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    enabled,
    orientation,
    preventDefault,
    stopPropagation,
    focusNext,
    focusPrevious,
    focusFirst,
    focusLast,
  ]);

  return {
    containerRef,
    focusFirst,
    focusLast,
    focusNext,
    focusPrevious,
    focusElement,
    getFocusableElements,
    getCurrentIndex,
  };
}

// Hook for keyboard shortcuts
export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[], enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const { key, ctrl = false, alt = false, shift = false, meta = false, callback } = shortcut;

        const keyMatches = event.key.toLowerCase() === key.toLowerCase();
        const ctrlMatches = event.ctrlKey === ctrl;
        const altMatches = event.altKey === alt;
        const shiftMatches = event.shiftKey === shift;
        const metaMatches = event.metaKey === meta;

        if (keyMatches && ctrlMatches && altMatches && shiftMatches && metaMatches) {
          event.preventDefault();
          event.stopPropagation();
          callback(event);
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [shortcuts, enabled]);
}

// Hook for escape key handling
export function useEscapeKey(callback: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        callback();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [callback, enabled]);
}

// Hook for enter key handling
export function useEnterKey(callback: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        callback();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [callback, enabled]);
}

// Hook for arrow key navigation in grids/tables
export function useGridNavigation<T extends HTMLElement = HTMLElement>(
  rows: number,
  columns: number,
  options: Omit<KeyboardNavigationOptions, 'orientation'> & {
    onCellFocus?: (row: number, col: number) => void;
  } = {}
) {
  const containerRef = useRef<T>(null);
  const { enabled = true, loop = false, preventDefault = true, onCellFocus } = options;

  const getCellElement = useCallback((row: number, col: number): HTMLElement | null => {
    if (!containerRef.current) return null;

    const selector = `[data-row="${row}"][data-col="${col}"], [data-grid-row="${row}"][data-grid-col="${col}"]`;
    return containerRef.current.querySelector<HTMLElement>(selector);
  }, []);

  const getCurrentCell = useCallback((): { row: number; col: number } | null => {
    const activeElement = document.activeElement as HTMLElement;
    const row =
      activeElement?.getAttribute('data-row') || activeElement?.getAttribute('data-grid-row');
    const col =
      activeElement?.getAttribute('data-col') || activeElement?.getAttribute('data-grid-col');

    if (row !== null && col !== null) {
      return { row: parseInt(row, 10), col: parseInt(col, 10) };
    }

    return null;
  }, []);

  const focusCell = useCallback(
    (row: number, col: number) => {
      let targetRow = row;
      let targetCol = col;

      if (loop) {
        if (targetRow < 0) targetRow = rows - 1;
        if (targetRow >= rows) targetRow = 0;
        if (targetCol < 0) targetCol = columns - 1;
        if (targetCol >= columns) targetCol = 0;
      } else {
        targetRow = Math.max(0, Math.min(rows - 1, targetRow));
        targetCol = Math.max(0, Math.min(columns - 1, targetCol));
      }

      const cell = getCellElement(targetRow, targetCol);
      if (cell) {
        cell.focus();
        onCellFocus?.(targetRow, targetCol);
      }
    },
    [rows, columns, loop, getCellElement, onCellFocus]
  );

  useEffect(() => {
    if (!enabled) return;

    const container = containerRef.current;
    if (!container) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      const currentCell = getCurrentCell();
      if (!currentCell) return;

      const { row, col } = currentCell;
      let handled = false;

      switch (event.key) {
        case 'ArrowUp':
          focusCell(row - 1, col);
          handled = true;
          break;
        case 'ArrowDown':
          focusCell(row + 1, col);
          handled = true;
          break;
        case 'ArrowLeft':
          focusCell(row, col - 1);
          handled = true;
          break;
        case 'ArrowRight':
          focusCell(row, col + 1);
          handled = true;
          break;
        case 'Home':
          if (event.ctrlKey) {
            focusCell(0, 0); // Go to first cell
          } else {
            focusCell(row, 0); // Go to first column in current row
          }
          handled = true;
          break;
        case 'End':
          if (event.ctrlKey) {
            focusCell(rows - 1, columns - 1); // Go to last cell
          } else {
            focusCell(row, columns - 1); // Go to last column in current row
          }
          handled = true;
          break;
      }

      if (handled && preventDefault) {
        event.preventDefault();
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, preventDefault, getCurrentCell, focusCell, rows, columns]);

  return {
    containerRef,
    focusCell,
    getCurrentCell,
    getCellElement,
  };
}

// Hook for roving tabindex pattern
export function useRovingTabIndex<T extends HTMLElement = HTMLElement>(
  options: KeyboardNavigationOptions = {}
) {
  const { enabled = true } = options;
  const { containerRef, focusFirst, getCurrentIndex, getFocusableElements } =
    useFocusManagement<T>(options);

  useEffect(() => {
    if (!enabled) return;

    const updateTabIndex = () => {
      const elements = getFocusableElements();
      const currentIndex = getCurrentIndex();

      elements.forEach((element, index) => {
        if (index === currentIndex) {
          element.setAttribute('tabindex', '0');
        } else {
          element.setAttribute('tabindex', '-1');
        }
      });
    };

    const container = containerRef.current;
    if (!container) return;

    // Set initial focus
    const elements = getFocusableElements();
    if (elements.length > 0 && !elements.some((el) => el.getAttribute('tabindex') === '0')) {
      elements[0].setAttribute('tabindex', '0');
    }

    const handleFocus = (event: FocusEvent) => {
      const target = event.target as HTMLElement;
      if (container.contains(target)) {
        updateTabIndex();
      }
    };

    const handleFocusIn = () => {
      if (getCurrentIndex() === -1) {
        focusFirst();
      }
    };

    container.addEventListener('focusin', handleFocusIn);
    document.addEventListener('focusin', handleFocus);

    return () => {
      container.removeEventListener('focusin', handleFocusIn);
      document.removeEventListener('focusin', handleFocus);
    };
  }, [enabled, containerRef, getFocusableElements, getCurrentIndex, focusFirst]);

  return containerRef;
}

// Hook for accessible dropdown/menu navigation
export function useMenuNavigation<T extends HTMLElement = HTMLElement>(
  options: KeyboardNavigationOptions & {
    onSelect?: (index: number) => void;
    onClose?: () => void;
  } = {}
) {
  const { onSelect, onClose, ...navOptions } = options;
  const navigation = useFocusManagement<T>({
    ...navOptions,
    orientation: 'vertical',
  });

  useEffect(() => {
    const container = navigation.containerRef.current;
    if (!container) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'Enter':
        case ' ':
          event.preventDefault();
          const currentIndex = navigation.getCurrentIndex();
          if (currentIndex !== -1) {
            onSelect?.(currentIndex);
          }
          break;
        case 'Escape':
          event.preventDefault();
          onClose?.();
          break;
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [navigation, onSelect, onClose]);

  return navigation;
}
