import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const tenant = request.headers.get('x-tenant-id') || request.headers.get('x-tenant');
  const apiVersion = request.headers.get('x-api-version');
  const userAgent = request.headers.get('user-agent');

  return NextResponse.json({
    ok: true,
    portal: 'management-admin',
    tenant,
    apiVersion,
    userAgent,
    receivedAt: new Date().toISOString(),
  });
}

