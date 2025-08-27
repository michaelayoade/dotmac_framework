# API Integration Guide

## Overview

This document outlines the API integration patterns, error handling, and data management strategies for the DotMac Admin Portal.

## API Architecture

### Base Configuration

```typescript
// API Client Configuration
const apiConfig = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://api.dotmac.com',
  timeout: 30000,
  retries: 3,
  retryDelay: 1000,
}

// Request interceptors
const setupInterceptors = (client: AxiosInstance) => {
  client.interceptors.request.use((config) => {
    // Add authentication token
    const token = getAuthToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Add CSRF token for state-changing requests
    if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase())) {
      config.headers['X-CSRF-Token'] = getCSRFToken()
    }
    
    return config
  })
  
  client.interceptors.response.use(
    (response) => response,
    (error) => handleApiError(error)
  )
}
```

### Authentication

#### Token Management
```typescript
interface AuthTokens {
  accessToken: string
  refreshToken: string
  expiresAt: number
}

class TokenManager {
  private tokens: AuthTokens | null = null
  
  async getValidToken(): Promise<string> {
    if (!this.tokens) {
      throw new Error('No authentication tokens available')
    }
    
    if (this.isTokenExpired()) {
      await this.refreshTokens()
    }
    
    return this.tokens.accessToken
  }
  
  private isTokenExpired(): boolean {
    return Date.now() >= this.tokens!.expiresAt - 60000 // 1 minute buffer
  }
  
  private async refreshTokens(): Promise<void> {
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          refreshToken: this.tokens!.refreshToken 
        })
      })
      
      if (!response.ok) {
        throw new Error('Token refresh failed')
      }
      
      this.tokens = await response.json()
    } catch (error) {
      this.tokens = null
      window.location.href = '/login'
      throw error
    }
  }
}
```

## React Query Integration

### Query Configuration
```typescript
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on auth errors
        if (error?.status === 401 || error?.status === 403) {
          return false
        }
        // Don't retry client errors (4xx)
        if (error?.status >= 400 && error?.status < 500) {
          return false
        }
        return failureCount < 3
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})
```

### Custom Hooks Pattern

#### Data Fetching Hook
```typescript
import { useQuery } from '@tanstack/react-query'
import { useApiErrorTracking } from '@/hooks/useErrorTracking'

interface PaginationParams {
  page: number
  pageSize: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  filters?: Record<string, any>
}

export function useCustomers(params: PaginationParams) {
  const { wrapApiCall } = useApiErrorTracking('customers')
  
  return useQuery({
    queryKey: ['customers', params],
    queryFn: () => wrapApiCall(
      async () => {
        const searchParams = new URLSearchParams({
          page: params.page.toString(),
          pageSize: params.pageSize.toString(),
          ...(params.sortBy && { sortBy: params.sortBy }),
          ...(params.sortOrder && { sortOrder: params.sortOrder }),
          ...params.filters,
        })
        
        const response = await fetch(`/api/customers?${searchParams}`)
        if (!response.ok) {
          throw new Error(`Failed to fetch customers: ${response.statusText}`)
        }
        
        return response.json()
      },
      'GET',
      `/api/customers`
    ),
    enabled: true,
    keepPreviousData: true, // For pagination
  })
}
```

#### Mutation Hook
```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useErrorTracking } from '@/hooks/useErrorTracking'

interface CreateCustomerData {
  name: string
  email: string
  phone: string
  address: string
}

export function useCreateCustomer() {
  const queryClient = useQueryClient()
  const { captureError } = useErrorTracking('create-customer')
  
  return useMutation({
    mutationFn: async (data: CreateCustomerData) => {
      const response = await fetch('/api/customers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCSRFToken(),
        },
        body: JSON.stringify(data),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Failed to create customer')
      }
      
      return response.json()
    },
    onSuccess: (newCustomer) => {
      // Invalidate and refetch customers list
      queryClient.invalidateQueries(['customers'])
      
      // Optimistic update
      queryClient.setQueryData(['customers'], (old: any) => {
        if (!old) return old
        return {
          ...old,
          data: [newCustomer, ...old.data],
          total: old.total + 1,
        }
      })
    },
    onError: (error) => {
      captureError(error as Error, {
        action: 'create-customer',
        data: Object.keys(data), // Don't log sensitive data
      })
    },
  })
}
```

## Error Handling

### Error Types
```typescript
interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  status: number
  timestamp: string
}

interface ValidationError extends ApiError {
  code: 'VALIDATION_ERROR'
  fields: Record<string, string[]>
}

interface AuthError extends ApiError {
  code: 'AUTH_ERROR' | 'PERMISSION_DENIED'
}

interface RateLimitError extends ApiError {
  code: 'RATE_LIMIT_EXCEEDED'
  retryAfter: number
}
```

