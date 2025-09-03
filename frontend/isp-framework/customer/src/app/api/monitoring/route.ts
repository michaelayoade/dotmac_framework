/**
 * Sentry Tunnel Route
 * Proxies Sentry requests to avoid ad blockers
 */

export async function POST(request: Request) {
  const envelope = await request.text();

  // Extract the Sentry DSN from the first line of the envelope
  const lines = envelope.split('\n');
  const header = JSON.parse(lines[0]);
  const { dsn } = header;

  if (!dsn || !process.env.NEXT_PUBLIC_SENTRY_DSN) {
    return new Response('Unauthorized', { status: 401 });
  }

  // Extract project ID from DSN
  const dsnUrl = new URL(dsn);
  const projectId = dsnUrl.pathname.split('/').pop();

  if (!projectId) {
    return new Response('Invalid DSN', { status: 400 });
  }

  // Forward to Sentry
  const sentryUrl = `https://sentry.io/api/${projectId}/envelope/`;

  try {
    const response = await fetch(sentryUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-sentry-envelope',
      },
      body: envelope,
    });

    return new Response(null, {
      status: response.status,
    });
  } catch (error) {
    console.error('Failed to forward to Sentry:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
}
