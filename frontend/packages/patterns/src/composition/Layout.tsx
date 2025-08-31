/**
 * Layout Composition Pattern
 * 
 * Flexible layout components that compose together to create
 * common application layouts with responsive behavior
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { Menu, X, ChevronLeft } from 'lucide-react';
import { Button } from '@dotmac/primitives';
import { withComponentRegistration } from '@dotmac/registry';

// Layout context for shared state
interface LayoutContextValue {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  isMobile: boolean;
}

const LayoutContext = createContext<LayoutContextValue | null>(null);

export function useLayout() {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error('useLayout must be used within a LayoutProvider');
  }
  return context;
}

// Layout Provider
interface LayoutProviderProps {
  children: React.ReactNode;
  initialSidebarOpen?: boolean;
  initialSidebarCollapsed?: boolean;
}

function LayoutProviderImpl({ 
  children, 
  initialSidebarOpen = false,
  initialSidebarCollapsed = false 
}: LayoutProviderProps) {
  const [sidebarOpen, setSidebarOpen] = useState(initialSidebarOpen);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(initialSidebarCollapsed);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  React.useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const contextValue: LayoutContextValue = {
    sidebarOpen,
    setSidebarOpen,
    sidebarCollapsed,
    setSidebarCollapsed,
    isMobile,
  };

  return (
    <LayoutContext.Provider value={contextValue}>
      {children}
    </LayoutContext.Provider>
  );
}

export const LayoutProvider = withComponentRegistration(LayoutProviderImpl, {
  name: 'LayoutProvider',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Provides layout context and state management',
});

// Root Layout Container
interface LayoutRootProps {
  children: React.ReactNode;
  className?: string;
  direction?: 'horizontal' | 'vertical';
}

function LayoutRootImpl({ 
  children, 
  className,
  direction = 'horizontal' 
}: LayoutRootProps) {
  return (
    <div 
      className={clsx(
        'min-h-screen bg-background',
        direction === 'horizontal' ? 'flex' : 'flex flex-col',
        className
      )}
    >
      {children}
    </div>
  );
}

export const LayoutRoot = withComponentRegistration(LayoutRootImpl, {
  name: 'LayoutRoot',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Root layout container with flexible direction',
});

// Header Component
interface LayoutHeaderProps {
  children: React.ReactNode;
  className?: string;
  sticky?: boolean;
  showSidebarToggle?: boolean;
  height?: string;
}

function LayoutHeaderImpl({ 
  children, 
  className,
  sticky = true,
  showSidebarToggle = false,
  height = 'h-16'
}: LayoutHeaderProps) {
  const { sidebarOpen, setSidebarOpen, isMobile } = useLayout();

  const toggleSidebar = useCallback(() => {
    setSidebarOpen(!sidebarOpen);
  }, [sidebarOpen, setSidebarOpen]);

  return (
    <header 
      className={clsx(
        height,
        'w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60',
        sticky && 'sticky top-0 z-50',
        className
      )}
    >
      <div className="flex h-full items-center justify-between px-4">
        <div className="flex items-center gap-4">
          {showSidebarToggle && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
              className="md:hidden"
            >
              {sidebarOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </Button>
          )}
          {children}
        </div>
      </div>
    </header>
  );
}

export const LayoutHeader = withComponentRegistration(LayoutHeaderImpl, {
  name: 'LayoutHeader',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Application header with optional sidebar toggle',
});

// Sidebar Component
interface LayoutSidebarProps {
  children: React.ReactNode;
  className?: string;
  width?: string;
  collapsedWidth?: string;
  collapsible?: boolean;
  overlay?: boolean;
}

function LayoutSidebarImpl({ 
  children, 
  className,
  width = 'w-64',
  collapsedWidth = 'w-16',
  collapsible = true,
  overlay = false
}: LayoutSidebarProps) {
  const { 
    sidebarOpen, 
    setSidebarOpen, 
    sidebarCollapsed, 
    setSidebarCollapsed, 
    isMobile 
  } = useLayout();

  const toggleCollapsed = useCallback(() => {
    setSidebarCollapsed(!sidebarCollapsed);
  }, [sidebarCollapsed, setSidebarCollapsed]);

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
  }, [setSidebarOpen]);

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'bg-card border-r transition-all duration-300 ease-in-out',
          // Mobile styles
          isMobile && [
            'fixed left-0 top-0 z-50 h-full',
            sidebarOpen ? width : '-translate-x-full',
          ],
          // Desktop styles
          !isMobile && [
            'relative flex-shrink-0',
            sidebarCollapsed && collapsible ? collapsedWidth : width,
          ],
          className
        )}
      >
        <div className="flex h-full flex-col">
          {/* Sidebar header with collapse toggle */}
          {collapsible && !isMobile && (
            <div className="flex h-16 items-center justify-end border-b px-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleCollapsed}
                aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                <ChevronLeft 
                  className={clsx(
                    'h-5 w-5 transition-transform',
                    sidebarCollapsed ? 'rotate-180' : ''
                  )} 
                />
              </Button>
            </div>
          )}

          {/* Sidebar content */}
          <div className="flex-1 overflow-y-auto p-4">
            {children}
          </div>
        </div>
      </aside>
    </>
  );
}

export const LayoutSidebar = withComponentRegistration(LayoutSidebarImpl, {
  name: 'LayoutSidebar',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Collapsible sidebar with responsive behavior',
});

// Main Content Area
interface LayoutMainProps {
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
}

function LayoutMainImpl({ 
  children, 
  className,
  padding = true 
}: LayoutMainProps) {
  return (
    <main 
      className={clsx(
        'flex-1 overflow-y-auto',
        padding && 'p-6',
        className
      )}
    >
      {children}
    </main>
  );
}

