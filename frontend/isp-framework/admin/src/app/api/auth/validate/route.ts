/**
 * Session Validation API Endpoint
 * Validates current session and returns user info
 */

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
  try {
    const cookieStore = cookies();

    // Get access token from cookie
    const accessToken = cookieStore.get('access_token')?.value;
    const sessionId = cookieStore.get('session_id')?.value;

    if (!accessToken || !sessionId) {
      return NextResponse.json({ success: false, error: 'No active session' }, { status: 401 });
    }

    // Verify the JWT token
    const { verifyAccessToken, SessionManager } = await import('../../../../lib/jwt');

    const payload = await verifyAccessToken(accessToken);

    if (!payload) {
      return NextResponse.json({ success: false, error: 'Invalid session token' }, { status: 401 });
    }

    // Check if session is still active
    if (!SessionManager.isSessionActive(sessionId)) {
      return NextResponse.json({ success: false, error: 'Session expired' }, { status: 401 });
    }

    // Update session activity
    SessionManager.updateSessionActivity(sessionId);

    // Validate user with ISP Framework
    const userData = await validateUserWithBackend(payload.sub);

    if (!userData) {
      return NextResponse.json(
        { success: false, error: 'User validation failed' },
        { status: 401 }
      );
    }

    return NextResponse.json({
      success: true,
      user: {
        id: payload.sub,
        email: payload.email,
        name: userData.name || payload.email,
        role: payload.role,
        permissions: payload.permissions || [],
        tenantId: payload.tenantId,
      },
      sessionId: payload.sessionId,
      expiresAt: payload.exp ? payload.exp * 1000 : null, // Convert to milliseconds
    });
  } catch (error) {
    console.error('Session validation error:', error);
    return NextResponse.json(
      { success: false, error: 'Session validation failed' },
      { status: 500 }
    );
  }
}

/**
 * Validate user with ISP Framework backend
 */
async function validateUserWithBackend(userId: string): Promise<any> {
  try {
    const ispApiUrl = process.env.NEXT_PUBLIC_ISP_API_URL || 'http://localhost:8001';

    const response = await fetch(`${ispApiUrl}/api/v1/auth/validate-user/${userId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'DotMac-Admin-Portal/1.0',
      },
    });

    if (!response.ok) {
      console.warn(`User validation failed: ${response.status}`);
      return null;
    }

    return await response.json();
  } catch (error) {
    console.warn('Backend user validation error:', error);
    // Return minimal user info to allow session to continue
    return { name: null };
  }
}
