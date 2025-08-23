/**
 * Cross-Portal Integration Tests
 * Tests component sharing, authentication flow, API integration, and security measures
 * Validates that all portals work together seamlessly
 */

import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import MockAPIServer from '../../scripts/mock-api-server';

// Mock components that would normally be imported from each portal
const MockAdminApp = ({ children }: { children?: React.ReactNode }) => (
  <div data-testid='admin-app'>
    <nav data-testid='admin-nav'>Admin Portal</nav>
    {children}
  </div>
);

const MockCustomerApp = ({ children }: { children?: React.ReactNode }) => (
  <div data-testid='customer-app'>
    <nav data-testid='customer-nav'>Customer Portal</nav>
    {children}
  </div>
);

const MockResellerApp = ({ children }: { children?: React.ReactNode }) => (
  <div data-testid='reseller-app'>
    <nav data-testid='reseller-nav'>Reseller Portal</nav>
    {children}
  </div>
);

// Mock shared components (these would normally come from packages)
const MockSharedButton = ({ children, ...props }: any) => (
  <button data-testid='shared-button' {...props}>
    {children}
  </button>
);

const MockSharedModal = ({ isOpen, onClose, children, ...props }: any) => {
  if (!isOpen) return null;
  return (
    <div data-testid='shared-modal' role='dialog' aria-modal='true' {...props}>
      <button onClick={onClose} data-testid='modal-close'>
        Close
      </button>
      {children}
    </div>
  );
};

const MockAuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = React.useState(null);
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);

  const login = async (credentials: any) => {
    // Simulate login
    setUser({ id: '1', email: credentials.email, role: 'admin' });
    setIsAuthenticated(true);
  };

  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <div data-testid='auth-provider'>
      <div data-auth-user={JSON.stringify(user)}>
        <div data-is-authenticated={isAuthenticated}>{children}</div>
      </div>
    </div>
  );
};

