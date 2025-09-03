import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function PrivacyPolicyPage() {
  return (
    <div className='min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-4xl mx-auto'>
        <div className='bg-white shadow-sm rounded-lg overflow-hidden'>
          <div className='px-6 py-8 border-b border-gray-200'>
            <div className='flex items-center justify-between'>
              <div>
                <h1 className='text-3xl font-bold text-gray-900'>Privacy Policy</h1>
                <p className='mt-2 text-sm text-gray-600'>DotMac ISP Management Platform</p>
              </div>
              <Link
                href='/login'
                className='inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50'
              >
                <ArrowLeft className='h-4 w-4 mr-2' />
                Back to Login
              </Link>
            </div>
          </div>

          <div className='px-6 py-8 prose max-w-none'>
            <div className='space-y-6'>
              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Information We Collect</h2>
                <p className='text-gray-700'>
                  The DotMac ISP Management Platform collects information necessary for providing
                  internet service provider management capabilities, including:
                </p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>Administrative user account information</li>
                  <li>Network infrastructure data and metrics</li>
                  <li>Customer service and billing records</li>
                  <li>System logs and performance data</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Data Security</h2>
                <p className='text-gray-700'>
                  We implement industry-standard security measures to protect your data:
                </p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>End-to-end encryption for all data transmission</li>
                  <li>Role-based access controls and multi-factor authentication</li>
                  <li>Regular security audits and compliance monitoring</li>
                  <li>SOC 2 Type II and ISO 27001 compliance standards</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>
                  ISP-Specific Protections
                </h2>
                <p className='text-gray-700'>
                  As an ISP management platform, we understand the critical nature of
                  telecommunications data:
                </p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>Customer network usage data is encrypted and compartmentalized</li>
                  <li>Network topology information is protected with additional access controls</li>
                  <li>Billing and payment data follows PCI DSS compliance standards</li>
                  <li>Geographic location data is anonymized where possible</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Data Retention</h2>
                <p className='text-gray-700'>
                  We retain data only as long as necessary for business operations and legal
                  requirements:
                </p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>Network logs: 30 days for operational data, 1 year for security events</li>
                  <li>Customer records: As required by telecommunications regulations</li>
                  <li>Billing data: 7 years as per financial record requirements</li>
                  <li>System backups: 90 days with automated deletion</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Contact Information</h2>
                <p className='text-gray-700'>
                  For privacy-related questions or concerns, please contact:
                </p>
                <div className='mt-2 bg-gray-50 p-4 rounded-md'>
                  <p className='text-sm text-gray-700'>
                    <strong>Privacy Officer</strong>
                    <br />
                    DotMac ISP Framework
                    <br />
                    Email: privacy@dotmac.com
                    <br />
                    Phone: 1-800-DOTMAC-1
                  </p>
                </div>
              </div>

              <div className='border-t border-gray-200 pt-6'>
                <p className='text-sm text-gray-500'>
                  Last updated: February 2024
                  <br />
                  This privacy policy is specific to the DotMac ISP Management Platform and
                  administrative portal access.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
