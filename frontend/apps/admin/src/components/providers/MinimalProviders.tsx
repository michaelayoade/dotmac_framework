/**
 * Minimal Providers - Simple fallback for startup testing
 */

import React, { ReactNode } from 'react';

interface MinimalProvidersProps {
  children: ReactNode;
}

export function MinimalProviders({ children }: MinimalProvidersProps) {
  return <div className="min-h-screen">{children}</div>;
}