### Global Error Handler
```typescript
import { logger } from '@/lib/logger'
import { toast } from '@/components/ui/Toast'

export function handleApiError(error: any): never {
  const apiError: ApiError = {
    code: error.response?.data?.code || 'UNKNOWN_ERROR',
    message: error.response?.data?.message || error.message,
    details: error.response?.data?.details,
    status: error.response?.status || 500,
    timestamp: new Date().toISOString(),
  }
  
  // Log the error
  logger.error('API Error', {
    component: 'api-client',
    action: 'request',
    ...apiError,
  }, error)
  
  // Handle specific error types
  switch (apiError.code) {
    case 'AUTH_ERROR':
      handleAuthError(apiError as AuthError)
      break
    case 'PERMISSION_DENIED':
      handlePermissionError(apiError as AuthError)
      break
    case 'RATE_LIMIT_EXCEEDED':
      handleRateLimitError(apiError as RateLimitError)
      break
    case 'VALIDATION_ERROR':
      handleValidationError(apiError as ValidationError)
      break
    default:
      handleGenericError(apiError)
  }
  
  throw apiError
}

function handleAuthError(error: AuthError) {
  // Clear auth state and redirect to login
  useAuthStore.getState().logout()
  window.location.href = '/login'
}

function handlePermissionError(error: AuthError) {
  toast.error('You do not have permission to perform this action')
}

function handleRateLimitError(error: RateLimitError) {
  toast.error(`Rate limit exceeded. Please try again in ${error.retryAfter} seconds`)
}

function handleValidationError(error: ValidationError) {
  // Display field-specific errors
  Object.entries(error.fields).forEach(([field, messages]) => {
    toast.error(`${field}: ${messages.join(', ')}`)
  })
}

function handleGenericError(error: ApiError) {
  toast.error(error.message || 'An unexpected error occurred')
}
```

## Data Management

### Caching Strategy

#### Cache Keys
```typescript
// Hierarchical cache key structure
const cacheKeys = {
  customers: ['customers'] as const,
  customer: (id: string) => ['customers', id] as const,
  customerBilling: (id: string) => ['customers', id, 'billing'] as const,
  
  billing: ['billing'] as const,
  invoices: (filters: any) => ['billing', 'invoices', filters] as const,
  invoice: (id: string) => ['billing', 'invoices', id] as const,
  
  users: ['users'] as const,
  user: (id: string) => ['users', id] as const,
} as const
```

#### Cache Invalidation
```typescript
export class CacheManager {
  constructor(private queryClient: QueryClient) {}
  
  // Invalidate all customer-related data
  invalidateCustomers() {
    this.queryClient.invalidateQueries(['customers'])
  }
  
  // Invalidate specific customer
  invalidateCustomer(customerId: string) {
    this.queryClient.invalidateQueries(['customers', customerId])
  }
  
  // Remove customer from cache
  removeCustomer(customerId: string) {
    this.queryClient.removeQueries(['customers', customerId])
    
    // Update customers list
    this.queryClient.setQueryData(['customers'], (old: any) => {
      if (!old) return old
      return {
        ...old,
        data: old.data.filter((customer: any) => customer.id !== customerId),
        total: old.total - 1,
      }
    })
  }
}
```

### Optimistic Updates

```typescript
export function useUpdateCustomer() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: updateCustomerApi,
    onMutate: async (variables) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries(['customers', variables.id])
      
      // Snapshot previous value
      const previousCustomer = queryClient.getQueryData(['customers', variables.id])
      
      // Optimistically update
      queryClient.setQueryData(['customers', variables.id], {
        ...previousCustomer,
        ...variables.updates,
      })
      
      return { previousCustomer }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousCustomer) {
        queryClient.setQueryData(['customers', variables.id], context.previousCustomer)
      }
    },
    onSettled: (data, error, variables) => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries(['customers', variables.id])
    },
  })
}
```

### Real-time Updates

#### WebSocket Integration
```typescript
export function useRealTimeUpdates() {
  const queryClient = useQueryClient()
  
  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL!)
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      
      switch (message.type) {
        case 'CUSTOMER_UPDATED':
          queryClient.invalidateQueries(['customers', message.data.id])
          break
          
        case 'INVOICE_CREATED':
          queryClient.invalidateQueries(['billing', 'invoices'])
          break
          
        case 'USER_STATUS_CHANGED':
          queryClient.invalidateQueries(['users'])
          break
      }
    }
    
    return () => ws.close()
  }, [queryClient])
}
```

## Performance Optimization

