/**
 * Plugin Management Page
 * Main page for managing plugins in the ISP platform
 * Following DRY patterns from existing pages
 */

import { PluginManagement } from '@/components/plugins/PluginManagement';

export const metadata = {
  title: 'Plugin Management - Management Admin',
  description: 'Manage plugins and integrations for your ISP platform',
};

export default function PluginManagementPage() {
  return (
    <div className="space-y-6">
      <PluginManagement />
    </div>
  );
}
