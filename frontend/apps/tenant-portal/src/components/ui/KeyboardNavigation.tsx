/**
 * Keyboard Navigation Components
 * Enhanced keyboard navigation and focus management utilities
 */

'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { handleArrowKeyNavigation, createFocusTrap } from '@/lib/accessibility';

// ============================================================================
// KEYBOARD NAVIGATION HOOK
// ============================================================================

export interface UseKeyboardNavigationOptions {
  onEscape?: () => void;
  onEnter?: () => void;
  onSpace?: () => void;
  onArrowUp?: () => void;
  onArrowDown?: () => void;
  onArrowLeft?: () => void;
  onArrowRight?: () => void;
  onTab?: (event: KeyboardEvent) => void;
  onHome?: () => void;
  onEnd?: () => void;
  preventDefault?: boolean;
  stopPropagation?: boolean;
}

export function useKeyboardNavigation(
  ref: React.RefObject<HTMLElement>,
  options: UseKeyboardNavigationOptions = {}
) {
  const {
    onEscape,
    onEnter,
    onSpace,
    onArrowUp,
    onArrowDown,
    onArrowLeft,
    onArrowRight,
    onTab,
    onHome,
    onEnd,
    preventDefault = true,
    stopPropagation = false,
  } = options;

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (stopPropagation) {
        event.stopPropagation();
      }

      switch (event.key) {
        case 'Escape':
          if (onEscape) {
            if (preventDefault) event.preventDefault();
            onEscape();
          }
          break;
        case 'Enter':
          if (onEnter) {
            if (preventDefault) event.preventDefault();
            onEnter();
          }
          break;
        case ' ':
          if (onSpace) {
            if (preventDefault) event.preventDefault();
            onSpace();
          }
          break;
        case 'ArrowUp':
          if (onArrowUp) {
            if (preventDefault) event.preventDefault();
            onArrowUp();
          }
          break;
        case 'ArrowDown':
          if (onArrowDown) {
            if (preventDefault) event.preventDefault();
            onArrowDown();
          }
          break;
        case 'ArrowLeft':
          if (onArrowLeft) {
            if (preventDefault) event.preventDefault();
            onArrowLeft();
          }
          break;
        case 'ArrowRight':
          if (onArrowRight) {
            if (preventDefault) event.preventDefault();
            onArrowRight();
          }
          break;
        case 'Tab':
          if (onTab) {
            onTab(event);
          }
          break;
        case 'Home':
          if (onHome) {
            if (preventDefault) event.preventDefault();
            onHome();
          }
          break;
        case 'End':
          if (onEnd) {
            if (preventDefault) event.preventDefault();
            onEnd();
          }
          break;
      }
    };

    element.addEventListener('keydown', handleKeyDown);
    return () => element.removeEventListener('keydown', handleKeyDown);
  }, [
    onEscape, onEnter, onSpace, onArrowUp, onArrowDown, 
    onArrowLeft, onArrowRight, onTab, onHome, onEnd,
    preventDefault, stopPropagation
  ]);
}

// ============================================================================
// ROVING TABINDEX HOOK
// ============================================================================

export interface UseRovingTabIndexOptions {
  orientation?: 'horizontal' | 'vertical' | 'both';
  wrap?: boolean;
  defaultIndex?: number;
  onIndexChange?: (index: number) => void;
}

