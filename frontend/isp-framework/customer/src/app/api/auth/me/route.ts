import { NextRequest, NextResponse } from 'next/server';

// Mock user database - replace with real database in production
const mockUsers = [
  {
    id: 'user-123',
    name: 'John Customer',
    email: 'customer@example.com',
    accountNumber: 'ACC-001',
    portalType: 'customer' as const,
    active: true,
  },
];

export async function GET(request: NextRequest) {
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
      return NextResponse.json({ success: false, error: 'Invalid token' }, { status: 401 });
    }

    const userId = userIdMatch[1];
    const user = mockUsers.find((u) => u.id === userId && u.active);

    if (!user) {
      return NextResponse.json({ success: false, error: 'User not found' }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        accountNumber: user.accountNumber,
        portalType: user.portalType,
      },
    });
  } catch (error) {
    console.error('[Auth] Get user error:', error);
    return NextResponse.json({ success: false, error: 'Internal server error' }, { status: 500 });
  }
}
