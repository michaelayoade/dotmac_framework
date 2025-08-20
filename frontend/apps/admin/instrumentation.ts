/**
 * Next.js instrumentation file
 * This runs before any other code when the server starts
 */

export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    // Only run on server
    const { initializeOTEL } = await import('@dotmac/headless/utils/telemetry');
    const { validateEnv } = await import('@dotmac/headless/utils/env-validation');
    
    // Validate environment variables first
    try {
      validateEnv();
      console.log('✅ Environment validation passed');
    } catch (error) {
      console.error('❌ Environment validation failed:', error);
      if (process.env.NODE_ENV === 'production') {
        process.exit(1);
      }
    }
    
    // Initialize OpenTelemetry
    initializeOTEL('admin-portal');
  }
}