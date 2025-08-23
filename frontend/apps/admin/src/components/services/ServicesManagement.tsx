'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  SearchIcon,
  FilterIcon,
  DownloadIcon,
  PlusIcon,
  SettingsIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  EditIcon,
  EyeIcon,
  ChevronRightIcon,
  WifiIcon,
  PhoneIcon,
  TvIcon,
  ShieldIcon,
  ClockIcon,
  UsersIcon,
  DollarSignIcon,
  TrendingUpIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  WorkflowIcon,
  ServerIcon,
} from 'lucide-react';

interface Service {
  id: string;
  name: string;
  category: string;
  type: 'residential' | 'business' | 'enterprise';
  status: 'active' | 'inactive' | 'deprecated' | 'draft';
  description: string;
  pricing: {
    monthly: number;
    setup: number;
    currency: string;
  };
  specifications: Record<string, any>;
  provisioning: {
    method: 'automated' | 'manual' | 'hybrid';
    estimatedTime: string;
    requiresTechnician: boolean;
  };
  availability: {
    regions: string[];
    coverage: number;
  };
  metrics: {
    activeSubscriptions: number;
    monthlyRevenue: number;
    customerSatisfaction: number;
    churnRate: number;
  };
  lifecycle: {
    createdAt: string;
    updatedAt: string;
    version: string;
    deprecated: boolean;
    deprecationDate?: string;
  };
  dependencies: string[];
  tags: string[];
}

interface Category {
  id: string;
  name: string;
  count: number;
}

interface Workflow {
  id: string;
  name: string;
  type: string;
  status: string;
  steps: {
    id: number;
    name: string;
    automated: boolean;
    duration: string;
  }[];
  metrics: {
    avgCompletionTime: string;
    successRate: number;
    executionsLastMonth: number;
  };
}

interface ServicesManagementProps {
  services: Service[];
  categories: Category[];
  workflows: Workflow[];
  totalCount: number;
  currentPage: number;
  pageSize: number;
}

type ViewMode = 'grid' | 'table' | 'workflows';

