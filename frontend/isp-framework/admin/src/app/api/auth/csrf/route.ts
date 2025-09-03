/**
 * CSRF Token Endpoint
 * Generates and validates CSRF tokens for state-changing operations
 */

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { generateNonce } from '../../../../lib/security';

// Generate CSRF token
export async function GET(request: NextRequest) {
  try {
    // Generate a secure random token
    const csrfToken = generateNonce();

    // Store token in secure httpOnly cookie
    cookies().set('csrf-token', csrfToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60, // 1 hour
      path: '/',
    });

    // Return token to client (also stored in cookie for server-side validation)
    return NextResponse.json({
      csrfToken,
      message: 'CSRF token generated successfully',
    });
  } catch (error) {
    console.error('CSRF token generation error:', error);
    return NextResponse.json({ error: 'Failed to generate CSRF token' }, { status: 500 });
  }
}

// Validate CSRF token (for debugging/testing)
export async function POST(request: NextRequest) {
  try {
    const { token } = await request.json();
    const storedToken = cookies().get('csrf-token')?.value;

    const isValid = token && storedToken && token === storedToken;

    return NextResponse.json({
      valid: isValid,
      message: isValid ? 'CSRF token is valid' : 'CSRF token is invalid',
    });
  } catch (error) {
    console.error('CSRF token validation error:', error);
    return NextResponse.json({ error: 'Failed to validate CSRF token' }, { status: 500 });
  }
}
