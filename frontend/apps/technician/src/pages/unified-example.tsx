/**
 * Comprehensive DRY Integration Example
 * Shows all unified packages working together in a real-world scenario
 */

import React from 'react';
import { 
  UniversalMetricsGrid, 
  UniversalLineChart,
  ChartContainer,
  MetricData 
} from '@dotmac/dashboard';
import { 
  useUniversalForm, 
  workOrderSchema, 
  FormField,
  FormButton,
  FormSelect 
} from '@dotmac/forms';
import { 
  formatCurrency, 
  formatNumber, 
  formatDuration,
  debounce,
  generateId 
} from '@dotmac/utils';
import { 
  useAsync, 
  useDebounce, 
  useLocalStorage 
} from '@dotmac/hooks';
import { 
  Wrench, Clock, CheckCircle, AlertTriangle,
  MapPin, User, Calendar, Activity 
} from 'lucide-react';

// Mock API function
const fetchTechnicianData = async (): Promise<any> => {
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  return {
    workOrders: {
      completed: 23,
      pending: 8,
      inProgress: 3,
      cancelled: 1
    },
    performance: {
      efficiency: 94,
      customerSatisfaction: 4.8,
      responseTime: 18, // minutes
      completionRate: 96
    },
    schedule: [
      { time: '9:00 AM', customer: 'John Smith', type: 'Installation', status: 'completed' },
      { time: '11:30 AM', customer: 'Sarah Johnson', type: 'Repair', status: 'in-progress' },
      { time: '2:00 PM', customer: 'Mike Brown', type: 'Maintenance', status: 'pending' },
      { time: '4:30 PM', customer: 'Lisa Davis', type: 'Installation', status: 'pending' }
    ],
    trends: [
      { name: 'Mon', completed: 4, pending: 2 },
      { name: 'Tue', completed: 6, pending: 1 },
      { name: 'Wed', completed: 5, pending: 3 },
      { name: 'Thu', completed: 7, pending: 2 },
      { name: 'Fri', completed: 8, pending: 1 }
    ]
  };
};

const createWorkOrder = async (data: any): Promise<any> => {
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  if (Math.random() > 0.8) {
    throw new Error('Failed to create work order. Please try again.');
  }
  
  return {
    id: generateId(),
    ...data,
    status: 'scheduled',
    createdAt: new Date().toISOString()
  };
};

