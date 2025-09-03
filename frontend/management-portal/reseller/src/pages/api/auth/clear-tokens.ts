import type { NextApiRequest, NextApiResponse } from 'next';
import { serialize } from 'cookie';
import { env } from '@/lib/environment';

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
    // Clear all authentication cookies by setting them with past expiration
    const cookiesToClear = [
      serialize('access_token', '', {
        httpOnly: true,
        secure: env.isProduction,
        sameSite: 'strict',
        expires: new Date(0),
        path: '/',
      }),
      serialize('refresh_token', '', {
        httpOnly: true,
        secure: env.isProduction,
        sameSite: 'strict',
        expires: new Date(0),
        path: '/api/auth',
      }),
      serialize('session_meta', '', {
        httpOnly: true,
        secure: env.isProduction,
        sameSite: 'strict',
        expires: new Date(0),
        path: '/',
      }),
    ];

    res.setHeader('Set-Cookie', cookiesToClear);

    return res.status(200).json({
      success: true,
      message: 'All tokens cleared successfully',
      cleared_at: Date.now(),
    });
  } catch (error) {
    console.error('Failed to clear tokens:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