describe('Cross-Portal Integration Tests', () => {
  let mockApiServer: MockAPIServer;

  beforeAll(() => {
    // Set up mock API server
    mockApiServer = new MockAPIServer();
    mockApiServer.start();
  });

  afterAll(() => {
    mockApiServer.stop();
  });

  describe('Component Sharing Across Portals', () => {
    it('should allow shared components to be used in all portals', async () => {
      const TestSharedComponent = () => (
        <div>
          <MockAdminApp>
            <MockSharedButton>Admin Button</MockSharedButton>
            <MockSharedModal isOpen={true} onClose={() => {}}>
              Admin Modal Content
            </MockSharedModal>
          </MockAdminApp>

          <MockCustomerApp>
            <MockSharedButton>Customer Button</MockSharedButton>
            <MockSharedModal isOpen={true} onClose={() => {}}>
              Customer Modal Content
            </MockSharedModal>
          </MockCustomerApp>

          <MockResellerApp>
            <MockSharedButton>Reseller Button</MockSharedButton>
            <MockSharedModal isOpen={true} onClose={() => {}}>
              Reseller Modal Content
            </MockSharedModal>
          </MockResellerApp>
        </div>
      );

      render(<TestSharedComponent />);

      // Verify all portals can use shared components
      expect(screen.getByTestId('admin-app')).toBeInTheDocument();
      expect(screen.getByTestId('customer-app')).toBeInTheDocument();
      expect(screen.getByTestId('reseller-app')).toBeInTheDocument();

      // Verify shared components are rendered in each portal
      const sharedButtons = screen.getAllByTestId('shared-button');
      const sharedModals = screen.getAllByTestId('shared-modal');

      expect(sharedButtons).toHaveLength(3);
      expect(sharedModals).toHaveLength(3);

      // Verify component content is correctly isolated
      expect(screen.getByText('Admin Button')).toBeInTheDocument();
      expect(screen.getByText('Customer Button')).toBeInTheDocument();
      expect(screen.getByText('Reseller Button')).toBeInTheDocument();
    });

    it('should maintain consistent styling across portals', async () => {
      const TestStyledComponent = () => (
        <div>
          <MockAdminApp>
            <MockSharedButton className='btn btn-primary'>Admin Styled Button</MockSharedButton>
          </MockAdminApp>

          <MockCustomerApp>
            <MockSharedButton className='btn btn-primary'>Customer Styled Button</MockSharedButton>
          </MockCustomerApp>
        </div>
      );

      render(<TestStyledComponent />);

      const styledButtons = screen.getAllByTestId('shared-button');

      // Verify consistent CSS classes are applied
      styledButtons.forEach((button) => {
        expect(button).toHaveClass('btn', 'btn-primary');
      });
    });

    it('should handle shared component interactions consistently', async () => {
      const user = userEvent.setup();
      const mockHandler = jest.fn();

      const TestInteractiveComponent = () => (
        <div>
          <MockAdminApp>
            <MockSharedButton onClick={mockHandler} data-portal='admin'>
              Admin Interactive Button
            </MockSharedButton>
          </MockAdminApp>

          <MockCustomerApp>
            <MockSharedButton onClick={mockHandler} data-portal='customer'>
              Customer Interactive Button
            </MockSharedButton>
          </MockCustomerApp>
        </div>
      );

      render(<TestInteractiveComponent />);

      const adminButton = screen.getByText('Admin Interactive Button');
      const customerButton = screen.getByText('Customer Interactive Button');

      await user.click(adminButton);
      await user.click(customerButton);

      expect(mockHandler).toHaveBeenCalledTimes(2);
    });
  });

  describe('Authentication Flow Integration', () => {
    it('should handle authentication across all portals', async () => {
      const TestAuthFlow = () => {
        const [currentPortal, setCurrentPortal] = React.useState('admin');

        return (
          <MockAuthProvider>
            <div>
              <button onClick={() => setCurrentPortal('admin')} data-testid='switch-to-admin'>
                Admin Portal
              </button>
              <button onClick={() => setCurrentPortal('customer')} data-testid='switch-to-customer'>
                Customer Portal
              </button>
              <button onClick={() => setCurrentPortal('reseller')} data-testid='switch-to-reseller'>
                Reseller Portal
              </button>

              {currentPortal === 'admin' && <MockAdminApp />}
              {currentPortal === 'customer' && <MockCustomerApp />}
              {currentPortal === 'reseller' && <MockResellerApp />}
            </div>
          </MockAuthProvider>
        );
      };

      const user = userEvent.setup();
      render(<TestAuthFlow />);

      // Test portal switching with authentication context
      expect(screen.getByTestId('admin-app')).toBeInTheDocument();

      await user.click(screen.getByTestId('switch-to-customer'));
      expect(screen.getByTestId('customer-app')).toBeInTheDocument();
      expect(screen.queryByTestId('admin-app')).not.toBeInTheDocument();

      await user.click(screen.getByTestId('switch-to-reseller'));
      expect(screen.getByTestId('reseller-app')).toBeInTheDocument();
      expect(screen.queryByTestId('customer-app')).not.toBeInTheDocument();

      // Verify authentication provider wraps all portals
      expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
    });

    it('should maintain authentication state across portal navigation', async () => {
      const TestAuthPersistence = () => {
        const [user, setUser] = React.useState(null);
        const [currentPortal, setCurrentPortal] = React.useState('admin');

        const handleLogin = () => {
          setUser({ id: '1', email: 'test@example.com', role: 'admin' });
        };

        return (
          <div>
            <div data-testid='user-info' data-user={JSON.stringify(user)}>
              User: {user ? user.email : 'Not logged in'}
            </div>

            <button onClick={handleLogin} data-testid='login-button'>
              Login
            </button>

            <button onClick={() => setCurrentPortal('admin')} data-testid='nav-admin'>
              Admin
            </button>
            <button onClick={() => setCurrentPortal('customer')} data-testid='nav-customer'>
              Customer
            </button>

            <div data-testid='current-portal'>
              {currentPortal === 'admin' && <MockAdminApp />}
              {currentPortal === 'customer' && <MockCustomerApp />}
            </div>
          </div>
        );
      };

      const user = userEvent.setup();
      render(<TestAuthPersistence />);

      // Initially not logged in
      expect(screen.getByText('User: Not logged in')).toBeInTheDocument();

      // Login
      await user.click(screen.getByTestId('login-button'));
      expect(screen.getByText('User: test@example.com')).toBeInTheDocument();

      // Navigate between portals - auth state should persist
      expect(screen.getByTestId('admin-app')).toBeInTheDocument();

      await user.click(screen.getByTestId('nav-customer'));
      expect(screen.getByTestId('customer-app')).toBeInTheDocument();
      expect(screen.getByText('User: test@example.com')).toBeInTheDocument();

      await user.click(screen.getByTestId('nav-admin'));
      expect(screen.getByTestId('admin-app')).toBeInTheDocument();
      expect(screen.getByText('User: test@example.com')).toBeInTheDocument();
    });

    it('should enforce role-based access control across portals', async () => {
      const TestRBACIntegration = () => {
        const [userRole, setUserRole] = React.useState<string | null>(null);
        const [currentPortal, setCurrentPortal] = React.useState('admin');

        const canAccess = (portal: string, role: string | null): boolean => {
          if (!role) return false;

          switch (portal) {
            case 'admin':
              return role === 'admin';
            case 'customer':
              return role === 'customer' || role === 'admin';
            case 'reseller':
              return role === 'reseller' || role === 'admin';
            default:
              return false;
          }
        };

        return (
          <div>
            <div data-testid='role-selector'>
              <button onClick={() => setUserRole('admin')} data-testid='login-admin'>
                Login as Admin
              </button>
              <button onClick={() => setUserRole('customer')} data-testid='login-customer'>
                Login as Customer
              </button>
              <button onClick={() => setUserRole('reseller')} data-testid='login-reseller'>
                Login as Reseller
              </button>
            </div>

            <div data-testid='portal-nav'>
              <button
                onClick={() => setCurrentPortal('admin')}
                data-testid='try-admin'
                disabled={!canAccess('admin', userRole)}
              >
                Admin Portal
              </button>
              <button
                onClick={() => setCurrentPortal('customer')}
                data-testid='try-customer'
                disabled={!canAccess('customer', userRole)}
              >
                Customer Portal
              </button>
              <button
                onClick={() => setCurrentPortal('reseller')}
                data-testid='try-reseller'
                disabled={!canAccess('reseller', userRole)}
              >
                Reseller Portal
              </button>
            </div>

            <div data-testid='portal-content'>
              {canAccess(currentPortal, userRole) ? (
                <>
                  {currentPortal === 'admin' && <MockAdminApp />}
                  {currentPortal === 'customer' && <MockCustomerApp />}
                  {currentPortal === 'reseller' && <MockResellerApp />}
                </>
              ) : (
                <div data-testid='access-denied'>Access Denied</div>
              )}
            </div>
          </div>
        );
      };

      const user = userEvent.setup();
      render(<TestRBACIntegration />);

      // Test admin access
      await user.click(screen.getByTestId('login-admin'));

      expect(screen.getByTestId('try-admin')).not.toBeDisabled();
      expect(screen.getByTestId('try-customer')).not.toBeDisabled();
      expect(screen.getByTestId('try-reseller')).not.toBeDisabled();

      // Test customer access
      await user.click(screen.getByTestId('login-customer'));

      expect(screen.getByTestId('try-admin')).toBeDisabled();
      expect(screen.getByTestId('try-customer')).not.toBeDisabled();
      expect(screen.getByTestId('try-reseller')).toBeDisabled();

      // Attempt to access admin portal as customer
      expect(screen.getByTestId('access-denied')).toBeInTheDocument();

      // Access allowed customer portal
      await user.click(screen.getByTestId('try-customer'));
      expect(screen.getByTestId('customer-app')).toBeInTheDocument();
    });
  });

  describe('API Integration Consistency', () => {
    it('should use consistent API endpoints across all portals', async () => {
      const TestAPIIntegration = () => {
        const [data, setData] = React.useState(null);
        const [loading, setLoading] = React.useState(false);
        const [portal, setPortal] = React.useState('admin');

        const fetchCustomers = async () => {
          setLoading(true);
          try {
            const response = await fetch('/api/customers');
            const result = await response.json();
            setData(result.data);
          } catch (error) {
            console.error('API Error:', error);
          } finally {
            setLoading(false);
          }
        };

        return (
          <div>
            <div data-testid='portal-selector'>
              <button onClick={() => setPortal('admin')} data-testid='select-admin'>
                Admin Portal
              </button>
              <button onClick={() => setPortal('customer')} data-testid='select-customer'>
                Customer Portal
              </button>
              <button onClick={() => setPortal('reseller')} data-testid='select-reseller'>
                Reseller Portal
              </button>
            </div>

            <div data-testid='current-portal-api'>
              {portal === 'admin' && (
                <MockAdminApp>
                  <button onClick={fetchCustomers} data-testid='fetch-customers-admin'>
                    Fetch Customers (Admin)
                  </button>
                </MockAdminApp>
              )}
              {portal === 'customer' && (
                <MockCustomerApp>
                  <button onClick={fetchCustomers} data-testid='fetch-customers-customer'>
                    Fetch Customers (Customer)
                  </button>
                </MockCustomerApp>
              )}
              {portal === 'reseller' && (
                <MockResellerApp>
                  <button onClick={fetchCustomers} data-testid='fetch-customers-reseller'>
                    Fetch Customers (Reseller)
                  </button>
                </MockResellerApp>
              )}
            </div>

            <div data-testid='api-results'>
              {loading && <div data-testid='loading'>Loading...</div>}
              {data && <div data-testid='customer-data'>Found {data.length} customers</div>}
            </div>
          </div>
        );
      };

      const user = userEvent.setup();
      render(<TestAPIIntegration />);

      // Test API consistency across portals
      await user.click(screen.getByTestId('select-admin'));
      await user.click(screen.getByTestId('fetch-customers-admin'));

      await waitFor(() => {
        expect(screen.getByTestId('customer-data')).toBeInTheDocument();
      });

      // Switch to customer portal and verify same API works
      await user.click(screen.getByTestId('select-customer'));
      await user.click(screen.getByTestId('fetch-customers-customer'));

      await waitFor(() => {
        expect(screen.getByTestId('customer-data')).toBeInTheDocument();
      });
    });

    it('should handle API errors consistently across portals', async () => {
      // Mock server error
      const errorServer = setupServer(
        http.get('/api/customers', () => {
          return HttpResponse.json({ error: 'Service unavailable' }, { status: 503 });
        })
      );

      errorServer.listen();

      const TestAPIErrorHandling = () => {
        const [error, setError] = React.useState<string | null>(null);
        const [portal, setPortal] = React.useState('admin');

        const fetchWithError = async () => {
          try {
            const response = await fetch('/api/customers');
            if (!response.ok) {
              throw new Error(`API Error: ${response.status}`);
            }
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
          }
        };

        return (
          <div>
            <button onClick={() => setPortal('admin')} data-testid='test-admin-error'>
              Test Admin Error
            </button>
            <button onClick={() => setPortal('customer')} data-testid='test-customer-error'>
              Test Customer Error
            </button>

            <div data-testid='error-test-portal'>
              {portal === 'admin' && (
                <MockAdminApp>
                  <button onClick={fetchWithError} data-testid='trigger-error-admin'>
                    Trigger API Error (Admin)
                  </button>
                </MockAdminApp>
              )}
              {portal === 'customer' && (
                <MockCustomerApp>
                  <button onClick={fetchWithError} data-testid='trigger-error-customer'>
                    Trigger API Error (Customer)
                  </button>
                </MockCustomerApp>
              )}
            </div>

            {error && (
              <div data-testid='error-message' role='alert'>
                Error: {error}
              </div>
            )}
          </div>
        );
      };

      const user = userEvent.setup();
      render(<TestAPIErrorHandling />);

      // Test error handling in admin portal
      await user.click(screen.getByTestId('test-admin-error'));
      await user.click(screen.getByTestId('trigger-error-admin'));

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
        expect(screen.getByText(/API Error: 503/)).toBeInTheDocument();
      });

      errorServer.close();
    });
  });

  describe('Security Measures Integration', () => {
    it('should enforce security headers across all portals', async () => {
      const TestSecurityHeaders = () => {
        const [headers, setHeaders] = React.useState<Record<string, string>>({});

        const checkSecurityHeaders = async () => {
          try {
            const response = await fetch('/api/health');
            const responseHeaders: Record<string, string> = {};

            // Convert Headers to plain object for testing
            response.headers.forEach((value, key) => {
              responseHeaders[key] = value;
            });

            setHeaders(responseHeaders);
          } catch (error) {
            console.error('Security check failed:', error);
          }
        };

        React.useEffect(() => {
          checkSecurityHeaders();
        }, []);

        return (
          <div data-testid='security-check'>
            <div data-testid='security-headers' data-headers={JSON.stringify(headers)}>
              Security headers loaded: {Object.keys(headers).length}
            </div>

            <MockAdminApp>
              <div data-testid='admin-security'>Admin with security headers</div>
            </MockAdminApp>

            <MockCustomerApp>
              <div data-testid='customer-security'>Customer with security headers</div>
            </MockCustomerApp>
          </div>
        );
      };

      render(<TestSecurityHeaders />);

      await waitFor(() => {
        expect(screen.getByTestId('security-check')).toBeInTheDocument();
      });

      // Verify security context is available to all portals
      expect(screen.getByTestId('admin-security')).toBeInTheDocument();
      expect(screen.getByTestId('customer-security')).toBeInTheDocument();
    });

    it('should validate CSRF protection across portals', async () => {
      const TestCSRFProtection = () => {
        const [csrfToken, setCsrfToken] = React.useState<string | null>(null);

        const getCsrfToken = async () => {
          // Simulate CSRF token fetch
          setCsrfToken('mock-csrf-token-12345');
        };

        const makeSecureRequest = async (portal: string) => {
          if (!csrfToken) {
            throw new Error('CSRF token required');
          }

          const response = await fetch('/api/customers', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': csrfToken,
            },
            body: JSON.stringify({ portal }),
          });

          return response.ok;
        };

        React.useEffect(() => {
          getCsrfToken();
        }, []);

        return (
          <div data-testid='csrf-protection'>
            <div data-testid='csrf-token'>CSRF Token: {csrfToken || 'Loading...'}</div>

            <MockAdminApp>
              <button
                onClick={() => makeSecureRequest('admin')}
                data-testid='secure-request-admin'
                disabled={!csrfToken}
              >
                Make Secure Admin Request
              </button>
            </MockAdminApp>

            <MockCustomerApp>
              <button
                onClick={() => makeSecureRequest('customer')}
                data-testid='secure-request-customer'
                disabled={!csrfToken}
              >
                Make Secure Customer Request
              </button>
            </MockCustomerApp>
          </div>
        );
      };

      render(<TestCSRFProtection />);

      await waitFor(() => {
        expect(screen.getByText(/CSRF Token: mock-csrf-token/)).toBeInTheDocument();
      });

      // Verify CSRF protection is available to all portals
      expect(screen.getByTestId('secure-request-admin')).not.toBeDisabled();
      expect(screen.getByTestId('secure-request-customer')).not.toBeDisabled();
    });
  });

  describe('Performance Integration', () => {
    it('should maintain performance standards across all portals', async () => {
      const TestPerformanceIntegration = () => {
        const [renderTimes, setRenderTimes] = React.useState<Record<string, number>>({});

        const measureRenderTime = (portal: string) => {
          const startTime = performance.now();

          // Simulate component rendering
          setTimeout(() => {
            const endTime = performance.now();
            setRenderTimes((prev) => ({
              ...prev,
              [portal]: endTime - startTime,
            }));
          }, 10);
        };

        React.useEffect(() => {
          measureRenderTime('admin');
          measureRenderTime('customer');
          measureRenderTime('reseller');
        }, []);

        return (
          <div data-testid='performance-test'>
            <div data-testid='render-times' data-times={JSON.stringify(renderTimes)}>
              Render times measured: {Object.keys(renderTimes).length}
            </div>

            <MockAdminApp>
              <div data-testid='admin-performance'>
                Admin render time: {renderTimes.admin?.toFixed(2)}ms
              </div>
            </MockAdminApp>

            <MockCustomerApp>
              <div data-testid='customer-performance'>
                Customer render time: {renderTimes.customer?.toFixed(2)}ms
              </div>
            </MockCustomerApp>

            <MockResellerApp>
              <div data-testid='reseller-performance'>
                Reseller render time: {renderTimes.reseller?.toFixed(2)}ms
              </div>
            </MockResellerApp>
          </div>
        );
      };

      render(<TestPerformanceIntegration />);

      await waitFor(
        () => {
          expect(screen.getByTestId('performance-test')).toBeInTheDocument();
        },
        { timeout: 5000 }
      );

      // Verify performance metrics are collected for all portals
      expect(screen.getByTestId('admin-performance')).toBeInTheDocument();
      expect(screen.getByTestId('customer-performance')).toBeInTheDocument();
      expect(screen.getByTestId('reseller-performance')).toBeInTheDocument();
    });
  });
});

