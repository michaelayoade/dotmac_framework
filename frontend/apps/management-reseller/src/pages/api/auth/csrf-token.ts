import type { NextApiRequest, NextApiResponse } from 'next';
import { serialize } from 'cookie';
import crypto from 'crypto';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  // Generate CSRF token
  const token = crypto.randomBytes(32).toString('hex');
  
  // Set CSRF token in cookie
  const csrfCookie = serialize('csrf-token', token, {
    httpOnly: false, // Needs to be accessible by client for header
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    maxAge: 60 * 60, // 1 hour
    path: '/',
  });

  res.setHeader('Set-Cookie', csrfCookie);
  res.status(200).json({ token });
}