'use client';

interface SystemStatusData {
  api: string;
  database: string;
  cache: string;
  network: string;
  billing: string;
  support: string;
}

export function SystemStatus({ status }: { status: SystemStatusData }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'down':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const services = [
    { name: 'API Gateway', status: status.api },
    { name: 'Database', status: status.database },
    { name: 'Cache Layer', status: status.cache },
    { name: 'Network Services', status: status.network },
    { name: 'Billing System', status: status.billing },
    { name: 'Support Portal', status: status.support },
  ];

  const hasIssues = Object.values(status).some((s) => s !== 'operational');

  return (
    <div className='bg-white rounded-lg shadow'>
      <div className='px-6 py-4 border-b border-gray-200'>
        <div className='flex items-center justify-between'>
          <h2 className='text-lg font-medium text-gray-900'>System Status</h2>
          <div className='flex items-center'>
            <div
              className={`h-2 w-2 rounded-full ${hasIssues ? 'bg-yellow-500' : 'bg-green-500'} mr-2`}
            />
            <span className='text-sm text-gray-500'>
              {hasIssues ? 'Some issues detected' : 'All systems operational'}
            </span>
          </div>
        </div>
      </div>
      <div className='px-6 py-4'>
        <div className='space-y-3'>
          {services.map((service) => (
            <div key={service.name} className='flex items-center justify-between'>
              <span className='text-sm text-gray-900'>{service.name}</span>
              <div className='flex items-center'>
                <span className='text-xs text-gray-500 mr-2'>{getStatusText(service.status)}</span>
                <div className={`h-2 w-2 rounded-full ${getStatusColor(service.status)}`} />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className='px-6 py-3 border-t border-gray-200'>
        <button className='text-sm text-indigo-600 hover:text-indigo-500 font-medium'>
          View detailed status →
        </button>
      </div>
    </div>
  );
}