export const LayoutMain = withComponentRegistration(LayoutMainImpl, {
  name: 'LayoutMain',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Main content area with optional padding',
});

// Footer Component
interface LayoutFooterProps {
  children: React.ReactNode;
  className?: string;
  sticky?: boolean;
}

function LayoutFooterImpl({ 
  children, 
  className,
  sticky = false 
}: LayoutFooterProps) {
  return (
    <footer 
      className={clsx(
        'border-t bg-background',
        sticky && 'sticky bottom-0',
        className
      )}
    >
      <div className="p-4">
        {children}
      </div>
    </footer>
  );
}

export const LayoutFooter = withComponentRegistration(LayoutFooterImpl, {
  name: 'LayoutFooter',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Application footer with optional sticky positioning',
});

// Content Container
interface LayoutContainerProps {
  children: React.ReactNode;
  className?: string;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full' | 'none';
  centered?: boolean;
}

function LayoutContainerImpl({ 
  children, 
  className,
  maxWidth = 'none',
  centered = true 
}: LayoutContainerProps) {
  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    full: 'max-w-full',
    none: '',
  };

  return (
    <div 
      className={clsx(
        'w-full',
        maxWidth !== 'none' && maxWidthClasses[maxWidth],
        centered && 'mx-auto',
        className
      )}
    >
      {children}
    </div>
  );
}

export const LayoutContainer = withComponentRegistration(LayoutContainerImpl, {
  name: 'LayoutContainer',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Content container with responsive max-width',
});

// Grid Layout
interface LayoutGridProps {
  children: React.ReactNode;
  className?: string;
  cols?: 1 | 2 | 3 | 4 | 6 | 12;
  gap?: number;
  responsive?: {
    sm?: 1 | 2 | 3 | 4 | 6 | 12;
    md?: 1 | 2 | 3 | 4 | 6 | 12;
    lg?: 1 | 2 | 3 | 4 | 6 | 12;
    xl?: 1 | 2 | 3 | 4 | 6 | 12;
  };
}

function LayoutGridImpl({ 
  children, 
  className,
  cols = 1,
  gap = 4,
  responsive = {} 
}: LayoutGridProps) {
  const colsClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    6: 'grid-cols-6',
    12: 'grid-cols-12',
  };

  const responsiveClasses = {
    sm: {
      1: 'sm:grid-cols-1',
      2: 'sm:grid-cols-2',
      3: 'sm:grid-cols-3',
      4: 'sm:grid-cols-4',
      6: 'sm:grid-cols-6',
      12: 'sm:grid-cols-12',
    },
    md: {
      1: 'md:grid-cols-1',
      2: 'md:grid-cols-2',
      3: 'md:grid-cols-3',
      4: 'md:grid-cols-4',
      6: 'md:grid-cols-6',
      12: 'md:grid-cols-12',
    },
    lg: {
      1: 'lg:grid-cols-1',
      2: 'lg:grid-cols-2',
      3: 'lg:grid-cols-3',
      4: 'lg:grid-cols-4',
      6: 'lg:grid-cols-6',
      12: 'lg:grid-cols-12',
    },
    xl: {
      1: 'xl:grid-cols-1',
      2: 'xl:grid-cols-2',
      3: 'xl:grid-cols-3',
      4: 'xl:grid-cols-4',
      6: 'xl:grid-cols-6',
      12: 'xl:grid-cols-12',
    },
  };

  return (
    <div 
      className={clsx(
        'grid',
        colsClasses[cols],
        `gap-${gap}`,
        responsive.sm && responsiveClasses.sm[responsive.sm],
        responsive.md && responsiveClasses.md[responsive.md],
        responsive.lg && responsiveClasses.lg[responsive.lg],
        responsive.xl && responsiveClasses.xl[responsive.xl],
        className
      )}
    >
      {children}
    </div>
  );
}

export const LayoutGrid = withComponentRegistration(LayoutGridImpl, {
  name: 'LayoutGrid',
  category: 'layout',
  portal: 'shared',
  version: '1.0.0',
  description: 'Responsive grid layout component',
});

// Complete Application Layout
interface AppLayoutProps {
  children: React.ReactNode;
  header?: React.ReactNode;
  sidebar?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  sidebarProps?: Partial<LayoutSidebarProps>;
  headerProps?: Partial<LayoutHeaderProps>;
  mainProps?: Partial<LayoutMainProps>;
  footerProps?: Partial<LayoutFooterProps>;
}

function AppLayoutImpl({ 
  children,
  header,
  sidebar,
  footer,
  className,
  sidebarProps = {},
  headerProps = {},
  mainProps = {},
  footerProps = {},
}: AppLayoutProps) {
  return (
    <LayoutProvider>
      <LayoutRoot className={className}>
        {sidebar && (
          <LayoutSidebar {...sidebarProps}>
            {sidebar}
          </LayoutSidebar>
        )}
        
        <div className="flex flex-1 flex-col">
          {header && (
            <LayoutHeader showSidebarToggle={!!sidebar} {...headerProps}>
              {header}
            </LayoutHeader>
          )}
          
          <LayoutMain {...mainProps}>
            {children}
          </LayoutMain>
          
          {footer && (
            <LayoutFooter {...footerProps}>
              {footer}
            </LayoutFooter>
          )}
        </div>
      </LayoutRoot>
    </LayoutProvider>
  );
}

export const AppLayout = withComponentRegistration(AppLayoutImpl, {
  name: 'AppLayout',
  category: 'template',
  portal: 'shared',
  version: '1.0.0',
  description: 'Complete application layout with header, sidebar, main, and footer',
});

// Layout hook is already exported above
