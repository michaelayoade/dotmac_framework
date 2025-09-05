'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, X } from 'lucide-react'

export function UnifiedHeader() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const pathname = usePathname()

  const getNavigationItems = () => {
    if (pathname.startsWith('/marketing')) {
      return {
        brand: { name: 'DotMac Platform', href: '/marketing' },
        items: [
          { name: 'Features', href: '/marketing#features' },
          { name: 'Pricing', href: '/marketing/pricing' },
          { name: 'Documentation', href: '/docs' },
          { name: 'Contact', href: '/marketing/contact' },
        ],
        cta: { name: 'Get Started', href: '/marketing/signup' }
      }
    } else if (pathname.startsWith('/docs')) {
      return {
        brand: { name: 'DotMac Docs', href: '/docs' },
        items: [
          { name: 'Overview', href: '/docs' },
          { name: 'API Reference', href: '/docs/api-reference' },
          { name: 'Guides', href: '/docs/guides' },
          { name: 'Plugins', href: '/docs/plugins' },
          { name: 'Pricing', href: '/docs/pricing' },
        ],
        cta: { name: 'Start Trial', href: '/docs/signup' }
      }
    } else {
      // Default admin navigation
      return {
        brand: { name: 'DotMac Admin', href: '/' },
        items: [
          { name: 'Dashboard', href: '/dashboard' },
          { name: 'Marketing', href: '/marketing' },
          { name: 'Documentation', href: '/docs' },
          { name: 'Settings', href: '/settings' },
        ],
        cta: { name: 'Admin Portal', href: '/dashboard' }
      }
    }
  }

  const navigation = getNavigationItems()

  const isActive = (href: string) => {
    if (href === '/' || href === '/marketing' || href === '/docs') {
      return pathname === href
    }
    return pathname.startsWith(href)
  }

  return (
    <header className="bg-white shadow-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Brand */}
          <div className="flex items-center">
            <Link href={navigation.brand.href} className="flex items-center">
              <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">D</span>
              </div>
              <span className="ml-2 text-xl font-bold text-gray-900">
                {navigation.brand.name}
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-8">
            {navigation.items.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive(item.href)
                    ? 'text-purple-600 bg-purple-50'
                    : 'text-gray-700 hover:text-purple-600 hover:bg-gray-50'
                }`}
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* CTA Button */}
          <div className="hidden md:flex items-center space-x-4">
            {/* Cross-navigation links */}
            {pathname.startsWith('/marketing') && (
              <Link
                href="/docs"
                className="text-gray-700 hover:text-purple-600 text-sm font-medium"
              >
                Docs
              </Link>
            )}
            {pathname.startsWith('/docs') && (
              <Link
                href="/marketing"
                className="text-gray-700 hover:text-purple-600 text-sm font-medium"
              >
                Marketing
              </Link>
            )}
            
            <Link
              href={navigation.cta.href}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors"
            >
              {navigation.cta.name}
            </Link>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 rounded-md text-gray-700 hover:text-purple-600 hover:bg-gray-50"
            >
              {isMobileMenuOpen ? (
                <X className="w-6 h-6" />
              ) : (
                <Menu className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200">
            <div className="pt-2 pb-3 space-y-1">
              {navigation.items.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`block px-3 py-2 rounded-md text-base font-medium ${
                    isActive(item.href)
                      ? 'text-purple-600 bg-purple-50'
                      : 'text-gray-700 hover:text-purple-600 hover:bg-gray-50'
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {item.name}
                </Link>
              ))}
              
              {/* Mobile cross-navigation */}
              <div className="border-t border-gray-200 pt-4 mt-4">
                {pathname.startsWith('/marketing') && (
                  <Link
                    href="/docs"
                    className="block px-3 py-2 text-gray-700 hover:text-purple-600"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    Documentation
                  </Link>
                )}
                {pathname.startsWith('/docs') && (
                  <Link
                    href="/marketing"
                    className="block px-3 py-2 text-gray-700 hover:text-purple-600"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    Marketing Site
                  </Link>
                )}
                
                <Link
                  href={navigation.cta.href}
                  className="block px-3 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 mt-2"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {navigation.cta.name}
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}