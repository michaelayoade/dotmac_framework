import { AdminLayout } from '@/components/layout/AdminLayout';
import { RouteErrorBoundary } from '@/components/ErrorBoundary/RouteErrorBoundary';
import { QueryErrorBoundary } from '@/components/ErrorBoundary/QueryErrorBoundary';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RouteErrorBoundary>
      <AdminLayout>
        <QueryErrorBoundary>
          {children}
        </QueryErrorBoundary>
      </AdminLayout>
    </RouteErrorBoundary>
  );
}