import type { ReactNode } from 'react';

interface ProtectedLayoutProps {
  children: ReactNode;
}

// Server Component - authentication is now handled by middleware
export default function ProtectedLayout({ children }: ProtectedLayoutProps) {
  return <>{children}</>;
}
