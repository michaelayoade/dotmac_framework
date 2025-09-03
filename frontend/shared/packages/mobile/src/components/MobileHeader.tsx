import React from 'react';

interface MobileHeaderProps {
  children?: React.ReactNode;
}

export function MobileHeader({ children }: MobileHeaderProps) {
  return <div>{children} - Coming Soon</div>;
}
