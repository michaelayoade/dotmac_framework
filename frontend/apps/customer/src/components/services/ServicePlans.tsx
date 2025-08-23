'use client';

import { useCachedData } from '@dotmac/headless';
import { Card } from '@dotmac/styled-components/customer';
import {
  Check,
  Star,
  Zap,
  Shield,
  Headphones,
  Wifi,
  Phone,
  Tv,
  Clock,
  ArrowRight,
  Info,
} from 'lucide-react';
import { useState } from 'react';

// Mock service plans data
const mockServicePlans = {
  internetPlans: [
    {
      id: 'fiber-100',
      name: 'Fiber 100',
      category: 'internet',
      speed: { download: 100, upload: 100 },
      price: 79.99,
      isCurrentPlan: true,
      isPopular: false,
      features: [
        'Unlimited Data',
        'No Contracts',
        'Free Installation',
        '24/7 Technical Support',
        'WiFi Router Included',
        'IPv6 Ready',
      ],
      idealFor: 'Perfect for streaming, gaming, and working from home',
      setupFee: 0,
      contractLength: 'No Contract',
      dataAllowance: 'Unlimited',
    },
    {
      id: 'fiber-500',
      name: 'Fiber 500',
      category: 'internet',
      speed: { download: 500, upload: 500 },
      price: 119.99,
      isCurrentPlan: false,
      isPopular: true,
      features: [
        'Unlimited Data',
        'No Contracts',
        'Free Installation',
        'Priority Technical Support',
        'WiFi 6 Router Included',
        'IPv6 Ready',
        'Gaming Optimization',
        'Advanced Security Suite',
      ],
      idealFor: 'Ideal for heavy users, multiple devices, and 4K streaming',
      setupFee: 0,
      contractLength: 'No Contract',
      dataAllowance: 'Unlimited',
      upgradeFrom: 'fiber-100',
    },
    {
      id: 'fiber-gig',
      name: 'Fiber Gigabit',
      category: 'internet',
      speed: { download: 1000, upload: 1000 },
      price: 199.99,
      isCurrentPlan: false,
      isPopular: false,
      features: [
        'Unlimited Data',
        'No Contracts',
        'Free Installation',
        'White Glove Support',
        'WiFi 6E Router Included',
        'IPv6 Ready',
        'Gaming Optimization',
        'Advanced Security Suite',
        'Mesh Network Support',
        'Business-Class Service',
      ],
      idealFor: 'Maximum performance for power users and small businesses',
      setupFee: 0,
      contractLength: 'No Contract',
      dataAllowance: 'Unlimited',
      upgradeFrom: 'fiber-500',
    },
  ],
  phonePlans: [
    {
      id: 'basic-phone',
      name: 'Basic Phone',
      category: 'phone',
      price: 29.99,
      isCurrentPlan: true,
      isPopular: false,
      features: [
        'Unlimited Local Calls',
        'Voicemail',
        'Caller ID',
        'Call Waiting',
        'Three-Way Calling',
      ],
      idealFor: 'Essential phone service for everyday use',
      setupFee: 0,
      contractLength: 'Month-to-Month',
    },
    {
      id: 'premium-phone',
      name: 'Premium Phone',
      category: 'phone',
      price: 44.99,
      isCurrentPlan: false,
      isPopular: true,
      features: [
        'Unlimited Local & Long Distance',
        'Advanced Voicemail',
        'Caller ID with Name',
        'Call Waiting & Forwarding',
        'Three-Way Calling',
        'International Calling Credits',
        'Call Blocking',
        'E911 Enhanced',
      ],
      idealFor: 'Complete phone solution with enhanced features',
      setupFee: 0,
      contractLength: 'Month-to-Month',
      upgradeFrom: 'basic-phone',
    },
  ],
  tvPlans: [
    {
      id: 'tv-basic',
      name: 'Basic TV',
      category: 'tv',
      price: 59.99,
      isCurrentPlan: false,
      isPopular: false,
      features: [
        '100+ Channels',
        'Local Broadcast Channels',
        'HD Channels Included',
        'Digital Video Recorder',
        'Parental Controls',
        'On-Demand Library',
      ],
      idealFor: 'Essential TV entertainment package',
      setupFee: 99.99,
      contractLength: '12 Months',
      channels: 100,
    },
    {
      id: 'tv-premium',
      name: 'Premium TV',
      category: 'tv',
      price: 89.99,
      isCurrentPlan: false,
      isPopular: true,
      features: [
        '200+ Channels',
        'Premium Movie Channels',
        'Sports Packages',
        '4K UHD Channels',
        'Advanced DVR (8 recordings)',
        'Streaming App Access',
        'Multi-Room Support',
        'Voice Remote',
      ],
      idealFor: 'Complete entertainment with premium content',
      setupFee: 99.99,
      contractLength: '12 Months',
      channels: 200,
    },
  ],
  bundles: [
    {
      id: 'triple-play',
      name: 'Triple Play Bundle',
      services: ['fiber-500', 'premium-phone', 'tv-premium'],
      originalPrice: 254.97,
      bundlePrice: 199.99,
      savings: 54.98,
      isPopular: true,
      features: [
        'Fiber 500 Internet',
        'Premium Phone Service',
        'Premium TV Package',
        'Free Installation for All Services',
        'Single Bill Convenience',
        'Priority Customer Support',
      ],
      idealFor: 'Best value for complete home connectivity',
      contractLength: '12 Months',
    },
    {
      id: 'internet-phone',
      name: 'Internet + Phone',
      services: ['fiber-100', 'basic-phone'],
      originalPrice: 109.98,
      bundlePrice: 99.99,
      savings: 9.99,
      isPopular: false,
      features: [
        'Fiber 100 Internet',
        'Basic Phone Service',
        'Free Installation',
        'Single Bill Convenience',
      ],
      idealFor: 'Essential connectivity without TV',
      contractLength: 'No Contract',
    },
  ],
};

