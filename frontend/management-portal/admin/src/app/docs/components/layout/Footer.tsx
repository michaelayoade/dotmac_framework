import Link from 'next/link'
import { 
  Network,
  Mail,
  Phone,
  MapPin,
  Facebook,
  Twitter,
  Linkedin,
  Youtube,
  Github,
  ArrowRight
} from 'lucide-react'

const navigation = {
  product: [
    { name: 'Features', href: '/features' },
    { name: 'Pricing', href: '/pricing' },
    { name: 'Documentation', href: '/docs' },
    { name: 'API Reference', href: '/docs/api' },
    { name: 'Integrations', href: '/integrations' },
    { name: 'Demo', href: '/demo' },
  ],
  solutions: [
    { name: 'Network Management', href: '/solutions/network' },
    { name: 'Customer Portal', href: '/solutions/customer' },
    { name: 'Analytics & Reporting', href: '/solutions/analytics' },
    { name: 'Security & Compliance', href: '/solutions/security' },
    { name: 'Automation Tools', href: '/solutions/automation' },
    { name: 'Professional Services', href: '/solutions/services' },
  ],
  resources: [
    { name: 'Blog', href: '/blog' },
    { name: 'Case Studies', href: '/case-studies' },
    { name: 'Whitepapers', href: '/resources/whitepapers' },
    { name: 'Webinars', href: '/resources/webinars' },
    { name: 'Help Center', href: '/help' },
    { name: 'Community', href: '/community' },
  ],
  company: [
    { name: 'About Us', href: '/about' },
    { name: 'Careers', href: '/careers' },
    { name: 'Press', href: '/press' },
    { name: 'Partners', href: '/partners' },
    { name: 'Contact', href: '/contact' },
    { name: 'Trust Center', href: '/trust' },
  ],
  legal: [
    { name: 'Privacy Policy', href: '/privacy' },
    { name: 'Terms of Service', href: '/terms' },
    { name: 'Cookie Policy', href: '/cookies' },
    { name: 'Security', href: '/security' },
    { name: 'Compliance', href: '/compliance' },
    { name: 'SLA', href: '/sla' },
  ],
}

const social = [
  {
    name: 'Facebook',
    href: '#',
    icon: Facebook,
  },
  {
    name: 'Twitter',
    href: '#',
    icon: Twitter,
  },
  {
    name: 'LinkedIn',
    href: '#',
    icon: Linkedin,
  },
  {
    name: 'YouTube',
    href: '#',
    icon: Youtube,
  },
  {
    name: 'GitHub',
    href: '#',
    icon: Github,
  },
]

export function Footer() {
  return (
    <footer className="bg-background border-t border-border">
      <div className="container-custom">
        {/* Main Footer Content */}
        <div className="py-16 lg:py-20">
          <div className="grid lg:grid-cols-6 gap-8">
            {/* Company Info */}
            <div className="lg:col-span-2">
              <Link href="/" className="flex items-center space-x-2 mb-6">
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <Network className="w-5 h-5 text-primary-foreground" />
                </div>
                <span className="text-xl font-bold text-foreground">
                  ISP Framework
                </span>
              </Link>
              
              <p className="text-muted-foreground mb-6 max-w-sm">
                The complete ISP management platform that automates operations, 
                streamlines customer experiences, and scales your business with 
                enterprise-grade reliability.
              </p>

              {/* Contact Info */}
              <div className="space-y-3 mb-6">
                <div className="flex items-center text-sm text-muted-foreground">
                  <Mail className="w-4 h-4 mr-3" />
                  <Link href="mailto:hello@ispframework.com" className="hover:text-foreground transition-colors">
                    hello@ispframework.com
                  </Link>
                </div>
                <div className="flex items-center text-sm text-muted-foreground">
                  <Phone className="w-4 h-4 mr-3" />
                  <Link href="tel:+1-555-ISP-FRAM" className="hover:text-foreground transition-colors">
                    +1 (555) ISP-FRAM
                  </Link>
                </div>
                <div className="flex items-center text-sm text-muted-foreground">
                  <MapPin className="w-4 h-4 mr-3" />
                  <span>San Francisco, CA</span>
                </div>
              </div>

              {/* Social Links */}
              <div className="flex space-x-4">
                {social.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className="p-2 bg-muted hover:bg-muted/80 rounded-lg transition-colors"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <item.icon className="w-4 h-4 text-muted-foreground hover:text-foreground transition-colors" />
                    <span className="sr-only">{item.name}</span>
                  </Link>
                ))}
              </div>
            </div>

            {/* Navigation Links */}
            <div className="lg:col-span-4 grid grid-cols-2 md:grid-cols-4 gap-8">
              {/* Product */}
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-4">
                  Product
                </h3>
                <ul className="space-y-3">
                  {navigation.product.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Solutions */}
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-4">
                  Solutions
                </h3>
                <ul className="space-y-3">
                  {navigation.solutions.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Resources */}
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-4">
                  Resources
                </h3>
                <ul className="space-y-3">
                  {navigation.resources.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Company */}
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-4">
                  Company
                </h3>
                <ul className="space-y-3">
                  {navigation.company.map((item) => (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Newsletter Signup */}
        <div className="py-8 border-t border-border">
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Stay updated with ISP insights
              </h3>
              <p className="text-sm text-muted-foreground">
                Get the latest ISP industry news, platform updates, and best practices 
                delivered to your inbox monthly.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-4 py-2 bg-background border border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              <button className="px-6 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors flex items-center justify-center">
                Subscribe
                <ArrowRight className="w-4 h-4 ml-2" />
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="py-8 border-t border-border">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Copyright */}
            <div className="text-sm text-muted-foreground">
              © {new Date().getFullYear()} ISP Framework by DotMac Platform. All rights reserved.
            </div>

            {/* Legal Links */}
            <div className="flex flex-wrap gap-6">
              {navigation.legal.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {item.name}
                </Link>
              ))}
            </div>
          </div>

          {/* Additional Info */}
          <div className="mt-6 pt-6 border-t border-border">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs text-muted-foreground">
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse" />
                <span>All systems operational</span>
              </div>
              <div>
                <span>SOC 2 Type II Certified</span>
              </div>
              <div>
                <span>GDPR & CCPA Compliant</span>
              </div>
              <div>
                <span>99.9% Uptime SLA</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}