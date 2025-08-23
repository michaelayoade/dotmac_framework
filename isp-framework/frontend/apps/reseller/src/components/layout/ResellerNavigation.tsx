'use client';

import { clsx } from 'clsx';
import {
  Award,
  BarChart3,
  CheckSquare,
  DollarSign,
  FileText,
  LayoutDashboard,
  MapPin,
  Settings,
  Target,
  UserPlus,
  Users,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type React from 'react';

interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  description?: string;
}

const navItems: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
    description: 'Overview and metrics',
  },
  {
    id: 'workflow',
    label: 'Workflow Center',
    href: '/workflow',
    icon: CheckSquare,
    description: 'Unified task and pipeline management',
    badge: '5',
  },
  {
    id: 'customers',
    label: 'My Customers',
    href: '/customers-advanced',
    icon: Users,
    description: 'Manage customer accounts',
  },
  {
    id: 'territory',
    label: 'Territory',
    href: '/territory',
    icon: MapPin,
    description: 'Coverage area and prospects',
  },
  {
    id: 'commissions',
    label: 'Commissions',
    href: '/commissions',
    icon: DollarSign,
    description: 'Track earnings and payouts',
  },
  {
    id: 'sales-tools',
    label: 'Sales Tools',
    href: '/sales-tools',
    icon: FileText,
    description: 'Resources and marketing materials',
  },
  {
    id: 'partner',
    label: 'Partner Program',
    href: '/partner',
    icon: Award,
    description: 'Benefits and program info',
  },
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: Settings,
    description: 'Account preferences',
  },
];

export function ResellerNavigation() {
  const pathname = usePathname();

  return (
    <nav className='reseller-nav'>
      <div className='container mx-auto px-4'>
        <div className='flex space-x-0 overflow-x-auto'>
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.id}
                href={item.href}
                className={clsx(
                  'group flex items-center whitespace-nowrap border-b-2 px-4 py-3 font-medium text-sm transition-colors',
                  isActive
                    ? 'border-green-500 bg-green-50 text-green-600'
                    : 'border-transparent text-gray-600 hover:border-gray-300 hover:bg-gray-50 hover:text-gray-900'
                )}
                title={item.description}
              >
                <Icon
                  className={clsx(
                    'mr-2 h-4 w-4 flex-shrink-0 transition-colors',
                    isActive ? 'text-green-500' : 'text-gray-400 group-hover:text-gray-600'
                  )}
                />
                <span>{item.label}</span>
                {item.badge ? (
                  <span
                    className={clsx(
                      'ml-2 inline-flex items-center justify-center rounded-full px-2 py-1 font-bold text-xs',
                      isActive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
                    )}
                  >
                    {item.badge}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
