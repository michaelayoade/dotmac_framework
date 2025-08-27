'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { audit, auditContext } from '@dotmac/monitoring';
import { validateInput } from '@dotmac/headless/utils/validation';
import { headers } from 'next/headers';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function loginAction(formData: FormData) {
  // Extract and validate form data
  const rawEmail = formData.get('email') as string;
  const rawPassword = formData.get('password') as string;
  
  // Validate and sanitize inputs
  const emailValidation = validateInput(rawEmail, 'email', { required: true, maxLength: 255 });
  const passwordValidation = validateInput(rawPassword, 'password', { required: true, minLength: 8, maxLength: 128 });
  
  if (!emailValidation.isValid) {
    return { success: false, error: emailValidation.error };
  }
  
  if (!passwordValidation.isValid) {
    return { success: false, error: passwordValidation.error };
  }
  
  const email = emailValidation.sanitizedValue;
  const password = passwordValidation.sanitizedValue;

  // Get request context for audit logging
  const headersList = headers();
  const context = auditContext.fromRequest({
    headers: headersList,
  } as any);

  try {
    // Log login attempt
    await audit.logAuthentication(
      'login',
      { ...context, userId: email },
      { portal: 'customer' }
    );

    const response = await fetch(`${API_URL}/api/auth/customer/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Trace-ID': context.traceId || '',
        'X-Correlation-ID': context.correlationId || '',
      },
      body: JSON.stringify({
        email,
        password,
        portal: 'customer',
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      
      // Log failed login
      await audit.logAuthentication(
        'failed_login',
        { ...context, userId: email },
        { 
          portal: 'customer',
          error: error.message || 'Invalid credentials',
          statusCode: response.status,
        }
      );
      
      return {
        success: false,
        error: error.message || 'Invalid credentials',
      };
    }

    const data = await response.json();

    // Set secure cookies
    const cookieStore = cookies();
    const secureOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict' as const,
      maxAge: 8 * 60 * 60, // 8 hours (reduced from 7 days)
      path: '/',
    };

    cookieStore.set('secure-auth-token', data.token, secureOptions);
    cookieStore.set('portal-type', 'customer', secureOptions);
    cookieStore.set('user-id', data.customer.id, secureOptions);
    cookieStore.set('session-id', data.sessionId || '', secureOptions);

    // Generate and set CSRF token
    const csrfToken = generateCSRFToken();
    cookieStore.set('csrf-token', csrfToken, secureOptions);

    // Store non-sensitive user data
    cookieStore.set(
      'user-data',
      JSON.stringify({
        id: data.customer.id,
        email: data.customer.email,
        name: data.customer.name,
        accountNumber: data.customer.accountNumber,
      }),
      {
        httpOnly: false,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 8 * 60 * 60, // 8 hours
        path: '/',
      }
    );

    // Log successful login
    await audit.logAuthentication(
      'login',
      { 
        ...context, 
        userId: data.customer.id,
        sessionId: data.sessionId,
      },
      { 
        portal: 'customer',
        userRole: 'customer',
        loginMethod: 'password',
      }
    );

    return {
      success: true,
      customer: data.customer,
    };
  } catch (error) {
    // Log system error
    await audit.system(
      'login_system_error',
      'auth_action',
      false,
      'high',
      {
        error: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
      }
    );
    
    console.error('Login error:', error);
    return {
      success: false,
      error: 'An error occurred during login',
    };
  }
}

export async function registerAction(formData: FormData) {
  const registrationData = {
    email: formData.get('email'),
    password: formData.get('password'),
    name: formData.get('name'),
    phone: formData.get('phone'),
    address: formData.get('address'),
  };

  try {
    const response = await fetch(`${API_URL}/api/auth/customer/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(registrationData),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Registration failed',
      };
    }

    const data = await response.json();

    // Auto-login after registration
    cookies().set('auth-token', data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    cookies().set('portal-type', 'customer', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    return {
      success: true,
      customer: data.customer,
    };
  } catch (error) {
    console.error('Registration error:', error);
    return {
      success: false,
      error: 'An error occurred during registration',
    };
  }
}

export async function logoutAction() {
  try {
    const cookieStore = cookies();
    const userId = cookieStore.get('user-id')?.value;
    const sessionId = cookieStore.get('session-id')?.value;
    
    // Get context for audit logging
    const context = auditContext.fromBrowser(userId, sessionId);

    // Log logout attempt
    await audit.logAuthentication(
      'logout',
      context,
      { logoutMethod: 'user_initiated' }
    );

    // Clear all auth cookies
    cookieStore.delete('secure-auth-token');
    cookieStore.delete('auth-token'); // Legacy cookie
    cookieStore.delete('portal-type');
    cookieStore.delete('user-data');
    cookieStore.delete('user-id');
    cookieStore.delete('session-id');
    cookieStore.delete('csrf-token');

    // Log successful logout
    await audit.logAuthentication(
      'logout',
      context,
      { result: 'success' }
    );

  } catch (error) {
    // Log error but continue with logout
    await audit.system(
      'logout_error',
      'auth_action',
      false,
      'medium',
      { error: error instanceof Error ? error.message : 'Unknown error' }
    );
  }

  // Always redirect to login page
  redirect('/');
}

/**
 * Generate CSRF token
 */
function generateCSRFToken(): string {
  // Use cryptographically secure random number generation
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    // Browser environment
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    const randomString = Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    const timestamp = Date.now().toString(36);
    return `csrf_${timestamp}_${randomString}`;
  } else if (typeof require !== 'undefined') {
    // Node.js environment
    try {
      const crypto = require('crypto');
      const randomBytes = crypto.randomBytes(32);
      const randomString = randomBytes.toString('hex');
      const timestamp = Date.now().toString(36);
      return `csrf_${timestamp}_${randomString}`;
    } catch (error) {
      console.error('Crypto module not available, falling back to timestamp-based token');
      // Fallback for environments without crypto
      const timestamp = Date.now().toString(36);
      const processId = process?.pid?.toString(36) || 'unknown';
      const random = Date.now().toString(36).split('').reverse().join('');
      return `csrf_${timestamp}_${processId}_${random}`;
    }
  } else {
    throw new Error('Secure random number generation not available');
  }
}