### Request Batching
```typescript
class RequestBatcher {
  private batches: Map<string, any[]> = new Map()
  private timers: Map<string, NodeJS.Timeout> = new Map()
  
  batch<T>(
    key: string,
    request: any,
    batchFn: (requests: any[]) => Promise<T[]>,
    delay = 50
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      // Add to batch
      if (!this.batches.has(key)) {
        this.batches.set(key, [])
      }
      
      this.batches.get(key)!.push({ request, resolve, reject })
      
      // Set timer if not exists
      if (!this.timers.has(key)) {
        const timer = setTimeout(async () => {
          const batch = this.batches.get(key) || []
          this.batches.delete(key)
          this.timers.delete(key)
          
          try {
            const results = await batchFn(batch.map(b => b.request))
            batch.forEach((b, index) => b.resolve(results[index]))
          } catch (error) {
            batch.forEach(b => b.reject(error))
          }
        }, delay)
        
        this.timers.set(key, timer)
      }
    })
  }
}

// Usage example
const batcher = new RequestBatcher()

export function useCustomer(id: string) {
  return useQuery({
    queryKey: ['customers', id],
    queryFn: () => batcher.batch(
      'customers',
      id,
      async (ids: string[]) => {
        const response = await fetch('/api/customers/batch', {
          method: 'POST',
          body: JSON.stringify({ ids }),
        })
        return response.json()
      }
    ),
  })
}
```

### Response Compression
```typescript
// Request with compression support
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Accept-Encoding': 'gzip, deflate, br',
  },
  decompress: true,
})
```

## Testing API Integration

### Mock Setup
```typescript
// __mocks__/api.ts
export const mockApiResponses = {
  customers: {
    get: {
      data: [
        { id: '1', name: 'John Doe', email: 'john@example.com' },
        { id: '2', name: 'Jane Smith', email: 'jane@example.com' },
      ],
      pagination: { page: 1, pageSize: 10, total: 2 },
    },
  },
}

export const setupApiMocks = () => {
  global.fetch = jest.fn().mockImplementation((url, options) => {
    // Parse URL and method to return appropriate mock
    const method = options?.method || 'GET'
    const endpoint = url.split('/').pop()
    
    const mockResponse = mockApiResponses[endpoint]?.[method.toLowerCase()]
    
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })
  })
}
```

### Integration Tests
```typescript
describe('Customer API Integration', () => {
  beforeEach(() => {
    setupApiMocks()
  })
  
  it('should fetch customers with pagination', async () => {
    const { result, waitFor } = renderHook(
      () => useCustomers({ page: 1, pageSize: 10 }),
      { wrapper: QueryProvider }
    )
    
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
    
    expect(result.current.data).toEqual(mockApiResponses.customers.get)
  })
  
  it('should handle API errors gracefully', async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error('Network error'))
    
    const { result, waitFor } = renderHook(
      () => useCustomers({ page: 1, pageSize: 10 }),
      { wrapper: QueryProvider }
    )
    
    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })
    
    expect(result.current.error).toBeTruthy()
  })
})
```

## Monitoring and Analytics

### API Metrics
```typescript
export function trackApiMetrics(
  method: string,
  endpoint: string,
  status: number,
  duration: number
) {
  logger.apiRequest(method, endpoint, status, duration)
  
  // Track performance metrics
  if (duration > 1000) {
    logger.warn('Slow API request', {
      component: 'api-client',
      method,
      endpoint,
      duration,
      threshold: 1000,
    })
  }
  
  // Track error rates
  if (status >= 400) {
    logger.error('API request failed', {
      component: 'api-client',
      method,
      endpoint,
      status,
    })
  }
}
```

### Performance Monitoring
```typescript
export function useApiPerformance() {
  const [metrics, setMetrics] = useState({
    averageResponseTime: 0,
    errorRate: 0,
    requestCount: 0,
  })
  
  useEffect(() => {
    const interval = setInterval(() => {
      // Calculate metrics from logged data
      const recentMetrics = calculateMetrics()
      setMetrics(recentMetrics)
    }, 30000) // Every 30 seconds
    
    return () => clearInterval(interval)
  }, [])
  
  return metrics
}
```

## Best Practices

### Request Optimization
1. Use appropriate HTTP methods (GET, POST, PUT, DELETE)
2. Implement proper caching headers
3. Use pagination for large datasets
4. Batch similar requests when possible
5. Implement request deduplication

### Error Handling
1. Provide meaningful error messages
2. Implement proper retry logic
3. Handle network failures gracefully
4. Log errors for debugging
5. Display user-friendly error states

### Security
1. Always validate input on both client and server
2. Use HTTPS for all requests
3. Implement proper authentication
4. Include CSRF protection
5. Rate limit API endpoints

### Performance
1. Minimize payload sizes
2. Use compression when available
3. Implement proper caching strategies
4. Monitor API performance metrics
5. Optimize for mobile networks