/**
 * Responsive Breakpoint Management System
 * 
 * Provides utilities for responsive design, breakpoint detection,
 * and device-specific adaptations for the ISP management platform
 */

import { themes } from '../tokens/design-tokens';

export type BreakpointKey = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface BreakpointConfig {
  key: BreakpointKey;
  minWidth: number;
  maxWidth?: number;
  name: string;
  description: string;
}

export interface ResponsiveValue<T> {
  xs?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  '2xl'?: T;
  default?: T;
}

export interface DeviceInfo {
  breakpoint: BreakpointKey;
  width: number;
  height: number;
  orientation: 'portrait' | 'landscape';
  devicePixelRatio: number;
  touchDevice: boolean;
  mobile: boolean;
  tablet: boolean;
  desktop: boolean;
}

class BreakpointManager {
  private breakpoints: BreakpointConfig[];
  private currentBreakpoint: BreakpointKey = 'md';
  private listeners: ((breakpoint: BreakpointKey, deviceInfo: DeviceInfo) => void)[] = [];
  private mediaQueryLists: Map<BreakpointKey, MediaQueryList> = new Map();
  private resizeObserver?: ResizeObserver;
  private initialized = false;

  constructor() {
    this.breakpoints = this.parseBreakpoints();
    
    if (typeof window !== 'undefined') {
      this.initialize();
    }
  }

  private parseBreakpoints(): BreakpointConfig[] {
    const tokenBreakpoints = themes.light.breakpoints;
    
    return [
      {
        key: 'xs',
        minWidth: 0,
        maxWidth: parseInt(tokenBreakpoints.sm) - 1,
        name: 'Extra Small',
        description: 'Mobile phones (portrait)',
      },
      {
        key: 'sm',
        minWidth: parseInt(tokenBreakpoints.sm),
        maxWidth: parseInt(tokenBreakpoints.md) - 1,
        name: 'Small',
        description: 'Mobile phones (landscape), small tablets',
      },
      {
        key: 'md',
        minWidth: parseInt(tokenBreakpoints.md),
        maxWidth: parseInt(tokenBreakpoints.lg) - 1,
        name: 'Medium',
        description: 'Tablets (portrait)',
      },
      {
        key: 'lg',
        minWidth: parseInt(tokenBreakpoints.lg),
        maxWidth: parseInt(tokenBreakpoints.xl) - 1,
        name: 'Large',
        description: 'Tablets (landscape), small desktops',
      },
      {
        key: 'xl',
        minWidth: parseInt(tokenBreakpoints.xl),
        maxWidth: parseInt(tokenBreakpoints['2xl']) - 1,
        name: 'Extra Large',
        description: 'Desktops',
      },
      {
        key: '2xl',
        minWidth: parseInt(tokenBreakpoints['2xl']),
        name: '2X Large',
        description: 'Large desktops, ultra-wide monitors',
      },
    ];
  }

  private initialize() {
    if (this.initialized) return;

    // Setup media query listeners
    this.setupMediaQueryListeners();
    
    // Setup resize observer for precise breakpoint detection
    this.setupResizeObserver();
    
    // Initial breakpoint detection
    this.detectBreakpoint();
    
    this.initialized = true;
  }

  private setupMediaQueryListeners() {
    this.breakpoints.forEach(bp => {
      const mediaQuery = this.createMediaQuery(bp);
      const mql = window.matchMedia(mediaQuery);
      
      this.mediaQueryLists.set(bp.key, mql);
      
      mql.addListener(() => {
        this.detectBreakpoint();
      });
    });
  }

  private setupResizeObserver() {
    if (!window.ResizeObserver) return;

    this.resizeObserver = new ResizeObserver(() => {
      this.detectBreakpoint();
    });

    this.resizeObserver.observe(document.documentElement);
  }

  private createMediaQuery(breakpoint: BreakpointConfig): string {
    if (breakpoint.maxWidth) {
      return `(min-width: ${breakpoint.minWidth}px) and (max-width: ${breakpoint.maxWidth}px)`;
    } else {
      return `(min-width: ${breakpoint.minWidth}px)`;
    }
  }

  private detectBreakpoint() {
    const width = window.innerWidth;
    const newBreakpoint = this.getBreakpointFromWidth(width);
    
    if (newBreakpoint !== this.currentBreakpoint) {
      this.currentBreakpoint = newBreakpoint;
      this.notifyListeners();
    }
  }

