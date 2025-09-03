/**
 * Side Panel Drawer
 * Reusable side panel component with customizable content and actions
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { clsx } from 'clsx';
import { trackAction } from '@dotmac/monitoring/observability';
import { Button, ScrollArea } from '@dotmac/primitives';
import { withComponentRegistration } from '@dotmac/registry';
import { X, ChevronRight, Maximize2, Minimize2 } from 'lucide-react';

export interface SidePanelAction {
  key: string;
  label: string;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  icon?: React.ReactNode;
  disabled?: boolean;
  loading?: boolean;
  onClick: () => void | Promise<void>;
}

export interface SidePanelDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  actions?: SidePanelAction[];
  width?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  position?: 'left' | 'right';
  overlay?: boolean;
  resizable?: boolean;
  collapsible?: boolean;
  className?: string;
  headerActions?: React.ReactNode;
  footerContent?: React.ReactNode;
  onResize?: (width: number) => void;
  onCollapse?: (collapsed: boolean) => void;
  'data-testid'?: string;
}

const WIDTH_CLASSES = {
  sm: 'w-80',
  md: 'w-96',
  lg: 'w-[32rem]',
  xl: 'w-[40rem]',
  full: 'w-full',
};

function SidePanelDrawerImpl({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  actions = [],
  width = 'md',
  position = 'right',
  overlay = true,
  resizable = false,
  collapsible = false,
  className = '',
  headerActions,
  footerContent,
  onResize,
  onCollapse,
  'data-testid': testId = 'side-panel-drawer',
}: SidePanelDrawerProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [currentWidth, setCurrentWidth] = useState(0);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);

  // Initialize width
  useEffect(() => {
    if (panelRef.current && currentWidth === 0) {
      setCurrentWidth(panelRef.current.offsetWidth);
    }
  }, [isOpen, currentWidth]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  // Handle resize
  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      if (!resizable) return;

      e.preventDefault();
      setIsResizing(true);
      resizeStartX.current = e.clientX;
      resizeStartWidth.current = currentWidth;

      const handleMouseMove = (e: MouseEvent) => {
        if (!panelRef.current) return;

        const deltaX =
          position === 'right'
            ? resizeStartX.current - e.clientX
            : e.clientX - resizeStartX.current;

        const newWidth = Math.max(280, Math.min(800, resizeStartWidth.current + deltaX));
        setCurrentWidth(newWidth);
        onResize?.(newWidth);
      };

      const handleMouseUp = () => {
        setIsResizing(false);
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [resizable, currentWidth, position, onResize]
  );

  // Handle collapse
  const handleCollapse = useCallback(() => {
    const newCollapsed = !isCollapsed;
    setIsCollapsed(newCollapsed);
    onCollapse?.(newCollapsed);

    try {
      trackAction('side_panel_collapse', 'ui', { collapsed: newCollapsed });
    } catch {}
  }, [isCollapsed, onCollapse]);

  // Handle close
  const handleClose = useCallback(() => {
    onClose();
    try {
      trackAction('side_panel_close', 'ui');
    } catch {}
  }, [onClose]);

  // Handle action click
  const handleActionClick = useCallback(async (action: SidePanelAction) => {
    try {
      await action.onClick();
      trackAction('side_panel_action', 'ui', { action: action.key });
    } catch (error) {
      console.error('Side panel action failed:', error);
    }
  }, []);

  if (!isOpen) return null;

  const panelClasses = clsx(
    'fixed z-50 bg-background border-border flex flex-col shadow-xl transition-all duration-300',
    position === 'right' && [
      'top-0 right-0 h-full border-l',
      isCollapsed ? 'translate-x-full' : 'translate-x-0',
    ],
    position === 'left' && [
      'top-0 left-0 h-full border-r',
      isCollapsed ? '-translate-x-full' : 'translate-x-0',
    ],
    !isCollapsed && (resizable ? '' : WIDTH_CLASSES[width]),
    isResizing && 'select-none',
    className
  );

  const overlayClasses = clsx(
    'fixed inset-0 z-40 bg-background/80 backdrop-blur-sm transition-opacity duration-300',
    isOpen && !isCollapsed ? 'opacity-100' : 'opacity-0 pointer-events-none'
  );

  return (
    <>
      {/* Overlay */}
      {overlay && (
        <div className={overlayClasses} onClick={handleClose} data-testid={`${testId}-overlay`} />
      )}

      {/* Panel */}
      <div
        ref={panelRef}
        className={panelClasses}
        style={resizable && currentWidth > 0 ? { width: currentWidth } : undefined}
        data-testid={testId}
        role='dialog'
        aria-modal='true'
        aria-labelledby={`${testId}-title`}
        aria-describedby={subtitle ? `${testId}-subtitle` : undefined}
      >
        {/* Resize Handle */}
        {resizable && !isCollapsed && (
          <div
            className={clsx(
              'absolute top-0 w-1 h-full cursor-col-resize hover:bg-primary/20 transition-colors',
              position === 'right' ? 'left-0' : 'right-0'
            )}
            onMouseDown={handleResizeStart}
            data-testid={`${testId}-resize-handle`}
          />
        )}

        {/* Header */}
        <div className='flex items-center justify-between p-6 border-b bg-muted/50'>
          <div className='flex-1 min-w-0'>
            <h2 id={`${testId}-title`} className='text-lg font-semibold text-foreground truncate'>
              {title}
            </h2>
            {subtitle && (
              <p id={`${testId}-subtitle`} className='mt-1 text-sm text-muted-foreground truncate'>
                {subtitle}
              </p>
            )}
          </div>

          <div className='flex items-center space-x-2 ml-4'>
            {headerActions}

            {collapsible && (
              <Button
                variant='ghost'
                size='icon'
                onClick={handleCollapse}
                aria-label={isCollapsed ? 'Expand panel' : 'Collapse panel'}
                data-testid={`${testId}-collapse-button`}
              >
                {isCollapsed ? (
                  <Maximize2 className='h-4 w-4' />
                ) : (
                  <Minimize2 className='h-4 w-4' />
                )}
              </Button>
            )}

            <Button
              variant='ghost'
              size='icon'
              onClick={handleClose}
              aria-label='Close panel'
              data-testid={`${testId}-close-button`}
            >
              <X className='h-4 w-4' />
            </Button>
          </div>
        </div>

        {/* Content */}
        {!isCollapsed && (
          <>
            <ScrollArea className='flex-1 p-6' data-testid={`${testId}-content`}>
              {children}
            </ScrollArea>

            {/* Footer */}
            {(actions.length > 0 || footerContent) && (
              <div className='border-t bg-muted/50 p-6'>
                {footerContent && (
                  <div className='mb-4' data-testid={`${testId}-footer-content`}>
                    {footerContent}
                  </div>
                )}

                {actions.length > 0 && (
                  <div className='flex items-center justify-end space-x-3'>
                    {actions.map((action) => (
                      <Button
                        key={action.key}
                        variant={action.variant || 'primary'}
                        disabled={action.disabled || action.loading}
                        onClick={() => handleActionClick(action)}
                        data-testid={`${testId}-action-${action.key}`}
                        className='flex items-center space-x-2'
                      >
                        {action.icon && <span className='w-4 h-4'>{action.icon}</span>}
                        <span>{action.label}</span>
                        {action.loading && (
                          <div className='w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin' />
                        )}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Collapsed State */}
        {isCollapsed && (
          <div className='flex flex-col items-center p-4 space-y-2'>
            <Button
              variant='ghost'
              size='icon'
              onClick={handleCollapse}
              aria-label='Expand panel'
              data-testid={`${testId}-expand-button`}
            >
              <ChevronRight
                className={clsx(
                  'h-5 w-5 transition-transform',
                  position === 'left' && 'rotate-180'
                )}
              />
            </Button>
            <span className='text-xs text-muted-foreground transform -rotate-90 whitespace-nowrap'>
              {title}
            </span>
          </div>
        )}
      </div>
    </>
  );
}

export const SidePanelDrawer = withComponentRegistration(SidePanelDrawerImpl, {
  name: 'SidePanelDrawer',
  category: 'overlay',
  portal: 'shared',
  version: '1.0.0',
  description: 'Reusable side panel component with customizable content and actions',
});

// Hook for managing side panel state
export function useSidePanel(initialOpen = false) {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const [content, setContent] = useState<React.ReactNode>(null);
  const [config, setConfig] = useState<Partial<SidePanelDrawerProps>>({});

  const open = useCallback(
    (panelContent: React.ReactNode, panelConfig: Partial<SidePanelDrawerProps> = {}) => {
      setContent(panelContent);
      setConfig(panelConfig);
      setIsOpen(true);
    },
    []
  );

  const close = useCallback(() => {
    setIsOpen(false);
    // Clear content after animation
    setTimeout(() => {
      setContent(null);
      setConfig({});
    }, 300);
  }, []);

  const toggle = useCallback(() => {
    if (isOpen) {
      close();
    } else {
      setIsOpen(true);
    }
  }, [isOpen, close]);

  const updateConfig = useCallback((newConfig: Partial<SidePanelDrawerProps>) => {
    setConfig((prev) => ({ ...prev, ...newConfig }));
  }, []);

  return {
    isOpen,
    content,
    config,
    open,
    close,
    toggle,
    updateConfig,
  };
}

export default SidePanelDrawer;
