'use client'

import { ReactNode, ComponentType, useEffect, useState } from 'react'

interface ComponentLoaderConfig {
  packageName: string
  componentName: string
  fallbackComponent: ComponentType<any>
  enableLogging?: boolean
}

interface LoadingState {
  loading: boolean
  error: string | null
  component: ComponentType<any> | null
}

/**
 * Progressive Enhancement Component Loader
 * Tries to load real workspace components, falls back to stubs gracefully
 */
export function useComponentLoader<T = any>(config: ComponentLoaderConfig) {
  const [state, setState] = useState<LoadingState>({
    loading: false,
    error: 'Adaptive loading temporarily disabled',
    component: config.fallbackComponent
  })

  // Temporarily return fallback components immediately to fix webpack issues
  // TODO: Implement proper module federation or dynamic loading strategy
  return state
}

interface AdaptiveComponentProps {
  packageName: string
  componentName: string
  fallbackComponent: ComponentType<any>
  enableLogging?: boolean
  loadingComponent?: ComponentType
  children?: ReactNode
  [key: string]: any
}

/**
 * Adaptive Component that loads real or fallback implementations
 */
export function AdaptiveComponent({ 
  packageName, 
  componentName, 
  fallbackComponent, 
  enableLogging = false,
  loadingComponent: LoadingComponent,
  children,
  ...props 
}: AdaptiveComponentProps) {
  const { loading, component: LoadedComponent } = useComponentLoader({
    packageName,
    componentName,
    fallbackComponent,
    enableLogging
  })

  if (loading && LoadingComponent) {
    return <LoadingComponent {...props}>{children}</LoadingComponent>
  }

  if (loading) {
    return (
      <div className="animate-pulse bg-gray-200 rounded h-8 w-full">
        <span className="sr-only">Loading {componentName}...</span>
      </div>
    )
  }

  if (!LoadedComponent) {
    const FallbackComponent = fallbackComponent
    return <FallbackComponent {...props}>{children}</FallbackComponent>
  }

  return <LoadedComponent {...props}>{children}</LoadedComponent>
}

/**
 * Feature flag for controlling component loading behavior
 */
export const COMPONENT_LOADING_CONFIG = {
  useRealComponents: process.env.NODE_ENV === 'development' 
    ? process.env.NEXT_PUBLIC_USE_REAL_COMPONENTS !== 'false'
    : true,
  enableLogging: process.env.NODE_ENV === 'development',
  fallbackMode: process.env.NEXT_PUBLIC_FALLBACK_MODE || 'graceful' // 'graceful' | 'strict' | 'stub-only'
}

/**
 * Smart component factory - temporarily using fallbacks only
 */
export function createAdaptiveComponent<T = any>(
  packageName: string,
  componentName: string,
  fallbackComponent: ComponentType<T>
) {
  return function SmartComponent(props: T & { children?: ReactNode }) {
    // Temporarily use only fallbacks to fix homepage 500 error
    // TODO: Re-enable adaptive loading after fixing module resolution
    const FallbackComponent = fallbackComponent
    return <FallbackComponent {...props} />
  }
}