import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { ManagementAuthProvider, useManagementAuth } from '../../auth/ManagementAuthProvider';
import { API } from '@/lib/api/endpoints';
import { tokenManager } from '@/lib/auth/token-manager';

// Mock dependencies
jest.mock('next/navigation');
jest.mock('@/lib/api/endpoints');
jest.mock('@/lib/auth/token-manager');
jest.mock('@/store', () => ({
  useAuthActions: () => ({
    setUser: jest.fn(),
    clearAuth: jest.fn(),
    updateLastActivity: jest.fn(),
  }),
}));

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
};

const mockTokenManager = tokenManager as jest.Mocked<typeof tokenManager>;
const mockAPI = API as jest.Mocked<typeof API>;

// Test component that uses the auth context
function TestComponent() {
  const {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    hasPermission,
    canManageResellers,
    canApproveCommissions,
    canViewAnalytics,
  } = useManagementAuth();

  if (isLoading) {
    return <div data-testid='loading'>Loading...</div>;
  }

  return (
    <div data-testid='auth-info'>
      <div data-testid='authenticated'>{isAuthenticated ? 'true' : 'false'}</div>
      {user && (
        <>
          <div data-testid='user-email'>{user.email}</div>
          <div data-testid='user-role'>{user.role}</div>
          <div data-testid='user-permissions'>{user.permissions.join(',')}</div>
        </>
      )}
      <div data-testid='can-manage-resellers'>{canManageResellers() ? 'true' : 'false'}</div>
      <div data-testid='can-approve-commissions'>{canApproveCommissions() ? 'true' : 'false'}</div>
      <div data-testid='can-view-analytics'>{canViewAnalytics() ? 'true' : 'false'}</div>
      <button onClick={() => login({ email: 'test@example.com', password: 'password' })}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
      <button onClick={() => hasPermission('MANAGE_RESELLERS')}>Check Permission</button>
    </div>
  );
}

