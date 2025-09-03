/**
 * Accessibility utilities for keyboard navigation and focus management
 */

// Focus trap for modals and dropdowns
export class FocusTrap {
  private element: HTMLElement;
  private focusableElements: NodeListOf<HTMLElement>;
  private firstFocusable: HTMLElement;
  private lastFocusable: HTMLElement;

  constructor(element: HTMLElement) {
    this.element = element;
    this.focusableElements = this.getFocusableElements();
    this.firstFocusable = this.focusableElements[0];
    this.lastFocusable = this.focusableElements[this.focusableElements.length - 1];
  }

  private getFocusableElements(): NodeListOf<HTMLElement> {
    return this.element.querySelectorAll(
      'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], input[type="email"], input[type="password"], input[type="number"], select, [tabindex]:not([tabindex="-1"])'
    );
  }

  trap(event: KeyboardEvent) {
    if (event.key !== 'Tab') return;

    if (event.shiftKey) {
      if (document.activeElement === this.firstFocusable) {
        this.lastFocusable.focus();
        event.preventDefault();
      }
    } else {
      if (document.activeElement === this.lastFocusable) {
        this.firstFocusable.focus();
        event.preventDefault();
      }
    }
  }

  activate() {
    this.element.addEventListener('keydown', this.trap.bind(this));
    this.firstFocusable?.focus();
  }

  deactivate() {
    this.element.removeEventListener('keydown', this.trap.bind(this));
  }
}

// Keyboard navigation for lists and menus
export function handleListNavigation(
  event: KeyboardEvent,
  items: HTMLElement[],
  currentIndex: number,
  onSelect?: (index: number) => void,
  onEscape?: () => void
): number | null {
  let newIndex = currentIndex;

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault();
      newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
      break;
    case 'ArrowUp':
      event.preventDefault();
      newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
      break;
    case 'Home':
      event.preventDefault();
      newIndex = 0;
      break;
    case 'End':
      event.preventDefault();
      newIndex = items.length - 1;
      break;
    case 'Enter':
    case ' ':
      event.preventDefault();
      if (onSelect) {
        onSelect(currentIndex);
      }
      return null;
    case 'Escape':
      event.preventDefault();
      if (onEscape) {
        onEscape();
      }
      return null;
    default:
      return null;
  }

  items[newIndex]?.focus();
  return newIndex;
}

// Skip link functionality
export function createSkipLink(
  targetId: string,
  text: string = 'Skip to main content'
): HTMLElement {
  const skipLink = document.createElement('a');
  skipLink.href = `#${targetId}`;
  skipLink.textContent = text;
  skipLink.className =
    'sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 bg-blue-600 text-white p-2 z-50 rounded-br';

  skipLink.addEventListener('click', (e) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      target.scrollIntoView();
    }
  });

  return skipLink;
}

// Announce dynamic content changes to screen readers
export function announceToScreenReader(
  message: string,
  priority: 'polite' | 'assertive' = 'polite'
) {
  const announcement = document.createElement('div');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;

  document.body.appendChild(announcement);

  // Clean up after announcement
  setTimeout(() => {
    if (document.body.contains(announcement)) {
      document.body.removeChild(announcement);
    }
  }, 1000);
}

// Manage focus restoration after modal/dialog closes
export class FocusManager {
  private previouslyFocusedElement: HTMLElement | null = null;

  save() {
    this.previouslyFocusedElement = document.activeElement as HTMLElement;
  }

  restore() {
    if (
      this.previouslyFocusedElement &&
      typeof this.previouslyFocusedElement.focus === 'function'
    ) {
      this.previouslyFocusedElement.focus();
      this.previouslyFocusedElement = null;
    }
  }
}

// High contrast mode detection
export function detectHighContrastMode(): boolean {
  // Create a test element to check for high contrast mode
  const testElement = document.createElement('div');
  testElement.style.position = 'absolute';
  testElement.style.left = '-9999px';
  testElement.style.color = 'rgb(31, 41, 59)'; // slate-700
  testElement.style.backgroundColor = 'rgb(148, 163, 184)'; // slate-400

  document.body.appendChild(testElement);

  const computedStyle = window.getComputedStyle(testElement);
  const isHighContrast =
    computedStyle.color !== 'rgb(31, 41, 59)' ||
    computedStyle.backgroundColor !== 'rgb(148, 163, 184)';

  document.body.removeChild(testElement);
  return isHighContrast;
}

// Reduced motion detection
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Color contrast ratio calculation (WCAG AA compliance)
export function getContrastRatio(color1: string, color2: string): number {
  const luminance1 = getLuminance(color1);
  const luminance2 = getLuminance(color2);

  const lighter = Math.max(luminance1, luminance2);
  const darker = Math.min(luminance1, luminance2);

  return (lighter + 0.05) / (darker + 0.05);
}

function getLuminance(color: string): number {
  // Convert color to RGB values
  const rgb = hexToRgb(color);
  if (!rgb) return 0;

  // Convert RGB to relative luminance
  const [r, g, b] = [rgb.r, rgb.g, rgb.b].map((c) => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

// Keyboard shortcut manager
export class KeyboardShortcuts {
  private shortcuts: Map<string, () => void> = new Map();

  register(key: string, callback: () => void) {
    this.shortcuts.set(key, callback);
  }

  unregister(key: string) {
    this.shortcuts.delete(key);
  }

  handleKeydown = (event: KeyboardEvent) => {
    const key = this.getKeyString(event);
    const callback = this.shortcuts.get(key);

    if (callback && !this.isInputActive()) {
      event.preventDefault();
      callback();
    }
  };

  private getKeyString(event: KeyboardEvent): string {
    const parts = [];

    if (event.ctrlKey) parts.push('ctrl');
    if (event.altKey) parts.push('alt');
    if (event.shiftKey) parts.push('shift');
    if (event.metaKey) parts.push('meta');

    parts.push(event.key.toLowerCase());

    return parts.join('+');
  }

  private isInputActive(): boolean {
    const activeElement = document.activeElement;
    return (
      activeElement instanceof HTMLInputElement ||
      activeElement instanceof HTMLTextAreaElement ||
      activeElement instanceof HTMLSelectElement ||
      (activeElement instanceof HTMLElement && activeElement.isContentEditable)
    );
  }

  activate() {
    document.addEventListener('keydown', this.handleKeydown);
  }

  deactivate() {
    document.removeEventListener('keydown', this.handleKeydown);
  }
}
