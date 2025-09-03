'use client';

import {
  UserPlusIcon,
  CreditCardIcon,
  WifiIcon,
  CheckCircleIcon,
  AlertCircleIcon,
} from 'lucide-react';

interface Activity {
  id: string;
  type: string;
  message: string;
  time: string;
}

export function RecentActivity({ activity }: { activity: Activity[] }) {
  const getIcon = (type: string) => {
    switch (type) {
      case 'customer_added':
        return <UserPlusIcon className='h-5 w-5 text-blue-600' />;
      case 'payment_received':
        return <CreditCardIcon className='h-5 w-5 text-green-600' />;
      case 'service_activated':
        return <WifiIcon className='h-5 w-5 text-indigo-600' />;
      case 'ticket_resolved':
        return <CheckCircleIcon className='h-5 w-5 text-purple-600' />;
      case 'network_alert':
        return <AlertCircleIcon className='h-5 w-5 text-yellow-600' />;
      default:
        return <AlertCircleIcon className='h-5 w-5 text-gray-600' />;
    }
  };

  return (
    <div className='bg-white rounded-lg shadow'>
      <div className='px-6 py-4 border-b border-gray-200'>
        <h2 className='text-lg font-medium text-gray-900'>Recent Activity</h2>
      </div>
      <div className='divide-y divide-gray-200'>
        {activity.map((item) => (
          <div key={item.id} className='px-6 py-4 flex items-start space-x-3 hover:bg-gray-50'>
            <div className='flex-shrink-0 mt-0.5'>{getIcon(item.type)}</div>
            <div className='flex-1 min-w-0'>
              <p className='text-sm text-gray-900'>{item.message}</p>
              <p className='text-xs text-gray-500 mt-1'>{item.time}</p>
            </div>
          </div>
        ))}
      </div>
      <div className='px-6 py-3 border-t border-gray-200'>
        <button className='text-sm text-indigo-600 hover:text-indigo-500 font-medium'>
          View all activity →
        </button>
      </div>
    </div>
  );
}
