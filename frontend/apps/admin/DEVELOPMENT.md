# Admin Portal Development Guide

## Overview

The DotMac Admin Portal is a comprehensive ISP administration interface built with Next.js, TypeScript, and modern React patterns. This guide covers development standards, testing practices, and architectural decisions.

## Architecture

### Technology Stack

- **Framework**: Next.js 14+ with App Router
- **Language**: TypeScript 5.3+
- **Styling**: Tailwind CSS + Styled Components
- **State Management**: Zustand
- **Data Fetching**: React Query (TanStack Query)
- **Testing**: Jest + React Testing Library
- **Authentication**: Custom JWT-based system
- **Logging**: Custom centralized logging system

### Project Structure

```
src/
├── app/                    # Next.js App Router pages and layouts
│   ├── (protected)/        # Protected routes requiring authentication
│   ├── api/               # API routes
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── providers.tsx      # Global providers
├── components/            # Reusable UI components
│   ├── auth/             # Authentication components
│   ├── ui/               # Base UI components
│   └── modules/          # Feature-specific components
├── hooks/                # Custom React hooks
├── lib/                  # Utility libraries
│   ├── logger.ts         # Centralized logging
│   ├── errorBoundary.ts  # Error tracking and boundaries
│   └── security.ts       # Security utilities
├── stores/               # Zustand stores
└── types/               # TypeScript type definitions
```

## Development Standards

### Code Style

- Use TypeScript for all new code
- Follow ESLint and Prettier configurations
- Use functional components with hooks
- Prefer composition over inheritance
- Use descriptive variable and function names

### Component Guidelines

1. **Component Structure**:
   ```typescript
   // imports
   import { useState } from 'react'
   import { Button } from '@/components/ui'
   
   // types
   interface ComponentProps {
     title: string
     onAction?: () => void
   }
   
   // component
   export function Component({ title, onAction }: ComponentProps) {
     // component logic
     return (
       // JSX
     )
   }
   ```

2. **Error Handling**:
   ```typescript
   import { useErrorTracking } from '@/hooks/useErrorTracking'
   
   export function Component() {
     const { captureError } = useErrorTracking('ComponentName')
     
     const handleAsyncAction = async () => {
       try {
         // async operation
       } catch (error) {
         captureError(error as Error, { action: 'async-action' })
       }
     }
   }
   ```

3. **Performance**:
   - Use React.memo for expensive components
   - Implement virtualization for large lists
   - Lazy load non-critical components
   - Use useMemo and useCallback appropriately

### State Management

- Use Zustand for global state
- Keep component state local when possible
- Use React Query for server state
- Implement optimistic updates where appropriate

### Testing Requirements

All components must have comprehensive test coverage:

1. **Unit Tests**: Test component behavior in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete user flows

#### Test Structure

```typescript
describe('ComponentName', () => {
  beforeEach(() => {
    // setup
  })

  it('renders correctly', () => {
    // rendering test
  })

  it('handles user interactions', async () => {
    // interaction test
  })

  it('handles error states', () => {
    // error handling test
  })
})
```

#### Coverage Requirements

- **Minimum Coverage**: 70% for all metrics
- **Critical Components**: 90%+ coverage
- **Security Functions**: 100% coverage

### Error Handling and Monitoring

#### Error Boundary Usage

Wrap components that might throw errors:

```typescript
import { withErrorBoundary } from '@/lib/errorBoundary'

const SafeComponent = withErrorBoundary(RiskyComponent, 'RiskyComponent')
```

#### Logging Best Practices

```typescript
import { logger } from '@/lib/logger'

// Log user actions
logger.userAction('button-click', 'component-name', { buttonId: 'submit' })

// Log API calls
logger.apiRequest('POST', '/api/users', 200, 150)

// Log security events
logger.securityEvent('permission-denied', 'high', { userId, action })
```

#### Performance Monitoring

```typescript
import { useErrorTracking } from '@/hooks/useErrorTracking'

const { measurePerformance } = useErrorTracking('ComponentName')

const expensiveOperation = measurePerformance('operation-name', () => {
  // expensive computation
})
```

## Security Guidelines

### Input Validation

- Validate all user inputs using Zod schemas
- Sanitize HTML content to prevent XSS
- Escape special characters in SQL-like operations

### Authentication

- Implement proper session management
- Use CSRF protection for state-changing operations
- Implement rate limiting for auth endpoints

### Authorization

- Check permissions at the component level
- Verify permissions on the server side
- Use role-based access control (RBAC)

## API Integration

### React Query Setup

```typescript
import { useQuery } from '@tanstack/react-query'
import { useApiErrorTracking } from '@/hooks/useErrorTracking'

function useApiData() {
  const { wrapApiCall } = useApiErrorTracking('ApiComponent')
  
  return useQuery({
    queryKey: ['api-data'],
    queryFn: () => wrapApiCall(
      () => fetch('/api/data').then(res => res.json()),
      'GET',
      '/api/data'
    ),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
```

### Error Handling

- Implement retry logic for transient failures
- Provide meaningful error messages to users
- Log all API errors for debugging

## Performance Optimization

### Bundle Optimization

- Use dynamic imports for code splitting
- Optimize images and assets
- Minimize third-party dependencies

### Runtime Performance

- Implement virtualization for large datasets
- Use React.memo for expensive renders
- Optimize re-renders with proper dependency arrays

### Monitoring

- Track Core Web Vitals
- Monitor bundle sizes
- Measure component render times

## Accessibility

### Requirements

- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- High contrast support

### Implementation

```typescript
// Use semantic HTML
<button onClick={handleClick} aria-label="Save document">
  Save
</button>

// Provide ARIA labels
<div role="tabpanel" aria-labelledby="tab-1">
  Content
</div>

// Support keyboard navigation
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ' ') {
    handleClick()
  }
}
```

## Build and Deployment

### Development

```bash
npm run dev          # Start development server
npm run lint         # Run linting
npm run type-check   # Run TypeScript checks
npm run test         # Run tests
```

### Production

```bash
npm run build        # Build for production
npm run start        # Start production server
npm run test:ci      # Run tests in CI mode
```

### Environment Variables

Required environment variables:

```
NEXT_PUBLIC_API_URL=          # Backend API URL
NEXT_PUBLIC_LOG_ENDPOINT=     # Logging endpoint
JWT_SECRET_KEY=               # JWT signing key
DATABASE_URL=                 # Database connection
```

## Troubleshooting

### Common Issues

1. **Build Failures**: Check TypeScript errors and import paths
2. **Test Failures**: Verify mock setups and async handling
3. **Performance Issues**: Use React DevTools Profiler
4. **Authentication Issues**: Check token expiration and refresh logic

### Debug Tools

- React DevTools
- Redux DevTools (for Zustand)
- Network tab for API debugging
- Console for error messages

## Contributing

1. Follow the established code style and patterns
2. Write comprehensive tests for new features
3. Update documentation for significant changes
4. Use descriptive commit messages
5. Create focused pull requests

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Query Documentation](https://tanstack.com/query/latest)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [Testing Library Documentation](https://testing-library.com/)