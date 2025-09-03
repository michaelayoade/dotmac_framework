/**
 * Universal Authentication System
 *
 * Complete authentication solution for all DotMac portals
 * Provides secure, type-safe, and portal-aware authentication functionality
 */

// Types
export type * from './types';

// Configuration
export { getPortalConfig, generatePortalCSS } from './config/portal-configs';

// Validation schemas
export {
  validateLoginCredentials,
  validatePasswordStrength,
  LOGIN_SCHEMAS,
  mfaVerificationSchema,
  userProfileUpdateSchema,
  passwordChangeSchema,
} from './validation/schemas';

// Components
export { UniversalLoginForm } from './components/UniversalLoginForm/UniversalLoginForm';
export { SimpleLoginForm } from './components/SimpleLoginForm';

// Hooks
export { useAuth } from './hooks/useAuth';

// Providers and Context
export {
  AuthProvider,
  useAuthContext,
  usePortalContext,
  ProtectedRoute,
  AuthGuard,
  PortalSwitcher,
} from './providers/AuthProvider';

// Services
export { AuthApiClient } from './services/AuthApiClient';
export { TokenManager } from './services/TokenManager';
export { SessionManager } from './services/SessionManager';
export { RateLimiter } from './services/RateLimiter';
export { SecurityService } from './services/SecurityService';

// Create default instances (convenience exports)
export const authApi = new AuthApiClient();
export const tokenManager = new TokenManager();
export const sessionManager = new SessionManager();
export const rateLimiter = new RateLimiter();
export const securityService = new SecurityService();
