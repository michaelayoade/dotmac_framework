/**
 * Screen Reader Support Components
 * Enhanced ARIA attributes, live regions, and screen reader optimizations
 */

'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { announceToScreenReader, generateId } from '@/lib/accessibility';

// ============================================================================
// LIVE REGION COMPONENT
// ============================================================================

interface LiveRegionProps {
  children: React.ReactNode;
  politeness?: 'polite' | 'assertive' | 'off';
  atomic?: boolean;
  relevant?: 'additions' | 'removals' | 'text' | 'all';
  className?: string;
  id?: string;
}

export function LiveRegion({
  children,
  politeness = 'polite',
  atomic = true,
  relevant = 'all',
  className = 'sr-only',
  id,
  ...props
}: LiveRegionProps) {
  const generatedId = useRef(id || generateId('live-region'));

  return (
    <div
      id={generatedId.current}
      aria-live={politeness}
      aria-atomic={atomic}
      aria-relevant={relevant}
      className={className}
      {...props}
    >
      {children}
    </div>
  );
}

// ============================================================================
// STATUS MESSAGE COMPONENT
// ============================================================================

interface StatusMessageProps {
  message: string;
  type?: 'success' | 'error' | 'warning' | 'info';
  visible?: boolean;
  duration?: number;
  onDismiss?: () => void;
}

export function StatusMessage({
  message,
  type = 'info',
  visible = true,
  duration = 5000,
  onDismiss,
}: StatusMessageProps) {
  const [isVisible, setIsVisible] = useState(visible);

  useEffect(() => {
    if (visible && duration > 0) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        onDismiss?.();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [visible, duration, onDismiss]);

  useEffect(() => {
    if (visible && message) {
      const politeness = type === 'error' ? 'assertive' : 'polite';
      announceToScreenReader(`${type}: ${message}`, politeness);
    }
  }, [visible, message, type]);

  if (!isVisible) return null;

  return (
    <LiveRegion politeness={type === 'error' ? 'assertive' : 'polite'}>
      {message}
    </LiveRegion>
  );
}

// ============================================================================
// PROGRESS ANNOUNCER COMPONENT
// ============================================================================

interface ProgressAnnouncerProps {
  value: number;
  max?: number;
  label?: string;
  announceInterval?: number;
  formatMessage?: (value: number, max: number) => string;
}

export function ProgressAnnouncer({
  value,
  max = 100,
  label = 'Progress',
  announceInterval = 25,
  formatMessage = (value, max) => `${label}: ${Math.round((value / max) * 100)}% complete`,
}: ProgressAnnouncerProps) {
  const lastAnnouncedValue = useRef<number>(-1);

  useEffect(() => {
    const percentage = Math.round((value / max) * 100);
    const shouldAnnounce = 
      percentage >= lastAnnouncedValue.current + announceInterval ||
      percentage === 100 ||
      value === 0;

    if (shouldAnnounce) {
      announceToScreenReader(formatMessage(value, max), 'polite');
      lastAnnouncedValue.current = percentage;
    }
  }, [value, max, announceInterval, formatMessage]);

  return (
    <LiveRegion politeness="polite">
      <span className="sr-only">
        {formatMessage(value, max)}
      </span>
    </LiveRegion>
  );
}

// ============================================================================
// LOADING STATE ANNOUNCER
// ============================================================================

interface LoadingStateAnnouncerProps {
  isLoading: boolean;
  loadingMessage?: string;
  completedMessage?: string;
  delay?: number;
}

export function LoadingStateAnnouncer({
  isLoading,
  loadingMessage = 'Loading content, please wait...',
  completedMessage = 'Content loaded successfully',
  delay = 1000,
}: LoadingStateAnnouncerProps) {
  const [shouldAnnounce, setShouldAnnounce] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (isLoading) {
      // Delay announcement to avoid spam for quick loads
      timeoutRef.current = setTimeout(() => {
        setShouldAnnounce(true);
        announceToScreenReader(loadingMessage, 'polite');
      }, delay);
    } else {
      // Clear timeout if loading completes quickly
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      // Announce completion only if we had announced loading
      if (shouldAnnounce) {
        announceToScreenReader(completedMessage, 'polite');
        setShouldAnnounce(false);
      }
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isLoading, loadingMessage, completedMessage, delay, shouldAnnounce]);

  return (
    <LiveRegion politeness="polite">
      {isLoading && shouldAnnounce && (
        <span className="sr-only">{loadingMessage}</span>
      )}
    </LiveRegion>
  );
}

