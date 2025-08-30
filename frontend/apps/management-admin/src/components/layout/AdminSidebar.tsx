'use client';

import { PortalSidebar, managementNavigation } from '@dotmac/portal-components';

interface AdminSidebarProps {
  open: boolean;
  onClose: () => void;
  isMobile: boolean;
}

export function AdminSidebar({ open, onClose, isMobile }: AdminSidebarProps) {
  return (
    <PortalSidebar
      open={open}
      onClose={onClose}
      isMobile={isMobile}
      navigation={managementNavigation}
      branding={{
        title: 'DotMac',
        subtitle: 'Management Console',
        version: 'v1.0.0'
      }}
    />
  );
}