export function ServicesManagement({
  services,
  categories,
  workflows,
  totalCount,
  currentPage,
  pageSize,
}: ServicesManagementProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [selectedServices, setSelectedServices] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [expandedWorkflows, setExpandedWorkflows] = useState<Set<string>>(new Set());

  const updateURL = useCallback(
    (params: Record<string, string | null>) => {
      const newParams = new URLSearchParams(searchParams);

      Object.entries(params).forEach(([key, value]) => {
        if (value === null || value === '') {
          newParams.delete(key);
        } else {
          newParams.set(key, value);
        }
      });

      router.push(`${pathname}?${newParams.toString()}`);
    },
    [pathname, router, searchParams]
  );

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    updateURL({ search: query, page: '1' });
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'internet':
        return WifiIcon;
      case 'voice':
        return PhoneIcon;
      case 'tv':
        return TvIcon;
      case 'security':
        return ShieldIcon;
      default:
        return ServerIcon;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'deprecated':
        return 'bg-red-100 text-red-800';
      case 'draft':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getProvisioningColor = (method: string) => {
    switch (method) {
      case 'automated':
        return 'bg-blue-100 text-blue-800';
      case 'manual':
        return 'bg-orange-100 text-orange-800';
      case 'hybrid':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const ServiceCard = ({ service }: { service: Service }) => {
    const Icon = getCategoryIcon(service.category);

    return (
      <div className='bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow'>
        <div className='flex items-start justify-between'>
          <div className='flex items-center space-x-3'>
            <div className='flex-shrink-0'>
              <div className='w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center'>
                <Icon className='w-6 h-6 text-blue-600' />
              </div>
            </div>
            <div>
              <h3 className='text-lg font-semibold text-gray-900'>{service.name}</h3>
              <p className='text-sm text-gray-500'>
                {service.category} • {service.type}
              </p>
            </div>
          </div>
          <span
            className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(service.status)}`}
          >
            {service.status}
          </span>
        </div>

        <p className='mt-4 text-sm text-gray-600 line-clamp-2'>{service.description}</p>

        {/* Pricing */}
        <div className='mt-4 flex items-center space-x-4'>
          <div className='text-sm'>
            <span className='text-2xl font-bold text-gray-900'>${service.pricing.monthly}</span>
            <span className='text-gray-500'>/month</span>
          </div>
          {service.pricing.setup > 0 && (
            <div className='text-sm text-gray-500'>Setup: ${service.pricing.setup}</div>
          )}
        </div>

        {/* Key Metrics */}
        <div className='mt-4 grid grid-cols-2 gap-4'>
          <div className='text-sm'>
            <div className='flex items-center text-gray-500 mb-1'>
              <UsersIcon className='w-4 h-4 mr-1' />
              Subscribers
            </div>
            <div className='font-semibold text-gray-900'>
              {service.metrics.activeSubscriptions.toLocaleString()}
            </div>
          </div>
          <div className='text-sm'>
            <div className='flex items-center text-gray-500 mb-1'>
              <DollarSignIcon className='w-4 h-4 mr-1' />
              Revenue
            </div>
            <div className='font-semibold text-gray-900'>
              ${service.metrics.monthlyRevenue.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Provisioning Method */}
        <div className='mt-4'>
          <span
            className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${getProvisioningColor(service.provisioning.method)}`}
          >
            {service.provisioning.method === 'automated' && <PlayIcon className='w-3 h-3 mr-1' />}
            {service.provisioning.method === 'manual' && <SettingsIcon className='w-3 h-3 mr-1' />}
            {service.provisioning.requiresTechnician && <UsersIcon className='w-3 h-3 mr-1' />}
            {service.provisioning.method} ({service.provisioning.estimatedTime})
          </span>
        </div>

        {/* Tags */}
        {service.tags.length > 0 && (
          <div className='mt-4 flex flex-wrap gap-1'>
            {service.tags.slice(0, 3).map((tag) => (
              <span key={tag} className='px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded'>
                {tag}
              </span>
            ))}
            {service.tags.length > 3 && (
              <span className='px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded'>
                +{service.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        <div className='mt-6 flex items-center justify-between'>
          <button
            onClick={() => router.push(`/services/${service.id}`)}
            className='text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center'
          >
            View Details <ChevronRightIcon className='w-4 h-4 ml-1' />
          </button>
          <div className='flex space-x-2'>
            <button
              onClick={() => router.push(`/services/${service.id}/edit`)}
              className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded'
            >
              <EditIcon className='w-4 h-4' />
            </button>
            <button className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded'>
              <SettingsIcon className='w-4 h-4' />
            </button>
          </div>
        </div>
      </div>
    );
  };

  const WorkflowCard = ({ workflow }: { workflow: Workflow }) => {
    const isExpanded = expandedWorkflows.has(workflow.id);

    return (
      <div className='bg-white rounded-xl shadow-sm border border-gray-200 p-6'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center space-x-3'>
            <div className='w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center'>
              <WorkflowIcon className='w-5 h-5 text-purple-600' />
            </div>
            <div>
              <h3 className='font-semibold text-gray-900'>{workflow.name}</h3>
              <p className='text-sm text-gray-500'>{workflow.type} workflow</p>
            </div>
          </div>
          <button
            onClick={() => {
              const newExpanded = new Set(expandedWorkflows);
              if (isExpanded) {
                newExpanded.delete(workflow.id);
              } else {
                newExpanded.add(workflow.id);
              }
              setExpandedWorkflows(newExpanded);
            }}
            className='p-2 hover:bg-gray-100 rounded-lg'
          >
            {isExpanded ? (
              <ChevronUpIcon className='w-4 h-4' />
            ) : (
              <ChevronDownIcon className='w-4 h-4' />
            )}
          </button>
        </div>

        {/* Metrics */}
        <div className='mt-4 grid grid-cols-3 gap-4'>
          <div className='text-center'>
            <div className='text-sm text-gray-500'>Avg Time</div>
            <div className='font-semibold text-gray-900'>{workflow.metrics.avgCompletionTime}</div>
          </div>
          <div className='text-center'>
            <div className='text-sm text-gray-500'>Success Rate</div>
            <div className='font-semibold text-green-600'>{workflow.metrics.successRate}%</div>
          </div>
          <div className='text-center'>
            <div className='text-sm text-gray-500'>Last Month</div>
            <div className='font-semibold text-gray-900'>
              {workflow.metrics.executionsLastMonth}
            </div>
          </div>
        </div>

        {/* Workflow Steps */}
        {isExpanded && (
          <div className='mt-6 space-y-3'>
            <h4 className='font-medium text-gray-900'>Workflow Steps</h4>
            <div className='space-y-2'>
              {workflow.steps.map((step, index) => (
                <div
                  key={step.id}
                  className='flex items-center space-x-3 p-3 bg-gray-50 rounded-lg'
                >
                  <div className='flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center text-xs font-medium text-blue-600'>
                    {index + 1}
                  </div>
                  <div className='flex-1'>
                    <div className='font-medium text-gray-900'>{step.name}</div>
                    <div className='text-sm text-gray-500'>Duration: {step.duration}</div>
                  </div>
                  <div className='flex-shrink-0'>
                    {step.automated ? (
                      <span className='inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full'>
                        <CheckCircleIcon className='w-3 h-3 mr-1' />
                        Auto
                      </span>
                    ) : (
                      <span className='inline-flex items-center px-2 py-1 text-xs font-medium bg-orange-100 text-orange-800 rounded-full'>
                        <UsersIcon className='w-3 h-3 mr-1' />
                        Manual
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className='space-y-6'>
      {/* Search and Filter Bar */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
        <div className='flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between'>
          <div className='flex-1 max-w-2xl'>
            <div className='relative'>
              <SearchIcon className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5' />
              <input
                type='text'
                placeholder='Search services by name, category, or tags...'
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className='w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
              />
            </div>
          </div>

          <div className='flex items-center gap-3'>
            {/* View Mode Toggle */}
            <div className='flex bg-gray-100 rounded-lg p-1'>
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'grid' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
                }`}
              >
                Services
              </button>
              <button
                onClick={() => setViewMode('workflows')}
                className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  viewMode === 'workflows' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
                }`}
              >
                Workflows
              </button>
            </div>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded-lg border font-medium transition-colors ${
                showFilters
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <FilterIcon className='h-4 w-4 mr-2 inline' />
              Filters
            </button>
          </div>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div className='mt-6 pt-6 border-t border-gray-200'>
            <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Status</label>
                <select className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'>
                  <option value=''>All Statuses</option>
                  <option value='active'>Active</option>
                  <option value='inactive'>Inactive</option>
                  <option value='deprecated'>Deprecated</option>
                  <option value='draft'>Draft</option>
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Category</label>
                <select className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'>
                  <option value=''>All Categories</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name} ({category.count})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Type</label>
                <select className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'>
                  <option value=''>All Types</option>
                  <option value='residential'>Residential</option>
                  <option value='business'>Business</option>
                  <option value='enterprise'>Enterprise</option>
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Provisioning</label>
                <select className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'>
                  <option value=''>All Methods</option>
                  <option value='automated'>Automated</option>
                  <option value='manual'>Manual</option>
                  <option value='hybrid'>Hybrid</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Categories Sidebar & Content */}
      <div className='grid grid-cols-1 lg:grid-cols-4 gap-6'>
        {/* Categories Sidebar */}
        <div className='space-y-4'>
          <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <h3 className='font-semibold text-gray-900 mb-4'>Categories</h3>
            <div className='space-y-2'>
              {categories.map((category) => {
                const Icon = getCategoryIcon(category.name);
                return (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`w-full flex items-center space-x-3 p-3 rounded-lg text-left hover:bg-gray-50 ${
                      selectedCategory === category.id ? 'bg-blue-50 border border-blue-200' : ''
                    }`}
                  >
                    <Icon className='w-5 h-5 text-gray-400' />
                    <div className='flex-1'>
                      <div className='font-medium text-gray-900'>{category.name}</div>
                      <div className='text-sm text-gray-500'>{category.count} services</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quick Stats */}
          <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <h3 className='font-semibold text-gray-900 mb-4'>Quick Stats</h3>
            <div className='space-y-3'>
              <div className='flex justify-between'>
                <span className='text-sm text-gray-500'>Active Services</span>
                <span className='font-medium text-gray-900'>
                  {services.filter((s) => s.status === 'active').length}
                </span>
              </div>
              <div className='flex justify-between'>
                <span className='text-sm text-gray-500'>Total Revenue</span>
                <span className='font-medium text-green-600'>
                  ${services.reduce((sum, s) => sum + s.metrics.monthlyRevenue, 0).toLocaleString()}
                </span>
              </div>
              <div className='flex justify-between'>
                <span className='text-sm text-gray-500'>Avg Satisfaction</span>
                <span className='font-medium text-blue-600'>
                  {(
                    services.reduce((sum, s) => sum + s.metrics.customerSatisfaction, 0) /
                    services.length
                  ).toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className='lg:col-span-3'>
          {viewMode === 'workflows' ? (
            <div className='space-y-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <h2 className='text-lg font-semibold text-gray-900'>Provisioning Workflows</h2>
                  <p className='text-sm text-gray-500'>
                    Automated service provisioning and lifecycle management
                  </p>
                </div>
                <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
                  Create Workflow
                </button>
              </div>

              <div className='grid gap-6'>
                {workflows.map((workflow) => (
                  <WorkflowCard key={workflow.id} workflow={workflow} />
                ))}
              </div>
            </div>
          ) : (
            <div className='space-y-6'>
              <div className='flex items-center justify-between'>
                <div>
                  <h2 className='text-lg font-semibold text-gray-900'>Service Plans</h2>
                  <p className='text-sm text-gray-500'>
                    Showing {services.length} of {totalCount} services
                  </p>
                </div>
              </div>

              {/* Services Grid */}
              <div className='grid grid-cols-1 xl:grid-cols-2 gap-6'>
                {services.map((service) => (
                  <ServiceCard key={service.id} service={service} />
                ))}
              </div>

              {/* Pagination */}
              <div className='flex items-center justify-center'>
                <div className='flex items-center space-x-2'>
                  <button
                    disabled={currentPage === 1}
                    className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
                  >
                    Previous
                  </button>
                  <span className='px-4 py-2 text-sm text-gray-700'>
                    Page {currentPage} of {Math.ceil(totalCount / pageSize)}
                  </span>
                  <button
                    disabled={currentPage >= Math.ceil(totalCount / pageSize)}
                    className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
