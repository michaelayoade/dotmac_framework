import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function TermsOfServicePage() {
  return (
    <div className='min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-4xl mx-auto'>
        <div className='bg-white shadow-sm rounded-lg overflow-hidden'>
          <div className='px-6 py-8 border-b border-gray-200'>
            <div className='flex items-center justify-between'>
              <div>
                <h1 className='text-3xl font-bold text-gray-900'>Terms of Service</h1>
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
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Platform Usage Terms</h2>
                <p className='text-gray-700'>
                  By accessing the DotMac ISP Management Platform, you agree to the following terms:
                </p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>You are an authorized administrator of an internet service provider</li>
                  <li>You will use the platform solely for legitimate business purposes</li>
                  <li>You will maintain the confidentiality of your login credentials</li>
                  <li>You will comply with all applicable telecommunications regulations</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Acceptable Use Policy</h2>
                <p className='text-gray-700'>
                  The platform must be used responsibly and in accordance with industry standards:
                </p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>Network management activities must follow FCC regulations</li>
                  <li>Customer data access is limited to authorized personnel only</li>
                  <li>System modifications require proper change management approval</li>
                  <li>Emergency procedures must be followed during network incidents</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Data Responsibilities</h2>
                <p className='text-gray-700'>ISP administrators are responsible for:</p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>Maintaining accurate customer and network information</li>
                  <li>Protecting customer privacy and data confidentiality</li>
                  <li>Ensuring compliance with GDPR, CCPA, and local privacy laws</li>
                  <li>Reporting security incidents within required timeframes</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Service Availability</h2>
                <p className='text-gray-700'>Platform availability and performance standards:</p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>99.9% uptime SLA with monitoring and alerting</li>
                  <li>Scheduled maintenance windows with advance notice</li>
                  <li>24/7 technical support for critical system issues</li>
                  <li>Disaster recovery procedures with 4-hour RTO</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>
                  Compliance Requirements
                </h2>
                <p className='text-gray-700'>All platform usage must comply with:</p>
                <ul className='mt-2 list-disc list-inside text-gray-700 space-y-1'>
                  <li>Federal Communications Commission (FCC) regulations</li>
                  <li>State and local telecommunications laws</li>
                  <li>Industry standards for network operations (TIA, IEEE)</li>
                  <li>Security frameworks (SOC 2, ISO 27001, NIST)</li>
                </ul>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>
                  Limitation of Liability
                </h2>
                <p className='text-gray-700'>
                  DotMac ISP Framework provides this platform "as-is" with standard enterprise
                  support. Users are responsible for proper network operations and customer service
                  delivery. Critical infrastructure decisions should always be validated with
                  qualified network engineers.
                </p>
              </div>

              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-3'>Contact Information</h2>
                <div className='bg-gray-50 p-4 rounded-md'>
                  <p className='text-sm text-gray-700'>
                    <strong>Legal Department</strong>
                    <br />
                    DotMac ISP Framework
                    <br />
                    Email: legal@dotmac.com
                    <br />
                    Phone: 1-800-DOTMAC-1
                    <br />
                    Emergency: support@dotmac.com
                  </p>
                </div>
              </div>

              <div className='border-t border-gray-200 pt-6'>
                <p className='text-sm text-gray-500'>
                  Last updated: February 2024
                  <br />
                  These terms are specific to administrative access to the DotMac ISP Management
                  Platform. End-customer terms of service are managed separately through your ISP's
                  customer portal.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
