import type { NextApiRequest, NextApiResponse } from 'next';

interface CSPReport {
  'csp-report': {
    'document-uri': string;
    referrer: string;
    'blocked-uri': string;
    'violated-directive': string;
    'original-policy': string;
    disposition: string;
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const report: CSPReport = req.body;

    // Log CSP violations (in production, send to monitoring service)
    console.warn('CSP Violation Report:', {
      timestamp: new Date().toISOString(),
      userAgent: req.headers['user-agent'],
      ip: req.headers['x-forwarded-for'] || req.connection.remoteAddress,
      report: report['csp-report'],
    });

    // In production, you would send this to your monitoring service
    if (process.env.NODE_ENV === 'production' && process.env.SENTRY_DSN) {
      // Example: Send to Sentry or other monitoring service
      // await sendToMonitoringService(report);
    }

    return res.status(200).json({ status: 'report received' });
  } catch (error) {
    console.error('Failed to process CSP report:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}

// Disable body parsing for CSP reports (they come as text)
export const config = {
  api: {
    bodyParser: {
      sizeLimit: '1mb',
    },
  },
};
