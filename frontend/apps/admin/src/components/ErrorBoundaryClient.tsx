'use client';

import { ErrorBoundary } from '@dotmac/primitives/error';
import type React from 'react';

export default function ErrorBoundaryClient({
  children,
  level = 'page',
}: {
  children: React.ReactNode;
  level?: 'page' | 'section' | 'component';
}) {
  const handleError = () => {
    // Implementation pending
  };

  return (
    <ErrorBoundary level={level} onError={handleError}>
      {children}
    </ErrorBoundary>
  );
}
