'use client';

import { useAuthStore } from '@dotmac/headless';
import { type ReactNode, useEffect } from 'react';

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { isSessionValid, clearAuth } = useAuthStore();

  useEffect(() => {
    // Check if session is still valid on mount
    if (!isSessionValid()) {
      clearAuth();
    }
  }, [isSessionValid, clearAuth]);

  return <>{children}</>;
}