export function ServicePlans() {
  const [activeCategory, setActiveCategory] = useState<'internet' | 'phone' | 'tv' | 'bundles'>(
    'internet'
  );
  const [showComparison, setShowComparison] = useState(false);

  const { data: plansData, isLoading } = useCachedData(
    'service-plans',
    async () => mockServicePlans,
    { ttl: 10 * 60 * 1000 }
  );

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const getPlanIcon = (category: string) => {
    switch (category) {
      case 'internet':
        return <Wifi className='h-6 w-6 text-blue-600' />;
      case 'phone':
        return <Phone className='h-6 w-6 text-green-600' />;
      case 'tv':
        return <Tv className='h-6 w-6 text-purple-600' />;
      default:
        return <Zap className='h-6 w-6 text-orange-600' />;
    }
  };

  if (isLoading || !plansData) {
    return (
      <div className='flex h-64 items-center justify-center'>
        <div className='h-8 w-8 animate-spin rounded-full border-blue-600 border-b-2' />
      </div>
    );
  }

  const getCurrentPlans = () => {
    switch (activeCategory) {
      case 'internet':
        return plansData.internetPlans;
      case 'phone':
        return plansData.phonePlans;
      case 'tv':
        return plansData.tvPlans;
      case 'bundles':
        return plansData.bundles;
      default:
        return [];
    }
  };

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-gray-900'>Available Plans</h2>
          <p className='mt-1 text-sm text-gray-500'>
            Explore our service plans and find the perfect fit for your needs
          </p>
        </div>
        <button
          onClick={() => setShowComparison(!showComparison)}
          className='rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50'
        >
          {showComparison ? 'Hide Comparison' : 'Compare Plans'}
        </button>
      </div>

      {/* Category Navigation */}
      <div className='border-b border-gray-200'>
        <nav className='-mb-px flex space-x-8'>
          {[
            { id: 'internet', label: 'Internet Plans', icon: Wifi },
            { id: 'phone', label: 'Phone Plans', icon: Phone },
            { id: 'tv', label: 'TV Plans', icon: Tv },
            { id: 'bundles', label: 'Bundle Deals', icon: Zap },
          ].map((category) => (
            <button
              key={category.id}
              onClick={() => setActiveCategory(category.id as any)}
              className={`flex items-center border-b-2 px-1 py-2 text-sm font-medium ${
                activeCategory === category.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              <category.icon className='mr-2 h-4 w-4' />
              {category.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Plans Grid */}
      <div
        className={`grid gap-6 ${showComparison ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'}`}
      >
        {getCurrentPlans().map((plan: any) => (
          <Card
            key={plan.id}
            className={`relative p-6 ${plan.isPopular ? 'ring-2 ring-blue-500' : ''}`}
          >
            {plan.isPopular && (
              <div className='absolute -top-3 left-1/2 transform -translate-x-1/2'>
                <span className='inline-flex items-center rounded-full bg-blue-500 px-3 py-1 text-xs font-medium text-white'>
                  <Star className='mr-1 h-3 w-3' />
                  Most Popular
                </span>
              </div>
            )}

            {plan.isCurrentPlan && (
              <div className='absolute -top-3 right-4'>
                <span className='inline-flex items-center rounded-full bg-green-500 px-3 py-1 text-xs font-medium text-white'>
                  Current Plan
                </span>
              </div>
            )}

            <div className='mb-6'>
              <div className='flex items-center mb-2'>
                {getPlanIcon(plan.category || 'bundle')}
                <h3 className='ml-2 text-xl font-bold text-gray-900'>{plan.name}</h3>
              </div>

              <div className='mb-2'>
                {plan.bundlePrice ? (
                  <div>
                    <div className='flex items-baseline'>
                      <span className='text-3xl font-bold text-gray-900'>
                        {formatCurrency(plan.bundlePrice)}
                      </span>
                      <span className='ml-2 text-sm text-gray-500'>/month</span>
                    </div>
                    <div className='flex items-center text-sm'>
                      <span className='text-gray-500 line-through'>
                        {formatCurrency(plan.originalPrice)}
                      </span>
                      <span className='ml-2 text-green-600 font-medium'>
                        Save {formatCurrency(plan.savings)}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className='flex items-baseline'>
                    <span className='text-3xl font-bold text-gray-900'>
                      {formatCurrency(plan.price)}
                    </span>
                    <span className='ml-2 text-sm text-gray-500'>/month</span>
                  </div>
                )}
              </div>

              <p className='text-sm text-gray-600'>{plan.idealFor}</p>

              {plan.speed && (
                <div className='mt-2 flex items-center text-sm text-blue-600'>
                  <Zap className='mr-1 h-4 w-4' />
                  <span className='font-medium'>
                    {plan.speed.download}/{plan.speed.upload} Mbps
                  </span>
                </div>
              )}

              {plan.channels && (
                <div className='mt-2 flex items-center text-sm text-purple-600'>
                  <Tv className='mr-1 h-4 w-4' />
                  <span className='font-medium'>{plan.channels}+ Channels</span>
                </div>
              )}
            </div>

            <div className='mb-6'>
              <h4 className='mb-3 font-medium text-gray-900'>Features Include:</h4>
              <ul className='space-y-2'>
                {plan.features.map((feature: string, index: number) => (
                  <li key={index} className='flex items-start text-sm text-gray-600'>
                    <Check className='mr-2 h-4 w-4 text-green-500 flex-shrink-0 mt-0.5' />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className='mb-6 space-y-2 text-sm'>
              {plan.setupFee !== undefined && (
                <div className='flex justify-between'>
                  <span className='text-gray-600'>Setup Fee:</span>
                  <span
                    className={plan.setupFee === 0 ? 'text-green-600 font-medium' : 'text-gray-900'}
                  >
                    {plan.setupFee === 0 ? 'FREE' : formatCurrency(plan.setupFee)}
                  </span>
                </div>
              )}
              <div className='flex justify-between'>
                <span className='text-gray-600'>Contract:</span>
                <span className='text-gray-900'>{plan.contractLength}</span>
              </div>
              {plan.dataAllowance && (
                <div className='flex justify-between'>
                  <span className='text-gray-600'>Data Allowance:</span>
                  <span className='text-gray-900'>{plan.dataAllowance}</span>
                </div>
              )}
            </div>

            <div className='space-y-2'>
              {plan.isCurrentPlan ? (
                <button
                  disabled
                  className='w-full rounded-lg bg-gray-100 px-4 py-2 text-gray-500 cursor-not-allowed'
                >
                  Current Plan
                </button>
              ) : plan.upgradeFrom ? (
                <button className='w-full rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700'>
                  <span className='flex items-center justify-center'>
                    Upgrade to This Plan
                    <ArrowRight className='ml-2 h-4 w-4' />
                  </span>
                </button>
              ) : (
                <button className='w-full rounded-lg bg-green-600 px-4 py-2 text-white transition-colors hover:bg-green-700'>
                  Add This Service
                </button>
              )}
              <button className='w-full rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50'>
                Learn More
              </button>
            </div>
          </Card>
        ))}
      </div>

      {/* Plan Comparison Table */}
      {showComparison && activeCategory !== 'bundles' && (
        <Card className='p-6 overflow-x-auto'>
          <h3 className='mb-4 text-lg font-semibold text-gray-900'>Plan Comparison</h3>
          <table className='min-w-full'>
            <thead>
              <tr className='border-b border-gray-200'>
                <th className='text-left py-3 px-4 font-medium text-gray-900'>Feature</th>
                {getCurrentPlans().map((plan: any) => (
                  <th key={plan.id} className='text-center py-3 px-4'>
                    <div className='font-medium text-gray-900'>{plan.name}</div>
                    <div className='text-2xl font-bold text-blue-600 mt-1'>
                      {formatCurrency(plan.price)}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className='divide-y divide-gray-200'>
              {activeCategory === 'internet' && (
                <>
                  <tr>
                    <td className='py-3 px-4 font-medium text-gray-900'>Download Speed</td>
                    {getCurrentPlans().map((plan: any) => (
                      <td key={plan.id} className='text-center py-3 px-4'>
                        <span className='font-medium text-blue-600'>
                          {plan.speed.download} Mbps
                        </span>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className='py-3 px-4 font-medium text-gray-900'>Upload Speed</td>
                    {getCurrentPlans().map((plan: any) => (
                      <td key={plan.id} className='text-center py-3 px-4'>
                        <span className='font-medium text-blue-600'>{plan.speed.upload} Mbps</span>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className='py-3 px-4 font-medium text-gray-900'>Data Allowance</td>
                    {getCurrentPlans().map((plan: any) => (
                      <td key={plan.id} className='text-center py-3 px-4'>
                        <Check className='h-5 w-5 text-green-500 mx-auto' />
                      </td>
                    ))}
                  </tr>
                </>
              )}

              <tr>
                <td className='py-3 px-4 font-medium text-gray-900'>Setup Fee</td>
                {getCurrentPlans().map((plan: any) => (
                  <td key={plan.id} className='text-center py-3 px-4'>
                    <span
                      className={
                        plan.setupFee === 0 ? 'text-green-600 font-medium' : 'text-gray-900'
                      }
                    >
                      {plan.setupFee === 0 ? 'FREE' : formatCurrency(plan.setupFee)}
                    </span>
                  </td>
                ))}
              </tr>

              <tr>
                <td className='py-3 px-4 font-medium text-gray-900'>Contract Length</td>
                {getCurrentPlans().map((plan: any) => (
                  <td key={plan.id} className='text-center py-3 px-4'>
                    <span className='text-gray-900'>{plan.contractLength}</span>
                  </td>
                ))}
              </tr>

              <tr>
                <td className='py-3 px-4 font-medium text-gray-900'>24/7 Support</td>
                {getCurrentPlans().map((plan: any) => (
                  <td key={plan.id} className='text-center py-3 px-4'>
                    <Check className='h-5 w-5 text-green-500 mx-auto' />
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </Card>
      )}

      {/* Additional Information */}
      <Card className='p-6 bg-blue-50 border-blue-200'>
        <div className='flex items-start'>
          <Info className='h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0' />
          <div className='ml-3'>
            <h3 className='font-medium text-blue-900'>Need Help Choosing?</h3>
            <p className='mt-1 text-sm text-blue-700'>
              Our customer service team is available 24/7 to help you find the perfect plan for your
              needs. Call us at{' '}
              <a href='tel:+1-800-123-4567' className='font-medium underline'>
                1-800-123-4567
              </a>{' '}
              or{' '}
              <button className='font-medium underline hover:no-underline'>
                chat with us online
              </button>
              .
            </p>
            <div className='mt-3 flex space-x-4'>
              <div className='flex items-center text-sm text-blue-700'>
                <Shield className='mr-1 h-4 w-4' />
                30-Day Money Back Guarantee
              </div>
              <div className='flex items-center text-sm text-blue-700'>
                <Clock className='mr-1 h-4 w-4' />
                No Long-Term Contracts
              </div>
              <div className='flex items-center text-sm text-blue-700'>
                <Headphones className='mr-1 h-4 w-4' />
                24/7 Customer Support
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