describe('ManagementAuthProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    sessionStorage.clear();

    // Default mocks
    mockTokenManager.getAccessToken.mockResolvedValue(null);
    mockTokenManager.setTokens.mockResolvedValue(undefined);
    mockTokenManager.clearTokens.mockResolvedValue(undefined);

    global.fetch = jest.fn();
  });

  it('should render loading state initially', () => {
    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('should handle successful login', async () => {
    const mockLoginResponse = {
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      user: {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'channel_manager',
        last_login: new Date().toISOString(),
      },
    };

    mockAPI.auth = {
      login: jest.fn().mockResolvedValue(mockLoginResponse),
      logout: jest.fn().mockResolvedValue(undefined),
    };

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-info')).toBeInTheDocument();
    });

    const loginButton = screen.getByText('Login');
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(mockAPI.auth.login).toHaveBeenCalledWith('test@example.com', 'password');
      expect(mockTokenManager.setTokens).toHaveBeenCalledWith(
        'mock-access-token',
        'mock-refresh-token'
      );
      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard');
    });

    // Check that user is set in sessionStorage
    const storedUser = sessionStorage.getItem('management_user');
    expect(storedUser).toBeTruthy();

    const parsedUser = JSON.parse(storedUser!);
    expect(parsedUser.email).toBe('test@example.com');
    expect(parsedUser.role).toBe('CHANNEL_MANAGER');
  });

  it('should handle login error', async () => {
    const loginError = new Error('Invalid credentials');
    mockAPI.auth = {
      login: jest.fn().mockRejectedValue(loginError),
      logout: jest.fn().mockResolvedValue(undefined),
    };

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-info')).toBeInTheDocument();
    });

    const loginButton = screen.getByText('Login');

    await expect(async () => {
      fireEvent.click(loginButton);
      await waitFor(() => {
        expect(mockAPI.auth.login).toHaveBeenCalled();
      });
    }).rejects.toThrow('Invalid credentials');
  });

  it('should handle logout', async () => {
    // Set up authenticated state
    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'CHANNEL_MANAGER' as const,
      permissions: ['MANAGE_RESELLERS'],
      departments: ['Channel Operations'],
      last_login: new Date(),
    };

    sessionStorage.setItem('management_user', JSON.stringify(mockUser));
    mockTokenManager.getAccessToken.mockResolvedValue('mock-token');

    mockAPI.auth = {
      login: jest.fn(),
      logout: jest.fn().mockResolvedValue(undefined),
    };

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });

    const logoutButton = screen.getByText('Logout');
    fireEvent.click(logoutButton);

    await waitFor(() => {
      expect(mockAPI.auth.logout).toHaveBeenCalled();
      expect(mockTokenManager.clearTokens).toHaveBeenCalled();
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
      expect(sessionStorage.getItem('management_user')).toBeNull();
    });
  });

  it('should handle logout API failure gracefully', async () => {
    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'CHANNEL_MANAGER' as const,
      permissions: ['MANAGE_RESELLERS'],
      departments: ['Channel Operations'],
      last_login: new Date(),
    };

    sessionStorage.setItem('management_user', JSON.stringify(mockUser));
    mockTokenManager.getAccessToken.mockResolvedValue('mock-token');

    mockAPI.auth = {
      login: jest.fn(),
      logout: jest.fn().mockRejectedValue(new Error('Logout failed')),
    };

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    });

    const logoutButton = screen.getByText('Logout');
    fireEvent.click(logoutButton);

    await waitFor(() => {
      // Should still clean up client-side state even if API fails
      expect(mockTokenManager.clearTokens).toHaveBeenCalled();
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
      expect(sessionStorage.getItem('management_user')).toBeNull();
    });
  });

  it('should check permissions correctly', async () => {
    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'CHANNEL_MANAGER' as const,
      permissions: ['MANAGE_RESELLERS', 'APPROVE_COMMISSIONS', 'VIEW_ANALYTICS'],
      departments: ['Channel Operations'],
      last_login: new Date(),
    };

    sessionStorage.setItem('management_user', JSON.stringify(mockUser));
    mockTokenManager.getAccessToken.mockResolvedValue('mock-token');

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('can-manage-resellers')).toHaveTextContent('true');
      expect(screen.getByTestId('can-approve-commissions')).toHaveTextContent('true');
      expect(screen.getByTestId('can-view-analytics')).toHaveTextContent('true');
    });
  });

  it('should handle master admin permissions', async () => {
    const mockUser = {
      id: 'user-1',
      email: 'admin@example.com',
      name: 'Admin User',
      role: 'MASTER_ADMIN' as const,
      permissions: ['VIEW_DASHBOARD'],
      departments: ['Platform Administration'],
      last_login: new Date(),
    };

    sessionStorage.setItem('management_user', JSON.stringify(mockUser));
    mockTokenManager.getAccessToken.mockResolvedValue('mock-token');

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user-role')).toHaveTextContent('MASTER_ADMIN');
      // Master admin should have access to everything
      expect(screen.getByTestId('can-manage-resellers')).toHaveTextContent('true');
      expect(screen.getByTestId('can-approve-commissions')).toHaveTextContent('true');
      expect(screen.getByTestId('can-view-analytics')).toHaveTextContent('true');
    });
  });

  it('should redirect to login when not authenticated', async () => {
    (useRouter as jest.Mock).mockReturnValue({
      ...mockRouter,
      pathname: '/dashboard', // User is trying to access protected route
    });

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
    });
  });

  it('should not redirect when on login page', async () => {
    (useRouter as jest.Mock).mockReturnValue({
      ...mockRouter,
      pathname: '/login',
    });

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('auth-info')).toBeInTheDocument();
    });

    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  it('should handle token refresh failure', async () => {
    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'CHANNEL_MANAGER' as const,
      permissions: ['MANAGE_RESELLERS'],
      departments: ['Channel Operations'],
      last_login: new Date(),
    };

    sessionStorage.setItem('management_user', JSON.stringify(mockUser));
    mockTokenManager.getAccessToken.mockResolvedValue(null);

    // Mock fetch to fail
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
    });

    mockAPI.auth = {
      login: jest.fn(),
      logout: jest.fn().mockResolvedValue(undefined),
    };

    render(
      <ManagementAuthProvider>
        <TestComponent />
      </ManagementAuthProvider>
    );

    await waitFor(() => {
      expect(mockTokenManager.clearTokens).toHaveBeenCalled();
      expect(mockRouter.push).toHaveBeenCalledWith('/login');
    });
  });

  it('should throw error when used outside provider', () => {
    // Suppress console error for this test
    const originalError = console.error;
    console.error = jest.fn();

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useManagementAuth must be used within a ManagementAuthProvider');

    console.error = originalError;
  });
});
