/**
 * ClientOnly Component
 * Prevents SSR/hydration issues by only rendering children on the client side
 */

'use client';

import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';

interface ClientOnlyProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Wrapper component that only renders children after client-side hydration
 * This prevents hydration mismatches for components that must be client-only
 */
export function ClientOnly({ children, fallback = null }: ClientOnlyProps) {
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  if (!hasMounted) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
