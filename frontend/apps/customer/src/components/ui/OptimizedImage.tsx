/**
 * Optimized Image Component
 * Handles responsive images with lazy loading and format optimization
 */

'use client';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import {
  createBlurPlaceholder,
  getImageConfig,
  getOptimizedImageUrl,
  type ImageConfigType,
  ImageLoadingState,
} from '../../lib/utils/imageOptimization';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  priority?: boolean;
  quality?: number;
  placeholder?: 'blur' | 'empty';
  configType?: ImageConfigType;
  onLoad?: () => void;
  onError?: () => void;
  fallbackSrc?: string;
}

export function OptimizedImage({
  src,
  alt,
  width,
  height,
  className = '',
  priority = false,
  quality = 85,
  placeholder = 'blur',
  configType,
  onLoad,
  onError,
  fallbackSrc = '/images/placeholder.svg',
}: OptimizedImageProps) {
  const [loadingState, setLoadingState] = useState<ImageLoadingState>(ImageLoadingState.Loading);
  const [currentSrc, setCurrentSrc] = useState(src);
  const imgRef = useRef<HTMLImageElement>(null);

  // Get predefined config if specified
  const config = configType ? getImageConfig(configType) : null;
  const finalPriority = config?.priority ?? priority;
  const finalQuality = config?.quality ?? quality;
  const sizes = config?.sizes;

  // Handle image load
  const handleLoad = () => {
    setLoadingState(ImageLoadingState.Loaded);
    onLoad?.();
  };

  // Handle image error with fallback
  const handleError = () => {
    if (currentSrc !== fallbackSrc) {
      setCurrentSrc(fallbackSrc);
    } else {
      setLoadingState(ImageLoadingState.Error);
      onError?.();
    }
  };

  // Create blur placeholder if needed
  const blurDataURL =
    placeholder === 'blur' && width && height ? createBlurPlaceholder(width, height) : undefined;

  // Determine if image should be lazy loaded
  const shouldLazyLoad = !finalPriority;

  return (
    <div className={`relative overflow-hidden ${className}`}>
      {/* Main optimized image */}
      <Image
        ref={imgRef}
        src={currentSrc}
        alt={alt}
        width={width}
        height={height}
        quality={finalQuality}
        priority={finalPriority}
        placeholder={placeholder}
        blurDataURL={blurDataURL}
        sizes={sizes}
        loading={shouldLazyLoad ? 'lazy' : 'eager'}
        onLoad={handleLoad}
        onError={handleError}
        className={`
          transition-opacity duration-300 
          ${loadingState === ImageLoadingState.Loading ? 'opacity-0' : 'opacity-100'}
        `}
        style={{
          width: width ? 'auto' : '100%',
          height: height ? 'auto' : 'auto',
        }}
      />

      {/* Loading skeleton */}
      {loadingState === ImageLoadingState.Loading && (
        <div
          className="absolute inset-0 bg-gray-200 animate-pulse flex items-center justify-center"
          style={{ width, height }}
        >
          <svg
            className="w-8 h-8 text-gray-400"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
              clipRule="evenodd"
            />
          </svg>
        </div>
      )}

      {/* Error state */}
      {loadingState === ImageLoadingState.Error && (
        <div
          className="absolute inset-0 bg-red-50 border-2 border-dashed border-red-300 flex items-center justify-center"
          style={{ width, height }}
        >
          <div className="text-center">
            <svg
              className="w-8 h-8 text-red-400 mx-auto mb-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
            <span className="text-sm text-red-600">Failed to load</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Specialized image components for common use cases
export function AvatarImage({
  src,
  alt,
  size = 48,
  className = '',
  ...props
}: Omit<OptimizedImageProps, 'width' | 'height' | 'configType'> & { size?: number }) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      width={size}
      height={size}
      configType="avatar"
      className={`rounded-full ${className}`}
      {...props}
    />
  );
}

export function HeroImage({
  src,
  alt,
  className = '',
  ...props
}: Omit<OptimizedImageProps, 'configType'>) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      configType="hero"
      className={`w-full h-auto ${className}`}
      priority={true}
      {...props}
    />
  );
}

export function ThumbnailImage({
  src,
  alt,
  className = '',
  ...props
}: Omit<OptimizedImageProps, 'configType'>) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      configType="thumbnail"
      className={`rounded-lg ${className}`}
      {...props}
    />
  );
}

export function LogoImage({
  src,
  alt,
  className = '',
  ...props
}: Omit<OptimizedImageProps, 'configType'>) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      configType="logo"
      className={`object-contain ${className}`}
      priority={true}
      {...props}
    />
  );
}
