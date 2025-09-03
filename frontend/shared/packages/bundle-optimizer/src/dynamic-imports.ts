/**
 * Dynamic Import Optimization
 * Advanced lazy loading and code splitting strategies
 */

import React from 'react';

export interface DynamicImportConfig {
  components: ComponentImportConfig[];
  routes: RouteImportConfig[];
  libraries: LibraryImportConfig[];
  preloadStrategy: PreloadStrategy;
}

export interface ComponentImportConfig {
  name: string;
  path: string;
  preload: 'critical' | 'interaction' | 'viewport' | 'idle' | 'never';
  fallback?: React.ComponentType;
  errorBoundary?: React.ComponentType<{ error: Error; retry: () => void }>;
  chunkName?: string;
  dependencies?: string[];
}

export interface RouteImportConfig {
  path: string;
  component: string;
  preload?: boolean;
  prefetch?: boolean;
  priority: 'high' | 'normal' | 'low';
}

export interface LibraryImportConfig {
  name: string;
  imports: string[];
  condition?: 'interaction' | 'feature-flag' | 'runtime';
  fallback?: any;
}

export type PreloadStrategy = 'aggressive' | 'conservative' | 'adaptive';

/**
 * Create optimized dynamic import for components
 */
export const createDynamicComponent = (config: ComponentImportConfig) => {
  const LazyComponent = React.lazy(() => {
    const importPromise = import(
      /* webpackChunkName: "[request]" */
      /* webpackPrefetch: true */
      config.path
    );
    
    // Add error handling
    return importPromise.catch(error => {
      console.error(`Failed to load component ${config.name}:`, error);
      // Return fallback or empty component
      return { 
        default: config.fallback || (() => React.createElement('div', { 
          children: `Error loading ${config.name}` 
        }))
      };
    });
  });
  
  // Add display name for debugging
  LazyComponent.displayName = `Dynamic(${config.name})`;
  
  return LazyComponent;
};

/**
 * Create component with advanced loading strategies
 */
export const createAdvancedDynamicComponent = (config: ComponentImportConfig) => {
  const LazyComponent = React.lazy(() => {
    // Implement preload strategy
    switch (config.preload) {
      case 'critical':
        // Load immediately
        return import(/* webpackChunkName: "[request]-critical" */ config.path);
      
      case 'interaction':
        // Load on first user interaction
        return new Promise((resolve) => {
          const loadComponent = () => {
            import(/* webpackChunkName: "[request]-interaction" */ config.path)
              .then(resolve)
              .catch(resolve);
          };
          
          // Listen for first interaction
          const events = ['mousedown', 'touchstart', 'keydown'];
          const listener = () => {
            events.forEach(event => document.removeEventListener(event, listener));
            loadComponent();
          };
          
          events.forEach(event => document.addEventListener(event, listener, { once: true }));
          
          // Fallback: load after 5 seconds
          setTimeout(loadComponent, 5000);
        });
      
      case 'viewport':
        // Load when component enters viewport
        return new Promise((resolve) => {
          const loadComponent = () => {
            import(/* webpackChunkName: "[request]-viewport" */ config.path)
              .then(resolve)
              .catch(resolve);
          };
          
          // Use Intersection Observer
          if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
              entries.forEach(entry => {
                if (entry.isIntersecting) {
                  observer.disconnect();
                  loadComponent();
                }
              });
            });
            
            // Observe placeholder element
            const placeholder = document.querySelector(`[data-dynamic="${config.name}"]`);
            if (placeholder) {
              observer.observe(placeholder);
            } else {
              // Fallback if no placeholder found
              setTimeout(loadComponent, 1000);
            }
          } else {
            // Fallback for browsers without Intersection Observer
            setTimeout(loadComponent, 1000);
          }
        });
      
      case 'idle':
        // Load when browser is idle
        return new Promise((resolve) => {
          const loadComponent = () => {
            import(/* webpackChunkName: "[request]-idle" */ config.path)
              .then(resolve)
              .catch(resolve);
          };
          
          if ('requestIdleCallback' in window) {
            (window as any).requestIdleCallback(loadComponent);
          } else {
            setTimeout(loadComponent, 0);
          }
        });
      
      default:
        // Load normally
        return import(config.path);
    }
  });
  
  LazyComponent.displayName = `Advanced(${config.name})`;
  
  return LazyComponent;
};

