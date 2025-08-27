/**
 * Performance-optimized lazy loading image component
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ImageIcon } from 'lucide-react';

export interface LazyImageProps extends Omit<React.ImgHTMLAttributes<HTMLImageElement>, 'src' | 'loading'> {
  src: string;
  alt: string;
  fallbackSrc?: string;
  placeholder?: React.ReactNode;
  errorPlaceholder?: React.ReactNode;
  threshold?: number;
  rootMargin?: string;
  onLoad?: (event: React.SyntheticEvent<HTMLImageElement>) => void;
  onError?: (event: React.SyntheticEvent<HTMLImageElement>) => void;
  retryCount?: number;
  retryDelay?: number;
  className?: string;
}

export function LazyImage({
  src,
  alt,
  fallbackSrc,
  placeholder,
  errorPlaceholder,
  threshold = 0.1,
  rootMargin = '50px',
  onLoad,
  onError,
  retryCount = 2,
  retryDelay = 1000,
  className = '',
  ...props
}: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [currentRetries, setCurrentRetries] = useState(0);
  const [isIntersecting, setIsIntersecting] = useState(false);

  const imgRef = useRef<HTMLImageElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Setup intersection observer for lazy loading
  useEffect(() => {
    const element = imgRef.current;
    if (!element) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          setIsIntersecting(true);
          observerRef.current?.disconnect();
        }
      },
      {
        threshold,
        rootMargin,
      }
    );

    observerRef.current.observe(element);

    return () => {
      observerRef.current?.disconnect();
    };
  }, [threshold, rootMargin]);

  // Load image when in viewport
  useEffect(() => {
    if (!isIntersecting || isLoaded || isLoading) return;

    setIsLoading(true);
    setHasError(false);

    const img = new Image();
    
    const handleLoad = () => {
      setIsLoaded(true);
      setIsLoading(false);
      setCurrentRetries(0);
    };

    const handleError = () => {
      setIsLoading(false);
      
      if (currentRetries < retryCount) {
        // Retry after delay
        setTimeout(() => {
          setCurrentRetries(prev => prev + 1);
          setIsIntersecting(true); // Trigger retry
        }, retryDelay);
      } else {
        setHasError(true);
      }
    };

    img.addEventListener('load', handleLoad);
    img.addEventListener('error', handleError);
    img.src = src;

    // Cleanup
    return () => {
      img.removeEventListener('load', handleLoad);
      img.removeEventListener('error', handleError);
    };
  }, [isIntersecting, src, retryCount, retryDelay, currentRetries, isLoaded, isLoading]);

  const handleImageLoad = useCallback((event: React.SyntheticEvent<HTMLImageElement>) => {
    setIsLoaded(true);
    setIsLoading(false);
    onLoad?.(event);
  }, [onLoad]);

  const handleImageError = useCallback((event: React.SyntheticEvent<HTMLImageElement>) => {
    setIsLoading(false);
    if (fallbackSrc && event.currentTarget.src !== fallbackSrc) {
      event.currentTarget.src = fallbackSrc;
    } else {
      setHasError(true);
      onError?.(event);
    }
  }, [fallbackSrc, onError]);

  // Default placeholder
  const defaultPlaceholder = (
    <div className="flex items-center justify-center bg-gray-200 text-gray-400">
      {isLoading ? (
        <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-400 border-t-transparent" />
      ) : (
        <ImageIcon className="h-8 w-8" />
      )}
    </div>
  );

  // Default error placeholder
  const defaultErrorPlaceholder = (
    <div className="flex flex-col items-center justify-center bg-gray-100 text-gray-500 p-4">
      <ImageIcon className="h-8 w-8 mb-2" />
      <span className="text-sm">Failed to load image</span>
      {currentRetries < retryCount && (
        <span className="text-xs mt-1">Retrying... ({currentRetries + 1}/{retryCount})</span>
      )}
    </div>
  );

  return (
    <div className={`relative overflow-hidden ${className}`} {...props}>
      <img
        ref={imgRef}
        src={isIntersecting && !hasError ? src : undefined}
        alt={alt}
        onLoad={handleImageLoad}
        onError={handleImageError}
        className={`
          w-full h-full object-cover transition-opacity duration-300
          ${isLoaded ? 'opacity-100' : 'opacity-0'}
          ${className}
        `}
        loading="lazy"
      />

      {/* Show placeholder while loading or not in view */}
      {(!isLoaded || !isIntersecting) && !hasError && (
        <div className="absolute inset-0 flex items-center justify-center">
          {placeholder || defaultPlaceholder}
        </div>
      )}

      {/* Show error placeholder */}
      {hasError && (
        <div className="absolute inset-0 flex items-center justify-center">
          {errorPlaceholder || defaultErrorPlaceholder}
        </div>
      )}
    </div>
  );
}

// Hook for preloading images
export function useImagePreloader() {
  const [preloadedImages, setPreloadedImages] = useState<Set<string>>(new Set());
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());

  const preloadImage = useCallback((src: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (preloadedImages.has(src)) {
        resolve();
        return;
      }

      if (failedImages.has(src)) {
        reject(new Error('Image previously failed to load'));
        return;
      }

      const img = new Image();
      
      img.onload = () => {
        setPreloadedImages(prev => new Set(prev).add(src));
        resolve();
      };

      img.onerror = () => {
        setFailedImages(prev => new Set(prev).add(src));
        reject(new Error('Failed to preload image'));
      };

      img.src = src;
    });
  }, [preloadedImages, failedImages]);

  const preloadImages = useCallback(async (srcs: string[]): Promise<void> => {
    const promises = srcs.map(src => preloadImage(src).catch(() => {})); // Ignore individual failures
    await Promise.all(promises);
  }, [preloadImage]);

  const isPreloaded = useCallback((src: string): boolean => {
    return preloadedImages.has(src);
  }, [preloadedImages]);

  const hasFailed = useCallback((src: string): boolean => {
    return failedImages.has(src);
  }, [failedImages]);

  return {
    preloadImage,
    preloadImages,
    isPreloaded,
    hasFailed,
    preloadedCount: preloadedImages.size,
    failedCount: failedImages.size
  };
}