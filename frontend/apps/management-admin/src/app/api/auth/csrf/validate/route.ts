import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(request: NextRequest) {
  try {
    const cookieStore = cookies();
    const storedToken = cookieStore.get('mgmt_csrf_token');
    
    const { token } = await request.json();
    const headerToken = request.headers.get('X-CSRF-Token');
    
    // CSRF token must be provided in both body and header
    if (!token || !headerToken || !storedToken?.value) {
      return NextResponse.json(
        { error: 'Missing CSRF token' },
        { status: 400 }
      );
    }

    // All three tokens must match
    if (token !== headerToken || token !== storedToken.value) {
      return NextResponse.json(
        { error: 'Invalid CSRF token' },
        { status: 403 }
      );
    }

    return NextResponse.json({ valid: true });
  } catch (error) {
    console.error('CSRF validation error:', error);
    return NextResponse.json(
      { error: 'CSRF validation failed' },
      { status: 500 }
    );
  }
}