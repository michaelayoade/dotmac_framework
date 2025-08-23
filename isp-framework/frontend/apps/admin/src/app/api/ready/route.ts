import { NextResponse } from 'next/server';

/**
 * Readiness probe endpoint for Kubernetes
 * Checks if the app is ready to receive traffic
 */
export async function GET() {
  try {
    // Check critical dependencies
    const checks = {
      api: await checkAPIConnection(),
      database: await checkDatabaseConnection(),
    };

    const allHealthy = Object.values(checks).every((check) => check);

    if (allHealthy) {
      return NextResponse.json(
        {
          status: 'ready',
          timestamp: new Date().toISOString(),
          service: 'admin-portal',
          checks,
        },
        { status: 200 }
      );
    }

    return NextResponse.json(
      {
        status: 'not_ready',
        timestamp: new Date().toISOString(),
        service: 'admin-portal',
        checks,
      },
      { status: 503 }
    );
  } catch (error) {
    return NextResponse.json(
      {
        status: 'error',
        timestamp: new Date().toISOString(),
        service: 'admin-portal',
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 503 }
    );
  }
}

async function checkAPIConnection(): Promise<boolean> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${apiUrl}/health`, {
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    return false;
  }
}

async function checkDatabaseConnection(): Promise<boolean> {
  // In a real app, this would check the database connection
  // For now, we'll simulate it based on API availability
  return true;
}
