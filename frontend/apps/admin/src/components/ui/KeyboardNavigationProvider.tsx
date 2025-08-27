/**
 * Keyboard Navigation Provider
 * Context provider for global keyboard navigation settings
 */

'use client';

import React, { 
  createContext, 
  useContext, 
  ReactNode, 
  useState, 
  useCallback,
  useEffect
} from 'react';
import { 
  useKeyboardShortcuts, 
  type KeyboardShortcut 
} from '../hooks/useKeyboardNavigation';

// Types
interface KeyboardNavigationContextValue {
  isEnabled: boolean;
  showFocusIndicators: boolean;
  shortcuts: KeyboardShortcut[];
  toggleEnabled: () => void;
  toggleFocusIndicators: () => void;
  addShortcut: (shortcut: KeyboardShortcut) => void;
  removeShortcut: (key: string) => void;
  clearShortcuts: () => void;
}

// Context
const KeyboardNavigationContext = createContext<KeyboardNavigationContextValue | undefined>(
  undefined
);

export function useKeyboardNavigationContext() {
  const context = useContext(KeyboardNavigationContext);
  if (!context) {
    throw new Error(
      'useKeyboardNavigationContext must be used within a KeyboardNavigationProvider'
    );
  }
  return context;
}

// Provider Props
interface KeyboardNavigationProviderProps {
  children: ReactNode;
  defaultEnabled?: boolean;
  defaultShowFocusIndicators?: boolean;
  globalShortcuts?: KeyboardShortcut[];
}

// Focus indicator styles
const focusIndicatorStyles = `
  .keyboard-navigation-enabled *:focus {
    outline: 2px solid #3b82f6 !important;
    outline-offset: 2px !important;
  }

  .keyboard-navigation-enabled *:focus:not(:focus-visible) {
    outline: none !important;
  }

  .keyboard-navigation-enabled button:focus,
  .keyboard-navigation-enabled [role="button"]:focus,
  .keyboard-navigation-enabled input:focus,
  .keyboard-navigation-enabled textarea:focus,
  .keyboard-navigation-enabled select:focus {
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
  }

  /* High contrast focus indicators for better accessibility */
  @media (prefers-contrast: high) {
    .keyboard-navigation-enabled *:focus {
      outline: 3px solid #000 !important;
      outline-offset: 2px !important;
    }
  }

  /* Skip links */
  .skip-link {
    position: absolute;
    left: -9999px;
    z-index: 999999;
    padding: 8px 16px;
    background: #000;
    color: #fff;
    text-decoration: none;
    border-radius: 4px;
  }

  .skip-link:focus {
    left: 16px;
    top: 16px;
  }

  /* Focus trap indicator */
  .focus-trap-active {
    position: relative;
  }

  .focus-trap-active::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    border: 3px solid #3b82f6;
    pointer-events: none;
    z-index: 9999;
  }
`;

