import type { NextApiRequest, NextApiResponse } from 'next';
import { parse } from 'cookie';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // CSRF protection
  const xRequestedWith = req.headers['x-requested-with'];
  if (xRequestedWith !== 'XMLHttpRequest') {
    return res.status(403).json({ error: 'Invalid request' });
  }

  try {
    const parsedCookies = parse(req.headers.cookie || '');
    const accessToken = parsedCookies.access_token;

    if (!accessToken) {
      return res.status(401).json({
        error: 'No access token found',
        needs_refresh: true,
      });
    }

    // Validate token structure (basic JWT validation)
    const tokenParts = accessToken.split('.');
    if (tokenParts.length !== 3) {
      return res.status(401).json({
        error: 'Invalid token format',
        needs_refresh: true,
      });
    }

    try {
      const payload = JSON.parse(atob(tokenParts[1]));
      const now = Math.floor(Date.now() / 1000);

      if (payload.exp && now >= payload.exp) {
        return res.status(401).json({
          error: 'Token expired',
          needs_refresh: true,
        });
      }
    } catch {
      return res.status(401).json({
        error: 'Invalid token payload',
        needs_refresh: true,
      });
    }

    return res.status(200).json({
      access_token: accessToken,
      valid: true,
    });
  } catch (error) {
    console.error('Failed to retrieve token:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
