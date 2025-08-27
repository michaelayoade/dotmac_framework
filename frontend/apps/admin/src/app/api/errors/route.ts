/**
 * Error Reporting API Endpoint
 * Handles error reports from the frontend application
 */

import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const errorReport = await request.json();
    
    // Validate required fields
    if (!errorReport.message || !errorReport.timestamp) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Log error (in production, this would go to logging service)
    console.group('🚨 Frontend Error Report');
    console.error('Message:', errorReport.message);
    console.error('URL:', errorReport.url);
    console.error('Timestamp:', errorReport.timestamp);
    console.error('Context:', errorReport.context);
    if (errorReport.stack) {
      console.error('Stack:', errorReport.stack);
    }
    console.groupEnd();

    // In production, you would:
    // 1. Send to error tracking service (Sentry, Bugsnag, etc.)
    // 2. Store in database for analysis
    // 3. Send alerts for critical errors
    // 4. Generate metrics for error monitoring
    
    // Example: Send to external service
    if (process.env.ERROR_TRACKING_URL) {
      try {
        await fetch(process.env.ERROR_TRACKING_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.ERROR_TRACKING_TOKEN}`,
          },
          body: JSON.stringify({
            ...errorReport,
            environment: process.env.NODE_ENV,
            service: 'dotmac-admin',
            version: process.env.npm_package_version || '1.0.0',
          }),
        });
      } catch (externalError) {
        console.error('Failed to send error to external service:', externalError);
        // Don't fail the request if external service fails
      }
    }

    return NextResponse.json(
      { success: true, message: 'Error reported successfully' },
      { status: 200 }
    );

  } catch (error) {
    console.error('Error in error reporting endpoint:', error);
    
    // Don't expose internal errors to client
    return NextResponse.json(
      { error: 'Failed to process error report' },
      { status: 500 }
    );
  }
}

// Optional: GET endpoint for error statistics (admin only)
export async function GET(request: NextRequest) {
  // This would require authentication/authorization
  const url = new URL(request.url);
  const timeframe = url.searchParams.get('timeframe') || '24h';
  
  // Mock response - in production this would query your error database
  const mockStats = {
    timeframe,
    totalErrors: 42,
    errorsByType: {
      reactError: 25,
      javascriptError: 12,
      unhandledRejection: 5,
    },
    topErrors: [
      {
        message: 'Cannot read property of undefined',
        count: 8,
        lastSeen: '2024-02-20T14:30:00Z',
      },
      {
        message: 'Network request failed',
        count: 6,
        lastSeen: '2024-02-20T14:15:00Z',
      },
    ],
  };

  return NextResponse.json(mockStats);
}