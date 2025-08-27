/**
 * Token Refresh API Endpoint
 * Exchanges refresh token for new access token
 */

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(request: NextRequest) {
  try {
    const cookieStore = cookies();
    
    // Get refresh token and session ID
    const refreshToken = cookieStore.get('refresh_token')?.value;
    const sessionId = cookieStore.get('session_id')?.value;
    
    if (!refreshToken || !sessionId) {
      return NextResponse.json(
        { success: false, error: 'No refresh token available' },
        { status: 401 }
      );
    }
    
    // Verify refresh token
    const { verifyRefreshToken, SessionManager, createAccessToken } = await import('../../../../lib/jwt');
    
    const payload = await verifyRefreshToken(refreshToken);
    
    if (!payload) {
      return NextResponse.json(
        { success: false, error: 'Invalid refresh token' },
        { status: 401 }
      );
    }
    
    // Check if session is still active
    if (!SessionManager.isSessionActive(sessionId)) {
      return NextResponse.json(
        { success: false, error: 'Session expired' },
        { status: 401 }
      );
    }
    
    // Validate session matches token
    if (payload.sessionId !== sessionId) {
      return NextResponse.json(
        { success: false, error: 'Session mismatch' },
        { status: 401 }
      );
    }
    
    // Get fresh user data from backend
    const userData = await fetchUserData(payload.sub);
    
    if (!userData) {
      return NextResponse.json(
        { success: false, error: 'User not found' },
        { status: 401 }
      );
    }
    
    // Create new access token with fresh data
    const newAccessToken = await createAccessToken({
      sub: payload.sub,
      email: userData.email,
      role: userData.role,
      permissions: userData.permissions || [],
      tenantId: userData.tenantId,
      sessionId: sessionId,
    });
    
    // Update session activity
    SessionManager.updateSessionActivity(sessionId);
    
    // Set new access token cookie
    const expiresAt = Date.now() + (30 * 60 * 1000); // 30 minutes
    
    cookieStore.set('access_token', newAccessToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 30 * 60, // 30 minutes
      path: '/',
    });
    
    return NextResponse.json({
      success: true,
      expiresAt,
      user: {
        id: payload.sub,
        email: userData.email,
        name: userData.name || userData.email,
        role: userData.role,
        permissions: userData.permissions || [],
        tenantId: userData.tenantId,
      },
    });
    
  } catch (error) {
    console.error('Token refresh error:', error);
    return NextResponse.json(
      { success: false, error: 'Token refresh failed' },
      { status: 500 }
    );
  }
}

/**
 * Fetch fresh user data from ISP Framework
 */
async function fetchUserData(userId: string): Promise<any> {
  try {
    const ispApiUrl = process.env.NEXT_PUBLIC_ISP_API_URL || 'http://localhost:8001';
    
    const response = await fetch(`${ispApiUrl}/api/v1/users/${userId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'DotMac-Admin-Portal/1.0',
      },
    });
    
    if (!response.ok) {
      console.warn(`User fetch failed: ${response.status}`);
      return null;
    }
    
    const userData = await response.json();
    
    return {
      id: userData.id,
      email: userData.email,
      name: userData.name,
      role: userData.role || 'admin',
      permissions: userData.permissions || [],
      tenantId: userData.tenant_id,
    };
    
  } catch (error) {
    console.warn('Backend user fetch error:', error);
    return null;
  }
}