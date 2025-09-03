import { NextRequest, NextResponse } from 'next/server';
import { getAuditManager, AuditEventType } from '@/lib/audit';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { error, errorInfo, metadata } = body;

    // Basic validation
    if (!error?.message) {
      return NextResponse.json({ error: 'Invalid error data' }, { status: 400 });
    }

    const auditManager = getAuditManager();

    // Log the error to the audit system
    const errorId = await auditManager.logSystem(
      AuditEventType.SYSTEM_ERROR,
      `Client-side error: ${error.message}`,
      {
        applicationName: 'DotMac Management Admin Portal',
        environment: process.env.NODE_ENV || 'development',
        resourceType: 'client_error',
        ipAddress: req.headers.get('x-forwarded-for') || req.headers.get('x-real-ip') || 'unknown',
        userAgent: req.headers.get('user-agent') || 'unknown',
      },
      {
        reason: 'client_side_error',
        customData: {
          errorMessage: error.message,
          errorName: error.name,
          errorStack: typeof error.stack === 'string' ? error.stack.substring(0, 2000) : undefined,
          componentStack:
            typeof errorInfo?.componentStack === 'string'
              ? errorInfo.componentStack.substring(0, 1000)
              : undefined,
          clientErrorId: metadata?.errorId,
          componentName: metadata?.componentName,
          retryCount: metadata?.retryCount,
          url: metadata?.url,
          timestamp: metadata?.timestamp || new Date().toISOString(),
        },
      }
    );

    // In production, you would also send to external monitoring services
    if (process.env.NODE_ENV === 'production') {
      // Example: Send to Sentry, DataDog, or other monitoring service
      // await sendToExternalMonitoring(error, errorInfo, metadata);
    }

    return NextResponse.json({
      success: true,
      errorId,
      message: 'Error reported successfully',
    });
  } catch (apiError) {
    console.error('Error tracking API failed:', apiError);

    // Fallback: still try to log the original error even if API fails
    try {
      const auditManager = getAuditManager();
      await auditManager.logSystem(
        AuditEventType.SYSTEM_ERROR,
        `Error tracking API failure: ${apiError instanceof Error ? apiError.message : 'Unknown error'}`,
        {
          applicationName: 'DotMac Management Admin Portal',
          resourceType: 'api_error',
        }
      );
    } catch {
      // Silent fail for audit logging
    }

    return NextResponse.json({ error: 'Failed to process error report' }, { status: 500 });
  }
}