export function useRovingTabIndex(
  itemsRef: React.RefObject<HTMLElement[]>,
  options: UseRovingTabIndexOptions = {}
) {
  const {
    orientation = 'vertical',
    wrap = true,
    defaultIndex = 0,
    onIndexChange,
  } = options;

  const [currentIndex, setCurrentIndex] = useState(defaultIndex);

  const updateIndex = useCallback((newIndex: number) => {
    const items = itemsRef.current;
    if (!items || items.length === 0) return;

    let targetIndex = newIndex;

    if (wrap) {
      if (targetIndex < 0) targetIndex = items.length - 1;
      if (targetIndex >= items.length) targetIndex = 0;
    } else {
      targetIndex = Math.max(0, Math.min(targetIndex, items.length - 1));
    }

    setCurrentIndex(targetIndex);
    onIndexChange?.(targetIndex);

    // Update tabindex attributes
    items.forEach((item, index) => {
      if (item) {
        item.tabIndex = index === targetIndex ? 0 : -1;
        if (index === targetIndex) {
          item.focus();
        }
      }
    });
  }, [wrap, onIndexChange, itemsRef]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const items = itemsRef.current;
    if (!items || items.length === 0) return;

    switch (event.key) {
      case 'ArrowUp':
        if (orientation === 'vertical' || orientation === 'both') {
          event.preventDefault();
          updateIndex(currentIndex - 1);
        }
        break;
      case 'ArrowDown':
        if (orientation === 'vertical' || orientation === 'both') {
          event.preventDefault();
          updateIndex(currentIndex + 1);
        }
        break;
      case 'ArrowLeft':
        if (orientation === 'horizontal' || orientation === 'both') {
          event.preventDefault();
          updateIndex(currentIndex - 1);
        }
        break;
      case 'ArrowRight':
        if (orientation === 'horizontal' || orientation === 'both') {
          event.preventDefault();
          updateIndex(currentIndex + 1);
        }
        break;
      case 'Home':
        event.preventDefault();
        updateIndex(0);
        break;
      case 'End':
        event.preventDefault();
        updateIndex(items.length - 1);
        break;
    }
  }, [currentIndex, orientation, updateIndex, itemsRef]);

  // Initialize tabindex on mount
  useEffect(() => {
    const items = itemsRef.current;
    if (!items || items.length === 0) return;

    items.forEach((item, index) => {
      if (item) {
        item.tabIndex = index === currentIndex ? 0 : -1;
      }
    });
  }, [currentIndex, itemsRef]);

  return {
    currentIndex,
    setCurrentIndex: updateIndex,
    handleKeyDown,
  };
}

// ============================================================================
// MENU NAVIGATION COMPONENT
// ============================================================================

interface MenuNavigationProps {
  children: React.ReactNode;
  onEscape?: () => void;
  orientation?: 'horizontal' | 'vertical';
  wrap?: boolean;
  className?: string;
  role?: string;
  ariaLabel?: string;
}

export const MenuNavigation = React.forwardRef<HTMLDivElement, MenuNavigationProps>(
  function MenuNavigation({
    children,
    onEscape,
    orientation = 'vertical',
    wrap = true,
    className = '',
    role = 'menu',
    ariaLabel,
    ...props
  }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const itemsRef = useRef<HTMLElement[]>([]);
    
    const { currentIndex, handleKeyDown } = useRovingTabIndex(itemsRef, {
      orientation,
      wrap,
    });

    // Collect menu items
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const items = Array.from(
        container.querySelectorAll('[role="menuitem"], [role="menuitemcheckbox"], [role="menuitemradio"], button, a[href]')
      ) as HTMLElement[];
      
      itemsRef.current = items;
    }, [children]);

    const combinedRef = useCallback((node: HTMLDivElement) => {
      containerRef.current = node;
      if (typeof ref === 'function') {
        ref(node);
      } else if (ref) {
        ref.current = node;
      }
    }, [ref]);

    useKeyboardNavigation(containerRef, {
      onEscape,
      preventDefault: false,
    });

    return (
      <div
        ref={combinedRef}
        role={role}
        aria-label={ariaLabel}
        className={className}
        onKeyDown={handleKeyDown}
        {...props}
      >
        {children}
      </div>
    );
  }
);

// ============================================================================
// TAB LIST COMPONENT
// ============================================================================

interface TabListProps {
  children: React.ReactNode;
  selectedIndex?: number;
  onSelectionChange?: (index: number) => void;
  className?: string;
  ariaLabel?: string;
}

export const TabList = React.forwardRef<HTMLDivElement, TabListProps>(
  function TabList({
    children,
    selectedIndex = 0,
    onSelectionChange,
    className = '',
    ariaLabel,
    ...props
  }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const itemsRef = useRef<HTMLElement[]>([]);

    const { handleKeyDown } = useRovingTabIndex(itemsRef, {
      orientation: 'horizontal',
      wrap: true,
      defaultIndex: selectedIndex,
      onIndexChange: onSelectionChange,
    });

    // Collect tab items
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;

      const items = Array.from(
        container.querySelectorAll('[role="tab"]')
      ) as HTMLElement[];
      
      itemsRef.current = items;
    }, [children]);

    const combinedRef = useCallback((node: HTMLDivElement) => {
      containerRef.current = node;
      if (typeof ref === 'function') {
        ref(node);
      } else if (ref) {
        ref.current = node;
      }
    }, [ref]);

    return (
      <div
        ref={combinedRef}
        role="tablist"
        aria-label={ariaLabel}
        className={className}
        onKeyDown={handleKeyDown}
        {...props}
      >
        {children}
      </div>
    );
  }
);

