import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET(_request: NextRequest) {
  try {
    const cookieStore = cookies();
    const accessToken = cookieStore.get('mgmt_access_token');
    const tokenMeta = cookieStore.get('mgmt_token_meta');

    if (!accessToken?.value) {
      return NextResponse.json({ error: 'No access token found' }, { status: 401 });
    }

    // Validate token hasn't expired
    if (tokenMeta?.value) {
      try {
        const meta = JSON.parse(tokenMeta.value);
        const expiresAt = new Date(meta.expiresAt);

        if (expiresAt <= new Date()) {
          return NextResponse.json({ error: 'Access token expired' }, { status: 401 });
        }
      } catch {
        // Invalid metadata, treat as expired
        return NextResponse.json({ error: 'Invalid token metadata' }, { status: 401 });
      }
    }

    return NextResponse.json({
      accessToken: accessToken.value,
      expiresAt: tokenMeta?.value ? JSON.parse(tokenMeta.value).expiresAt : null,
    });
  } catch (error) {
    console.error('Get token error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
