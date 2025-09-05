'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { 
  Menu, 
  X, 
  Sun, 
  Moon, 
  ChevronDown,
  Network,
  Users,
  BarChart3,
  Settings,
  Shield,
  Zap
} from 'lucide-react'

const navigation = [
  {
    name: 'Features',
    href: '/features',
    submenu: [
      { name: 'Network Management', href: '/features/network', icon: Network },
      { name: 'Customer Portal', href: '/features/customer', icon: Users },
      { name: 'Analytics & Reporting', href: '/features/analytics', icon: BarChart3 },
      { name: 'Automation Tools', href: '/features/automation', icon: Zap },
      { name: 'Security & Compliance', href: '/features/security', icon: Shield },
      { name: 'System Administration', href: '/features/admin', icon: Settings },
    ]
  },
  { name: 'Pricing', href: '/pricing' },
  { name: 'Documentation', href: '/docs' },
  { name: 'Demo', href: '/demo' },
]

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const handleScroll = () => {
      setScrolled(window.scrollY > 10)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  if (!mounted) return null

  return (
    <header className={`fixed w-full top-0 z-50 transition-all duration-300 ${
      scrolled 
        ? 'bg-background/95 backdrop-blur-md border-b border-border shadow-sm' 
        : 'bg-transparent'
    }`}>
      <nav className="container-custom" aria-label="Global">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex lg:flex-1">
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <Network className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold text-foreground">
                ISP Framework
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex lg:items-center lg:gap-x-8">
            {navigation.map((item) => (
              <div key={item.name} className="relative group">
                {item.submenu ? (
                  <div>
                    <button className="flex items-center gap-x-1 text-sm font-semibold leading-6 text-foreground hover:text-primary transition-colors">
                      {item.name}
                      <ChevronDown className="h-4 w-4 group-hover:rotate-180 transition-transform" />
                    </button>
                    
                    {/* Submenu */}
                    <div className="absolute left-1/2 z-10 mt-5 flex w-screen max-w-max -translate-x-1/2 px-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                      <div className="w-screen max-w-md flex-auto overflow-hidden rounded-2xl bg-background text-sm leading-6 shadow-lg ring-1 ring-border">
                        <div className="p-4">
                          {item.submenu.map((subItem) => (
                            <div key={subItem.name} className="group/item relative flex gap-x-6 rounded-lg p-4 hover:bg-muted">
                              <div className="mt-1 flex h-11 w-11 flex-none items-center justify-center rounded-lg bg-muted group-hover/item:bg-primary">
                                <subItem.icon className="h-6 w-6 text-muted-foreground group-hover/item:text-primary-foreground" />
                              </div>
                              <div>
                                <Link href={subItem.href} className="font-semibold text-foreground">
                                  {subItem.name}
                                  <span className="absolute inset-0" />
                                </Link>
                                <p className="mt-1 text-muted-foreground">Learn about {subItem.name.toLowerCase()}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <Link 
                    href={item.href} 
                    className="text-sm font-semibold leading-6 text-foreground hover:text-primary transition-colors"
                  >
                    {item.name}
                  </Link>
                )}
              </div>
            ))}
          </div>

          {/* Theme Toggle & CTA */}
          <div className="hidden lg:flex lg:flex-1 lg:justify-end lg:items-center lg:gap-x-4">
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </button>
            
            <Button asChild variant="outline">
              <Link href="/login">Sign In</Link>
            </Button>
            
            <Button asChild>
              <Link href="/demo">Request Demo</Link>
            </Button>
          </div>

          {/* Mobile menu button */}
          <div className="flex lg:hidden">
            <button
              type="button"
              className="p-2.5 rounded-md text-foreground"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-6 w-6" aria-hidden="true" />
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden">
          <div className="fixed inset-0 z-50" />
          <div className="fixed inset-y-0 right-0 z-50 w-full overflow-y-auto bg-background px-6 py-6 sm:max-w-sm sm:ring-1 sm:ring-border">
            <div className="flex items-center justify-between">
              <Link href="/" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <Network className="w-5 h-5 text-primary-foreground" />
                </div>
                <span className="text-xl font-bold text-foreground">
                  ISP Framework
                </span>
              </Link>
              <button
                type="button"
                className="rounded-md p-2.5 text-foreground"
                onClick={() => setMobileMenuOpen(false)}
              >
                <X className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>
            
            <div className="mt-6 flow-root">
              <div className="-my-6 divide-y divide-border">
                <div className="space-y-2 py-6">
                  {navigation.map((item) => (
                    <div key={item.name}>
                      {item.submenu ? (
                        <div className="space-y-2">
                          <div className="text-base font-semibold leading-7 text-foreground">
                            {item.name}
                          </div>
                          <div className="ml-4 space-y-2">
                            {item.submenu.map((subItem) => (
                              <Link
                                key={subItem.name}
                                href={subItem.href}
                                className="flex items-center gap-x-3 rounded-lg py-2 text-base leading-7 text-muted-foreground hover:text-foreground hover:bg-muted px-3 transition-colors"
                              >
                                <subItem.icon className="h-5 w-5" />
                                {subItem.name}
                              </Link>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <Link
                          href={item.href}
                          className="block rounded-lg py-2 px-3 text-base font-semibold leading-7 text-foreground hover:bg-muted transition-colors"
                        >
                          {item.name}
                        </Link>
                      )}
                    </div>
                  ))}
                </div>
                
                <div className="py-6 space-y-4">
                  <Button asChild variant="outline" className="w-full">
                    <Link href="/login">Sign In</Link>
                  </Button>
                  <Button asChild className="w-full">
                    <Link href="/demo">Request Demo</Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}