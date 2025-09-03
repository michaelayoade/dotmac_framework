'use client';

import React, { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  SearchIcon,
  FilterIcon,
  PlusIcon,
  ClockIcon,
  AlertCircleIcon,
  CheckCircleIcon,
  UserIcon,
  MessageCircleIcon,
  PhoneIcon,
  MailIcon,
  MonitorIcon,
  BarChartIcon,
  SettingsIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  StarIcon,
  TagIcon,
  CalendarIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ZapIcon,
  HeadphonesIcon,
  RefreshCwIcon,
  ExternalLinkIcon,
} from 'lucide-react';

interface Ticket {
  id: string;
  title: string;
  description: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  status: 'open' | 'in_progress' | 'pending' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  category: string;
  assigneeId: string | null;
  assigneeName: string | null;
  createdAt: string;
  updatedAt: string;
  resolvedAt: string | null;
  firstResponseAt: string | null;
  tags: string[];
  channel: 'web' | 'email' | 'phone' | 'chat';
  interactions: Array<{
    id: string;
    type: string;
    author: string;
    content: string;
    timestamp: string;
    internal: boolean;
  }>;
  sla: {
    firstResponseTime: number;
    resolutionTime: number;
    breached: boolean;
  };
  satisfaction: {
    rating: number;
    feedback: string;
  } | null;
}

interface Agent {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'online' | 'away' | 'busy' | 'offline';
  currentLoad: number;
  maxLoad: number;
  skills: string[];
  metrics: {
    avgFirstResponse: number;
    avgResolutionTime: number;
    customerSatisfaction: number;
    ticketsResolved: number;
    ticketsAssigned: number;
  };
}

interface Metrics {
  totalTickets: number;
  openTickets: number;
  overdueTickets: number;
  avgFirstResponse: number;
  avgResolutionTime: number;
  customerSatisfaction: number;
  slaCompliance: number;
  ticketVolume: {
    today: number;
    thisWeek: number;
    thisMonth: number;
  };
  trends: {
    tickets: number;
    satisfaction: number;
    resolution: number;
    sla: number;
  };
  channelDistribution: Array<{
    channel: string;
    count: number;
    percentage: number;
  }>;
  categoryBreakdown: Array<{
    category: string;
    count: number;
    percentage: number;
  }>;
}

interface Category {
  id: string;
  name: string;
  count: number;
  avgResolution: number;
}

interface Automation {
  id: string;
  name: string;
  description: string;
  trigger: string;
  condition: string;
  action: string;
  status: 'active' | 'inactive';
  executions: number;
  successRate: number;
}

interface SupportManagementProps {
  tickets: Ticket[];
  agents: Agent[];
  metrics: Metrics;
  categories: Category[];
  automations: Automation[];
  totalCount: number;
  currentPage: number;
  pageSize: number;
  currentView: string;
}

type ViewType = 'list' | 'kanban' | 'agents' | 'analytics';

