/**
 * Authentication types for ISP platform with portal-specific flows
 */

export interface LoginCredentials {
  // Common fields
  email?: string;
  password: string;
  rememberMe?: boolean;

  // Portal-specific fields
  portalId?: string; // Customer portal identification
  accountNumber?: string; // Customer account number
  partnerCode?: string; // Reseller partner code
  territory?: string; // Reseller territory
  mfaCode?: string; // Admin MFA code
}

export interface PortalConfig {
  id: string;
  name: string;
  type: 'admin' | 'customer' | 'reseller';
  subdomain?: string;
  customDomain?: string;
  tenantId: string;
  branding: {
    logo?: string;
    primaryColor: string;
    secondaryColor: string;
    companyName: string;
    favicon?: string;
  };
  features: {
    selfRegistration: boolean;
    passwordReset: boolean;
    mfaRequired: boolean;
    ssoEnabled: boolean;
    allowPortalIdLogin: boolean;
    allowAccountNumberLogin: boolean;
  };
  loginMethods: Array<'email' | 'portal_id' | 'account_number' | 'partner_code'>;
}

export interface AuthContext {
  user: User | null;
  portal: PortalConfig | null;
  tenant: Tenant | null;
  permissions: string[];
  roles: string[];
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginFlow {
  step: 'portal_detection' | 'credential_entry' | 'mfa_verification' | 'complete';
  portalType?: 'admin' | 'customer' | 'reseller';
  availableLoginMethods: string[];
  requiredFields: string[];
  mfaRequired: boolean;
  tenantId?: string;
}