// ============================================================================
// FORM VALIDATION ANNOUNCER
// ============================================================================

interface FormValidationAnnouncerProps {
  errors: Record<string, string>;
  fieldLabels?: Record<string, string>;
  announceOnChange?: boolean;
}

export function FormValidationAnnouncer({
  errors,
  fieldLabels = {},
  announceOnChange = true,
}: FormValidationAnnouncerProps) {
  const previousErrors = useRef<Record<string, string>>({});

  useEffect(() => {
    if (!announceOnChange) return;

    const currentErrorKeys = Object.keys(errors);
    const previousErrorKeys = Object.keys(previousErrors.current);

    // Announce new errors
    currentErrorKeys.forEach(fieldName => {
      if (!previousErrors.current[fieldName]) {
        const fieldLabel = fieldLabels[fieldName] || fieldName;
        const errorMessage = errors[fieldName];
        announceToScreenReader(
          `Error in ${fieldLabel}: ${errorMessage}`,
          'assertive'
        );
      }
    });

    // Announce resolved errors
    previousErrorKeys.forEach(fieldName => {
      if (!errors[fieldName]) {
        const fieldLabel = fieldLabels[fieldName] || fieldName;
        announceToScreenReader(
          `${fieldLabel} error resolved`,
          'polite'
        );
      }
    });

    previousErrors.current = { ...errors };
  }, [errors, fieldLabels, announceOnChange]);

  const errorCount = Object.keys(errors).length;
  const hasErrors = errorCount > 0;

  return (
    <LiveRegion politeness="assertive">
      {hasErrors && (
        <span className="sr-only">
          {errorCount === 1 
            ? 'Form has 1 error that needs to be fixed'
            : `Form has ${errorCount} errors that need to be fixed`
          }
        </span>
      )}
    </LiveRegion>
  );
}

// ============================================================================
// TABLE NAVIGATION HELPER
// ============================================================================

interface TableNavigationHelperProps {
  tableId: string;
  rowCount: number;
  columnCount: number;
  hasHeaders?: boolean;
  caption?: string;
}

export function TableNavigationHelper({
  tableId,
  rowCount,
  columnCount,
  hasHeaders = true,
  caption,
}: TableNavigationHelperProps) {
  useEffect(() => {
    const table = document.getElementById(tableId);
    if (!table) return;

    const handleFocus = () => {
      const instructions = [
        caption && `Table: ${caption}.`,
        `${rowCount} rows, ${columnCount} columns.`,
        hasHeaders && 'Table has headers.',
        'Use arrow keys to navigate between cells.',
        'Press Ctrl+Home to go to first cell, Ctrl+End to go to last cell.',
      ].filter(Boolean).join(' ');

      announceToScreenReader(instructions, 'polite');
    };

    table.addEventListener('focus', handleFocus);
    return () => table.removeEventListener('focus', handleFocus);
  }, [tableId, rowCount, columnCount, hasHeaders, caption]);

  return null;
}

// ============================================================================
// BREADCRUMB ANNOUNCER
// ============================================================================

interface BreadcrumbAnnouncerProps {
  items: Array<{ label: string; href?: string }>;
}

export function BreadcrumbAnnouncer({ items }: BreadcrumbAnnouncerProps) {
  useEffect(() => {
    if (items.length === 0) return;

    const breadcrumbText = items
      .map((item, index) => {
        if (index === items.length - 1) {
          return `current page: ${item.label}`;
        }
        return item.label;
      })
      .join(', ');

    announceToScreenReader(
      `Breadcrumb navigation: ${breadcrumbText}`,
      'polite'
    );
  }, [items]);

  return null;
}

// ============================================================================
// MODAL ANNOUNCER
// ============================================================================

interface ModalAnnouncerProps {
  isOpen: boolean;
  title: string;
  onOpen?: () => void;
  onClose?: () => void;
}

export function ModalAnnouncer({
  isOpen,
  title,
  onOpen,
  onClose,
}: ModalAnnouncerProps) {
  const previousState = useRef(isOpen);

  useEffect(() => {
    if (isOpen && !previousState.current) {
      announceToScreenReader(`Dialog opened: ${title}`, 'assertive');
      onOpen?.();
    } else if (!isOpen && previousState.current) {
      announceToScreenReader(`Dialog closed`, 'assertive');
      onClose?.();
    }
    
    previousState.current = isOpen;
  }, [isOpen, title, onOpen, onClose]);

  return null;
}