/**
 * Higher-order component for dynamic loading with Suspense
 */
export const withDynamicLoading = (config: ComponentImportConfig) => {
  const DynamicComponent = createAdvancedDynamicComponent(config);
  
  return (props: any) => {
    const ErrorBoundary = config.errorBoundary || DefaultErrorBoundary;
    const LoadingFallback = config.fallback || DefaultLoadingFallback;
    
    return React.createElement(
      ErrorBoundary,
      { 
        fallback: ({ error, retry }: { error: Error; retry: () => void }) =>
          React.createElement('div', {
            children: [
              `Error loading ${config.name}: ${error.message}`,
              React.createElement('button', { onClick: retry }, 'Retry')
            ]
          })
      },
      React.createElement(
        React.Suspense,
        { fallback: React.createElement(LoadingFallback) },
        React.createElement(DynamicComponent, props)
      )
    );
  };
};

/**
 * Route-based dynamic imports
 */
export const createDynamicRoutes = (routes: RouteImportConfig[]) => {
  return routes.map(route => {
    const RouteComponent = React.lazy(() => {
      const importOptions: any = {};
      
      // Set webpack chunk name
      importOptions.webpackChunkName = `route-${route.path.replace(/\//g, '-')}`;
      
      // Set preload/prefetch hints
      if (route.preload) {
        importOptions.webpackPreload = true;
      }
      if (route.prefetch) {
        importOptions.webpackPrefetch = true;
      }
      
      // Set priority
      switch (route.priority) {
        case 'high':
          importOptions.webpackPriority = 'high';
          break;
        case 'low':
          importOptions.webpackPriority = 'low';
          break;
        default:
          importOptions.webpackPriority = 'normal';
      }
      
      return import(
        /* webpackChunkName: "[request]" */
        /* webpackMode: "lazy" */
        route.component
      );
    });
    
    return {
      path: route.path,
      component: RouteComponent,
      preload: route.preload,
      prefetch: route.prefetch,
    };
  });
};

/**
 * Library-based dynamic imports
 */
export const createDynamicLibraryImports = (libraries: LibraryImportConfig[]) => {
  const importedLibraries = new Map<string, any>();
  
  return libraries.reduce((acc, lib) => {
    const importLibrary = async () => {
      if (importedLibraries.has(lib.name)) {
        return importedLibraries.get(lib.name);
      }
      
      try {
        const library = await import(
          /* webpackChunkName: "[request]-lib" */
          lib.name
        );
        
        // Extract specific imports
        const exports = lib.imports.reduce((libExports, importName) => {
          libExports[importName] = library[importName] || library.default?.[importName];
          return libExports;
        }, {} as any);
        
        importedLibraries.set(lib.name, exports);
        return exports;
      } catch (error) {
        console.error(`Failed to load library ${lib.name}:`, error);
        return lib.fallback || {};
      }
    };
    
    acc[lib.name] = importLibrary;
    return acc;
  }, {} as Record<string, () => Promise<any>>);
};

/**
 * Preload manager for optimizing loading
 */
export class PreloadManager {
  private preloadPromises = new Map<string, Promise<any>>();
  private strategy: PreloadStrategy;
  
  constructor(strategy: PreloadStrategy = 'conservative') {
    this.strategy = strategy;
  }
  
  /**
   * Preload component based on strategy
   */
  preloadComponent(config: ComponentImportConfig): Promise<any> {
    const key = config.path;
    
    if (this.preloadPromises.has(key)) {
      return this.preloadPromises.get(key)!;
    }
    
    const shouldPreload = this.shouldPreload(config);
    
    if (!shouldPreload) {
      return Promise.resolve();
    }
    
    const preloadPromise = import(config.path).catch(error => {
      console.warn(`Preload failed for ${config.name}:`, error);
      return null;
    });
    
    this.preloadPromises.set(key, preloadPromise);
    return preloadPromise;
  }
  
