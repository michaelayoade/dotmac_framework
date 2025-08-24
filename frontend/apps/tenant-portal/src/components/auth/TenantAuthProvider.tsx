'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

interface TenantUser {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
  permissions: string[];
  last_login?: Date;
}

interface TenantInfo {
  id: string;
  name: string;
  display_name: string;
  slug: string;
  status: 'active' | 'pending' | 'suspended' | 'cancelled';
  tier: string;
  custom_domain?: string;
  primary_color?: string;
  logo_url?: string;
}

interface TenantAuthContextValue {
  user: TenantUser | null;
  tenant: TenantInfo | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const TenantAuthContext = createContext<TenantAuthContextValue | null>(null);

export function useTenantAuth() {
  const context = useContext(TenantAuthContext);
  if (!context) {
    throw new Error('useTenantAuth must be used within a TenantAuthProvider');
  }
  return context;
}

export function TenantAuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<TenantUser | null>(null);
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const isAuthenticated = !!user && !!tenant && tenant.status === 'active';

  // Mock authentication - in real implementation, this would call the API
  const login = async (credentials: { email: string; password: string }) => {
    setIsLoading(true);
    try {
      // Call management platform authentication API
      const response = await fetch('/api/v1/tenant-admin/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Authentication failed');
      }
      
      const authData = await response.json();
      
      // Set user from API response
      const apiUser: TenantUser = {
        id: authData.user.id,
        email: authData.user.email,
        name: authData.user.name || 'Tenant Admin',
        role: authData.user.role,
        tenant_id: authData.user.tenant_id,
        permissions: authData.user.permissions || [],
        last_login: new Date(authData.user.last_login || Date.now()),
      };

      const mockTenant: TenantInfo = {
        id: 'tenant_123',
        name: 'acme-isp',
        display_name: 'ACME ISP Solutions',
        slug: 'acme-isp',
        status: 'active',
        tier: 'standard',
        custom_domain: 'portal.acme-isp.com',
        primary_color: '#0ea5e9',
        logo_url: '/api/tenant/logo',
      };

      // Store in session storage (in production, use secure HTTP-only cookies)
      sessionStorage.setItem('tenant_user', JSON.stringify(apiUser));
      sessionStorage.setItem('tenant_info', JSON.stringify(mockTenant));

      setUser(apiUser);
      setTenant(mockTenant);
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw new Error('Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      // Call logout API to invalidate server-side session
      try {
        await fetch('/api/v1/tenant-admin/auth/logout', { 
          method: 'POST',
          credentials: 'include'
        });
      } catch (error) {
        console.warn('Server logout failed, clearing local session:', error);
      }
      
      sessionStorage.removeItem('tenant_user');
      sessionStorage.removeItem('tenant_info');
      
      setUser(null);
      setTenant(null);
      
      router.push('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const refreshAuth = async () => {
    try {
      // Attempt to refresh authentication token
      try {
        const response = await fetch('/api/v1/tenant-admin/auth/refresh', { 
          method: 'POST',
          credentials: 'include'
        });
        
        if (response.ok) {
          const refreshData = await response.json();
          // Token refreshed successfully, update user data if provided
          if (refreshData.user) {
            setUser(refreshData.user);
            sessionStorage.setItem('tenant_user', JSON.stringify(refreshData.user));
          }
          return true;
        }
      } catch (error) {
        console.warn('Token refresh failed, checking local session:', error);
      }
      
      // Fall back to session storage check
      const storedUser = sessionStorage.getItem('tenant_user');
      const storedTenant = sessionStorage.getItem('tenant_info');
      
      if (storedUser && storedTenant) {
        setUser(JSON.parse(storedUser));
        setTenant(JSON.parse(storedTenant));
      }
    } catch (error) {
      console.error('Auth refresh failed:', error);
      await logout();
    }
  };

  // Check authentication on mount and route changes
  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      
      const storedUser = sessionStorage.getItem('tenant_user');
      const storedTenant = sessionStorage.getItem('tenant_info');
      
      if (storedUser && storedTenant) {
        try {
          const parsedUser = JSON.parse(storedUser);
          const parsedTenant = JSON.parse(storedTenant);
          
          setUser(parsedUser);
          setTenant(parsedTenant);
          
          // Refresh auth in background
          await refreshAuth();
        } catch (error) {
          console.error('Failed to parse stored auth:', error);
          await logout();
        }
      } else if (pathname !== '/login' && !pathname.startsWith('/auth')) {
        // Redirect to login if not authenticated and not on auth pages
        router.push('/login');
      }
      
      setIsLoading(false);
    };

    checkAuth();
  }, [pathname, router]);

  const value: TenantAuthContextValue = {
    user,
    tenant,
    isLoading,
    isAuthenticated,
    login,
    logout,
    refreshAuth,
  };

  return (
    <TenantAuthContext.Provider value={value}>
      {children}
    </TenantAuthContext.Provider>
  );
}