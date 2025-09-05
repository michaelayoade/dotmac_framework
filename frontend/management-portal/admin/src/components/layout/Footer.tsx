import Link from 'next/link'

export function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1">
            <div className="flex items-center mb-4">
              <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">D</span>
              </div>
              <span className="ml-2 text-xl font-bold text-gray-900">
                DotMac Platform
              </span>
            </div>
            <p className="text-gray-600 text-sm max-w-xs">
              Strategic ISP management platform with plugin-based architecture 
              and multi-tenant support.
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">
              Product
            </h3>
            <ul className="space-y-3">
              <li>
                <Link href="/docs/features" className="text-gray-600 hover:text-purple-600 text-sm">
                  Features
                </Link>
              </li>
              <li>
                <Link href="/docs/pricing" className="text-gray-600 hover:text-purple-600 text-sm">
                  Pricing
                </Link>
              </li>
              <li>
                <Link href="/docs/integrations" className="text-gray-600 hover:text-purple-600 text-sm">
                  Integrations
                </Link>
              </li>
              <li>
                <Link href="/docs/security" className="text-gray-600 hover:text-purple-600 text-sm">
                  Security
                </Link>
              </li>
            </ul>
          </div>

          {/* Developers */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">
              Developers
            </h3>
            <ul className="space-y-3">
              <li>
                <Link href="/docs/api-reference" className="text-gray-600 hover:text-purple-600 text-sm">
                  API Reference
                </Link>
              </li>
              <li>
                <Link href="/docs/guides" className="text-gray-600 hover:text-purple-600 text-sm">
                  Guides
                </Link>
              </li>
              <li>
                <Link href="/docs/plugins" className="text-gray-600 hover:text-purple-600 text-sm">
                  Plugin Development
                </Link>
              </li>
              <li>
                <Link href="/docs/webhooks" className="text-gray-600 hover:text-purple-600 text-sm">
                  Webhooks
                </Link>
              </li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">
              Support
            </h3>
            <ul className="space-y-3">
              <li>
                <Link href="/docs/help" className="text-gray-600 hover:text-purple-600 text-sm">
                  Help Center
                </Link>
              </li>
              <li>
                <Link href="/docs/contact-sales" className="text-gray-600 hover:text-purple-600 text-sm">
                  Contact Sales
                </Link>
              </li>
              <li>
                <Link href="/docs/community" className="text-gray-600 hover:text-purple-600 text-sm">
                  Community
                </Link>
              </li>
              <li>
                <Link href="/docs/status" className="text-gray-600 hover:text-purple-600 text-sm">
                  Status Page
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-gray-200 mt-8 pt-8 flex flex-col md:flex-row justify-between items-center">
          <div className="flex space-x-6 text-sm text-gray-600">
            <Link href="/docs/privacy" className="hover:text-purple-600">
              Privacy Policy
            </Link>
            <Link href="/docs/terms" className="hover:text-purple-600">
              Terms of Service
            </Link>
            <Link href="/docs/cookies" className="hover:text-purple-600">
              Cookie Policy
            </Link>
          </div>
          <div className="mt-4 md:mt-0">
            <p className="text-sm text-gray-600">
              © {new Date().getFullYear()} DotMac Platform. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}