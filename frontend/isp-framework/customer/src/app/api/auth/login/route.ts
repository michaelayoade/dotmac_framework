import { NextRequest, NextResponse } from 'next/server';

interface LoginRequest {
  email: string;
  password: string;
  portalId?: string;
  rememberMe?: boolean;
}

// Basic validation helper
function validateEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function validatePassword(password: string): boolean {
  return password && password.length >= 8;
}

// Mock user database - replace with real database in production
const mockUsers = [
  {
    id: 'user-123',
    name: 'John Customer',
    email: 'customer@example.com',
    password: 'hashedPassword123!', // In production, use bcrypt
    accountNumber: 'ACC-001',
    portalType: 'customer' as const,
    active: true,
  },
];

export async function POST(request: NextRequest) {
  try {
    const body: LoginRequest = await request.json();
    const { email, password, portalId, rememberMe } = body;

    // Validate input
    if (!email || !password) {
      return NextResponse.json(
        { success: false, error: 'Email and password are required' },
        { status: 400 }
      );
    }

    if (!validateEmail(email)) {
      return NextResponse.json({ success: false, error: 'Invalid email format' }, { status: 400 });
    }

    if (!validatePassword(password)) {
      return NextResponse.json(
        { success: false, error: 'Password must be at least 8 characters' },
        { status: 400 }
      );
    }

    // Rate limiting check (basic implementation)
    const clientIP = request.ip || request.headers.get('x-forwarded-for') || 'unknown';
    const rateLimitKey = `auth:${clientIP}:${email}`;

    // In production, use Redis or database for rate limiting
    // For now, just continue

    // Find user (replace with database query)
    const user = mockUsers.find((u) => u.email.toLowerCase() === email.toLowerCase() && u.active);

    if (!user) {
      // Don't reveal whether user exists
      return NextResponse.json({ success: false, error: 'Invalid credentials' }, { status: 401 });
    }

    // Verify password (in production, use bcrypt.compare)
    if (user.password !== 'hashedPassword123!') {
      return NextResponse.json({ success: false, error: 'Invalid credentials' }, { status: 401 });
    }

    // Generate tokens (simplified - use JWT in production)
    const sessionToken = `session_${user.id}_${Date.now()}`;
    const csrfToken = `csrf_${Math.random().toString(36).substring(2, 15)}`;

    // Create response
    const response = NextResponse.json({
      success: true,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        accountNumber: user.accountNumber,
        portalType: user.portalType,
      },
      message: 'Login successful',
    });

    // Set secure cookies
    const cookieOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict' as const,
      maxAge: rememberMe ? 30 * 24 * 60 * 60 * 1000 : 24 * 60 * 60 * 1000, // 30 days or 1 day
      path: '/',
    };

    response.cookies.set('secure-auth-token', sessionToken, cookieOptions);
    response.cookies.set('csrf-token', csrfToken, {
      ...cookieOptions,
      httpOnly: false, // CSRF token needs to be readable by client
    });
    response.cookies.set('portal-type', 'customer', {
      ...cookieOptions,
      httpOnly: false,
    });

    return response;
  } catch (error) {
    console.error('[Auth] Login error:', error);
    return NextResponse.json({ success: false, error: 'Internal server error' }, { status: 500 });
  }
}
