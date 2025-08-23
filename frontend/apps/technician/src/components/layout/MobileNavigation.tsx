'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, ClipboardList, Package, Users, Settings, MapPin } from 'lucide-react';
import { clsx } from 'clsx';

interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const navItems: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Home',
    href: '/',
    icon: Home,
  },
  {
    id: 'work-orders',
    label: 'Orders',
    href: '/work-orders',
    icon: ClipboardList,
    badge: 3,
  },
  {
    id: 'inventory',
    label: 'Inventory',
    href: '/inventory',
    icon: Package,
  },
  {
    id: 'customers',
    label: 'Customers',
    href: '/customers',
    icon: Users,
  },
  {
    id: 'map',
    label: 'Map',
    href: '/map',
    icon: MapPin,
  },
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];

export function MobileNavigation() {
  const pathname = usePathname();

  const handleNavClick = () => {
    // Haptic feedback on supported devices
    if ('vibrate' in navigator) {
      navigator.vibrate(10);
    }
  };

  return (
    <nav className='fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 safe-area-inset-bottom'>
      <div className='flex items-center justify-around px-2 py-1'>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.id}
              href={item.href}
              onClick={handleNavClick}
              className={clsx(
                'mobile-nav-item touch-feedback relative',
                isActive ? 'mobile-nav-active' : 'mobile-nav-inactive'
              )}
            >
              <div className='relative'>
                <Icon className='w-5 h-5 mx-auto mb-1' />
                {item.badge && item.badge > 0 && (
                  <div className='absolute -top-2 -right-2 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center'>
                    <span className='text-white text-xs font-bold'>
                      {item.badge > 9 ? '9+' : item.badge}
                    </span>
                  </div>
                )}
              </div>
              <span className='text-xs font-medium truncate w-full text-center'>{item.label}</span>

              {/* Active indicator */}
              {isActive && (
                <div className='absolute bottom-0 left-1/2 transform -translate-x-1/2 w-6 h-0.5 bg-primary-500 rounded-full' />
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
