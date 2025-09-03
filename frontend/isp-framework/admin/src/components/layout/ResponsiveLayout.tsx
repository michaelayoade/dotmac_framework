/**
 * Responsive Layout Components
 * Mobile-first responsive layouts with breakpoint management
 */

'use client';

import React, { ReactNode, useState, useEffect } from 'react';
import { Menu, X, ChevronLeft } from 'lucide-react';
import { cn, layoutUtils, responsiveUtils } from '../../design-system/utils';

// Breakpoint hook
export function useBreakpoint() {
  const [breakpoint, setBreakpoint] = useState<'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl'>('md');
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  const [isDesktop, setIsDesktop] = useState(true);

  useEffect(() => {
    const updateBreakpoint = () => {
      const width = window.innerWidth;

      if (width < 640) {
        setBreakpoint('xs');
        setIsMobile(true);
        setIsTablet(false);
        setIsDesktop(false);
      } else if (width < 768) {
        setBreakpoint('sm');
        setIsMobile(true);
        setIsTablet(false);
        setIsDesktop(false);
      } else if (width < 1024) {
        setBreakpoint('md');
        setIsMobile(false);
        setIsTablet(true);
        setIsDesktop(false);
      } else if (width < 1280) {
        setBreakpoint('lg');
        setIsMobile(false);
        setIsTablet(false);
        setIsDesktop(true);
      } else if (width < 1536) {
        setBreakpoint('xl');
        setIsMobile(false);
        setIsTablet(false);
        setIsDesktop(true);
      } else {
        setBreakpoint('2xl');
        setIsMobile(false);
        setIsTablet(false);
        setIsDesktop(true);
      }
    };

    updateBreakpoint();
    window.addEventListener('resize', updateBreakpoint);
    return () => window.removeEventListener('resize', updateBreakpoint);
  }, []);

  return {
    breakpoint,
    isMobile,
    isTablet,
    isDesktop,
    isSmallScreen: isMobile || isTablet,
  };
}

// Container Component
interface ContainerProps {
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl' | '6xl' | '7xl' | 'full';
  className?: string;
  fluid?: boolean;
}

export function Container({
  children,
  size = '7xl',
  className = '',
  fluid = false,
}: ContainerProps) {
  if (fluid) {
    return <div className={cn('w-full px-4 sm:px-6 lg:px-8', className)}>{children}</div>;
  }

  return <div className={cn(layoutUtils.container[size], className)}>{children}</div>;
}

// Grid System
interface GridProps {
  children: ReactNode;
  cols?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  gap?: 1 | 2 | 3 | 4 | 5 | 6 | 8;
  className?: string;
  responsive?: {
    sm?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
    md?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
    lg?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
    xl?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  };
}

export function Grid({ children, cols = 1, gap = 4, className = '', responsive }: GridProps) {
  const baseClass = `grid-cols-${cols}`;
  const gapClass = `gap-${gap}`;

  const responsiveClasses = responsive
    ? [
        responsive.sm && `sm:grid-cols-${responsive.sm}`,
        responsive.md && `md:grid-cols-${responsive.md}`,
        responsive.lg && `lg:grid-cols-${responsive.lg}`,
        responsive.xl && `xl:grid-cols-${responsive.xl}`,
      ]
        .filter(Boolean)
        .join(' ')
    : '';

  return (
    <div className={cn('grid', baseClass, gapClass, responsiveClasses, className)}>{children}</div>
  );
}

interface GridItemProps {
  children: ReactNode;
  span?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  className?: string;
  responsive?: {
    sm?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
    md?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
    lg?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
    xl?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  };
}

export function GridItem({ children, span = 1, className = '', responsive }: GridItemProps) {
  const baseClass = `col-span-${span}`;

  const responsiveClasses = responsive
    ? [
        responsive.sm && `sm:col-span-${responsive.sm}`,
        responsive.md && `md:col-span-${responsive.md}`,
        responsive.lg && `lg:col-span-${responsive.lg}`,
        responsive.xl && `xl:col-span-${responsive.xl}`,
      ]
        .filter(Boolean)
        .join(' ')
    : '';

  return <div className={cn(baseClass, responsiveClasses, className)}>{children}</div>;
}

