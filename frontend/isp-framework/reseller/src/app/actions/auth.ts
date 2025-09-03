'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { logAuthEvent, logger } from '../../utils/logger';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function loginAction(formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;

  try {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        portal: 'reseller',
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.message || 'Invalid credentials',
      };
    }

    const data = await response.json();

    // Set secure cookies
    cookies().set('auth-token', data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    cookies().set('portal-type', 'reseller', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    // Store user data in cookie (non-sensitive)
    cookies().set(
      'user-data',
      JSON.stringify({
        id: data.user.id,
        email: data.user.email,
        name: data.user.name,
        role: data.user.role,
        resellerLevel: data.user.resellerLevel,
      }),
      {
        httpOnly: false,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 60 * 60 * 24 * 7, // 7 days
        path: '/',
      }
    );

    return {
      success: true,
      user: data.user,
    };
  } catch (error) {
    logger.error('Login failed', error, { component: 'auth', action: 'login' });
    return {
      success: false,
      error: 'An error occurred during login',
    };
  }
}

export async function logoutAction() {
  // Clear all auth cookies
  cookies().delete('auth-token');
  cookies().delete('portal-type');
  cookies().delete('user-data');

  // Redirect to login page
  redirect('/');
}

export async function refreshTokenAction() {
  const token = cookies().get('auth-token');

  if (!token) {
    return { success: false, error: 'No auth token found' };
  }

  try {
    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token.value}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return { success: false, error: 'Failed to refresh token' };
    }

    const data = await response.json();

    // Update auth token
    cookies().set('auth-token', data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24 * 7, // 7 days
      path: '/',
    });

    return { success: true, token: data.token };
  } catch (error) {
    logger.error('Token refresh failed', error, {
      component: 'auth',
      action: 'refresh',
    });
    return { success: false, error: 'Failed to refresh token' };
  }
}

export async function validateSessionAction() {
  const token = cookies().get('auth-token');

  if (!token) {
    return { valid: false };
  }

  try {
    const response = await fetch(`${API_URL}/api/auth/validate`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token.value}`,
      },
    });

    return { valid: response.ok };
  } catch (error) {
    logger.error('Session validation failed', error, {
      component: 'auth',
      action: 'validate',
    });
    return { valid: false };
  }
}
