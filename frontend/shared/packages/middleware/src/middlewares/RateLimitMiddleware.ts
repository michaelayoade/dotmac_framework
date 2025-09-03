/**
 * Rate Limiting Middleware
 * In-memory rate limiting for frontend middleware
 */

import { NextResponse } from 'next/server';
import type { MiddlewareFunction, MiddlewareContext, RateLimitConfig } from '../types';
import { isAuthEndpoint } from '../utils';

/**
 * In-memory rate limit store
 * In production, use Redis or similar distributed cache
 */
const rateLimitStore = new Map<string, { count: number; resetTime: number; blocked: boolean }>();

/**
 * Clean up expired entries periodically
 */
let lastCleanup = 0;
const CLEANUP_INTERVAL = 5 * 60 * 1000; // 5 minutes

function cleanupExpiredEntries() {
  const now = Date.now();
  if (now - lastCleanup < CLEANUP_INTERVAL) return;

  for (const [key, entry] of rateLimitStore.entries()) {
    if (now > entry.resetTime) {
      rateLimitStore.delete(key);
    }
  }

  lastCleanup = now;
}

/**
 * Check rate limit for a given identifier
 */
function checkRateLimit(config: RateLimitConfig): {
  allowed: boolean;
  resetTime: number;
  remaining: number;
} {
  cleanupExpiredEntries();

  const now = Date.now();
  const { identifier, maxRequests, windowMs } = config;
  const entry = rateLimitStore.get(identifier);

  if (!entry || now > entry.resetTime) {
    // Create or reset entry
    const resetTime = now + windowMs;
    rateLimitStore.set(identifier, {
      count: 1,
      resetTime,
      blocked: false,
    });

    return {
      allowed: true,
      resetTime,
      remaining: maxRequests - 1,
    };
  }

  // Check if already blocked
  if (entry.blocked || entry.count >= maxRequests) {
    entry.blocked = true;
    return {
      allowed: false,
      resetTime: entry.resetTime,
      remaining: 0,
    };
  }

  // Increment count
  entry.count++;

  return {
    allowed: true,
    resetTime: entry.resetTime,
    remaining: maxRequests - entry.count,
  };
}

/**
 * Rate limiting middleware factory
 */
export function createRateLimitMiddleware(
  generalConfig: { requests: number; windowMs: number },
  authConfig: { requests: number; windowMs: number }
): MiddlewareFunction {
  return async (context: MiddlewareContext) => {
    const { pathname, clientIP } = context;

    // Determine rate limit config based on endpoint type
    const isAuth = isAuthEndpoint(pathname);
    const config: RateLimitConfig = isAuth
      ? {
          identifier: `auth:${clientIP}`,
          maxRequests: authConfig.requests,
          windowMs: authConfig.windowMs,
        }
      : {
          identifier: `general:${clientIP}`,
          maxRequests: generalConfig.requests,
          windowMs: generalConfig.windowMs,
        };

    // Check rate limit
    const { allowed, resetTime, remaining } = checkRateLimit(config);

    if (!allowed) {
      const retryAfter = Math.ceil((resetTime - Date.now()) / 1000);

      return NextResponse.json(
        {
          error: 'Rate limit exceeded',
          message: isAuth
            ? 'Too many authentication attempts. Please try again later.'
            : 'Too many requests. Please slow down.',
          retryAfter,
        },
        {
          status: 429,
          headers: {
            'Retry-After': retryAfter.toString(),
            'X-RateLimit-Limit': config.maxRequests.toString(),
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': Math.ceil(resetTime / 1000).toString(),
          },
        }
      );
    }

    // Add rate limit headers to successful responses
    context.request.headers.set('x-ratelimit-limit', config.maxRequests.toString());
    context.request.headers.set('x-ratelimit-remaining', remaining.toString());
    context.request.headers.set('x-ratelimit-reset', Math.ceil(resetTime / 1000).toString());

    return null; // Continue to next middleware
  };
}

/**
 * Sliding window rate limiter (more accurate but uses more memory)
 */
export function createSlidingWindowRateLimiter(
  maxRequests: number,
  windowMs: number
): MiddlewareFunction {
  const requestLog = new Map<string, number[]>();

  return async (context: MiddlewareContext) => {
    const { clientIP } = context;
    const now = Date.now();
    const windowStart = now - windowMs;

    // Get or create request log for this IP
    let requests = requestLog.get(clientIP) || [];

    // Remove requests outside the window
    requests = requests.filter((timestamp) => timestamp > windowStart);

    // Check if limit exceeded
    if (requests.length >= maxRequests) {
      const oldestRequest = Math.min(...requests);
      const resetTime = oldestRequest + windowMs;
      const retryAfter = Math.ceil((resetTime - now) / 1000);

      return NextResponse.json(
        {
          error: 'Rate limit exceeded',
          message: 'Too many requests in sliding window. Please slow down.',
          retryAfter,
        },
        {
          status: 429,
          headers: {
            'Retry-After': retryAfter.toString(),
            'X-RateLimit-Limit': maxRequests.toString(),
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': Math.ceil(resetTime / 1000).toString(),
          },
        }
      );
    }

    // Add current request to log
    requests.push(now);
    requestLog.set(clientIP, requests);

    // Cleanup old entries periodically
    if (Math.random() < 0.01) {
      // 1% chance to cleanup
      for (const [ip, logs] of requestLog.entries()) {
        const validLogs = logs.filter((timestamp) => timestamp > windowStart);
        if (validLogs.length === 0) {
          requestLog.delete(ip);
        } else {
          requestLog.set(ip, validLogs);
        }
      }
    }

    return null;
  };
}
