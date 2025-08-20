export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    // Server-side instrumentation
    const { registerOTel } = await import('./monitoring/otel');
    registerOTel('admin-portal');
  }

  if (process.env.NEXT_RUNTIME === 'edge') {
    // Edge runtime instrumentation
    console.log('Edge runtime initialized for admin portal');
  }
}

export async function onRequestError(
  error: Error,
  request: {
    path: string;
    method: string;
    headers: Record<string, string>;
  }
) {
  // Log errors to monitoring service
  console.error('Request error:', {
    error: error.message,
    stack: error.stack,
    path: request.path,
    method: request.method,
    timestamp: new Date().toISOString(),
  });

  // In production, send to error tracking service
  if (process.env.NODE_ENV === 'production') {
    // await sendToErrorTracking(error, request);
  }
}