// Flex Components
interface FlexProps {
  children: ReactNode;
  direction?: 'row' | 'col' | 'row-reverse' | 'col-reverse';
  justify?: 'start' | 'end' | 'center' | 'between' | 'around' | 'evenly';
  align?: 'start' | 'end' | 'center' | 'stretch' | 'baseline';
  wrap?: boolean;
  gap?: 1 | 2 | 3 | 4 | 5 | 6 | 8;
  className?: string;
  responsive?: {
    sm?: Partial<Pick<FlexProps, 'direction' | 'justify' | 'align'>>;
    md?: Partial<Pick<FlexProps, 'direction' | 'justify' | 'align'>>;
    lg?: Partial<Pick<FlexProps, 'direction' | 'justify' | 'align'>>;
  };
}

export function Flex({
  children,
  direction = 'row',
  justify = 'start',
  align = 'start',
  wrap = false,
  gap = 0,
  className = '',
  responsive,
}: FlexProps) {
  const baseClasses = [
    'flex',
    `flex-${direction}`,
    `justify-${justify}`,
    `items-${align}`,
    wrap && 'flex-wrap',
    gap > 0 && `gap-${gap}`,
  ].filter(Boolean);

  const responsiveClasses = responsive
    ? [
        responsive.sm?.direction && `sm:flex-${responsive.sm.direction}`,
        responsive.sm?.justify && `sm:justify-${responsive.sm.justify}`,
        responsive.sm?.align && `sm:items-${responsive.sm.align}`,
        responsive.md?.direction && `md:flex-${responsive.md.direction}`,
        responsive.md?.justify && `md:justify-${responsive.md.justify}`,
        responsive.md?.align && `md:items-${responsive.md.align}`,
        responsive.lg?.direction && `lg:flex-${responsive.lg.direction}`,
        responsive.lg?.justify && `lg:justify-${responsive.lg.justify}`,
        responsive.lg?.align && `lg:items-${responsive.lg.align}`,
      ].filter(Boolean)
    : [];

  return <div className={cn(baseClasses, responsiveClasses, className)}>{children}</div>;
}

// Stack Component (Vertical spacing)
interface StackProps {
  children: ReactNode;
  spacing?: 1 | 2 | 3 | 4 | 5 | 6 | 8;
  className?: string;
}

export function Stack({ children, spacing = 4, className = '' }: StackProps) {
  return <div className={cn(`space-y-${spacing}`, className)}>{children}</div>;
}

// Mobile Navigation
interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  className?: string;
}

export function MobileNav({ isOpen, onClose, children, title, className = '' }: MobileNavProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className='fixed inset-0 bg-black/50 z-40 lg:hidden' onClick={onClose} />

      {/* Sidebar */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 w-64 bg-white shadow-xl z-50 lg:hidden transform transition-transform duration-300',
          isOpen ? 'translate-x-0' : '-translate-x-full',
          className
        )}
      >
        {/* Header */}
        <div className='flex items-center justify-between p-4 border-b border-gray-200'>
          {title && <h2 className='font-semibold text-gray-900'>{title}</h2>}
          <button
            onClick={onClose}
            className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg'
          >
            <X className='w-5 h-5' />
          </button>
        </div>

        {/* Content */}
        <div className='flex-1 overflow-y-auto p-4'>{children}</div>
      </div>
    </>
  );
}

// Mobile Header
interface MobileHeaderProps {
  title: string;
  onMenuClick?: () => void;
  onBackClick?: () => void;
  rightContent?: ReactNode;
  className?: string;
  showBack?: boolean;
  showMenu?: boolean;
}

export function MobileHeader({
  title,
  onMenuClick,
  onBackClick,
  rightContent,
  className = '',
  showBack = false,
  showMenu = true,
}: MobileHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between p-4 bg-white border-b border-gray-200 lg:hidden',
        className
      )}
    >
      <div className='flex items-center gap-2'>
        {showBack && onBackClick && (
          <button
            onClick={onBackClick}
            className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg'
          >
            <ChevronLeft className='w-5 h-5' />
          </button>
        )}

        {showMenu && onMenuClick && !showBack && (
          <button
            onClick={onMenuClick}
            className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg'
          >
            <Menu className='w-5 h-5' />
          </button>
        )}

        <h1 className='text-lg font-semibold text-gray-900 truncate'>{title}</h1>
      </div>

      {rightContent && <div className='flex items-center gap-2'>{rightContent}</div>}
    </div>
  );
}