  private getBreakpointFromWidth(width: number): BreakpointKey {
    // Find the largest breakpoint that the width satisfies
    for (let i = this.breakpoints.length - 1; i >= 0; i--) {
      const bp = this.breakpoints[i];
      if (width >= bp.minWidth) {
        return bp.key;
      }
    }
    return 'xs';
  }

  private notifyListeners() {
    const deviceInfo = this.getDeviceInfo();
    this.listeners.forEach(listener => {
      listener(this.currentBreakpoint, deviceInfo);
    });
  }

  // Public API
  getCurrentBreakpoint(): BreakpointKey {
    return this.currentBreakpoint;
  }

  getDeviceInfo(): DeviceInfo {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    return {
      breakpoint: this.currentBreakpoint,
      width,
      height,
      orientation: width > height ? 'landscape' : 'portrait',
      devicePixelRatio: window.devicePixelRatio || 1,
      touchDevice: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
      mobile: this.currentBreakpoint === 'xs' || this.currentBreakpoint === 'sm',
      tablet: this.currentBreakpoint === 'md' || (this.currentBreakpoint === 'lg' && 'ontouchstart' in window),
      desktop: this.currentBreakpoint === 'lg' || this.currentBreakpoint === 'xl' || this.currentBreakpoint === '2xl',
    };
  }

  isBreakpoint(breakpoint: BreakpointKey): boolean {
    return this.currentBreakpoint === breakpoint;
  }

  isBreakpointUp(breakpoint: BreakpointKey): boolean {
    const currentIndex = this.breakpoints.findIndex(bp => bp.key === this.currentBreakpoint);
    const targetIndex = this.breakpoints.findIndex(bp => bp.key === breakpoint);
    return currentIndex >= targetIndex;
  }

  isBreakpointDown(breakpoint: BreakpointKey): boolean {
    const currentIndex = this.breakpoints.findIndex(bp => bp.key === this.currentBreakpoint);
    const targetIndex = this.breakpoints.findIndex(bp => bp.key === breakpoint);
    return currentIndex <= targetIndex;
  }

  onBreakpointChange(listener: (breakpoint: BreakpointKey, deviceInfo: DeviceInfo) => void): () => void {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  getBreakpointConfig(breakpoint: BreakpointKey): BreakpointConfig | undefined {
    return this.breakpoints.find(bp => bp.key === breakpoint);
  }

  getAllBreakpoints(): BreakpointConfig[] {
    return [...this.breakpoints];
  }

  // Responsive value resolver
  resolveResponsiveValue<T>(responsiveValue: ResponsiveValue<T>): T | undefined {
    // Start from current breakpoint and work down to find a value
    const currentIndex = this.breakpoints.findIndex(bp => bp.key === this.currentBreakpoint);
    
    for (let i = currentIndex; i >= 0; i--) {
      const bp = this.breakpoints[i];
      const value = responsiveValue[bp.key];
      if (value !== undefined) {
        return value;
      }
    }

    // Fallback to default or undefined
    return responsiveValue.default;
  }

  // CSS utilities
  generateResponsiveCSS<T>(
    property: string,
    responsiveValue: ResponsiveValue<T>,
    valueTransform?: (value: T) => string
  ): string {
    let css = '';
    
    this.breakpoints.forEach(bp => {
      const value = responsiveValue[bp.key];
      if (value !== undefined) {
        const transformedValue = valueTransform ? valueTransform(value) : String(value);
        
        if (bp.minWidth === 0) {
          // Base styles (no media query needed)
          css += `${property}: ${transformedValue};\n`;
        } else {
          // Media query styles
          css += `@media (min-width: ${bp.minWidth}px) {\n`;
          css += `  ${property}: ${transformedValue};\n`;
          css += `}\n`;
        }
      }
    });

    return css;
  }

  // Container query support (experimental)
  supportsContainerQueries(): boolean {
    return CSS.supports('container-type: inline-size');
  }

  // Utility methods for common responsive patterns
  isMobile(): boolean {
    return this.getDeviceInfo().mobile;
  }

  isTablet(): boolean {
    return this.getDeviceInfo().tablet;
  }

  isDesktop(): boolean {
    return this.getDeviceInfo().desktop;
  }

  isTouchDevice(): boolean {
    return this.getDeviceInfo().touchDevice;
  }

  getOptimalImageSize(): { width: number; height?: number } {
    const deviceInfo = this.getDeviceInfo();
    const { width, devicePixelRatio } = deviceInfo;
    
    // Return image dimensions based on screen size and pixel density
    if (deviceInfo.mobile) {
      return { width: Math.min(width * devicePixelRatio, 800) };
    } else if (deviceInfo.tablet) {
      return { width: Math.min(width * devicePixelRatio, 1200) };
    } else {
      return { width: Math.min(width * devicePixelRatio, 1920) };
    }
  }

  // ISP-specific responsive utilities
  getOptimalDashboardLayout(): 'mobile' | 'tablet' | 'desktop' | 'wide' {
    const bp = this.getCurrentBreakpoint();
    
    switch (bp) {
      case 'xs':
      case 'sm':
        return 'mobile';
      case 'md':
        return 'tablet';
      case 'lg':
      case 'xl':
        return 'desktop';
      case '2xl':
        return 'wide';
      default:
        return 'desktop';
    }
  }

  getDataTableDisplayMode(): 'cards' | 'horizontal-scroll' | 'full-table' {
    const deviceInfo = this.getDeviceInfo();
    
    if (deviceInfo.mobile) {
      return 'cards';
    } else if (deviceInfo.tablet) {
      return 'horizontal-scroll';
    } else {
      return 'full-table';
    }
  }

  getNetworkTopologyViewport(): { width: number; height: number } {
    const { width, height } = this.getDeviceInfo();
    
    // Reserve space for UI chrome based on device type
    if (this.isMobile()) {
      return { width: width - 32, height: height - 200 }; // Account for mobile navigation
    } else if (this.isTablet()) {
      return { width: width - 64, height: height - 120 }; // Account for tablet navigation
    } else {
      return { width: width - 300, height: height - 80 }; // Account for desktop sidebar
    }
  }

  destroy() {
    // Clean up media query listeners
    this.mediaQueryLists.forEach(mql => {
      mql.removeListener(() => this.detectBreakpoint());
    });
    this.mediaQueryLists.clear();

    // Clean up resize observer
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }

    // Clear listeners
    this.listeners = [];
    this.initialized = false;
  }
}

