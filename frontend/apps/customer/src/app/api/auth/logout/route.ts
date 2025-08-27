import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // Create response
    const response = NextResponse.json({
      success: true,
      message: 'Logged out successfully'
    });

    // Clear authentication cookies
    const cookieOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict' as const,
      maxAge: 0, // Expire immediately
      path: '/'
    };

    response.cookies.set('secure-auth-token', '', cookieOptions);
    response.cookies.set('csrf-token', '', {
      ...cookieOptions,
      httpOnly: false
    });
    response.cookies.set('portal-type', '', {
      ...cookieOptions,
      httpOnly: false
    });

    return response;

  } catch (error) {
    console.error('[Auth] Logout error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}