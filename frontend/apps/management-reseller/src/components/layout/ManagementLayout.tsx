'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Users, 
  MapPin, 
  DollarSign, 
  BarChart3, 
  GraduationCap,
  Settings,
  Bell,
  Menu,
  X,
  LogOut,
  ChevronDown,
  Shield,
  Target,
  FileText,
  Award,
} from 'lucide-react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';

interface NavigationItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  permission?: string;
  children?: NavigationItem[];
}

const navigation: NavigationItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { 
    name: 'Partners', 
    href: '/partners', 
    icon: Users,
    permission: 'MANAGE_RESELLERS',
    children: [
      { name: 'All Partners', href: '/partners', icon: Users },
      { name: 'Onboarding', href: '/partners/onboarding', icon: Target },
      { name: 'Applications', href: '/partners/applications', icon: FileText, badge: '3' },
    ]
  },
  { 
    name: 'Territories', 
    href: '/territories', 
    icon: MapPin,
    permission: 'MANAGE_TERRITORIES',
  },
  { 
    name: 'Commissions', 
    href: '/commissions', 
    icon: DollarSign,
    permission: 'APPROVE_COMMISSIONS',
    children: [
      { name: 'Payments', href: '/commissions', icon: DollarSign },
      { name: 'Calculations', href: '/commissions/calculations', icon: BarChart3 },
      { name: 'Disputes', href: '/commissions/disputes', icon: Shield, badge: '2' },
    ]
  },
  { 
    name: 'Training', 
    href: '/training', 
    icon: GraduationCap,
    permission: 'MANAGE_TRAINING',
  },
  { 
    name: 'Analytics', 
    href: '/analytics', 
    icon: BarChart3,
    permission: 'VIEW_ANALYTICS',
  },
  { 
    name: 'Incentives', 
    href: '/incentives', 
    icon: Award,
  },
  { name: 'Settings', href: '/settings', icon: Settings },
];

interface ManagementLayoutProps {
  children: React.ReactNode;
}

