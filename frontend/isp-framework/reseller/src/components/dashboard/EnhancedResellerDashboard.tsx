'use client';

import React from 'react';
import { clsx } from 'clsx';
import {
  TrendingUp,
  Users,
  DollarSign,
  Target,
  UserCheck,
  Megaphone,
  Handshake,
  Calendar,
  Bell,
  ArrowRight,
  Plus,
  Star,
  Clock,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import Link from 'next/link';

interface DashboardStats {
  totalLeads: number;
  qualifiedLeads: number;
  activeProjects: number;
  monthlyRevenue: number;
  conversionRate: number;
  marketingResources: number;
}

const dashboardStats: DashboardStats = {
  totalLeads: 127,
  qualifiedLeads: 34,
  activeProjects: 8,
  monthlyRevenue: 145000,
  conversionRate: 23.5,
  marketingResources: 45,
};

interface RecentActivity {
  id: string;
  type: 'lead' | 'project' | 'marketing' | 'collaboration';
  title: string;
  description: string;
  timestamp: string;
  priority: 'low' | 'medium' | 'high';
}

const recentActivities: RecentActivity[] = [
  {
    id: '1',
    type: 'lead',
    title: 'New qualified lead: Tech Solutions Inc',
    description: 'Enterprise client interested in fiber internet for 3 locations',
    timestamp: '2025-08-29T10:30:00Z',
    priority: 'high',
  },
  {
    id: '2',
    type: 'collaboration',
    title: 'Project update: Acme Corp Deployment',
    description: 'Technical specifications approved, moving to implementation phase',
    timestamp: '2025-08-29T09:15:00Z',
    priority: 'medium',
  },
  {
    id: '3',
    type: 'marketing',
    title: 'New marketing campaign launched',
    description: 'Q4 Small Business Outreach campaign is now live',
    timestamp: '2025-08-28T16:45:00Z',
    priority: 'medium',
  },
];

export function EnhancedResellerDashboard() {
  const getActivityIcon = (type: RecentActivity['type']) => {
    const icons = {
      lead: UserCheck,
      project: Handshake,
      marketing: Megaphone,
      collaboration: Users,
    };
    return icons[type] || Bell;
  };

  const getPriorityColor = (priority: RecentActivity['priority']) => {
    const colors = {
      low: 'text-gray-500',
      medium: 'text-yellow-500',
      high: 'text-red-500',
    };
    return colors[priority];
  };

  return (
    <div className='space-y-6'>
      {/* Welcome Header */}
      <div className='bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg p-6 text-white'>
        <h1 className='text-2xl font-bold mb-2'>Welcome back, Partner!</h1>
        <p className='text-blue-100'>
          Here's what's happening with your sales and partnerships today
        </p>
      </div>

      {/* Quick Stats */}
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
        <Link href='/leads' className='group'>
          <div className='bg-white rounded-lg p-6 shadow-sm border hover:shadow-md transition-all group-hover:border-blue-500'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm text-gray-600'>Total Leads</p>
                <p className='text-2xl font-bold text-gray-900'>{dashboardStats.totalLeads}</p>
                <p className='text-sm text-green-600 mt-1'>
                  {dashboardStats.qualifiedLeads} qualified
                </p>
              </div>
              <UserCheck className='w-8 h-8 text-blue-500 group-hover:scale-110 transition-transform' />
            </div>
          </div>
        </Link>

        <Link href='/collaboration' className='group'>
          <div className='bg-white rounded-lg p-6 shadow-sm border hover:shadow-md transition-all group-hover:border-purple-500'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm text-gray-600'>Active Projects</p>
                <p className='text-2xl font-bold text-gray-900'>{dashboardStats.activeProjects}</p>
                <p className='text-sm text-purple-600 mt-1'>3 with partners</p>
              </div>
              <Handshake className='w-8 h-8 text-purple-500 group-hover:scale-110 transition-transform' />
            </div>
          </div>
        </Link>

        <Link href='/marketing' className='group'>
          <div className='bg-white rounded-lg p-6 shadow-sm border hover:shadow-md transition-all group-hover:border-green-500'>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm text-gray-600'>Marketing Resources</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {dashboardStats.marketingResources}
                </p>
                <p className='text-sm text-green-600 mt-1'>12 new this month</p>
              </div>
              <Megaphone className='w-8 h-8 text-green-500 group-hover:scale-110 transition-transform' />
            </div>
          </div>
        </Link>

        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm text-gray-600'>Monthly Revenue</p>
              <p className='text-2xl font-bold text-gray-900'>
                ${dashboardStats.monthlyRevenue.toLocaleString()}
              </p>
              <p className='text-sm text-green-600 mt-1'>+12% from last month</p>
            </div>
            <DollarSign className='w-8 h-8 text-green-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm text-gray-600'>Conversion Rate</p>
              <p className='text-2xl font-bold text-gray-900'>{dashboardStats.conversionRate}%</p>
              <p className='text-sm text-green-600 mt-1'>+3.2% from last month</p>
            </div>
            <Target className='w-8 h-8 text-orange-500' />
          </div>
        </div>

        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm text-gray-600'>Team Performance</p>
              <p className='text-2xl font-bold text-gray-900'>92%</p>
              <p className='text-sm text-green-600 mt-1'>Above target</p>
            </div>
            <TrendingUp className='w-8 h-8 text-blue-500' />
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className='bg-white rounded-lg p-6 shadow-sm border'>
        <div className='flex items-center justify-between mb-4'>
          <h2 className='text-lg font-semibold text-gray-900'>Quick Actions</h2>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
          <Link href='/leads' className='group'>
            <div className='border rounded-lg p-4 hover:shadow-md transition-all group-hover:border-blue-500'>
              <div className='flex items-center space-x-3'>
                <div className='w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors'>
                  <Plus className='w-5 h-5 text-blue-600' />
                </div>
                <div>
                  <div className='font-medium text-gray-900'>Add New Lead</div>
                  <div className='text-sm text-gray-500'>Create lead record</div>
                </div>
              </div>
            </div>
          </Link>

          <Link href='/collaboration' className='group'>
            <div className='border rounded-lg p-4 hover:shadow-md transition-all group-hover:border-purple-500'>
              <div className='flex items-center space-x-3'>
                <div className='w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center group-hover:bg-purple-200 transition-colors'>
                  <Handshake className='w-5 h-5 text-purple-600' />
                </div>
                <div>
                  <div className='font-medium text-gray-900'>Start Project</div>
                  <div className='text-sm text-gray-500'>New collaboration</div>
                </div>
              </div>
            </div>
          </Link>

          <Link href='/marketing' className='group'>
            <div className='border rounded-lg p-4 hover:shadow-md transition-all group-hover:border-green-500'>
              <div className='flex items-center space-x-3'>
                <div className='w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition-colors'>
                  <Megaphone className='w-5 h-5 text-green-600' />
                </div>
                <div>
                  <div className='font-medium text-gray-900'>Browse Resources</div>
                  <div className='text-sm text-gray-500'>Marketing materials</div>
                </div>
              </div>
            </div>
          </Link>

          <Link href='/sales-tools' className='group'>
            <div className='border rounded-lg p-4 hover:shadow-md transition-all group-hover:border-orange-500'>
              <div className='flex items-center space-x-3'>
                <div className='w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center group-hover:bg-orange-200 transition-colors'>
                  <Target className='w-5 h-5 text-orange-600' />
                </div>
                <div>
                  <div className='font-medium text-gray-900'>Create Quote</div>
                  <div className='text-sm text-gray-500'>Generate proposal</div>
                </div>
              </div>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent Activity & Upcoming Tasks */}
      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        {/* Recent Activity */}
        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between mb-4'>
            <h2 className='text-lg font-semibold text-gray-900'>Recent Activity</h2>
            <button className='text-blue-600 hover:text-blue-700 text-sm font-medium'>
              View All
            </button>
          </div>

          <div className='space-y-4'>
            {recentActivities.map((activity) => {
              const Icon = getActivityIcon(activity.type);
              return (
                <div key={activity.id} className='flex items-start space-x-3'>
                  <div className='w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0'>
                    <Icon className='w-4 h-4 text-gray-600' />
                  </div>
                  <div className='flex-1 min-w-0'>
                    <div className='flex items-center space-x-2'>
                      <span className='font-medium text-gray-900'>{activity.title}</span>
                      <div
                        className={clsx(
                          'w-2 h-2 rounded-full',
                          getPriorityColor(activity.priority)
                        )}
                      >
                        <div className='w-full h-full rounded-full bg-current' />
                      </div>
                    </div>
                    <p className='text-sm text-gray-600 mt-1'>{activity.description}</p>
                    <p className='text-xs text-gray-500 mt-1'>
                      {new Date(activity.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Upcoming Tasks */}
        <div className='bg-white rounded-lg p-6 shadow-sm border'>
          <div className='flex items-center justify-between mb-4'>
            <h2 className='text-lg font-semibold text-gray-900'>Upcoming Tasks</h2>
            <Link
              href='/collaboration'
              className='text-blue-600 hover:text-blue-700 text-sm font-medium'
            >
              Manage Tasks
            </Link>
          </div>

          <div className='space-y-3'>
            <div className='flex items-center space-x-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200'>
              <Clock className='w-4 h-4 text-yellow-600 flex-shrink-0' />
              <div className='flex-1'>
                <div className='font-medium text-gray-900'>Follow up with Acme Corp</div>
                <div className='text-sm text-gray-600'>Send updated proposal</div>
                <div className='text-xs text-yellow-600 mt-1'>Due: Today, 3:00 PM</div>
              </div>
            </div>

            <div className='flex items-center space-x-3 p-3 bg-blue-50 rounded-lg border border-blue-200'>
              <Calendar className='w-4 h-4 text-blue-600 flex-shrink-0' />
              <div className='flex-1'>
                <div className='font-medium text-gray-900'>Partner meeting: Tech Alliance</div>
                <div className='text-sm text-gray-600'>Discuss Q4 marketing strategy</div>
                <div className='text-xs text-blue-600 mt-1'>Tomorrow, 10:00 AM</div>
              </div>
            </div>

            <div className='flex items-center space-x-3 p-3 bg-green-50 rounded-lg border border-green-200'>
              <CheckCircle className='w-4 h-4 text-green-600 flex-shrink-0' />
              <div className='flex-1'>
                <div className='font-medium text-gray-900'>Review training materials</div>
                <div className='text-sm text-gray-600'>Advanced networking course content</div>
                <div className='text-xs text-green-600 mt-1'>Due: Aug 31</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Overview */}
      <div className='bg-white rounded-lg p-6 shadow-sm border'>
        <div className='flex items-center justify-between mb-6'>
          <h2 className='text-lg font-semibold text-gray-900'>Performance Overview</h2>
          <Link
            href='/sales'
            className='text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center space-x-1'
          >
            <span>View Details</span>
            <ArrowRight className='w-4 h-4' />
          </Link>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
          {/* Lead Funnel */}
          <div>
            <h3 className='font-medium text-gray-900 mb-3'>Lead Funnel</h3>
            <div className='space-y-2'>
              <div className='flex items-center justify-between text-sm'>
                <span className='text-gray-600'>Total Leads</span>
                <span className='font-medium'>{dashboardStats.totalLeads}</span>
              </div>
              <div className='flex items-center justify-between text-sm'>
                <span className='text-gray-600'>Qualified</span>
                <span className='font-medium text-blue-600'>{dashboardStats.qualifiedLeads}</span>
              </div>
              <div className='flex items-center justify-between text-sm'>
                <span className='text-gray-600'>In Progress</span>
                <span className='font-medium text-orange-600'>18</span>
              </div>
              <div className='flex items-center justify-between text-sm'>
                <span className='text-gray-600'>Closed Won</span>
                <span className='font-medium text-green-600'>12</span>
              </div>
            </div>
          </div>

          {/* Monthly Progress */}
          <div>
            <h3 className='font-medium text-gray-900 mb-3'>Monthly Progress</h3>
            <div className='space-y-3'>
              <div>
                <div className='flex justify-between text-sm mb-1'>
                  <span className='text-gray-600'>Revenue Goal</span>
                  <span className='font-medium'>85%</span>
                </div>
                <div className='w-full bg-gray-200 rounded-full h-2'>
                  <div className='bg-green-600 h-2 rounded-full' style={{ width: '85%' }} />
                </div>
              </div>

              <div>
                <div className='flex justify-between text-sm mb-1'>
                  <span className='text-gray-600'>New Leads</span>
                  <span className='font-medium'>92%</span>
                </div>
                <div className='w-full bg-gray-200 rounded-full h-2'>
                  <div className='bg-blue-600 h-2 rounded-full' style={{ width: '92%' }} />
                </div>
              </div>
            </div>
          </div>

          {/* Top Performers */}
          <div>
            <h3 className='font-medium text-gray-900 mb-3'>Top Opportunities</h3>
            <div className='space-y-2'>
              <div className='flex items-center justify-between text-sm'>
                <span className='text-gray-600'>Enterprise Fiber Deal</span>
                <span className='font-medium text-green-600'>$250K</span>
              </div>
              <div className='flex items-center justify-between text-sm'>
                <span className='text-gray-600'>Regional Expansion</span>
                <span className='font-medium text-blue-600'>$2M</span>
              </div>
              <div className='flex items-center justify-between text-sm'>
                <span className='text-gray-600'>SMB Campaign</span>
                <span className='font-medium text-purple-600'>$75K</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Items */}
      <div className='bg-white rounded-lg p-6 shadow-sm border'>
        <div className='flex items-center justify-between mb-4'>
          <h2 className='text-lg font-semibold text-gray-900'>Priority Action Items</h2>
          <span className='text-sm text-gray-500'>3 items need attention</span>
        </div>

        <div className='space-y-3'>
          <div className='flex items-center space-x-3 p-3 bg-red-50 rounded-lg border border-red-200'>
            <AlertTriangle className='w-5 h-5 text-red-600 flex-shrink-0' />
            <div className='flex-1'>
              <div className='font-medium text-gray-900'>Overdue: TechCorp proposal review</div>
              <div className='text-sm text-red-600'>Due 2 days ago</div>
            </div>
            <Link
              href='/leads'
              className='bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 transition-colors'
            >
              Review Now
            </Link>
          </div>

          <div className='flex items-center space-x-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200'>
            <Clock className='w-5 h-5 text-yellow-600 flex-shrink-0' />
            <div className='flex-1'>
              <div className='font-medium text-gray-900'>Update project status</div>
              <div className='text-sm text-yellow-600'>Acme Corp deployment milestone</div>
            </div>
            <Link
              href='/collaboration'
              className='bg-yellow-600 text-white px-3 py-1 rounded text-sm hover:bg-yellow-700 transition-colors'
            >
              Update
            </Link>
          </div>

          <div className='flex items-center space-x-3 p-3 bg-blue-50 rounded-lg border border-blue-200'>
            <Star className='w-5 h-5 text-blue-600 flex-shrink-0' />
            <div className='flex-1'>
              <div className='font-medium text-gray-900'>New marketing campaign available</div>
              <div className='text-sm text-blue-600'>Q4 5G promotion materials ready</div>
            </div>
            <Link
              href='/marketing'
              className='bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors'
            >
              Explore
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
