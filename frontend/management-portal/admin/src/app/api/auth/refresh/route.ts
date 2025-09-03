import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { serverHttp } from '@/lib/server-http';

const MANAGEMENT_API_URL = process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000';

export async function POST(_request: NextRequest) {
  try {
    const cookieStore = cookies();
    const refreshToken = cookieStore.get('mgmt_refresh_token');

    if (!refreshToken?.value) {
      return NextResponse.json({ error: 'No refresh token found' }, { status: 401 });
    }

    // Call the management platform API to refresh the token
    try {
      const { data: tokenData } = await serverHttp.post(
        `${MANAGEMENT_API_URL}/api/v1/auth/refresh`,
        { refresh_token: refreshToken.value }
      );

      const { access_token, refresh_token: newRefreshToken, expires_at } = tokenData;

      // Update cookies with new tokens
      const COOKIE_OPTIONS = {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict' as const,
        path: '/',
      };

      cookies().set('mgmt_access_token', access_token, {
        ...COOKIE_OPTIONS,
        maxAge: 15 * 60, // 15 minutes
      });

      if (newRefreshToken) {
        cookies().set('mgmt_refresh_token', newRefreshToken, {
          ...COOKIE_OPTIONS,
          maxAge: 7 * 24 * 60 * 60, // 7 days
        });
      }

      cookies().set(
        'mgmt_token_meta',
        JSON.stringify({
          expiresAt: expires_at,
          issuedAt: new Date().toISOString(),
        }),
        {
          ...COOKIE_OPTIONS,
          maxAge: 7 * 24 * 60 * 60,
        }
      );

      return NextResponse.json({
        accessToken: access_token,
        expiresAt: expires_at,
      });
    } catch (err) {
      // Clear invalid refresh token
      cookies().set('mgmt_refresh_token', '', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        path: '/',
        maxAge: 0,
      });
      return NextResponse.json({ error: 'Invalid refresh token' }, { status: 401 });
    }
  } catch (error) {
    console.error('Refresh token error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
