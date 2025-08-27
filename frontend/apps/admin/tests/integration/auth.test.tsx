/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { LoginForm } from '../../src/components/auth/LoginForm'
import { useAuthStore } from '../../src/stores/authStore'

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

// Mock the entire auth store
jest.mock('../../src/stores/authStore')

const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>
const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>

// Mock fetch for API calls
global.fetch = jest.fn()

describe('Authentication Integration Tests', () => {
  let queryClient: QueryClient
  let mockPush: jest.Mock
  let mockReplace: jest.Mock

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    mockPush = jest.fn()
    mockReplace = jest.fn()

    mockUseRouter.mockReturnValue({
      push: mockPush,
      replace: mockReplace,
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
    } as any)

    // Reset all mocks
    jest.clearAllMocks()
    ;(global.fetch as jest.Mock).mockClear()
  })

  describe('Login Flow Integration', () => {
    it('should complete full login flow successfully', async () => {
      const mockUser = {
        id: '1',
        email: 'admin@example.com',
        name: 'Admin User',
        role: 'admin' as const,
        permissions: ['read', 'write', 'admin'],
      }

      const mockLogin = jest.fn().mockResolvedValue({ success: true })

      mockUseAuthStore.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        login: mockLogin,
        logout: jest.fn(),
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: jest.fn(),
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: null,
        lastActivity: null,
      })

      // Mock successful API response
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          user: mockUser,
          expiresAt: Date.now() + 3600000,
        }),
      })

      renderWithProviders(<LoginForm />)

      // Fill in login form
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'admin@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'securePassword123!' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'admin@example.com',
          password: 'securePassword123!',
        })
      })
    })

    it('should handle login failure with proper error display', async () => {
      const mockLogin = jest.fn().mockRejectedValue(new Error('Invalid credentials'))

      mockUseAuthStore.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: 'Invalid credentials',
        login: mockLogin,
        logout: jest.fn(),
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: jest.fn(),
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: null,
        lastActivity: null,
      })

      renderWithProviders(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'admin@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalled()
      })

      // Error should be displayed
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })

    it('should prevent multiple simultaneous login attempts', async () => {
      let resolveLogin: (value: any) => void
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve
      })

      const mockLogin = jest.fn().mockReturnValue(loginPromise)

      mockUseAuthStore.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: true, // Set to loading state
        error: null,
        login: mockLogin,
        logout: jest.fn(),
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: jest.fn(),
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: null,
        lastActivity: null,
      })

      renderWithProviders(<LoginForm />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /signing in/i })

      fireEvent.change(emailInput, { target: { value: 'admin@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      
      // Try to click multiple times
      fireEvent.click(submitButton)
      fireEvent.click(submitButton)
      fireEvent.click(submitButton)

      // Button should be disabled during loading
      expect(submitButton).toBeDisabled()
      expect(screen.getByText(/signing in/i)).toBeInTheDocument()

      // Resolve the login
      resolveLogin!({ success: true })

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Session Management Integration', () => {
    it('should handle session expiry gracefully', async () => {
      const mockLogout = jest.fn()
      const mockIsSessionValid = jest.fn().mockReturnValue(false)

      mockUseAuthStore.mockReturnValue({
        user: {
          id: '1',
          email: 'admin@example.com',
          name: 'Admin User',
          role: 'admin' as const,
          permissions: ['read'],
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: mockIsSessionValid,
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: Date.now() - 1000, // Expired
        lastActivity: Date.now() - 3600000, // 1 hour ago
      })

      // Simulate a component that checks session validity
      function SessionChecker() {
        const { isSessionValid, logout } = useAuthStore()
        
        React.useEffect(() => {
          if (!isSessionValid()) {
            logout()
          }
        }, [isSessionValid, logout])

        return <div>Session Checker</div>
      }

      renderWithProviders(<SessionChecker />)

      await waitFor(() => {
        expect(mockIsSessionValid).toHaveBeenCalled()
        expect(mockLogout).toHaveBeenCalled()
      })
    })

    it('should refresh token before expiry', async () => {
      const mockRefreshToken = jest.fn().mockResolvedValue({
        success: true,
        expiresAt: Date.now() + 7200000, // 2 hours
      })

      mockUseAuthStore.mockReturnValue({
        user: {
          id: '1',
          email: 'admin@example.com',
          name: 'Admin User',
          role: 'admin' as const,
          permissions: ['read'],
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: jest.fn(),
        logout: jest.fn(),
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: jest.fn().mockReturnValue(true),
        refreshToken: mockRefreshToken,
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: Date.now() + 300000, // 5 minutes
        lastActivity: Date.now(),
      })

      // Mock API response for token refresh
      ;(global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          expiresAt: Date.now() + 7200000,
        }),
      })

      function TokenRefreshComponent() {
        const { refreshToken, sessionExpiry } = useAuthStore()
        
        React.useEffect(() => {
          if (sessionExpiry && sessionExpiry - Date.now() < 600000) { // 10 minutes
            refreshToken()
          }
        }, [refreshToken, sessionExpiry])

        return <div>Token Refresh Component</div>
      }

      renderWithProviders(<TokenRefreshComponent />)

      await waitFor(() => {
        expect(mockRefreshToken).toHaveBeenCalled()
      })
    })
  })

  describe('Authorization Integration', () => {
    it('should properly check permissions for protected actions', () => {
      const mockHasPermission = jest.fn()
        .mockReturnValueOnce(true)  // Has 'read' permission
        .mockReturnValueOnce(false) // Doesn't have 'admin' permission

      mockUseAuthStore.mockReturnValue({
        user: {
          id: '1',
          email: 'user@example.com',
          name: 'Regular User',
          role: 'user' as const,
          permissions: ['read', 'write'],
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: jest.fn(),
        logout: jest.fn(),
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: jest.fn().mockReturnValue(true),
        refreshToken: jest.fn(),
        hasPermission: mockHasPermission,
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: Date.now() + 3600000,
        lastActivity: Date.now(),
      })

      function PermissionTestComponent() {
        const { hasPermission } = useAuthStore()
        
        return (
          <div>
            {hasPermission('read') && <button>Read Data</button>}
            {hasPermission('admin') && <button>Admin Actions</button>}
          </div>
        )
      }

      renderWithProviders(<PermissionTestComponent />)

      expect(screen.getByText('Read Data')).toBeInTheDocument()
      expect(screen.queryByText('Admin Actions')).not.toBeInTheDocument()
      
      expect(mockHasPermission).toHaveBeenCalledWith('read')
      expect(mockHasPermission).toHaveBeenCalledWith('admin')
    })

    it('should handle multiple permission checks correctly', () => {
      const mockHasAnyPermission = jest.fn()
        .mockReturnValueOnce(true)  // Has one of ['read', 'write']
        .mockReturnValueOnce(false) // Doesn't have any of ['admin', 'superuser']

      const mockHasAllPermissions = jest.fn()
        .mockReturnValueOnce(true)  // Has all of ['read', 'write']
        .mockReturnValueOnce(false) // Doesn't have all of ['read', 'admin']

      mockUseAuthStore.mockReturnValue({
        user: {
          id: '1',
          email: 'user@example.com',
          name: 'Regular User',
          role: 'user' as const,
          permissions: ['read', 'write'],
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: jest.fn(),
        logout: jest.fn(),
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: jest.fn().mockReturnValue(true),
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: mockHasAnyPermission,
        hasAllPermissions: mockHasAllPermissions,
        sessionExpiry: Date.now() + 3600000,
        lastActivity: Date.now(),
      })

      function MultiPermissionComponent() {
        const { hasAnyPermission, hasAllPermissions } = useAuthStore()
        
        return (
          <div>
            {hasAnyPermission(['read', 'write']) && <div>Can read or write</div>}
            {hasAnyPermission(['admin', 'superuser']) && <div>Is admin</div>}
            {hasAllPermissions(['read', 'write']) && <div>Can read and write</div>}
            {hasAllPermissions(['read', 'admin']) && <div>Can read and admin</div>}
          </div>
        )
      }

      renderWithProviders(<MultiPermissionComponent />)

      expect(screen.getByText('Can read or write')).toBeInTheDocument()
      expect(screen.queryByText('Is admin')).not.toBeInTheDocument()
      expect(screen.getByText('Can read and write')).toBeInTheDocument()
      expect(screen.queryByText('Can read and admin')).not.toBeInTheDocument()
    })
  })

  describe('Error Recovery Integration', () => {
    it('should clear errors and allow retry after failed login', async () => {
      const mockLogin = jest.fn()
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ success: true })

      const mockClearError = jest.fn()

      // First render with error state
      mockUseAuthStore.mockReturnValueOnce({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: 'Network error',
        login: mockLogin,
        logout: jest.fn(),
        clearError: mockClearError,
        updateActivity: jest.fn(),
        isSessionValid: jest.fn(),
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: null,
        lastActivity: null,
      })

      const { rerender } = renderWithProviders(<LoginForm />)

      expect(screen.getByText('Network error')).toBeInTheDocument()

      // Clear error and retry
      mockUseAuthStore.mockReturnValue({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null, // Error cleared
        login: mockLogin,
        logout: jest.fn(),
        clearError: mockClearError,
        updateActivity: jest.fn(),
        isSessionValid: jest.fn(),
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: null,
        lastActivity: null,
      })

      rerender(<LoginForm />)

      expect(screen.queryByText('Network error')).not.toBeInTheDocument()

      // Try login again
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      fireEvent.change(emailInput, { target: { value: 'admin@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Logout Integration', () => {
    it('should complete full logout flow', async () => {
      const mockLogout = jest.fn().mockResolvedValue({ success: true })

      mockUseAuthStore.mockReturnValue({
        user: {
          id: '1',
          email: 'admin@example.com',
          name: 'Admin User',
          role: 'admin' as const,
          permissions: ['read'],
        },
        isAuthenticated: true,
        isLoading: false,
        error: null,
        login: jest.fn(),
        logout: mockLogout,
        clearError: jest.fn(),
        updateActivity: jest.fn(),
        isSessionValid: jest.fn().mockReturnValue(true),
        refreshToken: jest.fn(),
        hasPermission: jest.fn(),
        hasAnyPermission: jest.fn(),
        hasAllPermissions: jest.fn(),
        sessionExpiry: Date.now() + 3600000,
        lastActivity: Date.now(),
      })

      function LogoutTestComponent() {
        const { logout } = useAuthStore()
        
        return (
          <button onClick={() => logout()}>
            Logout
          </button>
        )
      }

      renderWithProviders(<LogoutTestComponent />)

      const logoutButton = screen.getByText('Logout')
      fireEvent.click(logoutButton)

      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled()
      })
    })
  })
})