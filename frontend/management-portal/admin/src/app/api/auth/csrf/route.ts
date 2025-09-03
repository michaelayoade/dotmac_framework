import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { generateNonce } from '@/lib/csp-utils';

export async function GET(_request: NextRequest) {
  try {
    const cookieStore = cookies();

    // Generate CSRF token (reuse nonce generation for crypto security)
    const csrfToken = generateNonce() + generateNonce(); // Double length for CSRF

    // Store CSRF token in httpOnly cookie
    cookieStore.set('mgmt_csrf_token', csrfToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      path: '/',
      maxAge: 60 * 60, // 1 hour
    });

    return NextResponse.json({
      csrfToken,
      expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    });
  } catch (error) {
    console.error('CSRF token generation error:', error);
    return NextResponse.json({ error: 'Failed to generate CSRF token' }, { status: 500 });
  }
}