// ============================================================================
// FOCUS TRAP COMPONENT
// ============================================================================

interface FocusTrapProps {
  children: React.ReactNode;
  enabled?: boolean;
  restoreFocus?: boolean;
  className?: string;
}

export function FocusTrap({
  children,
  enabled = true,
  restoreFocus = true,
  className = '',
}: FocusTrapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!enabled || !containerRef.current) return;

    // Save previously focused element
    previouslyFocusedElement.current = document.activeElement as HTMLElement;

    // Create focus trap
    const cleanup = createFocusTrap(containerRef.current);

    return () => {
      cleanup();
      
      // Restore focus
      if (restoreFocus && previouslyFocusedElement.current) {
        previouslyFocusedElement.current.focus();
      }
    };
  }, [enabled, restoreFocus]);

  return (
    <div ref={containerRef} className={className}>
      {children}
    </div>
  );
}

// ============================================================================
// SKIP LINKS COMPONENT
// ============================================================================

interface SkipLink {
  href: string;
  label: string;
}

interface SkipLinksProps {
  links: SkipLink[];
  className?: string;
}

export function SkipLinks({ links, className = '' }: SkipLinksProps) {
  return (
    <nav 
      aria-label="Skip navigation links" 
      className={`skip-links ${className}`}
    >
      {links.map((link, index) => (
        <a
          key={index}
          href={link.href}
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-blue-600 text-white px-4 py-2 rounded-md z-50 focus:z-50 transition-all"
        >
          {link.label}
        </a>
      ))}
    </nav>
  );
}

// ============================================================================
// LANDMARK NAVIGATION
// ============================================================================

export function LandmarkNavigation() {
  const [landmarks, setLandmarks] = useState<Array<{ id: string; label: string; element: string }>>([]);

  useEffect(() => {
    // Find all landmarks on the page
    const landmarkElements = document.querySelectorAll('main, nav, aside, section[aria-label], section[aria-labelledby], header, footer');
    const foundLandmarks: Array<{ id: string; label: string; element: string }> = [];

    landmarkElements.forEach((element, index) => {
      const id = element.id || `landmark-${index}`;
      element.id = id;

      let label = '';
      const ariaLabel = element.getAttribute('aria-label');
      const ariaLabelledBy = element.getAttribute('aria-labelledby');
      
      if (ariaLabel) {
        label = ariaLabel;
      } else if (ariaLabelledBy) {
        const labelElement = document.getElementById(ariaLabelledBy);
        label = labelElement?.textContent || '';
      } else {
        // Default labels for common landmarks
        switch (element.tagName.toLowerCase()) {
          case 'main':
            label = 'Main content';
            break;
          case 'nav':
            label = 'Navigation';
            break;
          case 'header':
            label = 'Header';
            break;
          case 'footer':
            label = 'Footer';
            break;
          case 'aside':
            label = 'Sidebar';
            break;
          default:
            label = `Section ${index + 1}`;
        }
      }

      foundLandmarks.push({
        id,
        label,
        element: element.tagName.toLowerCase(),
      });
    });

    setLandmarks(foundLandmarks);
  }, []);

  if (landmarks.length === 0) return null;

  return (
    <nav 
      aria-label="Page landmarks"
      className="sr-only focus-within:not-sr-only focus-within:absolute focus-within:top-2 focus-within:right-2 bg-gray-900 text-white p-4 rounded-md z-50"
    >
      <h2 className="text-sm font-semibold mb-2">Jump to:</h2>
      <ul className="space-y-1">
        {landmarks.map((landmark) => (
          <li key={landmark.id}>
            <a
              href={`#${landmark.id}`}
              className="text-sm hover:underline focus:underline focus:outline-none"
            >
              {landmark.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}