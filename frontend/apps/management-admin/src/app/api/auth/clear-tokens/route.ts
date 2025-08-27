import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(_request: NextRequest) {
  try {
    const cookieStore = cookies();

    // Clear all authentication cookies
    const cookiesToClear = [
      'mgmt_access_token',
      'mgmt_refresh_token', 
      'mgmt_token_meta',
      'mgmt_csrf_token'
    ];

    cookiesToClear.forEach(cookieName => {
      cookieStore.set(cookieName, '', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        path: '/',
        maxAge: 0, // Immediate expiration
      });
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Clear tokens error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}