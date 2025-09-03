#!/usr/bin/env node

/**
 * Custom Next.js server with graceful shutdown support
 */

const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');

const dev = process.env.NODE_ENV !== 'production';
const hostname = process.env.HOSTNAME || '0.0.0.0';
const port = parseInt(process.env.PORT || '3001', 10);

// Create Next.js app
const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

// Track active connections for graceful shutdown
const connections = new Set();
let isShuttingDown = false;

app.prepare().then(() => {
  const server = createServer((req, res) => {
    // Don't accept new connections during shutdown
    if (isShuttingDown) {
      res.writeHead(503, { 'Content-Type': 'text/plain' });
      res.end('Server is shutting down');
      return;
    }

    // Parse URL
    const parsedUrl = parse(req.url, true);

    // Handle the request
    handle(req, res, parsedUrl);
  });

  // Track connections
  server.on('connection', (connection) => {
    connections.add(connection);
    connection.on('close', () => {
      connections.delete(connection);
    });
  });

  // Configure keep-alive timeout (default 5s, increase for large SSR)
  server.keepAliveTimeout = 30010; // 30 seconds
  server.headersTimeout = 31000; // Slightly higher than keepAliveTimeout

  // Start server
  server.listen(port, hostname, (err) => {
    if (err) throw err;
    console.log(`> Ready on http://${hostname}:${port}`);
    console.log(`> Environment: ${process.env.NODE_ENV || 'development'}`);
    console.log(`> Keep-alive timeout: ${server.keepAliveTimeout}ms`);
  });

  // Graceful shutdown handler
  const gracefulShutdown = (signal) => {
    console.log(`\n> Received ${signal}, starting graceful shutdown...`);
    isShuttingDown = true;

    // Stop accepting new connections
    server.close((err) => {
      if (err) {
        console.error('> Error during server close:', err);
        process.exit(1);
      }
      console.log('> Server closed successfully');
      process.exit(0);
    });

    // Close existing connections after a grace period
    const gracePeriod = parseInt(process.env.SHUTDOWN_GRACE_PERIOD || '30010', 10);

    setTimeout(() => {
      console.log(
        `> Grace period (${gracePeriod}ms) expired, forcefully closing ${connections.size} connections`
      );

      connections.forEach((connection) => {
        connection.destroy();
      });

      // Force exit after additional timeout
      setTimeout(() => {
        console.error('> Forced exit after timeout');
        process.exit(1);
      }, 5000);
    }, gracePeriod);
  };

  // Register shutdown handlers
  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));

  // Handle uncaught errors
  process.on('uncaughtException', (err) => {
    console.error('> Uncaught exception:', err);
    gracefulShutdown('UNCAUGHT_EXCEPTION');
  });

  process.on('unhandledRejection', (reason, promise) => {
    console.error('> Unhandled rejection at:', promise, 'reason:', reason);
    // Don't exit on unhandled rejection in development
    if (process.env.NODE_ENV === 'production') {
      gracefulShutdown('UNHANDLED_REJECTION');
    }
  });
});