// Responsive Show/Hide Components
interface ResponsiveShowProps {
  children: ReactNode;
  on?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export function ShowOnMobile({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn('block lg:hidden', className)}>{children}</div>;
}

export function HideOnMobile({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn('hidden lg:block', className)}>{children}</div>;
}

export function ShowOnTablet({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn('hidden md:block lg:hidden', className)}>{children}</div>;
}

export function ShowOnDesktop({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn('hidden lg:block', className)}>{children}</div>;
}

// Responsive Text
interface ResponsiveTextProps {
  children: ReactNode;
  size?: {
    base: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
    sm?: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
    md?: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
    lg?: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
  };
  weight?: 'normal' | 'medium' | 'semibold' | 'bold';
  className?: string;
}

export function ResponsiveText({
  children,
  size = { base: 'base' },
  weight = 'normal',
  className = '',
}: ResponsiveTextProps) {
  const sizeClasses = [
    `text-${size.base}`,
    size.sm && `sm:text-${size.sm}`,
    size.md && `md:text-${size.md}`,
    size.lg && `lg:text-${size.lg}`,
  ].filter(Boolean);

  const weightClass = `font-${weight}`;

  return <div className={cn(sizeClasses, weightClass, className)}>{children}</div>;
}

// Responsive Cards
interface ResponsiveCardProps {
  children: ReactNode;
  className?: string;
  padding?: {
    base: 'sm' | 'md' | 'lg';
    lg?: 'sm' | 'md' | 'lg';
  };
}

export function ResponsiveCard({
  children,
  className = '',
  padding = { base: 'md' },
}: ResponsiveCardProps) {
  const paddingClasses = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const basePadding = paddingClasses[padding.base];
  const lgPadding = padding.lg ? paddingClasses[padding.lg] : '';

  return (
    <div
      className={cn(
        'bg-white rounded-lg border shadow-sm',
        basePadding,
        lgPadding && `lg:${lgPadding}`,
        className
      )}
    >
      {children}
    </div>
  );
}

// App Shell Layout
interface AppShellProps {
  children: ReactNode;
  sidebar?: ReactNode;
  header?: ReactNode;
  mobileHeader?: ReactNode;
  className?: string;
  sidebarWidth?: 'sm' | 'md' | 'lg';
}

export function AppShell({
  children,
  sidebar,
  header,
  mobileHeader,
  className = '',
  sidebarWidth = 'md',
}: AppShellProps) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const { isMobile } = useBreakpoint();

  const sidebarWidths = {
    sm: 'w-56',
    md: 'w-64',
    lg: 'w-72',
  };

  return (
    <div className={cn('min-h-screen bg-gray-50', className)}>
      {/* Desktop Header */}
      {header && <HideOnMobile>{header}</HideOnMobile>}

      {/* Mobile Header */}
      {mobileHeader && <ShowOnMobile>{mobileHeader}</ShowOnMobile>}

      <div className='flex'>
        {/* Desktop Sidebar */}
        {sidebar && (
          <HideOnMobile>
            <div
              className={cn(
                'fixed inset-y-0 left-0 bg-white border-r border-gray-200',
                sidebarWidths[sidebarWidth],
                header && 'top-16' // Adjust if there's a header
              )}
            >
              {sidebar}
            </div>
          </HideOnMobile>
        )}

        {/* Mobile Sidebar */}
        {sidebar && (
          <MobileNav
            isOpen={isMobileNavOpen}
            onClose={() => setIsMobileNavOpen(false)}
            title='Menu'
          >
            {sidebar}
          </MobileNav>
        )}

        {/* Main Content */}
        <main
          className={cn(
            'flex-1',
            sidebar &&
              !isMobile &&
              sidebarWidths[sidebarWidth] &&
              `ml-${sidebarWidths[sidebarWidth].split('-')[1]}`,
            header && !isMobile && 'pt-16' // Adjust if there's a header
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
