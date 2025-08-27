/**
 * Content Security Policy Violation Reporting Endpoint
 * Handles CSP violation reports for security monitoring
 */

import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

// CSP Report schema validation
const cspReportSchema = z.object({
  'csp-report': z.object({
    'blocked-uri': z.string().optional(),
    'document-uri': z.string(),
    'original-policy': z.string(),
    'referrer': z.string().optional(),
    'violated-directive': z.string(),
    'effective-directive': z.string().optional(),
    'status-code': z.number().optional(),
    'script-sample': z.string().optional(),
    'source-file': z.string().optional(),
    'line-number': z.number().optional(),
    'column-number': z.number().optional(),
  }),
});

// Rate limiting for CSP reports (prevent spam)
const rateLimitMap = new Map<string, { count: number; timestamp: number }>();
const RATE_LIMIT_WINDOW = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX = 50; // Max 50 reports per minute per IP

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const existing = rateLimitMap.get(ip);
  
  if (!existing || now - existing.timestamp > RATE_LIMIT_WINDOW) {
    rateLimitMap.set(ip, { count: 1, timestamp: now });
    return true;
  }
  
  if (existing.count >= RATE_LIMIT_MAX) {
    return false;
  }
  
  existing.count++;
  return true;
}

export async function POST(request: NextRequest) {
  try {
    // Get client IP for rate limiting
    const clientIP = request.headers.get('x-forwarded-for')?.split(',')[0] || 
                     request.headers.get('x-real-ip') || 
                     'unknown';
    
    // Check rate limiting
    if (!checkRateLimit(clientIP)) {
      return NextResponse.json(
        { error: 'Rate limit exceeded' },
        { status: 429 }
      );
    }
    
    // Parse and validate the CSP report
    const body = await request.json();
    const validatedReport = cspReportSchema.parse(body);
    const report = validatedReport['csp-report'];
    
    // Enhanced CSP violation logging
    const violationInfo = {
      timestamp: new Date().toISOString(),
      clientIP,
      userAgent: request.headers.get('user-agent') || 'unknown',
      referer: request.headers.get('referer') || 'unknown',
      documentUri: report['document-uri'],
      blockedUri: report['blocked-uri'] || 'unknown',
      violatedDirective: report['violated-directive'],
      effectiveDirective: report['effective-directive'] || report['violated-directive'],
      originalPolicy: report['original-policy'],
      sourceFile: report['source-file'] || 'unknown',
      lineNumber: report['line-number'] || 0,
      columnNumber: report['column-number'] || 0,
      scriptSample: report['script-sample'] || '',
      statusCode: report['status-code'] || 0,
    };
    
    // Log the violation (in production, send to monitoring service)
    if (process.env.NODE_ENV === 'production') {
      console.error('CSP Violation Report:', JSON.stringify(violationInfo, null, 2));
      
      // TODO: Send to monitoring service (Sentry, DataDog, etc.)
      // await sendToMonitoringService(violationInfo);
    } else {
      console.warn('CSP Violation (Development):', {
        directive: report['violated-directive'],
        blockedUri: report['blocked-uri'],
        documentUri: report['document-uri'],
        sourceFile: report['source-file'],
        line: report['line-number'],
      });
    }
    
    // Analyze violation patterns for security insights
    const insights = analyzeViolation(report);
    if (insights.severity === 'high') {
      console.error('High-severity CSP violation detected:', insights.description);
      // TODO: Send immediate alert for high-severity violations
    }
    
    // Clean up old rate limit entries periodically
    cleanupRateLimitMap();
    
    return NextResponse.json(
      { received: true, timestamp: new Date().toISOString() },
      { status: 200 }
    );
    
  } catch (error) {
    console.error('CSP Report Handler Error:', error);
    
    return NextResponse.json(
      { error: 'Invalid report format' },
      { status: 400 }
    );
  }
}

// Only allow POST requests
export async function GET() {
  return NextResponse.json(
    { error: 'Method not allowed' },
    { status: 405 }
  );
}

/**
 * Analyze CSP violation for security insights
 */
function analyzeViolation(report: any) {
  const blockedUri = report['blocked-uri'] || '';
  const violatedDirective = report['violated-directive'] || '';
  const sourceFile = report['source-file'] || '';
  
  // Check for potential XSS attempts
  if (violatedDirective.includes('script-src') && blockedUri.includes('javascript:')) {
    return {
      severity: 'high',
      description: 'Potential XSS attempt detected - javascript: protocol blocked',
      category: 'xss_attempt',
    };
  }
  
  // Check for data exfiltration attempts
  if (violatedDirective.includes('connect-src') && 
      !blockedUri.includes(process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || '')) {
    return {
      severity: 'high',
      description: 'Potential data exfiltration - unauthorized external connection blocked',
      category: 'data_exfiltration',
    };
  }
  
  // Check for clickjacking attempts
  if (violatedDirective.includes('frame-src') || violatedDirective.includes('frame-ancestors')) {
    return {
      severity: 'medium',
      description: 'Potential clickjacking attempt - frame blocked',
      category: 'clickjacking',
    };
  }
  
  // Check for inline script violations (could be legitimate or malicious)
  if (violatedDirective.includes('script-src') && blockedUri === 'inline') {
    return {
      severity: 'medium',
      description: 'Inline script blocked - review for necessity',
      category: 'inline_script',
    };
  }
  
  // Check for unsafe eval violations
  if (violatedDirective.includes('script-src') && report['script-sample']?.includes('eval')) {
    return {
      severity: 'medium',
      description: 'Unsafe eval usage detected',
      category: 'unsafe_eval',
    };
  }
  
  return {
    severity: 'low',
    description: 'Standard CSP violation - likely legitimate content blocked',
    category: 'standard_violation',
  };
}

/**
 * Clean up old rate limit entries
 */
function cleanupRateLimitMap() {
  const now = Date.now();
  for (const [ip, data] of rateLimitMap.entries()) {
    if (now - data.timestamp > RATE_LIMIT_WINDOW) {
      rateLimitMap.delete(ip);
    }
  }
}

/**
 * Send violation report to external monitoring service
 * TODO: Implement integration with your monitoring service
 */
async function sendToMonitoringService(violation: any) {
  // Example integration with Sentry
  if (process.env.SENTRY_DSN) {
    try {
      // await Sentry.captureException(new Error('CSP Violation'), {
      //   tags: {
      //     violation_type: violation.violatedDirective,
      //     severity: violation.severity,
      //   },
      //   extra: violation,
      // });
    } catch (error) {
      console.error('Failed to send CSP violation to Sentry:', error);
    }
  }
  
  // Example integration with custom webhook
  if (process.env.CSP_WEBHOOK_URL) {
    try {
      await fetch(process.env.CSP_WEBHOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'TenantPortal-CSP-Reporter/1.0',
        },
        body: JSON.stringify({
          type: 'csp_violation',
          data: violation,
          timestamp: new Date().toISOString(),
        }),
      });
    } catch (error) {
      console.error('Failed to send CSP violation to webhook:', error);
    }
  }
}