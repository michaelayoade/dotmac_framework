/**
 * Nonce generation utility
 * Provides secure nonce generation for CSP headers
 */

import { randomBytes } from 'crypto';

/**
 * Generate a cryptographically secure nonce
 */
export function generateSecureNonce(): string {
  // Generate 16 bytes of random data and encode as base64
  return randomBytes(16).toString('base64');
}

/**
 * Browser-compatible nonce generation fallback
 */
export function generateClientNonce(): string {
  if (typeof window !== 'undefined' && window.crypto && window.crypto.getRandomValues) {
    const array = new Uint8Array(16);
    window.crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array));
  }
  
  // Fallback for environments without crypto.getRandomValues
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < 16; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Universal nonce generation that works in both Node.js and browser
 */
export function generateNonce(): string {
  if (typeof window === 'undefined') {
    // Server-side: use Node.js crypto
    return generateSecureNonce();
  } else {
    // Client-side: use Web Crypto API or fallback
    return generateClientNonce();
  }
}