import { NextApiRequest, NextApiResponse } from 'next';
// Simple JWT decode without verification for basic payload extraction
function simpleJwtDecode(token: string) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(Buffer.from(parts[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString());
    return payload;
  } catch {
    return null;
  }
}
// Note: Import security components when available
// import { InputSanitizer } from '@/lib/security/input-sanitizer';
// import { SecurityError } from '@/lib/security/types';

// Temporary basic validation for startup
function basicValidation(input: string): string {
  return input.trim();
}

interface TokenPayload {
  user_id: string;
  email: string;
  role: string;
  tenant_id?: string;
  permissions: string[];
  exp: number;
  iss: string;
  type: string;
}

interface ValidationResponse {
  isValid: boolean;
  payload?: TokenPayload;
  error?: string;
  expiresIn?: number;
}

/**
 * Server-side JWT token validation endpoint
 * Replaces the insecure client-side validation in middleware
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ValidationResponse>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({
      isValid: false,
      error: 'Method not allowed'
    });
  }

  try {
    const { token } = req.body;

    if (!token || typeof token !== 'string') {
      return res.status(400).json({
        isValid: false,
        error: 'Token is required'
      });
    }

    // Basic token validation for startup
    const sanitizedToken = basicValidation(token);

    // Validate token structure
    const tokenParts = sanitizedToken.split('.');
    if (tokenParts.length !== 3) {
      return res.status(400).json({
        isValid: false,
        error: 'Invalid token structure'
      });
    }

    // Decode token payload (without verification for now - we'll call the management platform)
    let payload: any;
    try {
      payload = simpleJwtDecode(sanitizedToken);
    } catch (decodeError) {
      return res.status(400).json({
        isValid: false,
        error: 'Invalid token encoding'
      });
    }

    if (!payload) {
      return res.status(400).json({
        isValid: false,
        error: 'Invalid token payload'
      });
    }

    // Validate token with management platform backend
    const validationResult = await validateTokenWithBackend(sanitizedToken);
    
    if (!validationResult.isValid) {
      return res.status(401).json(validationResult);
    }

    // Calculate time until expiration
    const now = Math.floor(Date.now() / 1000);
    const expiresIn = payload.exp ? payload.exp - now : 0;

    if (expiresIn <= 0) {
      return res.status(401).json({
        isValid: false,
        error: 'Token has expired'
      });
    }

    // Validate issuer
    if (payload.iss !== 'dotmac-management-platform') {
      return res.status(401).json({
        isValid: false,
        error: 'Invalid token issuer'
      });
    }

    // Validate token type
    if (payload.type !== 'access') {
      return res.status(401).json({
        isValid: false,
        error: 'Invalid token type'
      });
    }

    // Validate role and permissions for management portal
    const validRoles = ['master_admin', 'channel_manager', 'operations_manager', 'reseller_manager'];
    if (!validRoles.includes(payload.role)) {
      return res.status(403).json({
        isValid: false,
        error: 'Insufficient permissions for management portal'
      });
    }

    return res.status(200).json({
      isValid: true,
      payload: {
        user_id: payload.user_id,
        email: payload.email,
        role: payload.role,
        tenant_id: payload.tenant_id,
        permissions: payload.permissions || [],
        exp: payload.exp,
        iss: payload.iss,
        type: payload.type
      },
      expiresIn
    });

  } catch (error) {
    console.error('Token validation error:', error);
    
    // Handle any validation errors
    const errorMessage = error instanceof Error ? error.message : 'Token validation failed';
    if (errorMessage.includes('security') || errorMessage.includes('invalid')) {
      return res.status(400).json({
        isValid: false,
        error: 'Invalid token format'
      });
    }

    return res.status(500).json({
      isValid: false,
      error: 'Internal server error during token validation'
    });
  }
}

/**
 * Validate token with the management platform backend
 * This ensures proper signature verification and user status checks
 */
async function validateTokenWithBackend(token: string): Promise<ValidationResponse> {
  try {
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:8000';
    
    const response = await fetch(`${managementApiUrl}/api/v1/auth/validate-token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Client-Type': 'management-reseller'
      },
      body: JSON.stringify({ token })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        isValid: false,
        error: errorData.detail || errorData.message || 'Token validation failed'
      };
    }

    const data = await response.json();
    return {
      isValid: true,
      payload: data.user,
      expiresIn: data.expires_in
    };

  } catch (error) {
    console.error('Backend token validation error:', error);
    return {
      isValid: false,
      error: 'Unable to validate token with backend service'
    };
  }
}