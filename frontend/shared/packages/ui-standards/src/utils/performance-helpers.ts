/**
 * Performance helper utilities for optimizing React applications
 */

// Resource Hints
export const preloadResource = (href: string, as: string, crossorigin?: string) => {
  if (typeof document === 'undefined') return;
  
  const link = document.createElement('link');
  link.rel = 'preload';
  link.href = href;
  link.as = as;
  if (crossorigin) link.crossOrigin = crossorigin;
  
  document.head.appendChild(link);
};

export const prefetchResource = (href: string) => {
  if (typeof document === 'undefined') return;
  
  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.href = href;
  
  document.head.appendChild(link);
};

// Image Optimization
export const lazyLoadImage = (
  img: HTMLImageElement,
  src: string,
  placeholder?: string
) => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const image = entry.target as HTMLImageElement;
        image.src = src;
        image.onload = () => {
          image.classList.add('loaded');
        };
        observer.unobserve(image);
      }
    });
  });

  if (placeholder) {
    img.src = placeholder;
  }
  observer.observe(img);
};

// Bundle Analysis Helpers
export const measureBundleSize = () => {
  if (typeof navigator === 'undefined' || !('connection' in navigator)) return;

  const connection = (navigator as any).connection;
  console.log(`Network: ${connection.effectiveType}, Downlink: ${connection.downlink}Mbps`);
  
  // Calculate transferred size estimation
  const resources = performance.getEntriesByType('resource');
  const jsResources = resources.filter(r => r.name.endsWith('.js'));
  const cssResources = resources.filter(r => r.name.endsWith('.css'));
  
  const totalJSSize = jsResources.reduce((sum, r) => sum + (r.transferSize || 0), 0);
  const totalCSSSize = cssResources.reduce((sum, r) => sum + (r.transferSize || 0), 0);
  
  console.log(`JS Bundle Size: ${(totalJSSize / 1024).toFixed(2)}KB`);
  console.log(`CSS Bundle Size: ${(totalCSSSize / 1024).toFixed(2)}KB`);
};

// Memory Usage Monitoring
export const monitorMemoryUsage = () => {
  if (typeof performance === 'undefined' || !('memory' in performance)) return null;

  const memory = (performance as any).memory;
  return {
    used: Math.round(memory.usedJSHeapSize / 1048576 * 100) / 100,
    total: Math.round(memory.totalJSHeapSize / 1048576 * 100) / 100,
    limit: Math.round(memory.jsHeapSizeLimit / 1048576 * 100) / 100,
  };
};

// Critical Resource Priority
export const prioritizeCriticalResources = () => {
  if (typeof document === 'undefined') return;

  // Prioritize above-the-fold images
  const criticalImages = document.querySelectorAll('img[data-priority="high"]');
  criticalImages.forEach((img) => {
    if (img instanceof HTMLImageElement) {
      img.loading = 'eager';
      img.fetchPriority = 'high';
    }
  });

  // Preload critical fonts
  const criticalFonts = document.querySelectorAll('link[rel="preload"][as="font"]');
  criticalFonts.forEach((font) => {
    if (font instanceof HTMLLinkElement) {
      font.crossOrigin = 'anonymous';
    }
  });
};

// Performance Timing Helpers
export const measureFunction = <T extends (...args: any[]) => any>(
  fn: T,
  name: string
): T => {
  return ((...args: Parameters<T>) => {
    const start = performance.now();
    const result = fn(...args);
    const end = performance.now();
    
    console.log(`${name} took ${(end - start).toFixed(2)}ms`);
    return result;
  }) as T;
};

export const measureAsync = async <T>(
  promise: Promise<T>,
  name: string
): Promise<T> => {
  const start = performance.now();
  try {
    const result = await promise;
    const end = performance.now();
    console.log(`${name} took ${(end - start).toFixed(2)}ms`);
    return result;
  } catch (error) {
    const end = performance.now();
    console.log(`${name} failed after ${(end - start).toFixed(2)}ms`);
    throw error;
  }
};

// Component Performance Tracking
export const trackComponentRender = (componentName: string) => {
  return {
    onRenderStart: () => performance.mark(`${componentName}-render-start`),
    onRenderEnd: () => {
      performance.mark(`${componentName}-render-end`);
      performance.measure(
        `${componentName}-render`,
        `${componentName}-render-start`,
        `${componentName}-render-end`
      );
    }
  };
};

// Debounce and Throttle for Performance
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  delay: number
): ((...args: Parameters<T>) => void) => {
  let timeoutId: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
};

export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func.apply(null, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// Web Vitals Reporting
export const reportWebVitals = (metric: any) => {
  // Report to analytics service
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('web-vitals', {
      detail: {
        name: metric.name,
        value: metric.value,
        id: metric.id,
        timestamp: Date.now(),
      }
    }));
  }
};

// Resource Loading Strategy
export const createLoadingStrategy = () => {
  const loadedResources = new Set<string>();
  
  return {
    preloadCritical: (resources: string[]) => {
      resources.forEach(resource => {
        if (!loadedResources.has(resource)) {
          preloadResource(resource, 'script');
          loadedResources.add(resource);
        }
      });
    },
    
    prefetchNextPage: (resources: string[]) => {
      // Use requestIdleCallback for non-critical prefetching
      if ('requestIdleCallback' in window) {
        requestIdleCallback(() => {
          resources.forEach(resource => {
            if (!loadedResources.has(resource)) {
              prefetchResource(resource);
              loadedResources.add(resource);
            }
          });
        });
      } else {
        setTimeout(() => {
          resources.forEach(resource => {
            if (!loadedResources.has(resource)) {
              prefetchResource(resource);
              loadedResources.add(resource);
            }
          });
        }, 0);
      }
    }
  };
};