// Provider Component
export function KeyboardNavigationProvider({
  children,
  defaultEnabled = true,
  defaultShowFocusIndicators = true,
  globalShortcuts = [],
}: KeyboardNavigationProviderProps) {
  const [isEnabled, setIsEnabled] = useState(defaultEnabled);
  const [showFocusIndicators, setShowFocusIndicators] = useState(defaultShowFocusIndicators);
  const [shortcuts, setShortcuts] = useState<KeyboardShortcut[]>([
    // Default global shortcuts
    {
      key: '/',
      callback: () => {
        const searchInput = document.querySelector<HTMLInputElement>('[data-search-input]');
        if (searchInput) {
          searchInput.focus();
        }
      },
      description: 'Focus search input',
    },
    {
      key: '?',
      callback: () => {
        // Show keyboard shortcuts help
        console.log('Keyboard shortcuts help');
      },
      description: 'Show keyboard shortcuts help',
    },
    {
      key: 'Escape',
      callback: () => {
        // Close modals, dropdowns, etc.
        const activeElement = document.activeElement as HTMLElement;
        if (activeElement && activeElement.blur) {
          activeElement.blur();
        }
      },
      description: 'Close modals and dropdowns',
    },
    ...globalShortcuts,
  ]);

  const toggleEnabled = useCallback(() => {
    setIsEnabled(prev => !prev);
  }, []);

  const toggleFocusIndicators = useCallback(() => {
    setShowFocusIndicators(prev => !prev);
  }, []);

  const addShortcut = useCallback((shortcut: KeyboardShortcut) => {
    setShortcuts(prev => {
      // Remove existing shortcut with same key combination
      const filtered = prev.filter(s => 
        !(s.key === shortcut.key && 
          s.ctrl === shortcut.ctrl && 
          s.alt === shortcut.alt && 
          s.shift === shortcut.shift && 
          s.meta === shortcut.meta)
      );
      return [...filtered, shortcut];
    });
  }, []);

  const removeShortcut = useCallback((key: string) => {
    setShortcuts(prev => prev.filter(s => s.key !== key));
  }, []);

  const clearShortcuts = useCallback(() => {
    setShortcuts([]);
  }, []);

  // Apply keyboard shortcuts
  useKeyboardShortcuts(shortcuts, isEnabled);

  // Apply focus indicators styles
  useEffect(() => {
    const styleId = 'keyboard-navigation-styles';
    let styleElement = document.getElementById(styleId) as HTMLStyleElement;

    if (showFocusIndicators && !styleElement) {
      styleElement = document.createElement('style');
      styleElement.id = styleId;
      styleElement.textContent = focusIndicatorStyles;
      document.head.appendChild(styleElement);
    } else if (!showFocusIndicators && styleElement) {
      styleElement.remove();
    }

    // Add class to body
    if (showFocusIndicators) {
      document.body.classList.add('keyboard-navigation-enabled');
    } else {
      document.body.classList.remove('keyboard-navigation-enabled');
    }

    return () => {
      if (styleElement) {
        styleElement.remove();
      }
      document.body.classList.remove('keyboard-navigation-enabled');
    };
  }, [showFocusIndicators]);

  // Listen for keyboard usage to show focus indicators
  useEffect(() => {
    if (!isEnabled) return;

    let isUsingKeyboard = false;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Tab key indicates keyboard navigation
      if (event.key === 'Tab') {
        if (!isUsingKeyboard) {
          isUsingKeyboard = true;
          setShowFocusIndicators(true);
        }
      }
    };

    const handleMouseDown = () => {
      // Mouse usage - hide focus indicators temporarily
      if (isUsingKeyboard) {
        isUsingKeyboard = false;
        // Don't hide immediately, wait for next interaction
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleMouseDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, [isEnabled]);

  // Add skip links
  useEffect(() => {
    const skipLinkId = 'keyboard-navigation-skip-links';
    let skipLinks = document.getElementById(skipLinkId);

    if (isEnabled && !skipLinks) {
      skipLinks = document.createElement('div');
      skipLinks.id = skipLinkId;
      skipLinks.innerHTML = `
        <a href="#main-content" class="skip-link">Skip to main content</a>
        <a href="#navigation" class="skip-link">Skip to navigation</a>
      `;
      document.body.insertBefore(skipLinks, document.body.firstChild);
    } else if (!isEnabled && skipLinks) {
      skipLinks.remove();
    }

    return () => {
      if (skipLinks) {
        skipLinks.remove();
      }
    };
  }, [isEnabled]);

  const value: KeyboardNavigationContextValue = {
    isEnabled,
    showFocusIndicators,
    shortcuts,
    toggleEnabled,
    toggleFocusIndicators,
    addShortcut,
    removeShortcut,
    clearShortcuts,
  };

  return (
    <KeyboardNavigationContext.Provider value={value}>
      {children}
    </KeyboardNavigationContext.Provider>
  );
}

// Helper Components

// Keyboard shortcut display component
interface KeyboardShortcutProps {
  shortcut: KeyboardShortcut;
  className?: string;
}

export function KeyboardShortcutDisplay({ shortcut, className = '' }: KeyboardShortcutProps) {
  const keys = [];
  
  if (shortcut.meta) keys.push('⌘');
  if (shortcut.ctrl) keys.push('Ctrl');
  if (shortcut.alt) keys.push('Alt');
  if (shortcut.shift) keys.push('Shift');
  keys.push(shortcut.key.toUpperCase());

  return (
    <div className={`inline-flex items-center gap-1 ${className}`}>
      {keys.map((key, index) => (
        <kbd
          key={index}
          className="px-2 py-1 text-xs font-mono bg-gray-100 border border-gray-300 rounded"
        >
          {key}
        </kbd>
      ))}
    </div>
  );
}

// Keyboard shortcuts help modal trigger
interface KeyboardShortcutsHelpProps {
  children?: ReactNode;
  className?: string;
}

export function KeyboardShortcutsHelp({ children, className = '' }: KeyboardShortcutsHelpProps) {
  const { shortcuts } = useKeyboardNavigationContext();
  const [isOpen, setIsOpen] = useState(false);

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => setIsOpen(false);

  return (
    <>
      {children ? (
        <button onClick={handleOpen} className={className}>
          {children}
        </button>
      ) : (
        <button
          onClick={handleOpen}
          className={`p-2 text-gray-500 hover:text-gray-700 rounded-lg ${className}`}
          title="Keyboard shortcuts help"
        >
          <span className="sr-only">Keyboard shortcuts</span>
          ⌨️
        </button>
      )}

      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-md w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Keyboard Shortcuts</h2>
                <button
                  onClick={handleClose}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3">
                {shortcuts
                  .filter(shortcut => shortcut.description)
                  .map((shortcut, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">
                        {shortcut.description}
                      </span>
                      <KeyboardShortcutDisplay shortcut={shortcut} />
                    </div>
                  ))}
              </div>

              <div className="mt-6 pt-4 border-t border-gray-200 text-xs text-gray-500">
                Press <kbd className="px-1 bg-gray-100 border rounded">Escape</kbd> to close
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Focus trap component
interface FocusTrapProps {
  children: ReactNode;
  enabled?: boolean;
  className?: string;
}

export function FocusTrap({ children, enabled = true, className = '' }: FocusTrapProps) {
  const { showFocusIndicators } = useKeyboardNavigationContext();

  return (
    <div 
      className={`${showFocusIndicators && enabled ? 'focus-trap-active' : ''} ${className}`}
    >
      {children}
    </div>
  );
}