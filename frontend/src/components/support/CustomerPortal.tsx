/**
 * Customer Support Portal Dashboard
 * Comprehensive self-service interface leveraging DotMac design system
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  Search,
  MessageCircle,
  FileText,
  Clock,
  Star,
  Settings,
  HelpCircle,
  ChevronRight,
  TrendingUp,
  BookOpen,
  Users,
  Zap,
} from 'lucide-react';

// Leverage existing DotMac UI components
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';

// Import support-specific components
import KnowledgeBaseSearch from './KnowledgeBaseSearch';
import TicketList from './TicketList';
import LiveChatWidget from './LiveChatWidget';
import PortalSettings from './PortalSettings';

// Types
interface DashboardStats {
  openTickets: number;
  resolvedTickets: number;
  avgResolutionTime: number;
  knowledgeBaseViews: number;
}

interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType;
  action: () => void;
  color: string;
}

interface PopularArticle {
  id: string;
  title: string;
  category: string;
  views: number;
  helpful_votes: number;
  slug: string;
}

const CustomerPortal: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [searchQuery, setSearchQuery] = useState('');
  const [stats, setStats] = useState<DashboardStats>({
    openTickets: 0,
    resolvedTickets: 0,
    avgResolutionTime: 0,
    knowledgeBaseViews: 0,
  });
  const [popularArticles, setPopularArticles] = useState<PopularArticle[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Quick actions configuration
  const quickActions: QuickAction[] = [
    {
      id: 'new-ticket',
      title: 'Create Support Ticket',
      description: 'Get help with technical issues or account questions',
      icon: FileText,
      color: 'bg-blue-500',
      action: () => setActiveTab('tickets'),
    },
    {
      id: 'live-chat',
      title: 'Start Live Chat',
      description: 'Chat with our support team in real-time',
      icon: MessageCircle,
      color: 'bg-green-500',
      action: () => {
        // This would open the chat widget
        const chatWidget = document.getElementById('live-chat-widget');
        if (chatWidget) {
          chatWidget.click();
        }
      },
    },
    {
      id: 'knowledge-base',
      title: 'Browse Knowledge Base',
      description: 'Find answers in our comprehensive help articles',
      icon: BookOpen,
      color: 'bg-purple-500',
      action: () => setActiveTab('knowledge'),
    },
    {
      id: 'account-settings',
      title: 'Account Settings',
      description: 'Manage your account and notification preferences',
      icon: Settings,
      color: 'bg-orange-500',
      action: () => setActiveTab('settings'),
    },
  ];

  // Fetch dashboard data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);

        // Fetch user stats (would be real API calls)
        const [statsResponse, articlesResponse] = await Promise.all([
          // fetch('/api/customer/dashboard-stats'),
          // fetch('/api/knowledge/articles/popular?limit=5')
          Promise.resolve({
            json: () =>
              Promise.resolve({
                openTickets: 2,
                resolvedTickets: 8,
                avgResolutionTime: 24,
                knowledgeBaseViews: 15,
              }),
          }),
          Promise.resolve({
            json: () =>
              Promise.resolve([
                {
                  id: '1',
                  title: 'How to Reset Your Password',
                  category: 'Account Management',
                  views: 1234,
                  helpful_votes: 89,
                  slug: 'reset-password',
                },
                {
                  id: '2',
                  title: 'Setting Up Email on Mobile',
                  category: 'Technical Support',
                  views: 987,
                  helpful_votes: 76,
                  slug: 'email-mobile-setup',
                },
                {
                  id: '3',
                  title: 'Understanding Your Bill',
                  category: 'Billing',
                  views: 756,
                  helpful_votes: 63,
                  slug: 'understanding-bill',
                },
              ]),
          }),
        ]);

        const statsData = await statsResponse.json();
        const articlesData = await articlesResponse.json();

        setStats(statsData);
        setPopularArticles(articlesData);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setActiveTab('knowledge');
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    description: string;
    icon: React.ComponentType;
    trend?: number;
  }> = ({ title, value, description, icon: Icon, trend }) => (
    <Card>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium'>{title}</CardTitle>
        <Icon className='h-4 w-4 text-muted-foreground' />
      </CardHeader>
      <CardContent>
        <div className='text-2xl font-bold'>{value}</div>
        <p className='text-xs text-muted-foreground'>
          {description}
          {trend && (
            <span className={`ml-1 ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend > 0 ? '+' : ''}
              {trend}%
            </span>
          )}
        </p>
      </CardContent>
    </Card>
  );

  if (isLoading) {
    return (
      <div className='flex items-center justify-center min-h-screen'>
        <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600'></div>
      </div>
    );
  }

  return (
    <div className='container mx-auto px-4 py-6 max-w-7xl'>
      <div className='mb-8'>
        <h1 className='text-3xl font-bold text-gray-900 mb-2'>Support Portal</h1>
        <p className='text-gray-600'>Get help, find answers, and manage your support requests</p>
      </div>

      {/* Global Search Bar */}
      <div className='mb-8'>
        <div className='relative max-w-md'>
          <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4' />
          <Input
            type='text'
            placeholder='Search for help articles, tickets, or ask a question...'
            className='pl-10 pr-4'
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
          />
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className='space-y-6'>
        <TabsList className='grid w-full grid-cols-5'>
          <TabsTrigger value='dashboard'>Dashboard</TabsTrigger>
          <TabsTrigger value='knowledge'>Knowledge Base</TabsTrigger>
          <TabsTrigger value='tickets'>My Tickets</TabsTrigger>
          <TabsTrigger value='chat'>Live Chat</TabsTrigger>
          <TabsTrigger value='settings'>Settings</TabsTrigger>
        </TabsList>

        {/* Dashboard Tab */}
        <TabsContent value='dashboard' className='space-y-6'>
          {/* Stats Overview */}
          <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
            <StatCard
              title='Open Tickets'
              value={stats.openTickets}
              description='Active support requests'
              icon={Clock}
            />
            <StatCard
              title='Resolved Tickets'
              value={stats.resolvedTickets}
              description='Successfully closed tickets'
              icon={FileText}
              trend={12}
            />
            <StatCard
              title='Avg Resolution Time'
              value={`${stats.avgResolutionTime}h`}
              description='Average time to resolve'
              icon={TrendingUp}
              trend={-8}
            />
            <StatCard
              title='Help Articles Viewed'
              value={stats.knowledgeBaseViews}
              description="Articles you've accessed"
              icon={BookOpen}
            />
          </div>

          {/* Quick Actions */}
          <div>
            <h2 className='text-xl font-semibold mb-4'>Quick Actions</h2>
            <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
              {quickActions.map((action) => (
                <Card
                  key={action.id}
                  className='cursor-pointer hover:shadow-lg transition-shadow'
                  onClick={action.action}
                >
                  <CardContent className='p-6'>
                    <div className={`inline-flex p-3 rounded-lg ${action.color} text-white mb-4`}>
                      <action.icon className='h-6 w-6' />
                    </div>
                    <h3 className='font-semibold mb-2'>{action.title}</h3>
                    <p className='text-sm text-gray-600'>{action.description}</p>
                    <ChevronRight className='h-4 w-4 mt-2 text-gray-400' />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Popular Articles */}
          <div>
            <div className='flex justify-between items-center mb-4'>
              <h2 className='text-xl font-semibold'>Popular Help Articles</h2>
              <Button
                variant='ghost'
                onClick={() => setActiveTab('knowledge')}
                className='text-blue-600 hover:text-blue-700'
              >
                View All Articles <ChevronRight className='h-4 w-4 ml-1' />
              </Button>
            </div>
            <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
              {popularArticles.map((article) => (
                <Card key={article.id} className='hover:shadow-md transition-shadow cursor-pointer'>
                  <CardContent className='p-4'>
                    <Badge variant='secondary' className='mb-2'>
                      {article.category}
                    </Badge>
                    <h3 className='font-medium mb-2 line-clamp-2'>{article.title}</h3>
                    <div className='flex items-center justify-between text-sm text-gray-500'>
                      <div className='flex items-center space-x-2'>
                        <Users className='h-3 w-3' />
                        <span>{article.views.toLocaleString()} views</span>
                      </div>
                      <div className='flex items-center space-x-1'>
                        <Star className='h-3 w-3 fill-yellow-400 text-yellow-400' />
                        <span>{article.helpful_votes}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Your latest support interactions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className='space-y-3'>
                <div className='flex items-center space-x-3'>
                  <div className='bg-blue-100 p-2 rounded-full'>
                    <FileText className='h-4 w-4 text-blue-600' />
                  </div>
                  <div className='flex-1'>
                    <p className='text-sm font-medium'>Created support ticket #12345</p>
                    <p className='text-xs text-gray-500'>2 hours ago</p>
                  </div>
                </div>
                <div className='flex items-center space-x-3'>
                  <div className='bg-green-100 p-2 rounded-full'>
                    <MessageCircle className='h-4 w-4 text-green-600' />
                  </div>
                  <div className='flex-1'>
                    <p className='text-sm font-medium'>Completed live chat session</p>
                    <p className='text-xs text-gray-500'>1 day ago</p>
                  </div>
                </div>
                <div className='flex items-center space-x-3'>
                  <div className='bg-purple-100 p-2 rounded-full'>
                    <BookOpen className='h-4 w-4 text-purple-600' />
                  </div>
                  <div className='flex-1'>
                    <p className='text-sm font-medium'>Viewed "Email Setup Guide"</p>
                    <p className='text-xs text-gray-500'>2 days ago</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Knowledge Base Tab */}
        <TabsContent value='knowledge'>
          <KnowledgeBaseSearch initialQuery={searchQuery} />
        </TabsContent>

        {/* Tickets Tab */}
        <TabsContent value='tickets'>
          <TicketList />
        </TabsContent>

        {/* Chat Tab */}
        <TabsContent value='chat'>
          <Card>
            <CardHeader>
              <CardTitle>Live Chat Support</CardTitle>
              <CardDescription>
                Connect with our support team for real-time assistance
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='text-center py-8'>
                <MessageCircle className='h-16 w-16 text-gray-400 mx-auto mb-4' />
                <h3 className='text-lg font-medium mb-2'>Start a Conversation</h3>
                <p className='text-gray-600 mb-6'>
                  Our support team is available to help you with any questions or issues.
                </p>
                <Button
                  onClick={() => {
                    // Initialize live chat
                    const chatWidget = document.getElementById('live-chat-widget');
                    if (chatWidget) {
                      chatWidget.click();
                    }
                  }}
                >
                  <MessageCircle className='h-4 w-4 mr-2' />
                  Start Chat
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value='settings'>
          <PortalSettings />
        </TabsContent>
      </Tabs>

      {/* Live Chat Widget - Always available */}
      <LiveChatWidget />
    </div>
  );
};

export default CustomerPortal;
