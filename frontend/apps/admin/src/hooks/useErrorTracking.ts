/**
 * React hook for error tracking and monitoring
 */

import { useCallback, useEffect } from 'react'
import { errorTracker } from '../lib/errorBoundary'
import { logger } from '../lib/logger'

export interface UseErrorTrackingOptions {
  component?: string
  enablePerformanceTracking?: boolean
  enableUserActionTracking?: boolean
}

export interface ErrorTrackingHook {
  captureError: (error: Error, context?: Record<string, any>) => string
  captureException: (error: Error, context?: Record<string, any>) => string
  measurePerformance: <T>(operation: string, fn: () => T | Promise<T>) => T | Promise<T>
  trackUserAction: (action: string, details?: Record<string, any>) => void
  trackApiCall: (method: string, url: string, status: number, duration?: number) => void
}

export function useErrorTracking(
  componentName: string,
  options: UseErrorTrackingOptions = {}
): ErrorTrackingHook {
  const {
    enablePerformanceTracking = true,
    enableUserActionTracking = true,
  } = options

  // Setup error tracking for component
  useEffect(() => {
    if (enablePerformanceTracking) {
      logger.debug('Error tracking enabled for component', {
        component: componentName,
        enablePerformanceTracking,
        enableUserActionTracking,
      })
    }
  }, [componentName, enablePerformanceTracking, enableUserActionTracking])

  const captureError = useCallback(
    (error: Error, context?: Record<string, any>): string => {
      return errorTracker.captureError(error, {
        component: componentName,
        action: 'error',
        metadata: context,
      })
    },
    [componentName]
  )

  const captureException = useCallback(
    (error: Error, context?: Record<string, any>): string => {
      return errorTracker.captureError(error, {
        component: componentName,
        action: 'exception',
        metadata: {
          ...context,
          handled: true,
        },
      })
    },
    [componentName]
  )

  const measurePerformance = useCallback(
    <T>(operation: string, fn: () => T | Promise<T>): T | Promise<T> => {
      if (!enablePerformanceTracking) {
        return fn()
      }

      return errorTracker.measurePerformance(operation, componentName, fn)
    },
    [componentName, enablePerformanceTracking]
  )

  const trackUserAction = useCallback(
    (action: string, details?: Record<string, any>): void => {
      if (!enableUserActionTracking) {
        return
      }

      logger.userAction(action, componentName, details)
    },
    [componentName, enableUserActionTracking]
  )

  const trackApiCall = useCallback(
    (method: string, url: string, status: number, duration?: number): void => {
      logger.apiRequest(method, url, status, duration)
    },
    []
  )

  return {
    captureError,
    captureException,
    measurePerformance,
    trackUserAction,
    trackApiCall,
  }
}

// Specialized hook for API calls with automatic error handling
export function useApiErrorTracking(componentName: string) {
  const { captureError, trackApiCall } = useErrorTracking(componentName)

  const wrapApiCall = useCallback(
    async <T>(
      apiCall: () => Promise<T>,
      method: string,
      url: string
    ): Promise<T> => {
      const startTime = performance.now()
      
      try {
        const result = await apiCall()
        const duration = performance.now() - startTime
        trackApiCall(method, url, 200, duration)
        return result
      } catch (error) {
        const duration = performance.now() - startTime
        const status = (error as any)?.response?.status || 500
        
        trackApiCall(method, url, status, duration)
        
        captureError(error as Error, {
          apiCall: {
            method,
            url,
            status,
            duration,
          },
        })
        
        throw error
      }
    },
    [captureError, trackApiCall]
  )

  return { wrapApiCall }
}

// Hook for form error tracking
export function useFormErrorTracking(formName: string) {
  const { captureError, trackUserAction } = useErrorTracking(`form-${formName}`)

  const trackValidationError = useCallback(
    (field: string, error: string): void => {
      trackUserAction('validation-error', {
        form: formName,
        field,
        error,
      })
    },
    [formName, trackUserAction]
  )

  const trackSubmissionError = useCallback(
    (error: Error, formData?: Record<string, any>): string => {
      return captureError(error, {
        form: formName,
        formData: formData ? Object.keys(formData) : undefined, // Don't log actual form data for privacy
        action: 'form-submission',
      })
    },
    [formName, captureError]
  )

  const trackFormCompletion = useCallback(
    (duration: number, fields: string[]): void => {
      trackUserAction('form-completed', {
        form: formName,
        duration,
        fieldCount: fields.length,
      })
    },
    [formName, trackUserAction]
  )

  return {
    trackValidationError,
    trackSubmissionError,
    trackFormCompletion,
  }
}

// Hook for authentication error tracking
export function useAuthErrorTracking() {
  const { captureError, trackUserAction } = useErrorTracking('auth')

  const trackLoginAttempt = useCallback(
    (success: boolean, error?: Error, details?: Record<string, any>): void => {
      if (success) {
        trackUserAction('login-success', details)
        logger.authEvent('login', true, details?.userId, details)
      } else {
        trackUserAction('login-failure', { error: error?.message, ...details })
        logger.authEvent('login', false, details?.userId, { error: error?.message, ...details })
        
        if (error) {
          captureError(error, {
            action: 'login-attempt',
            ...details,
          })
        }
      }
    },
    [captureError, trackUserAction]
  )

  const trackLogout = useCallback(
    (userId?: string, reason?: string): void => {
      trackUserAction('logout', { userId, reason })
      logger.authEvent('logout', true, userId, { reason })
    },
    [trackUserAction]
  )

  const trackSessionExpiry = useCallback(
    (userId?: string): void => {
      trackUserAction('session-expired', { userId })
      logger.authEvent('session-expired', false, userId)
    },
    [trackUserAction]
  )

  const trackPermissionDenied = useCallback(
    (action: string, userId?: string, requiredPermissions?: string[]): void => {
      trackUserAction('permission-denied', {
        action,
        userId,
        requiredPermissions,
      })
      logger.securityEvent('permission-denied', 'medium', {
        action,
        userId,
        requiredPermissions,
      })
    },
    [trackUserAction]
  )

  return {
    trackLoginAttempt,
    trackLogout,
    trackSessionExpiry,
    trackPermissionDenied,
  }
}