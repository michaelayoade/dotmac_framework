'use client';

import { useState } from 'react';
import { Card } from '@dotmac/primitives';
import {
  Users,
  DollarSign,
  TrendingUp,
  Target,
  Calendar,
  CheckSquare,
  FileText,
  Phone,
  Mail,
  MapPin,
  Clock,
  AlertCircle,
  CheckCircle,
  Plus,
  Filter,
  Search,
  Download,
  Eye,
  Edit,
  ChevronRight,
  BarChart3,
  PieChart,
  Activity
} from 'lucide-react';

interface WorkflowTask {
  id: string;
  title: string;
  description: string;
  category: 'sales' | 'onboarding' | 'support' | 'administrative';
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed' | 'blocked';
  dueDate: string;
  assignee?: string;
  customer?: {
    name: string;
    id: string;
  };
  metadata?: Record<string, any>;
}

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  category: string;
  action: () => void;
}

interface WorkflowMetrics {
  activeTasks: number;
  completedToday: number;
  pendingApprovals: number;
  overdueItems: number;
  conversionRate: number;
  monthlyRevenue: number;
}

export function ConsolidatedWorkflowCenter() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tasks' | 'pipeline' | 'analytics'>('dashboard');
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'sales' | 'onboarding' | 'support' | 'administrative'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Mock data
  const workflowMetrics: WorkflowMetrics = {
    activeTasks: 24,
    completedToday: 8,
    pendingApprovals: 3,
    overdueItems: 2,
    conversionRate: 32.5,
    monthlyRevenue: 145620
  };

  const workflowTasks: WorkflowTask[] = [
    {
      id: 'task_1',
      title: 'Complete customer onboarding for John Smith',
      description: 'Finalize service activation and equipment delivery',
      category: 'onboarding',
      priority: 'high',
      status: 'in_progress',
      dueDate: '2024-02-15',
      customer: { name: 'John Smith', id: 'CUST-001' }
    },
    {
      id: 'task_2',
      title: 'Follow up on quote for ABC Corp',
      description: 'Business fiber internet proposal - $2,500/month',
      category: 'sales',
      priority: 'high',
      status: 'pending',
      dueDate: '2024-02-14',
      customer: { name: 'ABC Corp', id: 'LEAD-456' }
    },
    {
      id: 'task_3',
      title: 'Process commission payment request',
      description: 'January commission - $3,245 pending approval',
      category: 'administrative',
      priority: 'medium',
      status: 'pending',
      dueDate: '2024-02-16'
    },
    {
      id: 'task_4',
      title: 'Resolve billing inquiry - Customer ID: CUST-789',
      description: 'Customer dispute over upgrade charges',
      category: 'support',
      priority: 'medium',
      status: 'in_progress',
      dueDate: '2024-02-13',
      customer: { name: 'Jane Doe', id: 'CUST-789' }
    }
  ];

  const quickActions: QuickAction[] = [
    {
      id: 'add_customer',
      title: 'Add New Customer',
      description: 'Start customer onboarding process',
      icon: Users,
      category: 'sales',
      action: () => console.log('Add customer')
    },
    {
      id: 'create_quote',
      title: 'Create Quote',
      description: 'Generate service quote for prospect',
      icon: FileText,
      category: 'sales',
      action: () => console.log('Create quote')
    },
    {
      id: 'schedule_install',
      title: 'Schedule Installation',
      description: 'Book technician appointment',
      icon: Calendar,
      category: 'onboarding',
      action: () => console.log('Schedule install')
    },
    {
      id: 'view_commissions',
      title: 'View Commission Report',
      description: 'Check earnings and payments',
      icon: DollarSign,
      category: 'administrative',
      action: () => console.log('View commissions')
    },
    {
      id: 'contact_support',
      title: 'Contact Support',
      description: 'Get help from operations team',
      icon: Phone,
      category: 'support',
      action: () => console.log('Contact support')
    },
    {
      id: 'territory_map',
      title: 'View Territory',
      description: 'See coverage area and prospects',
      icon: MapPin,
      category: 'sales',
      action: () => console.log('View territory')
    }
  ];

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low':
        return 'text-green-600 bg-green-50 border-green-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'in_progress':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'blocked':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'pending':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      case 'in_progress':
        return <Clock className="h-4 w-4" />;
      case 'blocked':
        return <AlertCircle className="h-4 w-4" />;
      case 'pending':
        return <Clock className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const filteredTasks = workflowTasks.filter(task => {
    const matchesCategory = selectedCategory === 'all' || task.category === selectedCategory;
    const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         task.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Workflow Center</h1>
        <p className="text-gray-600">Manage your sales pipeline, customer relationships, and daily tasks</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
            { id: 'tasks', label: 'My Tasks', icon: CheckSquare },
            { id: 'pipeline', label: 'Sales Pipeline', icon: TrendingUp },
            { id: 'analytics', label: 'Performance', icon: PieChart }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center border-b-2 px-1 py-4 text-sm font-medium ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                <Icon className="mr-2 h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Dashboard Tab */}
      {activeTab === 'dashboard' && (
        <div className="space-y-6">
          {/* Metrics Cards */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card className="p-6">
              <div className="flex items-center">
                <CheckSquare className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <p className="text-2xl font-bold text-gray-900">{workflowMetrics.activeTasks}</p>
                  <p className="text-gray-600 text-sm">Active Tasks</p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center">
                <CheckCircle className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <p className="text-2xl font-bold text-gray-900">{workflowMetrics.completedToday}</p>
                  <p className="text-gray-600 text-sm">Completed Today</p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center">
                <Target className="h-8 w-8 text-purple-600" />
                <div className="ml-4">
                  <p className="text-2xl font-bold text-gray-900">{workflowMetrics.conversionRate}%</p>
                  <p className="text-gray-600 text-sm">Conversion Rate</p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <div className="flex items-center">
                <DollarSign className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(workflowMetrics.monthlyRevenue)}
                  </p>
                  <p className="text-gray-600 text-sm">Monthly Revenue</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Quick Actions */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Quick Actions</h3>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.id}
                    onClick={action.action}
                    className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50 hover:border-blue-300 transition-colors"
                  >
                    <Icon className="h-6 w-6 text-blue-600 mb-2" />
                    <span className="text-sm font-medium text-center">{action.title}</span>
                  </button>
                );
              })}
            </div>
          </Card>

          {/* Priority Tasks */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Priority Tasks</h3>
              <button
                onClick={() => setActiveTab('tasks')}
                className="text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                View All Tasks →
              </button>
            </div>
            
            <div className="space-y-3">
              {workflowTasks.filter(task => task.priority === 'high').slice(0, 3).map((task) => (
                <div key={task.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                  <div className="flex items-center flex-1">
                    {getStatusIcon(task.status)}
                    <div className="ml-3 flex-1">
                      <p className="font-medium text-gray-900">{task.title}</p>
                      <p className="text-gray-600 text-sm">{task.description}</p>
                      {task.customer && (
                        <p className="text-blue-600 text-xs mt-1">
                          Customer: {task.customer.name}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(task.priority)}`}>
                      {task.priority}
                    </span>
                    <span className="text-gray-500 text-xs">{formatDate(task.dueDate)}</span>
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Tasks Tab */}
      {activeTab === 'tasks' && (
        <div className="space-y-6">
          {/* Filters and Search */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tasks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
            
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as any)}
              className="border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Categories</option>
              <option value="sales">Sales</option>
              <option value="onboarding">Onboarding</option>
              <option value="support">Support</option>
              <option value="administrative">Administrative</option>
            </select>
          </div>

          {/* Task List */}
          <div className="space-y-4">
            {filteredTasks.map((task) => (
              <Card key={task.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start flex-1">
                    <div className="mr-4 mt-1">
                      {getStatusIcon(task.status)}
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900 mb-1">{task.title}</h4>
                      <p className="text-gray-600 text-sm mb-3">{task.description}</p>
                      
                      <div className="flex items-center space-x-4 text-xs">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full font-medium ${getPriorityColor(task.priority)}`}>
                          {task.priority} priority
                        </span>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full font-medium ${getStatusColor(task.status)}`}>
                          {task.status.replace('_', ' ')}
                        </span>
                        <span className="text-gray-500">Due: {formatDate(task.dueDate)}</span>
                        {task.customer && (
                          <span className="text-blue-600">
                            Customer: {task.customer.name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    <button className="p-2 text-gray-400 hover:text-gray-600">
                      <Eye className="h-4 w-4" />
                    </button>
                    <button className="p-2 text-gray-400 hover:text-gray-600">
                      <Edit className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Pipeline Tab */}
      {activeTab === 'pipeline' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Sales Pipeline</h3>
            
            <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
              {[
                { stage: 'Prospects', count: 12, value: '$45,600' },
                { stage: 'Qualified', count: 8, value: '$32,400' },
                { stage: 'Proposal', count: 5, value: '$28,900' },
                { stage: 'Closed', count: 3, value: '$18,500' }
              ].map((stage) => (
                <div key={stage.stage} className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">{stage.stage}</h4>
                  <p className="text-2xl font-bold text-gray-900">{stage.count}</p>
                  <p className="text-gray-600 text-sm">{stage.value}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Monthly Performance</h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">New Customers</span>
                  <span className="font-medium">23</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Revenue Generated</span>
                  <span className="font-medium">{formatCurrency(workflowMetrics.monthlyRevenue)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Commission Earned</span>
                  <span className="font-medium">{formatCurrency(workflowMetrics.monthlyRevenue * 0.15)}</span>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Activity Summary</h3>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Tasks Completed</span>
                  <span className="font-medium">127</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Customer Interactions</span>
                  <span className="font-medium">89</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Quotes Generated</span>
                  <span className="font-medium">34</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}