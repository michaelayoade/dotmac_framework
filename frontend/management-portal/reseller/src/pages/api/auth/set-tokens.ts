import type { NextApiRequest, NextApiResponse } from 'next';
import { serialize } from 'cookie';
import { env } from '@/lib/environment';

interface SetTokensRequest {
  access_token: string;
  refresh_token?: string;
  timestamp: number;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // CSRF protection
  const xRequestedWith = req.headers['x-requested-with'];
  if (xRequestedWith !== 'XMLHttpRequest') {
    return res.status(403).json({ error: 'Invalid request' });
  }

  try {
    const { access_token, refresh_token, timestamp }: SetTokensRequest = req.body;

    if (!access_token || !timestamp) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // Validate timestamp to prevent replay attacks (within 5 minutes)
    const now = Date.now();
    if (Math.abs(now - timestamp) > 300000) {
      return res.status(400).json({ error: 'Request expired' });
    }

    const cookies: string[] = [];

    // Set access token cookie (short-lived, secure)
    const accessTokenCookie = serialize('access_token', access_token, {
      httpOnly: true,
      secure: env.isProduction,
      sameSite: 'strict',
      maxAge: 3600, // 1 hour
      path: '/',
    });
    cookies.push(accessTokenCookie);

    // Set refresh token cookie (long-lived, secure)
    if (refresh_token) {
      const refreshTokenCookie = serialize('refresh_token', refresh_token, {
        httpOnly: true,
        secure: env.isProduction,
        sameSite: 'strict',
        maxAge: 604800, // 7 days
        path: '/api/auth',
      });
      cookies.push(refreshTokenCookie);
    }

    // Set session metadata
    const sessionCookie = serialize(
      'session_meta',
      JSON.stringify({
        created: timestamp,
        last_refresh: timestamp,
        client_type: 'management-reseller',
      }),
      {
        httpOnly: true,
        secure: env.isProduction,
        sameSite: 'strict',
        maxAge: 604800, // 7 days
        path: '/',
      }
    );
    cookies.push(sessionCookie);

    // Set all cookies at once
    res.setHeader('Set-Cookie', cookies);

    return res.status(200).json({
      success: true,
      message: 'Tokens set successfully',
    });
  } catch (error) {
    console.error('Failed to set tokens:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
