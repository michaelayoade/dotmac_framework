/**
 * NonceProvider - Server Component for accessing CSP nonce
 */

import { headers } from 'next/headers';
import Script from 'next/script';
import type React from 'react';

/**
 * Get the CSP nonce from request headers
 */
export function getNonce(): string {
  const nonce = headers().get('x-nonce');
  return nonce || '';
}

/**
 * Script component with automatic nonce injection
 */
export function NonceScript({ 
  children, 
  ...props 
}: { 
  children?: React.ReactNode;
  id?: string;
  strategy?: 'beforeInteractive' | 'afterInteractive' | 'lazyOnload';
  src?: string;
}) {
  const nonce = getNonce();
  
  if (props.src) {
    // External script
    return <Script nonce={nonce} {...props} />;
  }
  
  // Inline script
  return (
    <script
      nonce={nonce}
      dangerouslySetInnerHTML={{
        __html: children as string,
      }}
      {...props}
    />
  );
}

/**
 * Provider component that makes nonce available to children
 */
export function NonceProvider({ children }: { children: React.ReactNode }) {
  const nonce = getNonce();
  
  return (
    <>
      {/* Add nonce to meta tag for client-side reference */}
      <meta name="csp-nonce" content={nonce} />
      {children}
    </>
  );
}

/**
 * Hook to get nonce on client side (for dynamic script injection)
 */
export function useNonce(): string {
  if (typeof window === 'undefined') {
    return getNonce();
  }
  
  const meta = document.querySelector('meta[name="csp-nonce"]');
  return meta?.getAttribute('content') || '';
}