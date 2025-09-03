import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const tenant = req.headers['x-tenant-id'] || req.headers['x-tenant'] || null;
  const apiVersion = req.headers['x-api-version'] || null;
  const userAgent = req.headers['user-agent'] || null;

  return res.status(200).json({
    ok: true,
    portal: 'management-reseller',
    tenant,
    apiVersion,
    userAgent,
    receivedAt: new Date().toISOString(),
  });
}

