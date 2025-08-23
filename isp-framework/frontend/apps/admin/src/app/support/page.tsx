import Link from 'next/link';
import { ArrowLeft, Phone, Mail, MessageSquare, Clock, AlertTriangle } from 'lucide-react';

export default function SupportPage() {
  return (
    <div className='min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8'>
      <div className='max-w-4xl mx-auto'>
        <div className='bg-white shadow-sm rounded-lg overflow-hidden'>
          <div className='px-6 py-8 border-b border-gray-200'>
            <div className='flex items-center justify-between'>
              <div>
                <h1 className='text-3xl font-bold text-gray-900'>Support Center</h1>
                <p className='mt-2 text-sm text-gray-600'>DotMac ISP Management Platform Support</p>
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

          <div className='px-6 py-8'>
            {/* Emergency Support Banner */}
            <div className='bg-red-50 border border-red-200 rounded-lg p-4 mb-8'>
              <div className='flex items-center'>
                <AlertTriangle className='h-5 w-5 text-red-600 mr-3' />
                <div>
                  <h3 className='text-sm font-medium text-red-800'>Network Emergency?</h3>
                  <p className='text-sm text-red-700 mt-1'>
                    For critical network outages affecting customer service, call our 24/7 emergency
                    line:
                    <strong className='ml-1'>1-800-EMERGENCY</strong>
                  </p>
                </div>
              </div>
            </div>

            <div className='grid grid-cols-1 md:grid-cols-2 gap-8'>
              {/* Contact Methods */}
              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-4'>Contact Support</h2>
                <div className='space-y-4'>
                  <div className='flex items-start space-x-3 p-4 border border-gray-200 rounded-lg'>
                    <Phone className='h-6 w-6 text-blue-600 mt-1' />
                    <div>
                      <h3 className='font-medium text-gray-900'>Phone Support</h3>
                      <p className='text-sm text-gray-600 mb-2'>Talk to our ISP specialists</p>
                      <p className='text-sm font-medium text-blue-600'>1-800-DOTMAC-1</p>
                      <p className='text-xs text-gray-500'>Available 24/7 for Tier 1 support</p>
                    </div>
                  </div>

                  <div className='flex items-start space-x-3 p-4 border border-gray-200 rounded-lg'>
                    <Mail className='h-6 w-6 text-green-600 mt-1' />
                    <div>
                      <h3 className='font-medium text-gray-900'>Email Support</h3>
                      <p className='text-sm text-gray-600 mb-2'>Detailed technical assistance</p>
                      <p className='text-sm font-medium text-green-600'>support@dotmac.com</p>
                      <p className='text-xs text-gray-500'>Response within 4 hours</p>
                    </div>
                  </div>

                  <div className='flex items-start space-x-3 p-4 border border-gray-200 rounded-lg'>
                    <MessageSquare className='h-6 w-6 text-purple-600 mt-1' />
                    <div>
                      <h3 className='font-medium text-gray-900'>Live Chat</h3>
                      <p className='text-sm text-gray-600 mb-2'>Quick questions and guidance</p>
                      <button className='text-sm font-medium text-purple-600 hover:text-purple-700'>
                        Start Chat Session
                      </button>
                      <p className='text-xs text-gray-500'>Available during business hours</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Support Categories */}
              <div>
                <h2 className='text-xl font-semibold text-gray-900 mb-4'>Support Categories</h2>
                <div className='space-y-3'>
                  <div className='p-3 bg-blue-50 rounded-lg'>
                    <h3 className='font-medium text-blue-900'>Network Operations</h3>
                    <p className='text-sm text-blue-700'>Topology, routing, monitoring, outages</p>
                  </div>

                  <div className='p-3 bg-green-50 rounded-lg'>
                    <h3 className='font-medium text-green-900'>Customer Management</h3>
                    <p className='text-sm text-green-700'>Provisioning, billing, service plans</p>
                  </div>

                  <div className='p-3 bg-purple-50 rounded-lg'>
                    <h3 className='font-medium text-purple-900'>Platform Administration</h3>
                    <p className='text-sm text-purple-700'>
                      User accounts, permissions, integrations
                    </p>
                  </div>

                  <div className='p-3 bg-orange-50 rounded-lg'>
                    <h3 className='font-medium text-orange-900'>Technical Issues</h3>
                    <p className='text-sm text-orange-700'>Bugs, performance, login problems</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Support Hours */}
            <div className='mt-8 bg-gray-50 rounded-lg p-6'>
              <div className='flex items-center mb-4'>
                <Clock className='h-5 w-5 text-gray-600 mr-2' />
                <h2 className='text-lg font-semibold text-gray-900'>Support Hours</h2>
              </div>
              <div className='grid grid-cols-1 md:grid-cols-3 gap-4 text-sm'>
                <div>
                  <h3 className='font-medium text-gray-900 mb-2'>Emergency Support</h3>
                  <p className='text-gray-600'>24/7/365 availability</p>
                  <p className='text-gray-600'>Critical network issues</p>
                </div>
                <div>
                  <h3 className='font-medium text-gray-900 mb-2'>Standard Support</h3>
                  <p className='text-gray-600'>Monday - Friday</p>
                  <p className='text-gray-600'>6:00 AM - 10:00 PM EST</p>
                </div>
                <div>
                  <h3 className='font-medium text-gray-900 mb-2'>Business Hours</h3>
                  <p className='text-gray-600'>Monday - Friday</p>
                  <p className='text-gray-600'>8:00 AM - 6:00 PM EST</p>
                </div>
              </div>
            </div>

            {/* Quick Links */}
            <div className='mt-8'>
              <h2 className='text-lg font-semibold text-gray-900 mb-4'>Quick Links</h2>
              <div className='grid grid-cols-2 md:grid-cols-4 gap-3 text-sm'>
                <a
                  href='#'
                  className='p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-center'
                >
                  📚 Documentation
                </a>
                <a
                  href='#'
                  className='p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-center'
                >
                  🎯 API Reference
                </a>
                <a
                  href='#'
                  className='p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-center'
                >
                  🔧 Troubleshooting
                </a>
                <a
                  href='#'
                  className='p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-center'
                >
                  📊 Status Page
                </a>
              </div>
            </div>

            <div className='mt-8 border-t border-gray-200 pt-6'>
              <p className='text-sm text-gray-500'>
                <strong>Note:</strong> This support center is specifically for the DotMac ISP
                Management Platform. For end-customer support issues, please refer to your ISP's
                customer service procedures.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