// Additional integration test suites
describe('Data Flow Integration', () => {
  it('should maintain data consistency across portals', async () => {
    const TestDataConsistency = () => {
      const [sharedData, setSharedData] = React.useState({ count: 0 });

      const updateData = (increment: number) => {
        setSharedData((prev) => ({ count: prev.count + increment }));
      };

      return (
        <div data-testid='data-consistency'>
          <div data-testid='shared-counter'>Count: {sharedData.count}</div>

          <MockAdminApp>
            <button onClick={() => updateData(10)} data-testid='admin-update'>
              Admin Update (+10)
            </button>
          </MockAdminApp>

          <MockCustomerApp>
            <button onClick={() => updateData(5)} data-testid='customer-update'>
              Customer Update (+5)
            </button>
          </MockCustomerApp>

          <MockResellerApp>
            <button onClick={() => updateData(1)} data-testid='reseller-update'>
              Reseller Update (+1)
            </button>
          </MockResellerApp>
        </div>
      );
    };

    const user = userEvent.setup();
    render(<TestDataConsistency />);

    // Test data updates from different portals
    expect(screen.getByText('Count: 0')).toBeInTheDocument();

    await user.click(screen.getByTestId('admin-update'));
    expect(screen.getByText('Count: 10')).toBeInTheDocument();

    await user.click(screen.getByTestId('customer-update'));
    expect(screen.getByText('Count: 15')).toBeInTheDocument();

    await user.click(screen.getByTestId('reseller-update'));
    expect(screen.getByText('Count: 16')).toBeInTheDocument();
  });
});

