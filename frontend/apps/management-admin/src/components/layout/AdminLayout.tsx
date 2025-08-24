'use client';

import { useState, ReactNode } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { AdminSidebar } from './AdminSidebar';
import { AdminHeader } from './AdminHeader';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { UserRole } from '@/types/auth';

interface AdminLayoutProps {
  children: ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user } = useAuth();

  return (
    <ProtectedRoute requireMasterAdmin>
      <div className="h-screen flex overflow-hidden bg-gray-50">
        {/* Mobile sidebar */}
        <AdminSidebar 
          open={sidebarOpen} 
          onClose={() => setSidebarOpen(false)}
          isMobile
        />

        {/* Desktop sidebar */}
        <AdminSidebar 
          open={true} 
          onClose={() => {}}
          isMobile={false}
        />

        {/* Main content */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <AdminHeader 
            user={user}
            onMenuClick={() => setSidebarOpen(true)}
          />
          
          <main className="flex-1 overflow-y-auto focus:outline-none">
            <div className="py-6">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                {children}
              </div>
            </div>
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}