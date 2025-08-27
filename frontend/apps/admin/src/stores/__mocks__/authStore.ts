/**
 * Mock implementation of auth store for testing
 */

const mockAuthStore = {
  // State
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  sessionExpiry: null,
  lastActivity: null,

  // Actions
  login: jest.fn().mockResolvedValue({ success: true }),
  logout: jest.fn().mockResolvedValue(undefined),
  refreshToken: jest.fn().mockResolvedValue(true),
  validateSession: jest.fn().mockResolvedValue(true),
  clearError: jest.fn(),
  updateActivity: jest.fn(),
  
  // Computed
  isSessionValid: jest.fn().mockReturnValue(true),
  hasPermission: jest.fn().mockReturnValue(true),
  hasAnyPermission: jest.fn().mockReturnValue(true),
  hasAllPermissions: jest.fn().mockReturnValue(true),
}

// Create a mock with getState method
const useAuthStoreMock = jest.fn().mockReturnValue(mockAuthStore)
useAuthStoreMock.getState = jest.fn().mockReturnValue(mockAuthStore)
useAuthStoreMock.setState = jest.fn()
useAuthStoreMock.subscribe = jest.fn()

export const useAuthStore = useAuthStoreMock

export default { useAuthStore }