  /**
   * Preload multiple components
   */
  preloadComponents(components: ComponentImportConfig[]): Promise<any[]> {
    return Promise.all(components.map(component => this.preloadComponent(component)));
  }
  
  /**
   * Determine if component should be preloaded
   */
  private shouldPreload(config: ComponentImportConfig): boolean {
    switch (this.strategy) {
      case 'aggressive':
        return config.preload !== 'never';
      
      case 'conservative':
        return config.preload === 'critical';
      
      case 'adaptive':
        // Preload based on connection and device capabilities
        const connection = (navigator as any).connection;
        const isSlowConnection = connection && 
          (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g');
        const isLowEndDevice = navigator.hardwareConcurrency && 
          navigator.hardwareConcurrency <= 2;
        
        if (isSlowConnection || isLowEndDevice) {
          return config.preload === 'critical';
        } else {
          return config.preload === 'critical' || config.preload === 'interaction';
        }
      
      default:
        return false;
    }
  }
  
  /**
   * Clear preload cache
   */
  clearCache(): void {
    this.preloadPromises.clear();
  }
  
  /**
   * Get preload statistics
   */
  getStats() {
    return {
      preloadedComponents: this.preloadPromises.size,
      strategy: this.strategy,
    };
  }
}

/**
 * Smart loading hook for components
 */
export const useSmartLoading = (components: ComponentImportConfig[]) => {
  const [loadedComponents, setLoadedComponents] = React.useState<Set<string>>(new Set());
  const [loadingComponents, setLoadingComponents] = React.useState<Set<string>>(new Set());
  const [errors, setErrors] = React.useState<Map<string, Error>>(new Map());
  
  const loadComponent = React.useCallback(async (componentName: string) => {
    const config = components.find(c => c.name === componentName);
    if (!config || loadedComponents.has(componentName) || loadingComponents.has(componentName)) {
      return;
    }
    
    setLoadingComponents(prev => new Set(prev.add(componentName)));
    
    try {
      await import(config.path);
      setLoadedComponents(prev => new Set(prev.add(componentName)));
      setErrors(prev => {
        const newErrors = new Map(prev);
        newErrors.delete(componentName);
        return newErrors;
      });
    } catch (error) {
      setErrors(prev => new Map(prev.set(componentName, error as Error)));
    } finally {
      setLoadingComponents(prev => {
        const newLoading = new Set(prev);
        newLoading.delete(componentName);
        return newLoading;
      });
    }
  }, [components, loadedComponents, loadingComponents]);
  
  const preloadComponent = React.useCallback((componentName: string) => {
    loadComponent(componentName);
  }, [loadComponent]);
  
  const isLoaded = React.useCallback((componentName: string) => {
    return loadedComponents.has(componentName);
  }, [loadedComponents]);
  
  const isLoading = React.useCallback((componentName: string) => {
    return loadingComponents.has(componentName);
  }, [loadingComponents]);
  
  const getError = React.useCallback((componentName: string) => {
    return errors.get(componentName);
  }, [errors]);
  
  return {
    loadComponent,
    preloadComponent,
    isLoaded,
    isLoading,
    getError,
    stats: {
      loaded: loadedComponents.size,
      loading: loadingComponents.size,
      errors: errors.size,
    },
  };
};

/**
 * Default error boundary for dynamic components
 */
const DefaultErrorBoundary: React.FC<{ 
  children: React.ReactNode; 
  fallback: (props: { error: Error; retry: () => void }) => React.ReactElement; 
}> = ({ children, fallback }) => {
  const [error, setError] = React.useState<Error | null>(null);
  
  React.useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      setError(new Error(event.message));
    };
    
    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, []);
  
  if (error) {
    return fallback({ error, retry: () => setError(null) });
  }
  
  return React.createElement(React.Fragment, {}, children);
};

/**
 * Default loading fallback
 */
const DefaultLoadingFallback: React.FC = () => {
  return React.createElement('div', {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    },
    children: 'Loading...',
  });
};