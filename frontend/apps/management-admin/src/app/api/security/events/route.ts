import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

interface SecurityEvent {
  type: string;
  severity: string;
  userId?: string;
  tenantId?: string;
  ipAddress: string;
  userAgent: string;
  timestamp: string;
  details: Record<string, any>;
  sessionId: string;
  requestId?: string;
}

export async function POST(request: NextRequest) {
  try {
    const cookieStore = cookies();
    const accessToken = cookieStore.get('mgmt_access_token');

    // Verify user is authenticated for security event logging
    if (!accessToken) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    const { events } = await request.json();

    if (!Array.isArray(events)) {
      return NextResponse.json(
        { error: 'Events must be an array' },
        { status: 400 }
      );
    }

    // Enhance events with server-side information
    const enhancedEvents = events.map((event: SecurityEvent) => ({
      ...event,
      ipAddress: getClientIP(request),
      serverTimestamp: new Date().toISOString(),
      source: 'management-admin-frontend',
    }));

    // In a real implementation, these would be sent to a security monitoring service
    // like Datadog, Splunk, or a custom security event collector
    await forwardToSecurityService(enhancedEvents);

    // Also log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('Security Events:', enhancedEvents);
    }

    return NextResponse.json({ 
      success: true, 
      processed: events.length,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Security event processing error:', error);
    return NextResponse.json(
      { error: 'Failed to process security events' },
      { status: 500 }
    );
  }
}

function getClientIP(request: NextRequest): string {
  // Try various headers to get the real client IP
  const forwarded = request.headers.get('x-forwarded-for');
  const realIP = request.headers.get('x-real-ip');
  const cloudflareIP = request.headers.get('cf-connecting-ip');
  
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  
  if (realIP) {
    return realIP;
  }
  
  if (cloudflareIP) {
    return cloudflareIP;
  }
  
  // Fallback to connection remote address
  return request.ip || 'unknown';
}

async function forwardToSecurityService(events: any[]): Promise<void> {
  // In production, forward to your security monitoring service
  const SECURITY_WEBHOOK_URL = process.env.SECURITY_WEBHOOK_URL;
  
  if (!SECURITY_WEBHOOK_URL) {
    console.warn('SECURITY_WEBHOOK_URL not configured, security events not forwarded');
    return;
  }

  try {
    const response = await fetch(SECURITY_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.SECURITY_WEBHOOK_TOKEN}`,
        'X-Service': 'dotmac-management-admin',
      },
      body: JSON.stringify({
        service: 'dotmac-management-admin',
        environment: process.env.NODE_ENV,
        events,
        timestamp: new Date().toISOString(),
      }),
    });

    if (!response.ok) {
      throw new Error(`Security service responded with ${response.status}`);
    }
  } catch (error) {
    console.error('Failed to forward security events:', error);
    // In production, you might want to queue these for retry
  }
}