export function ManagementLayout({ children }: ManagementLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState<string[]>([]);
  const pathname = usePathname();
  const { user, logout, isLoading, hasPermission } = useManagementAuth();

  // Toggle sidebar menu expansion
  const toggleMenu = (menuName: string) => {
    setExpandedMenus(prev => 
      prev.includes(menuName) 
        ? prev.filter(name => name !== menuName)
        : [...prev, menuName]
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-management-600" />
      </div>
    );
  }

  // Filter navigation based on permissions
  const filteredNavigation = navigation.filter(item => {
    if (!item.permission) return true;
    return hasPermission(item.permission);
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="relative flex w-full max-w-xs flex-col bg-white">
          <div className="absolute right-0 top-0 -mr-12 pt-2">
            <button
              type="button"
              className="ml-1 flex h-10 w-10 items-center justify-center rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-6 w-6 text-white" />
            </button>
          </div>
          <SidebarContent />
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <SidebarContent />
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top navigation */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          <button
            type="button"
            className="-m-2.5 p-2.5 text-gray-700 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>

          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="flex flex-1 items-center">
              <h1 className="text-xl font-semibold text-gray-900">
                {getCurrentPageTitle()}
              </h1>
            </div>

            <div className="flex items-center gap-x-4 lg:gap-x-6">
              {/* Notifications */}
              <button
                type="button"
                className="relative -m-2.5 p-2.5 text-gray-400 hover:text-gray-500"
              >
                <Bell className="h-6 w-6" />
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-red-500 text-xs text-white flex items-center justify-center">
                  5
                </span>
              </button>

              {/* User menu */}
              <div className="relative">
                <button
                  type="button"
                  className="flex items-center gap-x-4 px-6 py-3 text-sm font-semibold text-gray-900 hover:bg-gray-50"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                >
                  <div className="h-8 w-8 rounded-full bg-management-500 flex items-center justify-center text-white font-medium">
                    {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                  <div className="hidden lg:flex lg:items-center">
                    <span>{user?.name}</span>
                    <ChevronDown className="ml-2 h-5 w-5 text-gray-400" />
                  </div>
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 z-10 mt-2.5 w-56 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5">
                    <div className="px-4 py-2 border-b border-gray-200">
                      <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                      <p className="text-sm text-gray-500">{user?.email}</p>
                      <p className="text-xs text-gray-400 mt-1 capitalize">{user?.role.replace('_', ' ').toLowerCase()}</p>
                    </div>
                    <div className="px-4 py-2 border-b border-gray-200">
                      <p className="text-xs text-gray-500 mb-1">Departments</p>
                      {user?.departments.map(dept => (
                        <p key={dept} className="text-xs text-gray-700">{dept}</p>
                      ))}
                    </div>
                    <Link
                      href="/profile"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      Profile Settings
                    </Link>
                    <button
                      onClick={logout}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <LogOut className="inline h-4 w-4 mr-2" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="py-8">
          <div className="px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );

  function getCurrentPageTitle() {
    const currentNav = findCurrentNavigation(filteredNavigation, pathname);
    return currentNav?.name || 'Reseller Management';
  }

  function findCurrentNavigation(navItems: NavigationItem[], path: string): NavigationItem | null {
    for (const item of navItems) {
      if (item.href === path) return item;
      if (item.children) {
        const found = findCurrentNavigation(item.children, path);
        if (found) return found;
      }
    }
    return null;
  }

  function SidebarContent() {
    return (
      <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white border-r border-gray-200">
        {/* Logo */}
        <div className="flex h-16 shrink-0 items-center px-6 border-b border-gray-200">
          <div className="flex items-center gap-x-3">
            <div className="h-8 w-8 rounded bg-gradient-to-br from-management-600 to-reseller-600 flex items-center justify-center text-white font-bold text-sm">
              R
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-gray-900 truncate">
                Reseller Management
              </p>
              <p className="text-xs text-gray-500">
                Channel Operations
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-1 flex-col px-3">
          <ul role="list" className="space-y-1">
            {filteredNavigation.map((item) => {
              const isActive = pathname === item.href || 
                (item.children && item.children.some(child => pathname === child.href));
              const isExpanded = expandedMenus.includes(item.name);
              
              return (
                <li key={item.name}>
                  {item.children ? (
                    // Parent menu with children
                    <div>
                      <button
                        onClick={() => toggleMenu(item.name)}
                        className={`management-nav-item w-full ${isActive ? 'active' : ''}`}
                      >
                        <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                        {item.name}
                        {item.badge && (
                          <span className="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            {item.badge}
                          </span>
                        )}
                        <ChevronDown className={`ml-2 h-4 w-4 transition-transform ${
                          isExpanded ? 'rotate-180' : ''
                        }`} />
                      </button>
                      
                      {isExpanded && (
                        <ul className="mt-1 space-y-1 pl-6">
                          {item.children.map(child => (
                            <li key={child.href}>
                              <Link
                                href={child.href}
                                className={`management-nav-item ${pathname === child.href ? 'active' : ''}`}
                              >
                                <child.icon className="mr-3 h-4 w-4 flex-shrink-0" />
                                {child.name}
                                {child.badge && (
                                  <span className="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                    {child.badge}
                                  </span>
                                )}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ) : (
                    // Simple menu item
                    <Link
                      href={item.href}
                      className={`management-nav-item ${isActive ? 'active' : ''}`}
                    >
                      <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                      {item.name}
                      {item.badge && (
                        <span className="ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>

          {/* User info at bottom */}
          <div className="mt-auto p-4 border-t border-gray-200">
            <div className="flex items-center gap-x-3">
              <div className="h-8 w-8 rounded-full bg-management-500 flex items-center justify-center text-white font-medium text-sm">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-gray-900 truncate">
                  {user?.name}
                </p>
                <p className="text-xs text-gray-500 capitalize">
                  {user?.role.replace('_', ' ').toLowerCase()}
                </p>
              </div>
            </div>
          </div>
        </nav>
      </div>
    );
  }
}