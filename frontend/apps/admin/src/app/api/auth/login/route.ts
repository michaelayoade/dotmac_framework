/**
 * Secure Login API Endpoint
 * Implements secure authentication with proper session management
 */

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { rateLimit } from '../../../../lib/rate-limit';
import { validateCSRFToken } from '../../../../lib/csrf-protection';
import { sanitizeInput } from '../../../../lib/security';

interface LoginRequest {
  email: string;
  password: string;
  mfaCode?: string;
}

// Rate limiting: 5 attempts per 15 minutes per IP
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 attempts
  standardHeaders: true,
  legacyHeaders: false,
});

export async function POST(request: NextRequest) {
  try {
    // Apply rate limiting
    const rateLimitResult = await loginLimiter(request);
    if (!rateLimitResult.success) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Too many login attempts. Please try again later.',
          retryAfter: rateLimitResult.retryAfter 
        },
        { status: 429 }
      );
    }

    // Validate CSRF token
    const csrfValid = await validateCSRFToken(request);
    if (!csrfValid) {
      return NextResponse.json(
        { success: false, error: 'Invalid CSRF token' },
        { status: 403 }
      );
    }

    // Parse and validate request body
    const body: LoginRequest = await request.json();
    
    if (!body.email || !body.password) {
      return NextResponse.json(
        { success: false, error: 'Email and password are required' },
        { status: 400 }
      );
    }

    // Sanitize inputs
    const email = sanitizeInput(body.email).toLowerCase();
    const password = body.password; // Don't sanitize password, validate length only
    
    if (password.length < 8 || password.length > 128) {
      return NextResponse.json(
        { success: false, error: 'Invalid credentials' }, // Don't reveal password requirements
        { status: 401 }
      );
    }

    // Validate email format
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { success: false, error: 'Invalid credentials' },
        { status: 401 }
      );
    }

    // Authenticate with your backend service
    const authResult = await authenticateUser(email, password, body.mfaCode);
    
    if (!authResult.success) {
      // Log failed attempt (don't log password)
      console.warn(`Failed login attempt for ${email} from ${request.ip}`);
      
      return NextResponse.json(
        { 
          success: false, 
          error: authResult.error,
          requiresMFA: authResult.requiresMFA 
        },
        { status: 401 }
      );
    }

    // Create secure session with JWT tokens
    const sessionData = await createSecureSession(authResult.user, request);
    
    // Set secure HttpOnly cookies
    const cookieStore = cookies();
    
    // Access token (short-lived)
    cookieStore.set('access_token', sessionData.accessToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 30 * 60, // 30 minutes
      path: '/',
    });
    
    // Refresh token (longer-lived)
    cookieStore.set('refresh_token', sessionData.refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60, // 7 days
      path: '/api/auth',
    });
    
    // Session ID for tracking
    cookieStore.set('session_id', sessionData.sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60, // 7 days
      path: '/',
    });

    // Log successful login (without sensitive data)
    const clientIp = request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
    console.info('Successful admin login', {
      email: authResult.user.email,
      userId: authResult.user.id,
      sessionId: sessionData.sessionId,
      ipAddress: clientIp,
      timestamp: new Date().toISOString()
    });

    return NextResponse.json({
      success: true,
      user: {
        id: authResult.user.id,
        email: authResult.user.email,
        name: authResult.user.name,
        role: authResult.user.role,
        permissions: authResult.user.permissions,
        tenantId: authResult.user.tenantId,
      },
      expiresAt: sessionData.expiresAt,
      sessionId: sessionData.sessionId, // Client needs this for session management
    });

  } catch (error) {
    console.error('Login endpoint error:', error);
    
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * Authenticate user with backend service
 * Integrates with ISP Framework authentication
 */
async function authenticateUser(
  email: string, 
  password: string, 
  mfaCode?: string
): Promise<{
  success: boolean;
  error?: string;
  requiresMFA?: boolean;
  user?: any;
}> {
  try {
    // Get ISP Framework API URL from environment
    const ispApiUrl = process.env.NEXT_PUBLIC_ISP_API_URL || 'http://localhost:8001';
    
    // Authenticate with ISP Framework
    const response = await fetch(`${ispApiUrl}/api/v1/auth/admin/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'DotMac-Admin-Portal/1.0',
      },
      body: JSON.stringify({ 
        email, 
        password, 
        mfa_code: mfaCode,
        portal: 'admin'
      }),
    });

    const responseData = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: responseData.detail || 'Authentication failed',
        requiresMFA: responseData.requires_mfa,
      };
    }

    // Validate required user data
    if (!responseData.user || !responseData.user.id) {
      return {
        success: false,
        error: 'Invalid user data received',
      };
    }

    return {
      success: true,
      user: {
        id: responseData.user.id,
        email: responseData.user.email,
        name: responseData.user.name || responseData.user.email,
        role: responseData.user.role || 'admin',
        permissions: responseData.user.permissions || [],
        tenantId: responseData.user.tenant_id,
      },
    };
    
  } catch (error) {
    console.error('Authentication service error:', error);
    return {
      success: false,
      error: 'Authentication service unavailable',
    };
  }
}

/**
 * Create secure session token using JWT
 */
async function createSecureSession(user: any, request: NextRequest): Promise<{
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
  sessionId: string;
}> {
  // Import JWT utilities
  const { createTokenPair, SessionManager } = await import('../../../../lib/jwt');
  
  // Create secure token pair
  const tokenPair = await createTokenPair(user);
  
  // Register session with metadata
  const clientIp = request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
  const userAgent = request.headers.get('user-agent') || 'unknown';
  
  SessionManager.createSession(tokenPair.sessionId, user.id, {
    ipAddress: clientIp,
    userAgent: userAgent.substring(0, 200) // Limit length
  });
  
  // Log successful authentication
  console.info('Secure session created', {
    userId: user.id,
    email: user.email,
    sessionId: tokenPair.sessionId,
    ipAddress: clientIp,
    timestamp: new Date().toISOString()
  });
  
  return tokenPair;
}