export function SupportManagement({
  tickets,
  agents,
  metrics,
  categories,
  automations,
  totalCount,
  currentPage,
  pageSize,
  currentView,
}: SupportManagementProps) {
  const router = useRouter();
  const [selectedView, setSelectedView] = useState<ViewType>(currentView as ViewType);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTickets, setSelectedTickets] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'bg-blue-100 text-blue-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'pending':
        return 'bg-purple-100 text-purple-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'closed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'web':
        return MonitorIcon;
      case 'email':
        return MailIcon;
      case 'phone':
        return PhoneIcon;
      case 'chat':
        return MessageCircleIcon;
      default:
        return MessageCircleIcon;
    }
  };

  const getAgentStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-400';
      case 'away':
        return 'bg-yellow-400';
      case 'busy':
        return 'bg-red-400';
      case 'offline':
        return 'bg-gray-400';
      default:
        return 'bg-gray-400';
    }
  };

  const MetricCard = ({
    title,
    value,
    trend,
    icon: Icon,
    format = 'number',
  }: {
    title: string;
    value: number;
    trend?: number;
    icon: any;
    format?: 'number' | 'time' | 'percentage';
  }) => {
    const formatValue = (val: number) => {
      switch (format) {
        case 'time':
          return val < 60 ? `${val}m` : `${(val / 60).toFixed(1)}h`;
        case 'percentage':
          return `${val.toFixed(1)}%`;
        default:
          return val.toLocaleString();
      }
    };

    return (
      <div className='bg-white rounded-xl shadow-sm border border-gray-200 p-6'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center space-x-3'>
            <div className='p-2 bg-blue-100 rounded-lg'>
              <Icon className='w-6 h-6 text-blue-600' />
            </div>
            <div>
              <p className='text-sm font-medium text-gray-600'>{title}</p>
              <p className='text-2xl font-bold text-gray-900'>{formatValue(value)}</p>
            </div>
          </div>
          {trend !== undefined && (
            <div
              className={`flex items-center text-sm font-medium ${
                trend > 0 ? 'text-red-600' : trend < 0 ? 'text-green-600' : 'text-gray-600'
              }`}
            >
              {trend > 0 ? (
                <ArrowUpIcon className='w-4 h-4 mr-1' />
              ) : trend < 0 ? (
                <ArrowDownIcon className='w-4 h-4 mr-1' />
              ) : null}
              {Math.abs(trend).toFixed(1)}%
            </div>
          )}
        </div>
      </div>
    );
  };

  const TicketCard = ({ ticket }: { ticket: Ticket }) => {
    const ChannelIcon = getChannelIcon(ticket.channel);
    const timeSince = (date: string) => {
      const diff = Date.now() - new Date(date).getTime();
      const hours = Math.floor(diff / (1000 * 60 * 60));
      if (hours < 24) return `${hours}h ago`;
      return `${Math.floor(hours / 24)}d ago`;
    };

    return (
      <div className='bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow'>
        <div className='flex items-start justify-between'>
          <div className='flex-1'>
            <div className='flex items-center space-x-2 mb-2'>
              <span className='text-sm font-medium text-blue-600'>{ticket.id}</span>
              <span
                className={`px-2 py-1 text-xs font-medium rounded border ${getPriorityColor(ticket.priority)}`}
              >
                {ticket.priority}
              </span>
              <ChannelIcon className='w-4 h-4 text-gray-400' />
            </div>

            <h3 className='font-medium text-gray-900 mb-1 line-clamp-2'>{ticket.title}</h3>
            <p className='text-sm text-gray-500 mb-3 line-clamp-2'>{ticket.description}</p>

            <div className='flex items-center justify-between text-sm text-gray-500'>
              <div className='flex items-center space-x-4'>
                <span className='flex items-center'>
                  <UserIcon className='w-4 h-4 mr-1' />
                  {ticket.customerName}
                </span>
                <span>{timeSince(ticket.createdAt)}</span>
              </div>

              {ticket.assigneeName && (
                <span className='text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded'>
                  {ticket.assigneeName}
                </span>
              )}
            </div>
          </div>

          <div className='ml-3'>
            <span
              className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(ticket.status)}`}
            >
              {ticket.status.replace('_', ' ')}
            </span>
          </div>
        </div>

        {ticket.tags.length > 0 && (
          <div className='mt-3 flex flex-wrap gap-1'>
            {ticket.tags.slice(0, 3).map((tag) => (
              <span key={tag} className='px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded'>
                {tag}
              </span>
            ))}
          </div>
        )}

        {ticket.sla.breached && (
          <div className='mt-2 flex items-center text-xs text-red-600'>
            <AlertCircleIcon className='w-3 h-3 mr-1' />
            SLA Breached
          </div>
        )}
      </div>
    );
  };

  const AgentCard = ({ agent }: { agent: Agent }) => {
    const loadPercentage = (agent.currentLoad / agent.maxLoad) * 100;

    return (
      <div className='bg-white border border-gray-200 rounded-lg p-6'>
        <div className='flex items-start justify-between'>
          <div className='flex items-center space-x-3'>
            <div className='relative'>
              <div className='w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center'>
                <UserIcon className='w-5 h-5 text-gray-600' />
              </div>
              <div
                className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-white ${getAgentStatusColor(agent.status)}`}
              />
            </div>
            <div>
              <h3 className='font-medium text-gray-900'>{agent.name}</h3>
              <p className='text-sm text-gray-500'>{agent.role}</p>
            </div>
          </div>
          <span
            className={`px-2 py-1 text-xs font-medium rounded-full ${
              agent.status === 'online'
                ? 'bg-green-100 text-green-800'
                : agent.status === 'away'
                  ? 'bg-yellow-100 text-yellow-800'
                  : agent.status === 'busy'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-gray-100 text-gray-800'
            }`}
          >
            {agent.status}
          </span>
        </div>

        <div className='mt-4'>
          <div className='flex justify-between items-center mb-2'>
            <span className='text-sm font-medium text-gray-700'>Workload</span>
            <span className='text-sm text-gray-500'>
              {agent.currentLoad}/{agent.maxLoad} tickets
            </span>
          </div>
          <div className='w-full bg-gray-200 rounded-full h-2'>
            <div
              className={`h-2 rounded-full ${
                loadPercentage > 90
                  ? 'bg-red-500'
                  : loadPercentage > 70
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(loadPercentage, 100)}%` }}
            />
          </div>
        </div>

        <div className='mt-4 grid grid-cols-2 gap-4 text-sm'>
          <div>
            <div className='text-gray-500'>Avg Response</div>
            <div className='font-medium'>{agent.metrics.avgFirstResponse}m</div>
          </div>
          <div>
            <div className='text-gray-500'>Satisfaction</div>
            <div className='font-medium'>{agent.metrics.customerSatisfaction.toFixed(1)}/5</div>
          </div>
        </div>

        <div className='mt-4 flex flex-wrap gap-1'>
          {agent.skills.map((skill) => (
            <span key={skill} className='px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded'>
              {skill}
            </span>
          ))}
        </div>
      </div>
    );
  };

  const KanbanColumn = ({
    status,
    tickets: statusTickets,
  }: {
    status: string;
    tickets: Ticket[];
  }) => (
    <div className='bg-gray-50 rounded-lg p-4 min-h-[600px]'>
      <div className='flex items-center justify-between mb-4'>
        <h3 className='font-medium text-gray-900 capitalize'>
          {status.replace('_', ' ')} ({statusTickets.length})
        </h3>
      </div>
      <div className='space-y-3'>
        {statusTickets.map((ticket) => (
          <div
            key={ticket.id}
            className='cursor-pointer'
            onClick={() => router.push(`/support/tickets/${ticket.id}`)}
          >
            <TicketCard ticket={ticket} />
          </div>
        ))}
      </div>
    </div>
  );

  const ticketsByStatus = useMemo(() => {
    const statuses = ['open', 'in_progress', 'pending', 'resolved'];
    return statuses.reduce(
      (acc, status) => {
        acc[status] = tickets.filter((t) => t.status === status);
        return acc;
      },
      {} as Record<string, Ticket[]>
    );
  }, [tickets]);

  return (
    <div className='space-y-6'>
      {/* Key Metrics */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
        <MetricCard
          title='Open Tickets'
          value={metrics.openTickets}
          trend={metrics.trends.tickets}
          icon={AlertCircleIcon}
        />
        <MetricCard
          title='Avg First Response'
          value={metrics.avgFirstResponse}
          trend={metrics.trends.resolution}
          icon={ClockIcon}
          format='time'
        />
        <MetricCard
          title='Customer Satisfaction'
          value={metrics.customerSatisfaction}
          trend={metrics.trends.satisfaction}
          icon={StarIcon}
          format='number'
        />
        <MetricCard
          title='SLA Compliance'
          value={metrics.slaCompliance}
          trend={metrics.trends.sla}
          icon={CheckCircleIcon}
          format='percentage'
        />
      </div>

      {/* View Toggle and Actions */}
      <div className='flex items-center justify-between'>
        <div className='flex bg-gray-100 rounded-lg p-1'>
          <button
            onClick={() => setSelectedView('list')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              selectedView === 'list' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
            }`}
          >
            List View
          </button>
          <button
            onClick={() => setSelectedView('kanban')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              selectedView === 'kanban' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
            }`}
          >
            Kanban
          </button>
          <button
            onClick={() => setSelectedView('agents')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              selectedView === 'agents' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
            }`}
          >
            Agents
          </button>
          <button
            onClick={() => setSelectedView('analytics')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              selectedView === 'analytics' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
            }`}
          >
            Analytics
          </button>
        </div>

        <div className='flex items-center gap-3'>
          <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
            <PlusIcon className='w-4 h-4 mr-2 inline' />
            Create Ticket
          </button>
        </div>
      </div>

      {/* Main Content */}
      {selectedView === 'list' && (
        <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
          {/* Search and Filter Bar */}
          <div className='p-6 border-b border-gray-200'>
            <div className='flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between'>
              <div className='flex-1 max-w-lg'>
                <div className='relative'>
                  <SearchIcon className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5' />
                  <input
                    type='text'
                    placeholder='Search tickets by ID, title, customer, or email...'
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className='w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                  />
                </div>
              </div>

              <div className='flex items-center gap-3'>
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
                      <option value='open'>Open</option>
                      <option value='in_progress'>In Progress</option>
                      <option value='pending'>Pending</option>
                      <option value='resolved'>Resolved</option>
                    </select>
                  </div>

                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-2'>Priority</label>
                    <select className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'>
                      <option value=''>All Priorities</option>
                      <option value='urgent'>Urgent</option>
                      <option value='high'>High</option>
                      <option value='medium'>Medium</option>
                      <option value='low'>Low</option>
                    </select>
                  </div>

                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-2'>Category</label>
                    <select className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'>
                      <option value=''>All Categories</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className='block text-sm font-medium text-gray-700 mb-2'>Assignee</label>
                    <select className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'>
                      <option value=''>All Agents</option>
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.id}>
                          {agent.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Tickets Grid */}
          <div className='p-6'>
            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
              {tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className='cursor-pointer'
                  onClick={() => router.push(`/support/tickets/${ticket.id}`)}
                >
                  <TicketCard ticket={ticket} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {selectedView === 'kanban' && (
        <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
          <KanbanColumn status='open' tickets={ticketsByStatus.open || []} />
          <KanbanColumn status='in_progress' tickets={ticketsByStatus.in_progress || []} />
          <KanbanColumn status='pending' tickets={ticketsByStatus.pending || []} />
          <KanbanColumn status='resolved' tickets={ticketsByStatus.resolved || []} />
        </div>
      )}

      {selectedView === 'agents' && (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}

      {selectedView === 'analytics' && (
        <div className='grid grid-cols-1 lg:grid-cols-2 gap-8'>
          {/* Channel Distribution */}
          <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <h3 className='text-lg font-semibold text-gray-900 mb-4'>Channel Distribution</h3>
            <div className='space-y-4'>
              {metrics.channelDistribution.map((channel) => (
                <div key={channel.channel} className='flex items-center justify-between'>
                  <div className='flex items-center space-x-3'>
                    <div className='w-8 h-8 bg-blue-100 rounded flex items-center justify-center'>
                      {React.createElement(getChannelIcon(channel.channel.toLowerCase()), {
                        className: 'w-4 h-4 text-blue-600',
                      })}
                    </div>
                    <span className='font-medium text-gray-900'>{channel.channel}</span>
                  </div>
                  <div className='flex items-center space-x-3'>
                    <span className='text-sm text-gray-500'>{channel.count} tickets</span>
                    <span className='font-medium text-gray-900'>{channel.percentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Category Breakdown */}
          <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
            <h3 className='text-lg font-semibold text-gray-900 mb-4'>Category Breakdown</h3>
            <div className='space-y-4'>
              {metrics.categoryBreakdown.map((category) => (
                <div key={category.category} className='flex items-center justify-between'>
                  <span className='font-medium text-gray-900'>{category.category}</span>
                  <div className='flex items-center space-x-3'>
                    <span className='text-sm text-gray-500'>{category.count} tickets</span>
                    <span className='font-medium text-gray-900'>{category.percentage}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
