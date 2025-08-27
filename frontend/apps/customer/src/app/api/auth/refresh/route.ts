import { NextRequest, NextResponse } from 'next/server';

// Mock user database - replace with real database in production
const mockUsers = [
  {
    id: 'user-123',
    name: 'John Customer', 
    email: 'customer@example.com',
    accountNumber: 'ACC-001',
    portalType: 'customer' as const,
    active: true
  }
];

export async function POST(request: NextRequest) {
  try {
    const authToken = request.cookies.get('secure-auth-token');
    const portalType = request.cookies.get('portal-type');

    if (!authToken || portalType?.value !== 'customer') {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Extract user ID from token (simplified - use JWT verification in production)
    const userIdMatch = authToken.value.match(/session_(.+?)_/);
    if (!userIdMatch) {
      return NextResponse.json(
        { success: false, error: 'Invalid token' },
        { status: 401 }
      );
    }

    const userId = userIdMatch[1];
    const user = mockUsers.find(u => u.id === userId && u.active);

    if (!user) {
      return NextResponse.json(
        { success: false, error: 'User not found' },
        { status: 404 }
      );
    }

    // Generate new tokens
    const newSessionToken = `session_${user.id}_${Date.now()}`;
    const newCsrfToken = `csrf_${Math.random().toString(36).substring(2, 15)}`;

    const response = NextResponse.json({
      success: true,
      accessToken: newSessionToken,
      expiresIn: 3600, // 1 hour
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        accountNumber: user.accountNumber,
        portalType: user.portalType
      }
    });

    // Update cookies
    const cookieOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict' as const,
      maxAge: 24 * 60 * 60 * 1000, // 1 day
      path: '/'
    };

    response.cookies.set('secure-auth-token', newSessionToken, cookieOptions);
    response.cookies.set('csrf-token', newCsrfToken, {
      ...cookieOptions,
      httpOnly: false
    });

    return response;

  } catch (error) {
    console.error('[Auth] Refresh error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}