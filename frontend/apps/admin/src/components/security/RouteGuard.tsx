/**
 * CRITICAL SECURITY COMPONENT - Route-level authorization
 * Protects routes based on user authentication, permissions, and roles
 */
import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '../../stores/authStore';
import { AlertTriangle, Lock, UserX } from 'lucide-react';

interface RouteGuardProps {
  children: React.ReactNode;
  requiredPermissions?: string[];
  requiredRoles?: string[];
  fallback?: React.ReactNode;
  requireAuth?: boolean;
}

export function RouteGuard({ 
  children, 
  requiredPermissions = [], 
  requiredRoles = [], 
  fallback,
  requireAuth = true 
}: RouteGuardProps) {
  const router = useRouter();
  const { 
    user, 
    isAuthenticated, 
    hasPermission, 
    hasRole, 
    isSessionValid, 
    logout 
  } = useAuthStore();

  // Check authentication
  if (requireAuth && !isAuthenticated) {
    return fallback || <LoginRedirect />;
  }

  // Check session validity
  if (requireAuth && !isSessionValid()) {
    // Session expired - force logout
    logout();
    return <SessionExpired />;
  }

  // Check if user object exists
  if (requireAuth && !user) {
    return fallback || <LoginRedirect />;
  }

  // Check required permissions
  if (requiredPermissions.length > 0) {
    const hasAllPermissions = requiredPermissions.every(permission => 
      hasPermission(permission)
    );
    
    if (!hasAllPermissions) {
      return fallback || <AccessDenied requiredPermissions={requiredPermissions} />;
    }
  }

  // Check required roles
  if (requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some(role => hasRole(role));
    
    if (!hasRequiredRole) {
      return fallback || <AccessDenied requiredRoles={requiredRoles} />;
    }
  }

  // All checks passed - render children
  return <>{children}</>;
}

// Login redirect component
function LoginRedirect() {
  const router = useRouter();
  
  React.useEffect(() => {
    // Preserve current path for redirect after login
    const currentPath = window.location.pathname + window.location.search;
    router.replace(`/login?redirect=${encodeURIComponent(currentPath)}`);
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <Lock className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Authentication Required</h2>
        <p className="text-gray-600">Redirecting to login...</p>
      </div>
    </div>
  );
}

// Session expired component
function SessionExpired() {
  const router = useRouter();
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6 text-center">
        <AlertTriangle className="w-12 h-12 mx-auto text-amber-500 mb-4" />
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Session Expired</h2>
        <p className="text-gray-600 mb-4">Your session has expired for security reasons. Please log in again.</p>
        <button
          onClick={() => router.replace('/login')}
          className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
        >
          Return to Login
        </button>
      </div>
    </div>
  );
}

// Access denied component
function AccessDenied({ 
  requiredPermissions, 
  requiredRoles 
}: { 
  requiredPermissions?: string[]; 
  requiredRoles?: string[]; 
}) {
  const router = useRouter();
  const { user } = useAuthStore();
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6 text-center">
        <UserX className="w-12 h-12 mx-auto text-red-500 mb-4" />
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Access Denied</h2>
        <p className="text-gray-600 mb-4">
          You don't have permission to access this resource.
        </p>
        
        {requiredPermissions && (
          <div className="mb-4 text-sm">
            <p className="font-medium text-gray-700">Required permissions:</p>
            <ul className="text-gray-600 mt-1">
              {requiredPermissions.map(permission => (
                <li key={permission} className="font-mono text-xs bg-gray-100 px-2 py-1 rounded mt-1">
                  {permission}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {requiredRoles && (
          <div className="mb-4 text-sm">
            <p className="font-medium text-gray-700">Required roles:</p>
            <ul className="text-gray-600 mt-1">
              {requiredRoles.map(role => (
                <li key={role} className="font-mono text-xs bg-gray-100 px-2 py-1 rounded mt-1">
                  {role}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        <div className="text-xs text-gray-500 mb-4">
          Current user: {user?.email} ({user?.role})
        </div>
        
        <div className="flex space-x-2">
          <button
            onClick={() => router.back()}
            className="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300 font-medium"
          >
            Go Back
          </button>
          <button
            onClick={() => router.replace('/dashboard')}
            className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 font-medium"
          >
            Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}