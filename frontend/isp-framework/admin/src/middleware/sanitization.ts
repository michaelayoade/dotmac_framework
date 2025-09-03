/**
 * Input Sanitization Middleware
 * Automatically sanitizes request data to prevent XSS and injection attacks
 */

import { NextRequest, NextResponse } from 'next/server';
import { sanitizeObject, sanitizeInput, sanitizeEmail, sanitizeSearchTerm } from '../lib/security';

// Define sanitization rules for different endpoints
const SANITIZATION_RULES: Record<string, Record<string, (value: any) => any>> = {
  '/api/auth/login': {
    email: sanitizeEmail,
    password: (value: string) => value, // Don't sanitize passwords as it may break valid characters
  },
  '/api/isp/identity/customers': {
    search: sanitizeSearchTerm,
    name: sanitizeInput,
    email: sanitizeEmail,
    phone: (value: string) => value.replace(/[^\d+\-\s()]/g, '').slice(0, 20),
  },
  '/api/billing': {
    search: sanitizeSearchTerm,
    customerName: sanitizeInput,
    description: sanitizeInput,
    notes: sanitizeInput,
  },
  // Default rules for any endpoint
  default: {
    search: sanitizeSearchTerm,
    query: sanitizeSearchTerm,
    name: sanitizeInput,
    email: sanitizeEmail,
    description: sanitizeInput,
    title: sanitizeInput,
    content: sanitizeInput,
  },
};

export async function sanitizationMiddleware(request: NextRequest) {
  // Only process POST, PUT, PATCH requests with JSON body
  if (!['POST', 'PUT', 'PATCH'].includes(request.method)) {
    return NextResponse.next();
  }

  const contentType = request.headers.get('content-type');
  if (!contentType?.includes('application/json')) {
    return NextResponse.next();
  }

  try {
    // Parse request body
    const body = await request.json();

    // Get sanitization rules for this endpoint
    const pathname = request.nextUrl.pathname;
    const rules = SANITIZATION_RULES[pathname] || SANITIZATION_RULES.default;

    // Sanitize the request body
    const sanitizedBody = sanitizeObject(body, rules);

    // Create new request with sanitized body
    const sanitizedRequest = new NextRequest(request.url, {
      method: request.method,
      headers: request.headers,
      body: JSON.stringify(sanitizedBody),
    });

    // Continue with sanitized request
    return NextResponse.next({
      request: sanitizedRequest,
    });
  } catch (error) {
    console.error('Sanitization middleware error:', error);

    // If sanitization fails, reject the request
    return NextResponse.json({ error: 'Invalid request format' }, { status: 400 });
  }
}

// Query parameter sanitization
export function sanitizeSearchParams(searchParams: URLSearchParams): URLSearchParams {
  const sanitized = new URLSearchParams();

  for (const [key, value] of searchParams.entries()) {
    switch (key.toLowerCase()) {
      case 'search':
      case 'query':
      case 'q':
        sanitized.set(key, sanitizeSearchTerm(value));
        break;
      case 'email':
        sanitized.set(key, sanitizeEmail(value));
        break;
      case 'page':
      case 'limit':
      case 'size':
        // Ensure numeric values are integers within reasonable bounds
        const numValue = parseInt(value, 10);
        if (!isNaN(numValue) && numValue >= 0 && numValue <= 10000) {
          sanitized.set(key, numValue.toString());
        }
        break;
      case 'sort':
      case 'order':
        // Only allow alphanumeric characters and common sort directions
        const cleanSort = value.replace(/[^a-zA-Z0-9_-]/g, '');
        if (cleanSort && cleanSort.length <= 50) {
          sanitized.set(key, cleanSort);
        }
        break;
      default:
        // Generic string sanitization for other parameters
        const sanitizedValue = sanitizeInput(value);
        if (sanitizedValue && sanitizedValue.length <= 100) {
          sanitized.set(key, sanitizedValue);
        }
        break;
    }
  }

  return sanitized;
}

// Form data sanitization hook
export function useSanitizedFormData<T extends Record<string, any>>(
  initialData: T,
  customSanitizers?: Partial<Record<keyof T, (value: any) => any>>
) {
  return {
    sanitize: (data: T): T => {
      return sanitizeObject(data, customSanitizers);
    },
    sanitizeField: (field: keyof T, value: any): any => {
      const customSanitizer = customSanitizers?.[field];
      if (customSanitizer) {
        return customSanitizer(value);
      }
      if (typeof value === 'string') {
        return sanitizeInput(value);
      }
      return value;
    },
  };
}

// Real-time input sanitization for forms
export function createSanitizedInputHandler<T extends Record<string, any>>(
  setState: React.Dispatch<React.SetStateAction<T>>,
  fieldSanitizers?: Partial<Record<keyof T, (value: any) => any>>
) {
  return (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = event.target;

    // Apply field-specific sanitizer or default
    const sanitizer = fieldSanitizers?.[name as keyof T];
    const sanitizedValue = sanitizer ? sanitizer(value) : sanitizeInput(value);

    setState((prev) => ({
      ...prev,
      [name]: sanitizedValue,
    }));
  };
}
