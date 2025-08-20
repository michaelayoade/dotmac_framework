/**
 * Portal-specific authentication hook with tenant resolution
 */

import { useCallback, useEffect, useState } from 'react';

import { getApiClient } from '../api/client';
import { useAuthStore, useTenantStore } from '../stores';
import type { LoginCredentials, LoginFlow, PortalConfig } from '../types/auth';

export function usePortalAuth() {
  const { login: authLogin, user, isLoading: authLoading, error: authError } = useAuthStore();
  const { setCurrentTenant } = useTenantStore();

  const [currentPortal, setCurrentPortal] = useState<PortalConfig | null>(null);
  const [loginFlow, setLoginFlow] = useState<LoginFlow>({
    step: 'portal_detection',
    availableLoginMethods: [],
    requiredFields: [],
    mfaRequired: false,
  });
  const [isDetectingPortal, setIsDetectingPortal] = useState(false);

  // Portal detection composition helpers
  const PortalDetectionHelpers = {
    getPortalTypeFromURL: (): string => {
      const { hostname, _port } = window.location;

      // Development port detection
      const devPortMap: Record<string, string> = {
        '3000': 'admin',
        '3001': 'customer',
        '3002': 'reseller',
      };

      if (devPortMap[port]) {
        return devPortMap[port];
      }

      // Production subdomain detection
      const subdomain = hostname.split('.')[0];
      const subdomainMap: Record<string, string> = {
        admin: 'admin',
        manage: 'admin',
        my: 'customer',
        customer: 'customer',
        partner: 'reseller',
        reseller: 'reseller',
      };

      return subdomainMap[subdomain] || 'customer';
    },

    fetchPortalConfig: async (portalType: string): Promise<PortalConfig | null> => {
      try {
        const apiClient = getApiClient();
        const response = await apiClient.request(`/api/v1/portals/${portalType}/config`, {
          method: 'GET',
        });
        return response.data;
      } catch (_error) {
        return null;
      }
    },

    setupLoginFlow: (portal: PortalConfig, getRequiredFields: (p: PortalConfig) => string[]) => ({
      step: 'credential_entry' as const,
      portalType: portal.type,
      availableLoginMethods: portal.loginMethods,
      requiredFields: getRequiredFields(portal),
      mfaRequired: portal.features.mfaRequired,
      tenantId: portal.tenantId,
    }),
  };

  // Detect portal from URL/subdomain
  const detectPortal = useCallback(async (): Promise<PortalConfig | null> => {
    setIsDetectingPortal(true);

    try {
      const portalType = PortalDetectionHelpers.getPortalTypeFromURL();
      const portal = await PortalDetectionHelpers.fetchPortalConfig(portalType);

      if (portal) {
        setCurrentPortal(portal);
        setLoginFlow(PortalDetectionHelpers.setupLoginFlow(portal, getRequiredFields));
        return portal;
      }

      return null;
    } catch (_error) {
      return null;
    } finally {
      setIsDetectingPortal(false);
    }
  }, [
    PortalDetectionHelpers.fetchPortalConfig,
    PortalDetectionHelpers.getPortalTypeFromURL,
    PortalDetectionHelpers.setupLoginFlow,
    getRequiredFields,
  ]);

  // Get required fields based on portal configuration
  const getRequiredFields = (portal: PortalConfig): string[] => {
    const fields = ['password'];

    if (portal.loginMethods.includes('email')) {
      fields.push('email');
    }
    if (portal.features.allowPortalIdLogin) {
      // Portal ID is optional for customer portal
    }
    if (portal.features.allowAccountNumberLogin) {
      // Account number is optional for customer portal
    }
    if (portal.loginMethods.includes('partner_code')) {
      fields.push('partnerCode');
    }
    if (portal.features.mfaRequired) {
      fields.push('mfaCode');
    }

    return fields;
  };

  // Helper to build login payload
  const buildLoginPayload = useCallback(
    (credentials: LoginCredentials, portal: PortalConfig): unknown => {
      const payload: unknown = {
        password: credentials.password,
        portalId: portal.id,
        tenantId: portal.tenantId,
      };

      if (credentials.email) {
        payload.email = credentials.email;
      } else if (credentials.portalId && portal.features.allowPortalIdLogin) {
        payload.portalId = credentials.portalId;
      } else if (credentials.accountNumber && portal.features.allowAccountNumberLogin) {
        payload.accountNumber = credentials.accountNumber;
      } else if (credentials.partnerCode) {
        payload.partnerCode = credentials.partnerCode;
        if (credentials.territory) {
          payload.territory = credentials.territory;
        }
      }

      if (portal.features.mfaRequired && credentials.mfaCode) {
        payload.mfaCode = credentials.mfaCode;
      }

      return payload;
    },
    []
  );

  // Helper to get login identifier
  const getLoginIdentifier = useCallback((payload: unknown): string => {
    return payload.email || payload.portalId || payload.accountNumber || payload.partnerCode;
  }, []);

  // Portal-specific login
  const loginWithPortal = useCallback(
    async (credentials: LoginCredentials): Promise<boolean> => {
      if (!currentPortal) {
        throw new Error('Portal not detected');
      }
      // Validate credentials based on portal type
      const validationResult = validateCredentials(credentials, currentPortal);
      if (!validationResult.valid) {
        throw new Error(validationResult.error);
      }

      // Build login payload
      const loginPayload = buildLoginPayload(credentials, currentPortal);

      // Update MFA step if needed
      if (currentPortal.features.mfaRequired && credentials.mfaCode) {
        setLoginFlow((prev) => ({ ...prev, step: 'mfa_verification' }));
      }

      // Perform login
      const loginIdentifier = getLoginIdentifier(loginPayload);
      const loginResponse = await authLogin(loginIdentifier, credentials.password);

      if (loginResponse && user) {
        // Set tenant context based on login response
        setCurrentTenant(user.tenant, user);
        setLoginFlow((prev) => ({ ...prev, step: 'complete' }));
        return true;
      }

      return false;
    },
    [
      currentPortal,
      authLogin,
      setCurrentTenant,
      user,
      validateCredentials,
      buildLoginPayload,
      getLoginIdentifier,
    ]
  );

  // Credential validation composition helpers
  const CredentialValidation = {
    checkLoginMethods: (credentials: LoginCredentials, portal: PortalConfig): boolean => {
      const methods = [
        credentials.email,
        credentials.portalId && portal.features.allowPortalIdLogin,
        credentials.accountNumber && portal.features.allowAccountNumberLogin,
        credentials.partnerCode && portal.loginMethods.includes('partner_code'),
      ];
      return methods.some(Boolean);
    },

    validatePassword: (password: string | undefined) => (password ? null : 'Password is required'),

    validateMFA: (credentials: LoginCredentials, portal: PortalConfig, loginStep: string) =>
      portal.features.mfaRequired && !credentials.mfaCode && loginStep === 'mfa_verification'
        ? 'MFA code is required'
        : null,

    createValidationResult: (isValid: boolean, error?: string) => ({
      valid: isValid,
      ...(error && { error }),
    }),
  };

  // Validate credentials based on portal requirements
  const validateCredentials = useCallback(
    (credentials: LoginCredentials, portal: PortalConfig) => {
      // Check login methods
      if (!CredentialValidation.checkLoginMethods(credentials, portal)) {
        return CredentialValidation.createValidationResult(
          false,
          `Please provide ${portal.loginMethods.join(' or ')} to sign in`
        );
      }

      // Check password
      const passwordError = CredentialValidation.validatePassword(credentials.password);
      if (passwordError) {
        return CredentialValidation.createValidationResult(false, passwordError);
      }

      // Check MFA
      const mfaError = CredentialValidation.validateMFA(credentials, portal, loginFlow.step);
      if (mfaError) {
        return CredentialValidation.createValidationResult(false, mfaError);
      }

      return CredentialValidation.createValidationResult(true);
    },
    [
      loginFlow.step,
      CredentialValidation.checkLoginMethods,
      CredentialValidation.createValidationResult,
      CredentialValidation.validateMFA,
      CredentialValidation.validatePassword,
    ]
  );

  // Get default roles based on portal type
  const _getDefaultRoles = (portalType: string): string[] => {
    switch (portalType) {
      case 'admin':
        return ['tenant-admin'];
      case 'customer':
        return ['customer'];
      case 'reseller':
        return ['reseller-agent'];
      default:
        return [];
    }
  };

  // Initialize portal detection on mount
  useEffect(() => {
    detectPortal();
  }, [detectPortal]);

  // Apply portal branding
  useEffect(() => {
    if (currentPortal) {
      // Update CSS custom properties for portal branding
      const root = document.documentElement;
      root.style.setProperty('--portal-primary', currentPortal.branding.primaryColor);
      root.style.setProperty('--portal-secondary', currentPortal.branding.secondaryColor);

      // Update document title
      document.title = currentPortal.name;

      // Update favicon if provided
      if (currentPortal.branding.favicon) {
        const favicon = document.querySelector('link[rel="icon"]') as HTMLLinkElement;
        if (favicon) {
          favicon.href = currentPortal.branding.favicon;
        }
      }
    }
  }, [currentPortal]);

  return {
    // Portal state
    currentPortal,
    loginFlow,
    isDetectingPortal,

    // Auth state
    user,
    isLoading: authLoading || isDetectingPortal,
    error: authError,

    // Actions
    detectPortal,
    loginWithPortal,

    // Utilities
    getRequiredFields: () => (currentPortal ? getRequiredFields(currentPortal) : []),
    getLoginMethods: () => currentPortal?.loginMethods || [],
    isMfaRequired: () => currentPortal?.features.mfaRequired || false,
    getPortalBranding: () => currentPortal?.branding,
  };
}