// Global breakpoint manager instance
export const breakpointManager = new BreakpointManager();

// React hook for responsive behavior
export function useResponsive() {
  const [breakpoint, setBreakpoint] = React.useState<BreakpointKey>(
    breakpointManager.getCurrentBreakpoint()
  );
  const [deviceInfo, setDeviceInfo] = React.useState<DeviceInfo>(
    breakpointManager.getDeviceInfo()
  );

  React.useEffect(() => {
    const unsubscribe = breakpointManager.onBreakpointChange((bp, info) => {
      setBreakpoint(bp);
      setDeviceInfo(info);
    });

    return unsubscribe;
  }, []);

  return {
    breakpoint,
    deviceInfo,
    isMobile: deviceInfo.mobile,
    isTablet: deviceInfo.tablet,
    isDesktop: deviceInfo.desktop,
    isTouchDevice: deviceInfo.touchDevice,
    isBreakpoint: (bp: BreakpointKey) => breakpoint === bp,
    isBreakpointUp: (bp: BreakpointKey) => breakpointManager.isBreakpointUp(bp),
    isBreakpointDown: (bp: BreakpointKey) => breakpointManager.isBreakpointDown(bp),
    resolveResponsiveValue: <T>(value: ResponsiveValue<T>) => 
      breakpointManager.resolveResponsiveValue(value),
  };
}

// Utility functions
export function createResponsiveValue<T>(values: Partial<ResponsiveValue<T>>): ResponsiveValue<T> {
  return values;
}

export function isServer(): boolean {
  return typeof window === 'undefined';
}

// CSS-in-JS helpers
export function media(breakpoint: BreakpointKey): string {
  const bp = breakpointManager.getBreakpointConfig(breakpoint);
  if (!bp) return '';
  
  return `@media (min-width: ${bp.minWidth}px)`;
}

export function mediaDown(breakpoint: BreakpointKey): string {
  const bp = breakpointManager.getBreakpointConfig(breakpoint);
  if (!bp || !bp.maxWidth) return '';
  
  return `@media (max-width: ${bp.maxWidth}px)`;
}

export function mediaBetween(min: BreakpointKey, max: BreakpointKey): string {
  const minBp = breakpointManager.getBreakpointConfig(min);
  const maxBp = breakpointManager.getBreakpointConfig(max);
  
  if (!minBp || !maxBp || !maxBp.maxWidth) return '';
  
  return `@media (min-width: ${minBp.minWidth}px) and (max-width: ${maxBp.maxWidth}px)`;
}

export default BreakpointManager;