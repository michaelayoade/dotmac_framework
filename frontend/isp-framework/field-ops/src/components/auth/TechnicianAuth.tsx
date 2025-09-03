/**
 * Technician Authentication Components
 * Secure authentication system for field technicians
 */

'use client';

import { useState, useEffect, createContext, useContext } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  Lock,
  Eye,
  EyeOff,
  Smartphone,
  Shield,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import SecureTokenManager, {
  AuthState,
  TechnicianProfile,
} from '../../lib/auth/secure-token-manager';

// Auth Context
const AuthContext = createContext<{
  authState: AuthState;
  login: (employeeId: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  authenticatedRequest: (url: string, options?: RequestInit) => Promise<Response>;
} | null>(null);

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    loading: true,
    error: null,
  });

  const tokenManager = SecureTokenManager.getInstance();

  useEffect(() => {
    const unsubscribe = tokenManager.subscribe(setAuthState);
    return unsubscribe;
  }, []);

  const login = async (employeeId: string, password: string) => {
    await tokenManager.login(employeeId, password);
  };

  const logout = async () => {
    await tokenManager.logout();
  };

  const authenticatedRequest = async (url: string, options?: RequestInit) => {
    return tokenManager.authenticatedRequest(url, options);
  };

  return (
    <AuthContext.Provider
      value={{
        authState,
        login,
        logout,
        authenticatedRequest,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Login Form Component
interface LoginFormProps {
  onSuccess?: () => void;
}

export function TechnicianLoginForm({ onSuccess }: LoginFormProps) {
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    employeeId: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deviceChecks, setDeviceChecks] = useState({
    online: navigator.onLine,
    geolocation: false,
    camera: false,
  });

  useEffect(() => {
    // Check device capabilities
    checkDeviceCapabilities();
  }, []);

  const checkDeviceCapabilities = async () => {
    const checks = { ...deviceChecks };

    // Check geolocation
    if ('geolocation' in navigator) {
      try {
        await new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
        });
        checks.geolocation = true;
      } catch {
        checks.geolocation = false;
      }
    }

    // Check camera
    if (navigator.mediaDevices?.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        stream.getTracks().forEach((track) => track.stop());
        checks.camera = true;
      } catch {
        checks.camera = false;
      }
    }

    setDeviceChecks(checks);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.employeeId.trim() || !formData.password.trim()) {
      setError('Please enter both Employee ID and password');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login(formData.employeeId, formData.password);
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (error) setError(null);
  };

  return (
    <div className='min-h-screen bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center p-4'>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className='w-full max-w-md'
      >
        {/* Header */}
        <div className='text-center mb-8'>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className='w-20 h-20 bg-white rounded-full flex items-center justify-center mx-auto mb-4'
          >
            <Smartphone className='w-10 h-10 text-primary-600' />
          </motion.div>
          <h1 className='text-2xl font-bold text-white mb-2'>Field Service Portal</h1>
          <p className='text-primary-100'>Secure technician access</p>
        </div>

        {/* Device Status */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className='bg-white/10 backdrop-blur-sm rounded-lg p-4 mb-6'
        >
          <h3 className='text-white font-medium mb-3 flex items-center'>
            <Shield className='w-4 h-4 mr-2' />
            Device Status
          </h3>
          <div className='space-y-2'>
            <div className='flex items-center justify-between text-sm'>
              <span className='text-primary-100'>Network</span>
              <span
                className={`flex items-center ${deviceChecks.online ? 'text-green-300' : 'text-red-300'}`}
              >
                {deviceChecks.online ? (
                  <CheckCircle className='w-3 h-3 mr-1' />
                ) : (
                  <AlertCircle className='w-3 h-3 mr-1' />
                )}
                {deviceChecks.online ? 'Connected' : 'Offline'}
              </span>
            </div>
            <div className='flex items-center justify-between text-sm'>
              <span className='text-primary-100'>Location</span>
              <span
                className={`flex items-center ${deviceChecks.geolocation ? 'text-green-300' : 'text-yellow-300'}`}
              >
                {deviceChecks.geolocation ? (
                  <CheckCircle className='w-3 h-3 mr-1' />
                ) : (
                  <AlertCircle className='w-3 h-3 mr-1' />
                )}
                {deviceChecks.geolocation ? 'Available' : 'Permissions needed'}
              </span>
            </div>
            <div className='flex items-center justify-between text-sm'>
              <span className='text-primary-100'>Camera</span>
              <span
                className={`flex items-center ${deviceChecks.camera ? 'text-green-300' : 'text-yellow-300'}`}
              >
                {deviceChecks.camera ? (
                  <CheckCircle className='w-3 h-3 mr-1' />
                ) : (
                  <AlertCircle className='w-3 h-3 mr-1' />
                )}
                {deviceChecks.camera ? 'Ready' : 'Permissions needed'}
              </span>
            </div>
          </div>
        </motion.div>

        {/* Login Form */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className='bg-white rounded-lg shadow-xl p-6'
        >
          <form onSubmit={handleSubmit} className='space-y-4'>
            {/* Employee ID Field */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Employee ID</label>
              <div className='relative'>
                <User className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
                <input
                  type='text'
                  value={formData.employeeId}
                  onChange={(e) => handleInputChange('employeeId', e.target.value)}
                  className='w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
                  placeholder='Enter your employee ID'
                  disabled={loading}
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className='block text-sm font-medium text-gray-700 mb-1'>Password</label>
              <div className='relative'>
                <Lock className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                  className='w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors'
                  placeholder='Enter your password'
                  disabled={loading}
                />
                <button
                  type='button'
                  onClick={() => setShowPassword(!showPassword)}
                  className='absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600'
                  disabled={loading}
                >
                  {showPassword ? <EyeOff className='w-4 h-4' /> : <Eye className='w-4 h-4' />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className='bg-red-50 border border-red-200 rounded-lg p-3'
                >
                  <div className='flex items-center text-red-700 text-sm'>
                    <AlertCircle className='w-4 h-4 mr-2 flex-shrink-0' />
                    {error}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Login Button */}
            <button
              type='submit'
              disabled={loading || !deviceChecks.online}
              className='w-full bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center'
            >
              {loading ? (
                <>
                  <Loader2 className='w-4 h-4 mr-2 animate-spin' />
                  Signing In...
                </>
              ) : (
                'Sign In to Field Portal'
              )}
            </button>
          </form>

          {/* Offline Message */}
          {!deviceChecks.online && (
            <div className='mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg'>
              <div className='flex items-center text-yellow-800 text-sm'>
                <AlertCircle className='w-4 h-4 mr-2' />
                You're offline. Please connect to the internet to sign in.
              </div>
            </div>
          )}
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.8 }}
          className='text-center mt-6'
        >
          <p className='text-primary-100 text-sm'>Secure access for authorized technicians only</p>
        </motion.div>
      </motion.div>
    </div>
  );
}