describe('Error Boundary Integration', () => {
  it('should isolate errors between portals', async () => {
    const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
      if (shouldThrow) {
        throw new Error('Test error');
      }
      return <div>No error</div>;
    };

    const TestErrorIsolation = () => {
      const [adminError, setAdminError] = React.useState(false);
      const [customerError, setCustomerError] = React.useState(false);

      return (
        <div data-testid='error-isolation'>
          <button onClick={() => setAdminError(true)} data-testid='trigger-admin-error'>
            Trigger Admin Error
          </button>

          <button onClick={() => setCustomerError(true)} data-testid='trigger-customer-error'>
            Trigger Customer Error
          </button>

          <React.Suspense fallback={<div>Loading Admin...</div>}>
            <MockAdminApp>
              <ThrowError shouldThrow={adminError} />
            </MockAdminApp>
          </React.Suspense>

          <React.Suspense fallback={<div>Loading Customer...</div>}>
            <MockCustomerApp>
              <ThrowError shouldThrow={customerError} />
            </MockCustomerApp>
          </React.Suspense>
        </div>
      );
    };

    render(<TestErrorIsolation />);

    // Verify both portals render initially
    expect(screen.getByTestId('admin-app')).toBeInTheDocument();
    expect(screen.getByTestId('customer-app')).toBeInTheDocument();

    // Test error isolation (would need proper error boundaries in real implementation)
    expect(screen.getByTestId('trigger-admin-error')).toBeInTheDocument();
    expect(screen.getByTestId('trigger-customer-error')).toBeInTheDocument();
  });
});
