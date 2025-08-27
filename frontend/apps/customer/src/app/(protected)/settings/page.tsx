// import { SkeletonCard } from '@dotmac/primitives';

// Temporary skeleton component
const SkeletonCard = ({ className = "h-32" }: { className?: string }) => (
  <div className={`bg-gray-200 rounded animate-pulse ${className}`} />
);
import { Suspense } from 'react';
import { AccountSettings } from '../../../components/account/AccountSettings';
import { ContactPreferences } from '../../../components/account/ContactPreferences';
import { FamilyManagement } from '../../../components/account/FamilyManagement';
import { ProfileManagement } from '../../../components/account/ProfileManagement';
import { SecuritySettings } from '../../../components/account/SecuritySettings';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';

export default function SettingsPage() {
  return (
    <CustomerLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Account Settings</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your profile, security, and communication preferences
          </p>
        </div>

        <Suspense fallback={<SettingsSkeleton />}>
          <SettingsContent />
        </Suspense>
      </div>
    </CustomerLayout>
  );
}

function SettingsContent() {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <ProfileManagement />
          <SecuritySettings />
          <ContactPreferences />
        </div>
        <div className="space-y-8">
          <AccountSettings />
          <FamilyManagement />
        </div>
      </div>
    </div>
  );
}

function SettingsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <SkeletonCard className="h-96" />
          <SkeletonCard className="h-64" />
        </div>
        <div className="space-y-6">
          <SkeletonCard className="h-48" />
          <SkeletonCard className="h-64" />
        </div>
      </div>
    </div>
  );
}
