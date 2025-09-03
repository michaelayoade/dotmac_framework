/**
 * Secure Logout API Endpoint
 */

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(request: NextRequest) {
  try {
    const cookieStore = cookies();

    // Get session ID for proper invalidation
    const sessionId = cookieStore.get('session_id')?.value;

    if (sessionId) {
      // Invalidate session in session manager
      const { SessionManager } = await import('../../../../lib/jwt');
      SessionManager.invalidateSession(sessionId);

      console.info('Session invalidated during logout', {
        sessionId,
        timestamp: new Date().toISOString(),
      });
    }

    // Clear all authentication cookies
    cookieStore.delete('access_token');
    cookieStore.delete('refresh_token');
    cookieStore.delete('session_id');
    cookieStore.delete('csrf-token');

    return NextResponse.json({
      success: true,
      message: 'Logged out successfully',
    });
  } catch (error) {
    console.error('Logout error:', error);

    return NextResponse.json({ success: false, error: 'Logout failed' }, { status: 500 });
  }
}
