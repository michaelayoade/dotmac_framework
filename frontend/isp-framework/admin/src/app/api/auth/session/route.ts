/**
 * Session Validation API Endpoint
 */

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = cookies();
    const sessionToken = cookieStore.get('session')?.value;

    if (!sessionToken) {
      return NextResponse.json({ valid: false, error: 'No session found' }, { status: 401 });
    }

    // Validate session token
    const sessionData = await validateSessionToken(sessionToken);

    if (!sessionData.valid) {
      // Clear invalid session
      cookieStore.delete('session');

      return NextResponse.json(
        { valid: false, error: 'Session expired or invalid' },
        { status: 401 }
      );
    }

    // Check if session is close to expiring and extend it
    const now = Date.now();
    const timeUntilExpiry = sessionData.expiresAt - now;
    const fiveMinutes = 5 * 60 * 1000;

    if (timeUntilExpiry < fiveMinutes) {
      // Extend session by resetting the cookie
      const newExpiryTime = now + 30 * 60 * 1000; // 30 minutes from now
      const updatedSessionData = { ...sessionData, expiresAt: newExpiryTime };
      const newSessionToken = Buffer.from(JSON.stringify(updatedSessionData)).toString('base64');

      cookieStore.set('session', newSessionToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 30 * 60, // 30 minutes
        path: '/',
      });
    }

    return NextResponse.json({
      valid: true,
      user: {
        id: sessionData.userId,
        email: sessionData.email,
        role: sessionData.role,
        permissions: sessionData.permissions,
      },
      expiresAt: sessionData.expiresAt,
    });
  } catch (error) {
    console.error('Session validation error:', error);

    return NextResponse.json({ valid: false, error: 'Session validation failed' }, { status: 500 });
  }
}

async function validateSessionToken(token: string): Promise<{
  valid: boolean;
  userId?: string;
  email?: string;
  role?: string;
  permissions?: string[];
  expiresAt?: number;
  error?: string;
}> {
  try {
    // Decode the session token (in production, use proper JWT verification)
    const sessionData = JSON.parse(Buffer.from(token, 'base64').toString());

    // Check expiration
    if (Date.now() > sessionData.expiresAt) {
      return { valid: false, error: 'Session expired' };
    }

    // TODO: Verify session with your session store/database
    // This is a simplified implementation

    return {
      valid: true,
      userId: sessionData.userId,
      email: sessionData.email,
      role: sessionData.role,
      permissions: sessionData.permissions,
      expiresAt: sessionData.expiresAt,
    };
  } catch (error) {
    return { valid: false, error: 'Invalid session token' };
  }
}