// Protected Route Component
interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps) {
  const { authState } = useAuth();

  if (authState.loading) {
    return (
      <div className='min-h-screen bg-gray-50 flex items-center justify-center'>
        <div className='text-center'>
          <Loader2 className='w-8 h-8 animate-spin text-primary-600 mx-auto mb-4' />
          <p className='text-gray-600'>Verifying access...</p>
        </div>
      </div>
    );
  }

  if (!authState.isAuthenticated) {
    return fallback || <TechnicianLoginForm />;
  }

  return <>{children}</>;
}

// User Profile Component
export function UserProfile() {
  const { authState, logout } = useAuth();
  const [showDetails, setShowDetails] = useState(false);

  if (!authState.user) return null;

  const handleLogout = async () => {
    if (confirm('Are you sure you want to sign out?')) {
      await logout();
    }
  };

  return (
    <div className='relative'>
      <button
        onClick={() => setShowDetails(!showDetails)}
        className='flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors'
      >
        <div className='w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center'>
          <span className='text-white text-sm font-medium'>{authState.user.name.charAt(0)}</span>
        </div>
        <div className='hidden sm:block text-left'>
          <div className='text-sm font-medium text-gray-900'>{authState.user.name}</div>
          <div className='text-xs text-gray-500'>{authState.user.employeeId}</div>
        </div>
      </button>

      <AnimatePresence>
        {showDetails && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='absolute top-full right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-50'
          >
            <div className='border-b border-gray-200 pb-3 mb-3'>
              <h3 className='font-medium text-gray-900'>{authState.user.name}</h3>
              <p className='text-sm text-gray-500'>{authState.user.email}</p>
              <p className='text-sm text-gray-500'>ID: {authState.user.employeeId}</p>
            </div>

            <div className='space-y-2 mb-3'>
              <div className='flex justify-between text-sm'>
                <span className='text-gray-600'>Role:</span>
                <span className='font-medium'>{authState.user.role}</span>
              </div>
              <div className='flex justify-between text-sm'>
                <span className='text-gray-600'>Department:</span>
                <span className='font-medium'>{authState.user.department}</span>
              </div>
              <div className='flex justify-between text-sm'>
                <span className='text-gray-600'>Territory:</span>
                <span className='font-medium'>{authState.user.territory.name}</span>
              </div>
            </div>

            <button
              onClick={handleLogout}
              className='w-full bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors'
            >
              Sign Out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
