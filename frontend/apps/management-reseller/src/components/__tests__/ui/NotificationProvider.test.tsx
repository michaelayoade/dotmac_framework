import { render, screen, act, waitFor } from '@testing-library/react'
import { toast } from 'sonner'
import { NotificationProvider } from '../../ui/NotificationProvider'
import { useAppStore } from '@/store'

// Mock Sonner
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
    info: jest.fn(),
    dismiss: jest.fn(),
  },
  Toaster: ({ children }: { children: React.ReactNode }) => <div data-testid="toaster">{children}</div>,
}))

// Mock store
jest.mock('@/store', () => ({
  useAppStore: jest.fn(),
}))

const mockToast = toast as jest.Mocked<typeof toast>

describe('NotificationProvider', () => {
  let mockStore: any

  beforeEach(() => {
    jest.clearAllMocks()
    
    // Default mock store
    mockStore = {
      notifications: [],
      addNotification: jest.fn(),
      removeNotification: jest.fn(),
      clearNotifications: jest.fn(),
    }
    
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)
  })

  it('should render Toaster component', () => {
    render(<NotificationProvider />)
    expect(screen.getByTestId('toaster')).toBeInTheDocument()
  })

  it('should display success notification', async () => {
    const notification = {
      id: '1',
      type: 'success' as const,
      title: 'Success!',
      message: 'Operation completed successfully',
      duration: 5000,
      timestamp: Date.now(),
    }

    // Update mock to return notification
    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith('Success!', {
        description: 'Operation completed successfully',
        duration: 5000,
        id: '1',
      })
    })
  })

  it('should display error notification', async () => {
    const notification = {
      id: '2',
      type: 'error' as const,
      title: 'Error!',
      message: 'Something went wrong',
      duration: 0, // Persist until dismissed
      timestamp: Date.now(),
    }

    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith('Error!', {
        description: 'Something went wrong',
        duration: Infinity, // 0 duration becomes Infinity
        id: '2',
      })
    })
  })

  it('should display warning notification', async () => {
    const notification = {
      id: '3',
      type: 'warning' as const,
      title: 'Warning!',
      message: 'Please check your input',
      duration: 8000,
      timestamp: Date.now(),
    }

    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.warning).toHaveBeenCalledWith('Warning!', {
        description: 'Please check your input',
        duration: 8000,
        id: '3',
      })
    })
  })

  it('should display info notification', async () => {
    const notification = {
      id: '4',
      type: 'info' as const,
      title: 'Information',
      message: 'Here is some useful info',
      duration: 3000,
      timestamp: Date.now(),
    }

    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.info).toHaveBeenCalledWith('Information', {
        description: 'Here is some useful info',
        duration: 3000,
        id: '4',
      })
    })
  })

  it('should handle notification without message', async () => {
    const notification = {
      id: '5',
      type: 'success' as const,
      title: 'Title Only',
      message: '',
      duration: 5000,
      timestamp: Date.now(),
    }

    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith('Title Only', {
        description: undefined, // Empty message becomes undefined
        duration: 5000,
        id: '5',
      })
    })
  })

  it('should handle multiple notifications', async () => {
    const notifications = [
      {
        id: '1',
        type: 'success' as const,
        title: 'Success 1',
        message: 'First success',
        duration: 5000,
        timestamp: Date.now(),
      },
      {
        id: '2',
        type: 'error' as const,
        title: 'Error 1',
        message: 'First error',
        duration: 0,
        timestamp: Date.now() + 1000,
      },
    ]

    mockStore.notifications = notifications
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith('Success 1', {
        description: 'First success',
        duration: 5000,
        id: '1',
      })
      
      expect(mockToast.error).toHaveBeenCalledWith('Error 1', {
        description: 'First error',
        duration: Infinity,
        id: '2',
      })
    })
  })

  it('should handle dynamic notification updates', async () => {
    const { rerender } = render(<NotificationProvider />)

    // Initially no notifications
    expect(mockToast.success).not.toHaveBeenCalled()

    // Add a notification
    const notification = {
      id: '1',
      type: 'info' as const,
      title: 'New Info',
      message: 'Dynamic notification',
      duration: 4000,
      timestamp: Date.now(),
    }

    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    rerender(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.info).toHaveBeenCalledWith('New Info', {
        description: 'Dynamic notification',
        duration: 4000,
        id: '1',
      })
    })
  })

  it('should remove notifications from displayed set when they disappear from store', async () => {
    const notification = {
      id: '1',
      type: 'success' as const,
      title: 'Temporary',
      message: 'Will be removed',
      duration: 5000,
      timestamp: Date.now(),
    }

    // Start with notification
    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    const { rerender } = render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledTimes(1)
    })

    // Remove notification from store
    mockStore.notifications = []
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    rerender(<NotificationProvider />)

    // Should not call toast methods again for removed notifications
    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledTimes(1) // Still only called once
    })
  })

  it('should handle unknown notification types gracefully', async () => {
    const notification = {
      id: '1',
      type: 'unknown' as any,
      title: 'Unknown Type',
      message: 'This should default to info',
      duration: 5000,
      timestamp: Date.now(),
    }

    mockStore.notifications = [notification]
    ;(useAppStore as jest.Mock).mockReturnValue(mockStore)

    render(<NotificationProvider />)

    await waitFor(() => {
      expect(mockToast.info).toHaveBeenCalledWith('Unknown Type', {
        description: 'This should default to info',
        duration: 5000,
        id: '1',
      })
    })
  })
})