// ============================================================================
// SEARCH RESULTS ANNOUNCER
// ============================================================================

interface SearchResultsAnnouncerProps {
  query: string;
  resultCount: number;
  isLoading?: boolean;
  hasSearched?: boolean;
}

export function SearchResultsAnnouncer({
  query,
  resultCount,
  isLoading = false,
  hasSearched = false,
}: SearchResultsAnnouncerProps) {
  const previousQuery = useRef<string>('');

  useEffect(() => {
    if (!hasSearched || isLoading) return;

    // Only announce if query has changed
    if (query !== previousQuery.current) {
      const message = resultCount === 0 
        ? `No results found for "${query}"`
        : resultCount === 1
          ? `1 result found for "${query}"`
          : `${resultCount} results found for "${query}"`;

      announceToScreenReader(message, 'polite');
      previousQuery.current = query;
    }
  }, [query, resultCount, isLoading, hasSearched]);

  return (
    <LiveRegion politeness="polite">
      {hasSearched && !isLoading && (
        <span className="sr-only">
          {resultCount === 0 
            ? `No results found for "${query}"`
            : resultCount === 1
              ? `1 result found for "${query}"`
              : `${resultCount} results found for "${query}"`
          }
        </span>
      )}
    </LiveRegion>
  );
}

// ============================================================================
// PAGE CHANGE ANNOUNCER
// ============================================================================

interface PageChangeAnnouncerProps {
  pageTitle: string;
  route: string;
  previousRoute?: string;
}

export function PageChangeAnnouncer({
  pageTitle,
  route,
  previousRoute,
}: PageChangeAnnouncerProps) {
  const hasChanged = previousRoute && previousRoute !== route;

  useEffect(() => {
    if (hasChanged) {
      // Small delay to ensure page has loaded
      const timer = setTimeout(() => {
        announceToScreenReader(`Page changed to: ${pageTitle}`, 'assertive');
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [pageTitle, hasChanged]);

  return null;
}

// ============================================================================
// VISUALLY HIDDEN COMPONENT
// ============================================================================

interface VisuallyHiddenProps {
  children: React.ReactNode;
  focusable?: boolean;
  className?: string;
}

export function VisuallyHidden({
  children,
  focusable = false,
  className = '',
}: VisuallyHiddenProps) {
  const baseClass = focusable ? 'sr-only focus:not-sr-only' : 'sr-only';
  
  return (
    <span className={`${baseClass} ${className}`}>
      {children}
    </span>
  );
}

// ============================================================================
// DESCRIPTION LIST ENHANCER
// ============================================================================

interface DescriptionListEnhancerProps {
  listId: string;
}

export function DescriptionListEnhancer({ listId }: DescriptionListEnhancerProps) {
  useEffect(() => {
    const list = document.getElementById(listId);
    if (!list || list.tagName !== 'DL') return;

    // Enhance description list with ARIA relationships
    const terms = list.querySelectorAll('dt');
    const descriptions = list.querySelectorAll('dd');

    terms.forEach((term, index) => {
      const termId = term.id || `${listId}-term-${index}`;
      const descId = `${listId}-desc-${index}`;
      
      term.id = termId;
      
      if (descriptions[index]) {
        descriptions[index].id = descId;
        descriptions[index].setAttribute('aria-labelledby', termId);
      }
    });
  }, [listId]);

  return null;
}

// ============================================================================
// CUSTOM HOOK FOR SCREEN READER CONTEXT
// ============================================================================

export function useScreenReaderContext() {
  const [isScreenReaderActive, setIsScreenReaderActive] = useState(false);

  useEffect(() => {
    // Detect screen reader usage
    const hasScreenReader = 
      window.speechSynthesis || 
      window.navigator.userAgent.includes('NVDA') ||
      window.navigator.userAgent.includes('JAWS') ||
      window.navigator.userAgent.includes('VoiceOver') ||
      // Check for reduced motion preference as indicator
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    setIsScreenReaderActive(!!hasScreenReader);
  }, []);

  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    announceToScreenReader(message, priority);
  }, []);

  return {
    isScreenReaderActive,
    announce,
  };
}