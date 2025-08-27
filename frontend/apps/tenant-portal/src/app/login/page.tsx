'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTenantAuth } from '@/components/auth/TenantAuthProvider';
import { demoCredentials } from '@/lib/env-config';
import { AccessibleInput, AccessibleButton, AccessibleCheckbox, AccessibleAlert } from '@/components/ui/AccessibleForm';
import { announceToScreenReader } from '@/lib/accessibility';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login } = useTenantAuth();
  const router = useRouter();
  
  // Announce page load to screen readers
  useEffect(() => {
    announceToScreenReader('Login page loaded. Please enter your credentials to access the tenant portal.', 'polite');
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    // Announce login attempt
    announceToScreenReader('Attempting to sign in...', 'polite');

    try {
      await login({ email, password, rememberMe });
      announceToScreenReader('Login successful. Redirecting to dashboard...', 'polite');
      // Redirect is handled by the auth provider
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      announceToScreenReader(`Login failed: ${errorMessage}`, 'assertive');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Skip to main content link for keyboard users */}
        <a
          href="#login-form"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-blue-600 text-white px-4 py-2 rounded-md z-50 focus:z-50"
        >
          Skip to main content
        </a>
        
        {/* Header */}
        <header className="text-center">
          <div className="mx-auto h-12 w-12 bg-blue-600 rounded-lg flex items-center justify-center">
            <div className="text-white font-bold text-xl" aria-hidden="true">D</div>
          </div>
          <h1 className="mt-6 text-3xl font-bold text-gray-900">
            Sign in to your tenant portal
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Access your DotMac ISP Platform instance
          </p>
        </header>

        {/* Main Login Form */}
        <main>
          <form 
            id="login-form"
            className="mt-8 space-y-6" 
            onSubmit={handleSubmit}
            noValidate
            aria-label="Login form"
          >
            {/* Error Alert */}
            {error && (
              <AccessibleAlert type="error" dismissible onDismiss={() => setError('')}>
                {error}
              </AccessibleAlert>
            )}

            <div className="space-y-4">
              {/* Email Field */}
              <AccessibleInput
                id="login-email"
                name="email"
                type="email"
                label="Email address"
                description="Enter the email address associated with your account"
                autoComplete="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                error={error && email === '' ? 'Email is required' : undefined}
              />

              {/* Password Field */}
              <AccessibleInput
                id="login-password"
                name="password"
                type="password"
                label="Password"
                description="Enter your account password"
                autoComplete="current-password"
                required
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                showPasswordToggle
                error={error && password === '' ? 'Password is required' : undefined}
              />
            </div>

            <div className="flex items-center justify-between">
              {/* Remember Me Checkbox */}
              <AccessibleCheckbox
                id="remember-me"
                name="rememberMe"
                label="Remember me"
                description="Stay signed in on this device"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={isLoading}
              />

              {/* Forgot Password Link */}
              <div className="text-sm">
                <a 
                  href="/forgot-password" 
                  className="font-medium text-blue-600 hover:text-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 rounded-sm transition-colors"
                  aria-describedby="forgot-password-description"
                >
                  Forgot your password?
                </a>
                <div id="forgot-password-description" className="sr-only">
                  Opens forgot password page in same window
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <AccessibleButton
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              isLoading={isLoading}
              loadingText="Signing in..."
              disabled={isLoading || !email || !password}
              aria-describedby="submit-button-description"
            >
              Sign in
            </AccessibleButton>
            <div id="submit-button-description" className="sr-only">
              {isLoading 
                ? 'Currently signing you in, please wait' 
                : !email || !password 
                  ? 'Please enter both email and password to sign in'
                  : 'Click to sign in with your credentials'
              }
            </div>

            {/* Demo credentials - only show in development */}
            {demoCredentials.enabled && (
              <AccessibleAlert type="info">
                <div>
                  <h4 className="text-sm font-medium text-blue-800 mb-2">
                    Demo Access (Development Only)
                  </h4>
                  <p className="text-xs text-blue-700 mb-3">
                    Use these pre-configured credentials to access the demo tenant:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="space-y-1">
                      <div className="font-medium text-blue-800">Admin Account:</div>
                      <div className="font-mono text-blue-700">{demoCredentials.admin.email}</div>
                      <AccessibleButton
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEmail(demoCredentials.admin.email);
                          setPassword(demoCredentials.admin.password);
                          announceToScreenReader('Admin credentials filled', 'polite');
                        }}
                        disabled={isLoading}
                        className="text-blue-600 hover:text-blue-800 p-0 h-auto font-normal"
                        aria-label="Fill form with admin demo credentials"
                      >
                        Use admin credentials
                      </AccessibleButton>
                    </div>
                    <div className="space-y-1">
                      <div className="font-medium text-blue-800">User Account:</div>
                      <div className="font-mono text-blue-700">{demoCredentials.user.email}</div>
                      <AccessibleButton
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEmail(demoCredentials.user.email);
                          setPassword(demoCredentials.user.password);
                          announceToScreenReader('User credentials filled', 'polite');
                        }}
                        disabled={isLoading}
                        className="text-blue-600 hover:text-blue-800 p-0 h-auto font-normal"
                        aria-label="Fill form with user demo credentials"
                      >
                        Use user credentials
                      </AccessibleButton>
                    </div>
                  </div>
                </div>
              </AccessibleAlert>
            )}
          </form>
        </main>

        {/* Footer */}
        <footer className="text-center text-sm text-gray-600">
          <p>
            Need help?{' '}
            <a 
              href="/support" 
              className="font-medium text-blue-600 hover:text-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 rounded-sm transition-colors"
              aria-label="Contact support for login assistance"
            >
              Contact support
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}