export default function UnifiedExamplePage() {
  // Using unified hooks
  const { 
    data, 
    loading, 
    error, 
    refetch 
  } = useAsync(fetchTechnicianData, { 
    immediate: true,
    cacheKey: 'technician-dashboard',
    cacheTime: 5 * 60 * 1000 // 5 minutes
  });

  // Local storage for user preferences
  const [preferences, setPreferences] = useLocalStorage('tech-preferences', {
    showMetrics: true,
    showChart: true,
    showSchedule: true
  });

  // Debounced search
  const [searchTerm, setSearchTerm] = React.useState('');
  const debouncedSearch = useDebounce((term: string) => {
    console.log('Searching for:', term);
    // Perform search
  }, 300);

  React.useEffect(() => {
    if (searchTerm) {
      debouncedSearch(searchTerm);
    }
  }, [searchTerm, debouncedSearch]);

  // Unified form for work orders
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useUniversalForm({
    schema: workOrderSchema,
    defaultValues: {
      type: 'installation',
      priority: 'medium',
      customerId: '',
      description: '',
      scheduledDate: new Date(),
      estimatedDuration: 60
    }
  });

  const { execute: submitWorkOrder, loading: submitting } = useAsync(createWorkOrder, {
    onSuccess: (result) => {
      console.log('Work order created:', result);
      reset();
      refetch(); // Refresh dashboard data
    },
    onError: (error) => {
      console.error('Failed to create work order:', error);
    }
  });

  const handleFormSubmit = async (formData: any) => {
    await submitWorkOrder(formData);
  };

  // Transform data for metrics using unified formatters
  const metrics: MetricData[] = React.useMemo(() => {
    if (!data) return [];
    
    return [
      {
        name: 'Completed Today',
        value: formatNumber(data.workOrders.completed),
        icon: CheckCircle,
        trend: {
          value: '+12%',
          positive: true
        },
        description: 'work orders'
      },
      {
        name: 'Pending',
        value: formatNumber(data.workOrders.pending),
        icon: Clock,
        color: data.workOrders.pending > 5 ? 'warning' : 'primary',
        description: 'need attention'
      },
      {
        name: 'Efficiency',
        value: `${data.performance.efficiency}%`,
        icon: Activity,
        trend: {
          value: '+3%',
          positive: true
        },
        description: 'this week'
      },
      {
        name: 'Response Time',
        value: formatDuration(data.performance.responseTime * 60),
        icon: Wrench,
        trend: {
          value: '-5 min',
          positive: true
        },
        description: 'average'
      }
    ];
  }, [data]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-16 w-16 mx-auto text-red-500 mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Error Loading Dashboard
          </h1>
          <p className="text-gray-600 mb-4">{error.message}</p>
          <button
            onClick={refetch}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Technician Dashboard
            </h1>
            <p className="text-gray-600 mt-1">
              Comprehensive DRY Package Integration Example
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Search with debounce */}
            <input
              type="text"
              placeholder="Search work orders..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            
            <button
              onClick={refetch}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Unified Metrics Grid */}
        {preferences.showMetrics && (
          <UniversalMetricsGrid
            metrics={metrics}
            portal="technician"
            columns={4}
            size="md"
            isLoading={loading}
          />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Performance Chart */}
          {preferences.showChart && data && (
            <ChartContainer title="Weekly Performance">
              <UniversalLineChart
                data={data.trends}
                dataKey="completed"
                portal="technician"
                height={300}
                showDots={true}
              />
            </ChartContainer>
          )}

          {/* Work Order Form */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Create Work Order
            </h3>
            
            <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Type" error={errors.type?.message}>
                  <FormSelect
                    {...register('type')}
                    options={[
                      { label: 'Installation', value: 'installation' },
                      { label: 'Repair', value: 'repair' },
                      { label: 'Maintenance', value: 'maintenance' },
                      { label: 'Upgrade', value: 'upgrade' }
                    ]}
                  />
                </FormField>

                <FormField label="Priority" error={errors.priority?.message}>
                  <FormSelect
                    {...register('priority')}
                    options={[
                      { label: 'Low', value: 'low' },
                      { label: 'Medium', value: 'medium' },
                      { label: 'High', value: 'high' },
                      { label: 'Urgent', value: 'urgent' }
                    ]}
                  />
                </FormField>
              </div>

              <FormField label="Customer ID" error={errors.customerId?.message}>
                <input
                  {...register('customerId')}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  placeholder="Enter customer ID"
                />
              </FormField>

              <FormField label="Description" error={errors.description?.message}>
                <textarea
                  {...register('description')}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  placeholder="Describe the work to be done..."
                />
              </FormField>

              <div className="flex justify-end">
                <FormButton
                  type="submit"
                  isLoading={submitting}
                  loadingText="Creating..."
                  className="px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
                >
                  Create Work Order
                </FormButton>
              </div>
            </form>
          </div>
        </div>

        {/* Schedule (if enabled in preferences) */}
        {preferences.showSchedule && data && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Today's Schedule
              </h3>
              
              {/* Preferences Toggle */}
              <div className="flex items-center space-x-4 text-sm">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={preferences.showMetrics}
                    onChange={(e) => setPreferences(prev => ({
                      ...prev,
                      showMetrics: e.target.checked
                    }))}
                    className="mr-2"
                  />
                  Show Metrics
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={preferences.showChart}
                    onChange={(e) => setPreferences(prev => ({
                      ...prev,
                      showChart: e.target.checked
                    }))}
                    className="mr-2"
                  />
                  Show Chart
                </label>
              </div>
            </div>

            <div className="space-y-3">
              {data.schedule.map((item: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      item.status === 'completed' ? 'bg-green-500' :
                      item.status === 'in-progress' ? 'bg-blue-500' :
                      'bg-gray-400'
                    }`} />
                    <div>
                      <p className="font-medium">{item.time} - {item.customer}</p>
                      <p className="text-sm text-gray-600">{item.type}</p>
                    </div>
                  </div>
                  
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    item.status === 'completed' ? 'bg-green-100 text-green-800' :
                    item.status === 'in-progress' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {item.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}