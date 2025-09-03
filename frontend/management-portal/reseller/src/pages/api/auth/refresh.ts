import type { NextApiRequest, NextApiResponse } from 'next';
import { serialize, parse } from 'cookie';
import { env } from '@/lib/environment';
import { serverHttp } from '@/lib/server-http';

interface RefreshRequest {
  client_type: string;
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
    const parsedCookies = parse(req.headers.cookie || '');
    const refreshToken = parsedCookies.refresh_token;
    const sessionMeta = parsedCookies.session_meta;

    if (!refreshToken) {
      return res.status(401).json({
        error: 'No refresh token found',
        requires_login: true,
      });
    }

    // Validate session metadata
    if (sessionMeta) {
      try {
        const meta = JSON.parse(sessionMeta);
        const now = Date.now();

        // Check if session is too old (7 days)
        if (now - meta.created > 604800000) {
          return res.status(401).json({
            error: 'Session expired',
            requires_login: true,
          });
        }
      } catch {
        // Invalid session meta, continue with refresh attempt
      }
    }

    const { client_type }: RefreshRequest = req.body;

    // Call backend API to refresh token
    try {
      const { data } = await serverHttp.post(
        `${env.managementApiUrl}/api/v1/auth/refresh`,
        {
          refresh_token: refreshToken,
          client_type: client_type || 'management-reseller',
        },
        {
          headers: {
            'User-Agent': 'Management-Reseller/1.0',
            'X-Client-Type': client_type || 'management-reseller',
          },
        }
      );

      if (!data.access_token) {
        return res.status(500).json({
          error: 'Invalid refresh response',
          requires_login: true,
        });
      }

      const cookiesToSet: string[] = [];

      // Set new access token with updated expiry
      const accessCookie = serialize('access_token', data.access_token, {
        httpOnly: true,
        secure: env.isProduction,
        sameSite: 'strict',
        maxAge: data.expires_in || 3600, // Use server-provided expiry
        path: '/',
      });
      cookiesToSet.push(accessCookie);

      // Update refresh token if provided
      if (data.refresh_token) {
        const refreshCookie = serialize('refresh_token', data.refresh_token, {
          httpOnly: true,
          secure: env.isProduction,
          sameSite: 'strict',
          maxAge: 604800, // 7 days
          path: '/api/auth',
        });
        cookiesToSet.push(refreshCookie);
      }

      // Update session metadata
      const sessionCookie = serialize(
        'session_meta',
        JSON.stringify({
          created: sessionMeta ? JSON.parse(sessionMeta).created : Date.now(),
          last_refresh: Date.now(),
          client_type: client_type || 'management-reseller',
        }),
        {
          httpOnly: true,
          secure: env.isProduction,
          sameSite: 'strict',
          maxAge: 604800, // 7 days
          path: '/',
        }
      );
      cookiesToSet.push(sessionCookie);

      res.setHeader('Set-Cookie', cookiesToSet);

      return res.status(200).json({
        access_token: data.access_token,
        expires_in: data.expires_in || 3600,
        refreshed_at: Date.now(),
      });
    } catch (err: any) {
      // Clear all auth cookies if refresh fails
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

      return res.status(401).json({
        error: 'Token refresh failed',
        requires_login: true,
        status: err?.response?.status || 500,
      });
    }
  } catch (error) {
    console.error('Token refresh error:', error);

    // Clear cookies on error
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
    ];

    res.setHeader('Set-Cookie', cookiesToClear);

    return res.status(500).json({
      error: 'Internal server error',
      requires_login: true,
    });
  }
}
